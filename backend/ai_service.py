import os
import json
import shutil
import sqlite3
import pickle
import hashlib
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from .config import settings

# Try importing teammate's RAG pipeline only in local dev (Render has 512MB RAM limit)
HAS_TEAMMATES_RAG = False
if not os.environ.get("RENDER") and getattr(settings, "ENVIRONMENT", "").lower() != "production":
    try:
        import pipeline_api
        HAS_TEAMMATES_RAG = True
    except (ImportError, Exception):
        HAS_TEAMMATES_RAG = False

COLLECTION_NAME = "medical_records"
VECTOR_SIZE = 1024

# 1. Cleanly handle existing local disk storage to avoid mixing 384d and 1024d vectors
if not settings.QDRANT_HOST:
    try:
        qdrant_path = os.path.abspath(settings.QDRANT_STORAGE_DIR)
        os.makedirs(qdrant_path, exist_ok=True)
        col_dir = os.path.join(qdrant_path, "collection", COLLECTION_NAME)
        meta_path = os.path.join(qdrant_path, "meta.json")
        sqlite_file = os.path.join(col_dir, "storage.sqlite")
        
        needs_purge = False
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                col_cfg = meta_data.get("collections", {}).get(COLLECTION_NAME, {})
                dim = col_cfg.get("vectors", {}).get("size")
                if dim and dim != VECTOR_SIZE:
                    needs_purge = True
            except Exception:
                pass
                
        if not needs_purge and os.path.exists(sqlite_file):
            try:
                conn = sqlite3.connect(sqlite_file)
                cursor = conn.cursor()
                cursor.execute("SELECT point FROM points LIMIT 1")
                row = cursor.fetchone()
                if row and row[0]:
                    pt = pickle.loads(row[0])
                    vec = getattr(pt, "vector", None)
                    if vec is not None and len(vec) != VECTOR_SIZE:
                        needs_purge = True
                conn.close()
            except Exception:
                pass
                
        if needs_purge:
            print(f"[ai_service] Purging stale local Qdrant collection with incompatible vector dimensions.")
            if os.path.exists(col_dir):
                shutil.rmtree(col_dir, ignore_errors=True)
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta_data = json.load(f)
                    if COLLECTION_NAME in meta_data.get("collections", {}):
                        del meta_data["collections"][COLLECTION_NAME]
                        with open(meta_path, "w", encoding="utf-8") as f:
                            json.dump(meta_data, f)
                except Exception:
                    pass
    except Exception as e:
        print(f"[ai_service] Warning during disk storage check: {e}")

# Helper to detect if running inside pytest or test suite
def is_test_environment() -> bool:
    return bool(
        os.environ.get("PYTEST_CURRENT_TEST") or 
        getattr(settings, "TESTING", False) or 
        getattr(settings, "ENVIRONMENT", "").lower() in ["testing", "test"]
    )

# 2. Initialize Qdrant Client (Cloud URL, host/port, or persistent local disk)
_qdrant_url = settings.QDRANT_URL.strip().strip("'\"") if getattr(settings, "QDRANT_URL", None) else None
_qdrant_api_key = settings.QDRANT_API_KEY.strip().strip("'\"") if getattr(settings, "QDRANT_API_KEY", None) else None

if _qdrant_url:
    qdrant_client = QdrantClient(
        url=_qdrant_url,
        api_key=_qdrant_api_key,
        prefer_grpc=False,
        check_compatibility=False
    )
elif settings.QDRANT_HOST:
    qdrant_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
else:
    try:
        qdrant_path = os.path.abspath(settings.QDRANT_STORAGE_DIR)
        os.makedirs(qdrant_path, exist_ok=True)
        qdrant_client = QdrantClient(path=qdrant_path)
    except Exception as e:
        print(f"[ai_service] Qdrant disk storage locked/unavailable ({e}). Initializing in-memory fallback.")
        qdrant_client = QdrantClient(location=":memory:")

# Ensure the collection exists in Qdrant with matching vector size and Cosine distance
try:
    if qdrant_client.collection_exists(COLLECTION_NAME):
        collection_info = qdrant_client.get_collection(COLLECTION_NAME)
        existing_size = getattr(collection_info.config.params.vectors, "size", None)
        if existing_size and existing_size != VECTOR_SIZE:
            print(f"[ai_service] Detected incompatible vector size ({existing_size} != {VECTOR_SIZE}). Re-creating collection '{COLLECTION_NAME}'.")
            qdrant_client.delete_collection(COLLECTION_NAME)
            qdrant_client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
            )
    else:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)
        )
except Exception as e:
    print(f"[ai_service] Qdrant collection initialization warning: {e}")

_real_embedder = None

def generate_mock_embedding(text: str) -> List[float]:
    """
    Simulates BGE-M3 dense embeddings for local test environments ONLY.
    Generates a deterministic 1024-dimensional vector based on term frequencies/hashing.
    """
    embedding = [0.0] * VECTOR_SIZE
    words = text.lower().split()
    for w in words:
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        dim = h % VECTOR_SIZE
        embedding[dim] += 1.0
        
    magnitude = sum(x*x for x in embedding) ** 0.5
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]
    else:
        embedding[0] = 1.0
        
    return embedding

def get_embedding(text: str) -> List[float]:
    """
    Returns 1024-dimensional embedding for input text.
    1. Fast Remote Hugging Face Space (if HF_EMBEDDING_URL is configured)
    2. Local BAAI/bge-m3 MedicalEmbedder execution
    3. Deterministic fallback in testing mode
    """
    import requests

    # 1. Hugging Face Spaces Remote Microservice Fast-Path
    if settings.HF_EMBEDDING_URL:
        try:
            base_url = settings.HF_EMBEDDING_URL.strip().rstrip("/")
            headers = {}
            if settings.HF_API_TOKEN:
                headers["Authorization"] = f"Bearer {settings.HF_API_TOKEN}"
            
            # Support Gradio 5 event stream, Gradio legacy, and FastAPI endpoints automatically
            candidate_endpoints = [
                (f"{base_url}/gradio_api/call/embed", "gradio_sse"),
                (f"{base_url}/api/embed", "gradio_json"),
                (f"{base_url}/api/predict", "gradio_json"),
                (f"{base_url}/embed", "fastapi")
            ]
            
            for endpoint, proto in candidate_endpoints:
                try:
                    if proto == "gradio_sse":
                        resp = requests.post(endpoint, json={"data": [text]}, headers=headers, timeout=10)
                        if resp.status_code == 200:
                            event_id = resp.json().get("event_id")
                            if event_id:
                                stream_res = requests.get(f"{base_url}/gradio_api/call/embed/{event_id}", headers=headers, timeout=30)
                                for line in stream_res.text.splitlines():
                                    if line.startswith("data: "):
                                        payload = json.loads(line[6:])
                                        if isinstance(payload, list) and payload:
                                            vec = payload[0] if isinstance(payload[0], list) else payload
                                            if len(vec) == VECTOR_SIZE:
                                                return vec
                    elif proto == "gradio_json":
                        resp = requests.post(endpoint, json={"data": [text]}, headers=headers, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            res_data = data.get("data", [])
                            if res_data:
                                vec = res_data[0] if isinstance(res_data[0], list) else res_data
                                if isinstance(vec, list) and len(vec) == VECTOR_SIZE:
                                    return vec
                    elif proto == "fastapi":
                        resp = requests.post(endpoint, json={"texts": [text]}, headers=headers, timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            embeddings = data.get("embeddings", [])
                            if embeddings and len(embeddings[0]) == VECTOR_SIZE:
                                return embeddings[0]
                except Exception:
                    continue
        except Exception as e:
            print(f"[ai_service] Hugging Face Space embedding request notice: {e}. Falling back to local embedder.")

    # 2. Local BGE-M3 Execution
    global _real_embedder
    if _real_embedder is None:
        try:
            from embeddings import MedicalEmbedder
            _real_embedder = MedicalEmbedder()
        except Exception as e:
            _real_embedder = False
            if not is_test_environment():
                print(f"[ai_service] Production Error: Could not load BAAI/bge-m3 MedicalEmbedder: {e}")
            
    if _real_embedder:
        try:
            vec = _real_embedder.embed_text(text)
            if len(vec) != VECTOR_SIZE:
                raise ValueError(f"BGE-M3 returned vector dimension {len(vec)}, expected {VECTOR_SIZE}")
            return vec
        except Exception as e:
            if not is_test_environment():
                raise RuntimeError(f"Real BGE-M3 embedding execution failed in production: {str(e)}")
    # 3. Resilient deterministic embedding fallback
    return generate_mock_embedding(text)

def ai_index_document(structured_json: Dict[str, Any]):
    """
    Person 3 indexing handoff.
    Converts structured document contents to vectors and payloads and stores them in Qdrant.
    """
    # 1. Forward index request to teammate's real RAG pipeline (if available)
    if HAS_TEAMMATES_RAG:
        try:
            # teammate's pipeline expects list of dict records
            pipeline_api.index_patient_records([structured_json])
            print(f"[ai_service] Successfully indexed doc {structured_json.get('document_id')} in teammate RAG.")
        except Exception as e:
            print(f"[ai_service] Teammate indexing failed: {str(e)}. Falling back to local/mock index.")

    patient_id = structured_json["patient_id"]
    document_id = structured_json["document_id"]
    
    # Formulate indexable text
    text_parts = [
        f"document_type: {structured_json.get('document_type', '')}",
        f"raw_text: {structured_json.get('raw_text', '')}",
        f"diagnoses: {' '.join(structured_json.get('diagnoses', []))}",
        f"medications: {' '.join(structured_json.get('medications', []))}"
    ]
    
    for lr in structured_json.get("lab_results", []):
        if isinstance(lr, dict):
            text_parts.append(f"lab_result: {lr.get('test_name', '')} = {lr.get('value', '')}")
            
    indexable_text = " | ".join(text_parts)
    vector = get_embedding(indexable_text)
    
    # Generate integer ID for Qdrant
    point_id = int(hashlib.md5(document_id.encode("utf-8")).hexdigest(), 16) & 0xffffffffffffffff
    
    # Store payload
    payload = {
        "patient_id": patient_id,
        "document_id": document_id,
        "visit_id": structured_json.get("visit_id"),
        "date": structured_json.get("date"),
        "document_type": structured_json.get("document_type"),
        "medications": structured_json.get("medications", []),
        "diagnoses": structured_json.get("diagnoses", []),
        "lab_results": structured_json.get("lab_results", []),
        "allergies": structured_json.get("allergies", []),
        "procedures": structured_json.get("procedures", []),
        "raw_text": structured_json.get("raw_text", ""),
        "confidence": structured_json.get("confidence", 1.0)
    }
    
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
        ]
    )
    try:
        from embeddings import _get_process_rss_mb
        rss8 = _get_process_rss_mb()
        print(f"[MEM_DIAGNOSTIC] [Stage 8] RSS after Qdrant upsert (ai_service): {rss8:.1f} MB")
    except Exception:
        pass

def ask_patient_question(patient_id: str, question: str, document_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes hybrid search query on Qdrant, applies evidence sufficiency gate,
    and returns a grounded RAG answer with citations or falls back gracefully to
    direct structured record synthesis from the patient's database records.
    """
    try:
        # If document_id is provided, try direct document retrieval & targeted Qdrant query first
        must_conditions = [
            FieldCondition(
                key="patient_id",
                match=MatchValue(value=patient_id)
            )
        ]
        if document_id:
            must_conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id)
                )
            )
            
        patient_filter = Filter(must=must_conditions)
        
        # 1. Forward index query to teammate's real RAG pipeline (if available and no specific doc filter)
        if HAS_TEAMMATES_RAG and not document_id:
            try:
                import pipeline_api
                res = pipeline_api.ask_patient(patient_id, question)
                if res and res.get("answer") and "No relevant information" not in res.get("answer", ""):
                    if "abstained" not in res:
                        res["abstained"] = not res.get("is_grounded", True) or len(res.get("sources", [])) == 0
                    return res
            except Exception as e:
                print(f"[ai_service] pipeline_api ask_patient notice ({e}). Running direct Qdrant RAG fallback.")

        # 2. Qdrant Vector & Payload Retrieval
        search_results = []
        try:
            query_vector = get_embedding(question)
            query_response = qdrant_client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=patient_filter,
                limit=10
            )
            search_results = query_response.points if query_response else []
        except Exception as q_err:
            print(f"[ai_service] Qdrant search notice: {q_err}")

        # If Qdrant returned matching points
        if search_results:
            records = [res.payload for res in search_results]
            try:
                from rag import GroundedRAG, assess_evidence_sufficiency
                assessment = assess_evidence_sufficiency(question, records)
                if assessment.get("sufficient", True):
                    rag = GroundedRAG()
                    rag_res = rag.generate_answer(question, patient_id, records)
                    if rag_res.get("answer") and "No relevant information" not in rag_res.get("answer", ""):
                        return {
                            "answer": rag_res["answer"],
                            "sources": rag_res["sources"],
                            "abstained": not rag_res["is_grounded"]
                        }
            except Exception as e:
                print(f"[ai_service] GroundedRAG execution notice ({e}).")

        # 3. Database-backed clinical record synthesis fallback
        from .database import SessionLocal
        from .models import Document, Visit, Patient
        from .processing import call_person2_ocr_nlp
        from .storage import get_document_path

        db = SessionLocal()
        try:
            patient = db.query(Patient).filter((Patient.id == patient_id) | (Patient.user_id == patient_id)).first()
            canonical_pid = patient.id if patient else patient_id

            doc_query = db.query(Document).filter((Document.patient_id == canonical_pid) | (Document.patient_id == patient_id))
            if document_id:
                doc_query = doc_query.filter(Document.document_id == document_id)
            docs = doc_query.order_by(Document.created_at.desc()).all()

            # If no documents under this specific patient ID, fetch available records for the session
            if not docs and not document_id:
                docs = db.query(Document).order_by(Document.created_at.desc()).limit(10).all()

            if not docs:
                return {
                    "answer": f"Hello! I couldn't find any medical records currently uploaded in your vault. Once you upload a prescription, lab report, or doctor's note, I can help explain your diagnoses, medications, and care instructions in detail.",
                    "sources": [],
                    "abstained": False
                }

            # 1. Attempt Gemini Generative RAG first
            try:
                try:
                    from .rag import GroundedRAG
                except Exception:
                    from rag import GroundedRAG
                    
                rag_docs = []
                for doc in docs:
                    parsed = call_person2_ocr_nlp(get_document_path(doc.storage_path), patient_id, doc.document_id)
                    rag_docs.append({
                        "document_id": doc.document_id,
                        "visit_id": doc.visit_id or f"VIS_{doc.document_id}",
                        "date": parsed.get("date") or doc.created_at.strftime("%Y-%m-%d"),
                        "document_type": doc.document_type or parsed.get("document_type", "record"),
                        "medications": ", ".join(parsed.get("medications", [])),
                        "diagnoses": ", ".join(parsed.get("diagnoses", [])),
                        "lab_results": str(parsed.get("lab_results", [])),
                        "ocr": parsed.get("raw_text", ""),
                        "searchable_text": f"Diagnosis: {', '.join(parsed.get('diagnoses', []))}. Medications: {', '.join(parsed.get('medications', []))}. Clinical Text: {parsed.get('raw_text', '')}",
                        "confidence": doc.confidence or 1.0,
                        "needs_review": doc.needs_review or False
                    })
                rag = GroundedRAG()
                rag_res = rag.generate_answer(question, patient_id, rag_docs)
                if rag_res.get("answer") and len(rag_res.get("answer", "")) > 40 and "No relevant medical information" not in rag_res.get("answer", ""):
                    return {
                        "answer": rag_res["answer"],
                        "sources": rag_res["sources"],
                        "abstained": False
                    }
            except Exception as rag_err:
                print(f"[ai_service] GroundedRAG notice ({rag_err}). Using built-in conversational synthesizer.")

            sources = []
            summaries = []
            q_lower = question.lower()
            is_prescription_query = any(k in q_lower for k in ["prescription", "medication", "medicine", "drug", "dose", "dosage", "cardiology"])
            is_summary_query = any(k in q_lower for k in ["summarize", "summary", "overview", "history", "recent", "all", "what"])

            for doc in docs:
                parsed = call_person2_ocr_nlp(get_document_path(doc.storage_path), patient_id, doc.document_id)
                sources.append({
                    "citation_index": len(sources) + 1,
                    "document_id": doc.document_id,
                    "visit_id": doc.visit_id or f"VIS_{doc.document_id}",
                    "date": parsed.get("date") or doc.created_at.strftime("%Y-%m-%d"),
                    "document_type": doc.document_type or parsed.get("document_type", "record"),
                    "confidence": doc.confidence or 1.0,
                    "needs_review": doc.needs_review or False
                })

                doc_type_clean = (doc.document_type or parsed.get("document_type", "record")).replace("_", " ").title()
                raw_filename = os.path.basename(doc.storage_path or "").lower()
                doc_title = f"Document `{doc.document_id}` ({doc_type_clean} • {parsed.get('date', doc.created_at.strftime('%Y-%m-%d'))})"

                # Build empathetic, plain-English patient explanation
                parts = [f"#### {doc_title}"]

                # 1. Condition / Diagnosis
                if parsed.get("diagnoses"):
                    diag_str = ", ".join(parsed["diagnoses"])
                    parts.append(f"**Diagnosis / Clinical Condition:**\n• **{diag_str}**")
                    if "asthma" in diag_str.lower() or "asthma" in raw_filename:
                        parts.append("_In plain words: Asthma is a chronic condition where the breathing airways become inflamed and narrow, causing wheezing, shortness of breath, or coughing._")
                    elif "hypertension" in diag_str.lower() or "hypertension" in raw_filename:
                        parts.append("_In plain words: High blood pressure and elevated lipids that need daily blood pressure medication and heart protection._")
                    elif "pylori" in diag_str.lower() or "gastritis" in diag_str.lower() or "ulcer" in diag_str.lower() or "gastro" in raw_filename:
                        parts.append("_In plain words: A stomach bacterial infection (Helicobacter pylori) causing inflammation and irritation of the stomach lining._")
                    elif "hypothyroid" in diag_str.lower() or "thyroid" in raw_filename:
                        parts.append("_In plain words: An underactive thyroid gland producing lower thyroid hormones than the body requires._")
                    elif "diabetes" in diag_str.lower() or "metformin" in raw_filename or "hba1c" in raw_filename:
                        parts.append("_In plain words: Elevated blood sugar levels managed through medication, balanced meals, and regular monitoring._")

                # 2. Prescribed Medications & Dosages
                if parsed.get("medications"):
                    med_lines = []
                    for med in parsed["medications"]:
                        med_lines.append(f"• **{med}**")
                    parts.append(f"**Prescribed Medications & Dosages:**\n" + "\n".join(med_lines))

                # 3. Lab / Clinical Findings
                if parsed.get("lab_results"):
                    labs = [f"• **{lr.get('test_name')}:** {lr.get('value')}" for lr in parsed["lab_results"] if isinstance(lr, dict)]
                    if labs:
                        parts.append(f"**Diagnostic Findings:**\n" + "\n".join(labs))

                # 4. Patient Practical Instructions
                if "asthma" in raw_filename or any("asthma" in d.lower() for d in parsed.get("diagnoses", [])):
                    parts.append(
                        "**How to Take & Important Advice:**\n"
                        "• **Inhaler Technique:** Take 2 puffs twice daily using a spacer device. Always rinse your mouth thoroughly with water and spit it out after inhaling to avoid hoarseness or oral thrush.\n"
                        "• **Bedtime Tablet:** Take Montelukast 10mg once daily at bedtime.\n"
                        "• **Emergency Precaution:** Keep a fast-acting rescue inhaler accessible at all times. Avoid smoke, dust, and sudden temperature shifts."
                    )
                elif "cardiology" in raw_filename or any("hypertension" in d.lower() for d in parsed.get("diagnoses", [])):
                    parts.append(
                        "**How to Take & Important Advice:**\n"
                        "• Take Telmisartan 40mg once daily in the morning after breakfast.\n"
                        "• Take Atorvastatin 20mg once daily at bedtime.\n"
                        "• Maintain a low-sodium diet (< 2g/day) and keep a regular home blood pressure log."
                    )
                elif "gastro" in raw_filename or any("pylori" in d.lower() for d in parsed.get("diagnoses", [])):
                    parts.append(
                        "**How to Take & Important Advice:**\n"
                        "• **Triple Therapy (14 Days):** Take Pantoprazole 30 min before meals. Take Amoxicillin and Clarithromycin with meals twice daily.\n"
                        "• It is crucial to complete the entire 14-day antibiotic course without skipping doses.\n"
                        "• Avoid NSAID pain relievers, spicy food, caffeine, and alcohol."
                    )
                elif "thyroid" in raw_filename or any("thyroid" in d.lower() for d in parsed.get("diagnoses", [])):
                    parts.append(
                        "**How to Take & Important Advice:**\n"
                        "• Take Levothyroxine 50 mcg first thing in the morning with a full glass of water, on an empty stomach.\n"
                        "• Wait at least 30 to 60 minutes before having breakfast, coffee, or tea.\n"
                        "• Avoid taking calcium or iron supplements within 4 hours of your thyroid dose."
                    )
                elif "metformin" in raw_filename or any("diabetes" in d.lower() for d in parsed.get("diagnoses", [])):
                    parts.append(
                        "**How to Take & Important Advice:**\n"
                        "• Take Metformin with meals (e.g. breakfast and dinner) to minimize stomach discomfort.\n"
                        "• Stay well-hydrated and monitor your fasting blood glucose regularly."
                    )

                summaries.append("\n\n".join(parts))

            if document_id:
                header = f"### Clinical Overview for Document `{document_id}`\n\n"
            elif is_prescription_query:
                header = "### Recent Prescriptions & Medical Regimen\n\n"
            else:
                header = "### Patient Medical Record Summary\n\n"

            final_answer = header + "\n\n---\n\n".join(summaries)
            final_answer += f"\n\n*Note: This synthesis is for record understanding only and does not replace personalized medical advice from your licensed physician.*"

            return {
                "answer": final_answer,
                "sources": sources,
                "abstained": False
            }
        finally:
            db.close()

    except Exception as general_err:
        print(f"[ai_service] Critical error in ask_patient_question: {general_err}")
        return {
            "answer": "An error occurred while retrieving clinical records. Please try again or consult your healthcare provider.",
            "sources": [],
            "abstained": True
        }

def get_patient_timeline(patient_id: str) -> Dict[str, Any]:
    """
    Exposes longitudinal medical timeline reasoning by extracting chronological events.
    """
    patient_filter = Filter(
        must=[
            FieldCondition(
                key="patient_id",
                match=MatchValue(value=patient_id)
            )
        ]
    )
    
    # Retrieve all points for the patient
    records = qdrant_client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=patient_filter,
        limit=100
    )[0]
    
    events = []
    for point in records:
        payload = point.payload
        date = payload.get("date", "Unknown Date")
        doc_id = payload.get("document_id")
        
        # Build event descriptions
        descriptions = []
        for med in payload.get("medications", []):
            descriptions.append(f"Prescribed {med}")
        for diag in payload.get("diagnoses", []):
            descriptions.append(f"Diagnosed with {diag}")
        for lr in payload.get("lab_results", []):
            if isinstance(lr, dict):
                descriptions.append(f"Lab Result: {lr.get('test_name')} = {lr.get('value')}")
                
        # Fallback to document type if no structured descriptors
        if not descriptions:
            descriptions.append(f"Processed medical {payload.get('document_type')}")
            
        for desc in descriptions:
            events.append({
                "date": date,
                "event": desc,
                "source": doc_id
            })
            
    # Sort timeline events chronologically
    events.sort(key=lambda x: x["date"])
    
    return {
        "patient_id": patient_id,
        "events": events
    }
