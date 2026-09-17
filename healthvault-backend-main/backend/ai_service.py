import hashlib
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from .config import settings

# Try importing teammate's RAG pipeline from Hospital-records-system
try:
    import pipeline_api
    HAS_TEAMMATES_RAG = True
except ImportError:
    HAS_TEAMMATES_RAG = False

import os
import json
import shutil
import sqlite3
import pickle

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
            headers = {}
            if settings.HF_API_TOKEN:
                headers["Authorization"] = f"Bearer {settings.HF_API_TOKEN}"
            resp = requests.post(
                settings.HF_EMBEDDING_URL,
                json={"texts": [text]},
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                embeddings = data.get("embeddings", [])
                if embeddings and len(embeddings[0]) == VECTOR_SIZE:
                    return embeddings[0]
        except Exception as e:
            print(f"[ai_service] Hugging Face Space embedding request failed: {e}. Falling back to local embedder.")

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
            print(f"[ai_service] Test mode fallback triggered due to BGE-M3 embed error: {e}")
            
    if not is_test_environment():
        raise RuntimeError(
            "BAAI/bge-m3 MedicalEmbedder is not available in production environment. "
            "Refusing to insert fake/mock vector into production Qdrant collection."
        )

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

def ask_patient_question(patient_id: str, question: str) -> Dict[str, Any]:
    """
    Executes hybrid search query on Qdrant, applies evidence sufficiency gate,
    and returns a grounded RAG answer with citations or abstains safely.
    """
    try:
        import pipeline_api
        res = pipeline_api.ask_patient(patient_id, question)
        if "abstained" not in res:
            res["abstained"] = not res.get("is_grounded", True) or len(res.get("sources", [])) == 0
        return res
    except Exception as e:
        print(f"[ai_service] pipeline_api ask_patient notice ({e}). Running direct Qdrant RAG fallback.")

    query_vector = get_embedding(question)

    # Filter search results to current patient only (patient isolation)
    patient_filter = Filter(
        must=[
            FieldCondition(
                key="patient_id",
                match=MatchValue(value=patient_id)
            )
        ]
    )
    
    query_response = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=patient_filter,
        limit=10
    )
    search_results = query_response.points
    
    if not search_results:
        return {
            "answer": "No relevant information was found in the available records.",
            "sources": [],
            "abstained": True
        }
        
    records = [res.payload for res in search_results]
    
    # Check GroundedRAG synthesis
    try:
        from rag import GroundedRAG, assess_evidence_sufficiency
        assessment = assess_evidence_sufficiency(question, records)
        if not assessment.get("sufficient", True):
            return {
                "answer": "No relevant information was found in the available records.",
                "sources": [],
                "abstained": True
            }
        rag = GroundedRAG()
        rag_res = rag.generate_answer(question, patient_id, records)
        return {
            "answer": rag_res["answer"],
            "sources": rag_res["sources"],
            "abstained": not rag_res["is_grounded"]
        }
    except Exception as e:
        print(f"[ai_service] GroundedRAG execution notice ({e}).")

    return {
        "answer": "No relevant information was found in the available records.",
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
