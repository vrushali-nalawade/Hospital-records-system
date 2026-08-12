"""
embeddings.py - BAAI/bge-m3 Medical Embedding Engine & Adaptive Chunking
-----------------------------------------------------------------------
Converts Person 2 structured medical records into 1024-dimensional
vector embeddings using BAAI/bge-m3. Fails strictly if model loading fails.
"""

from typing import List, Dict, Any, Union, Optional

DEFAULT_MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

_CACHED_MODEL = None
_CACHED_MODEL_NAME = None


def format_record_for_embedding(record: Dict[str, Any]) -> str:
    """
    Transforms a Person 2 structured record JSON into a searchable text passage.
    Safely handles string or dictionary types for all fields.
    """
    doc_id = str(record.get("document_id", "UNKNOWN_DOC"))
    visit_id = str(record.get("visit_id", "UNKNOWN_VISIT"))
    patient_id = str(record.get("patient_id", "UNKNOWN_PATIENT"))
    doc_date = str(record.get("date", "UNKNOWN_DATE"))
    doc_type = str(record.get("document_type", "Medical Document"))

    date_str = "Undated / Unspecified Date" if doc_date in ["1970-01-01", "", None] else doc_date

    lines = [
        f"Medical Record Header: Patient={patient_id} | DocID={doc_id} | VisitID={visit_id} | Date={date_str} | Type={doc_type}"
    ]

    # Medications
    medications = record.get("medications", [])
    if medications:
        med_strs = []
        for m in medications:
            if isinstance(m, dict):
                med_name = m.get("medication", m.get("name", ""))
                dosage = m.get("dosage", "")
                freq = m.get("frequency", "")
                conf = m.get("confidence", 1.0)
                med_strs.append(f"{med_name} {dosage} {freq} (Confidence: {conf:.2f})".strip())
            else:
                med_strs.append(str(m))
        lines.append("Prescribed Medications: " + ", ".join(med_strs))

    # Diagnoses
    diagnoses = record.get("diagnoses", [])
    if diagnoses:
        diag_strs = []
        for d in diagnoses:
            if isinstance(d, dict):
                diag_name = d.get("diagnosis") or d.get("condition") or d.get("name") or str(d)
                diag_strs.append(str(diag_name))
            else:
                diag_strs.append(str(d))
        lines.append("Diagnoses/Conditions: " + ", ".join(diag_strs))

    # Lab Results
    lab_results = record.get("lab_results", [])
    if lab_results:
        lab_strs = []
        for l in lab_results:
            if isinstance(l, dict):
                test = l.get("lab_test", l.get("test", l.get("name", "")))
                val = l.get("value", "")
                unit = l.get("unit", "")
                conf = l.get("confidence", 1.0)
                lab_strs.append(f"{test} = {val} {unit} (Confidence: {conf:.2f})".strip())
            else:
                lab_strs.append(str(l))
        lines.append("Laboratory Test Results: " + ", ".join(lab_strs))

    # Allergies
    allergies = record.get("allergies", [])
    if allergies:
        alg_strs = []
        for a in allergies:
            if isinstance(a, dict):
                alg_name = a.get("allergen") or a.get("allergy") or a.get("name") or str(a)
                alg_strs.append(str(alg_name))
            else:
                alg_strs.append(str(a))
        lines.append("Recorded Allergies: " + ", ".join(alg_strs))

    # Procedures
    procedures = record.get("procedures", [])
    if procedures:
        proc_strs = []
        for p in procedures:
            if isinstance(p, dict):
                proc_name = p.get("procedure") or p.get("name") or str(p)
                proc_strs.append(str(proc_name))
            else:
                proc_strs.append(str(p))
        lines.append("Medical Procedures: " + ", ".join(proc_strs))

    # Original Raw OCR Text
    raw_ocr = record.get("ocr") or record.get("text") or record.get("full_text") or ""
    if isinstance(raw_ocr, dict):
        raw_text = str(raw_ocr.get("text") or raw_ocr.get("ocr") or raw_ocr.get("full_text") or str(raw_ocr)).strip()
    else:
        raw_text = str(raw_ocr).strip()

    if raw_text:
        lines.append(f"Original Text Context: {raw_text}")

    # Preserved Review Metadata
    if record.get("needs_review", False):
        conf_val = record.get("confidence", 0.0)
        lines.append(f"Note: Extraction contains low-confidence fields marked for human review (Confidence: {conf_val}).")

    return "\n".join(lines)


def adaptive_chunk_record(record: Dict[str, Any], max_chunk_chars: int = 800) -> List[Dict[str, Any]]:
    """
    Adaptive Chunking:
    Short records -> 1 passage.
    Long records -> Meaningful chunks preserving all metadata.
    """
    full_text = format_record_for_embedding(record)
    
    if len(full_text) <= max_chunk_chars:
        chunk = dict(record)
        chunk["searchable_text"] = full_text
        chunk["chunk_id"] = f"{record.get('document_id', 'DOC')}_c0"
        return [chunk]

    sections = [s.strip() for s in full_text.split("\n") if s.strip()]
    chunks = []
    current_chunk_lines = []
    current_len = 0
    chunk_index = 0

    for line in sections:
        if current_len + len(line) > max_chunk_chars and current_chunk_lines:
            chunk_data = dict(record)
            chunk_data["searchable_text"] = "\n".join(current_chunk_lines)
            chunk_data["chunk_id"] = f"{record.get('document_id', 'DOC')}_c{chunk_index}"
            chunks.append(chunk_data)
            chunk_index += 1
            current_chunk_lines = []
            current_len = 0
        
        current_chunk_lines.append(line)
        current_len += len(line)

    if current_chunk_lines:
        chunk_data = dict(record)
        chunk_data["searchable_text"] = "\n".join(current_chunk_lines)
        chunk_data["chunk_id"] = f"{record.get('document_id', 'DOC')}_c{chunk_index}"
        chunks.append(chunk_data)

    return chunks


class MedicalEmbedder:

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self.model = self._get_or_load_model()

    def _get_or_load_model(self):
        global _CACHED_MODEL, _CACHED_MODEL_NAME
        if _CACHED_MODEL is not None and _CACHED_MODEL_NAME == self.model_name:
            return _CACHED_MODEL

        try:
            from sentence_transformers import SentenceTransformer
            print(f"[embeddings] Loading embedding model '{self.model_name}' (strict, no fallbacks)...")
            _CACHED_MODEL = SentenceTransformer(self.model_name)
            _CACHED_MODEL_NAME = self.model_name
            return _CACHED_MODEL
        except ImportError:
            raise ImportError(
                "\n[ERROR] 'sentence-transformers' library is not installed.\n"
                "Please run: pip install sentence-transformers torch\n"
            )
        except Exception as e:
            raise RuntimeError(
                f"\n[ERROR] Failed to load required embedding model '{self.model_name}': {str(e)}\n"
                "Check network connection or local HuggingFace cache."
            )

    @property
    def embedding_dimension(self) -> int:
        if self.model is None:
            raise RuntimeError("Model is not initialized.")
        if hasattr(self.model, "get_embedding_dimension"):
            return self.model.get_embedding_dimension()
        return self.model.get_sentence_embedding_dimension()

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("Input text for embedding cannot be empty.")
        embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.tolist()

    def embed_documents(self, documents: List[Union[str, Dict[str, Any]]]) -> List[List[float]]:
        formatted_texts = []
        for doc in documents:
            if isinstance(doc, dict):
                formatted_texts.append(doc.get("searchable_text", format_record_for_embedding(doc)))
            elif isinstance(doc, str):
                formatted_texts.append(doc)
            else:
                raise TypeError(f"Document must be str or dict, got {type(doc)}")

        if not formatted_texts:
            return []

        embeddings = self.model.encode(
            formatted_texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings.tolist()