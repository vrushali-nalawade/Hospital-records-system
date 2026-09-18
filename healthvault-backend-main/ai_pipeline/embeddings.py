"""
embeddings.py - BAAI/bge-m3 Medical Embedding Engine & Adaptive Chunking
-----------------------------------------------------------------------
Converts Person 2 structured medical records into 1024-dimensional
vector embeddings using BAAI/bge-m3. Fails strictly if model loading fails.
"""

import os
from typing import List, Dict, Any, Union, Optional

DEFAULT_MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIM = 1024

_CACHED_MODEL = None
_CACHED_TOKENIZER = None
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


def _get_process_rss_mb() -> float:
    """Lightweight cross-platform RSS memory diagnostic helper."""
    import sys
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t),
                ]
            psapi = ctypes.windll.psapi
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            p = PROCESS_MEMORY_COUNTERS_EX()
            p.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
            if psapi.GetProcessMemoryInfo(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(p), p.cb):
                return round(p.WorkingSetSize / (1024 * 1024), 2)
        else:
            # Linux / Replit: parse /proc/self/status for accurate current VmRSS
            try:
                with open("/proc/self/status", "r") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            return round(float(line.split()[1]) / 1024.0, 2)
            except Exception:
                import resource
                return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 2)
    except Exception:
        pass
    return 0.0


try:
    from backend.config import settings
except Exception:
    settings = None

class MedicalEmbedder:

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, hf_embedding_url: Optional[str] = None):
        self.model_name = model_name
        self.hf_url = (
            hf_embedding_url or 
            os.getenv("HF_EMBEDDING_URL") or 
            (getattr(settings, "HF_EMBEDDING_URL", None) if settings else None) or
            "https://vrushalily-healthvault-ai.hf.space"
        )
        self.hf_token = os.getenv("HF_API_TOKEN") or (getattr(settings, "HF_API_TOKEN", None) if settings else None)
        self.tokenizer = None
        self.model = None

        if self.hf_url:
            print(f"[embeddings] Configured remote HF Space ZeroGPU embedding endpoint: {self.hf_url}")
        else:
            self.model = self._get_or_load_model()

    def _get_or_load_model(self):
        global _CACHED_MODEL, _CACHED_MODEL_NAME, _CACHED_TOKENIZER
        if _CACHED_MODEL is not None and _CACHED_MODEL_NAME == self.model_name:
            self.tokenizer = _CACHED_TOKENIZER
            return _CACHED_MODEL

        try:
            import gc
            import torch
            from transformers import AutoConfig, AutoModel, AutoTokenizer
            from safetensors.torch import load_file
            from huggingface_hub import hf_hub_download

            try:
                threads = min(os.cpu_count() or 4, 8)
                torch.set_num_threads(threads)
                torch.set_grad_enabled(False)
            except Exception:
                pass

            gc.collect()
            print(f"[embeddings] Loading embedding model '{self.model_name}' (compact BF16 safetensors)...")

            # 1. Check local BF16 safetensors artifact path
            local_model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
            local_artifact_path = os.path.join(local_model_dir, BF16_ARTIFACT_FILENAME)

            if os.path.exists(local_artifact_path):
                config = AutoConfig.from_pretrained(self.model_name)
                tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                model = AutoModel.from_config(config, torch_dtype=torch.bfloat16)
                weights = load_file(local_artifact_path)
                with torch.no_grad():
                    for name, param in model.named_parameters():
                        if name in weights:
                            param.copy_(weights[name])
                    for name, buf in model.named_buffers():
                        if name in weights:
                            buf.copy_(weights[name])
                del weights
                gc.collect()
            else:
                # Load public BAAI/bge-m3 model directly
                print(f"[embeddings] Loading public '{self.model_name}' weights from HuggingFace...")
                tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                model = AutoModel.from_pretrained(self.model_name)

            model.eval()
            print(f"[embeddings] Model ready. Embedding dimension: {EMBEDDING_DIM}")

            _CACHED_MODEL = model
            _CACHED_TOKENIZER = tokenizer
            _CACHED_MODEL_NAME = self.model_name
            self.tokenizer = tokenizer
            return _CACHED_MODEL
        except ImportError:
            raise ImportError(
                "\n[ERROR] 'transformers', 'safetensors', 'huggingface_hub' or 'torch' library is not installed.\n"
                "Please run: pip install transformers safetensors huggingface_hub torch\n"
            )
        except Exception as e:
            raise RuntimeError(
                f"\n[ERROR] Failed to load embedding model '{self.model_name}': {str(e)}\n"
                "Check network connection or local HuggingFace cache."
            )

    @property
    def embedding_dimension(self) -> int:
        return EMBEDDING_DIM

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise ValueError("Input text for embedding cannot be empty.")

        # 1. Use remote HF Space if configured
        if self.hf_url:
            import requests
            import json
            base_url = self.hf_url.strip().rstrip("/")
            headers = {"Content-Type": "application/json"}
            if self.hf_token:
                headers["Authorization"] = f"Bearer {self.hf_token}"
            
            # Try Gradio SSE, Gradio JSON, and FastAPI endpoints
            try:
                sse_res = requests.post(f"{base_url}/gradio_api/call/embed", json={"data": [text]}, headers=headers, timeout=10)
                if sse_res.status_code == 200:
                    event_id = sse_res.json().get("event_id")
                    if event_id:
                        stream_res = requests.get(f"{base_url}/gradio_api/call/embed/{event_id}", headers=headers, timeout=30)
                        for line in stream_res.text.splitlines():
                            if line.startswith("data: "):
                                payload = json.loads(line[6:])
                                if isinstance(payload, list) and payload:
                                    vec = payload[0] if isinstance(payload[0], list) else payload
                                    if len(vec) == EMBEDDING_DIM:
                                        return vec
            except Exception:
                pass

            try:
                res = requests.post(f"{base_url}/embed", json={"texts": [text]}, headers=headers, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    embeddings = data.get("embeddings", data)
                    if isinstance(embeddings, list) and len(embeddings) > 0:
                        return embeddings[0]
            except Exception as e:
                print(f"[embeddings] Remote HF embed request failed: {e}. Falling back to local embedder.")
                if self.model is None:
                    self.model = self._get_or_load_model()

        # 2. Local execution
        if self.model is None:
            self.model = self._get_or_load_model()

        import torch
        if self.tokenizer is None:
            global _CACHED_TOKENIZER
            self.tokenizer = _CACHED_TOKENIZER
        with torch.no_grad():
            inputs = self.tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors="pt")
            outputs = self.model(**inputs)
            # CLS token pooling (bge-m3 dense representation) + L2 normalize
            cls_rep = outputs.last_hidden_state[:, 0]
            norm_rep = torch.nn.functional.normalize(cls_rep.float(), p=2, dim=1)
            return norm_rep[0].tolist()

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

        # 1. Use remote HF Space if configured
        if self.hf_url:
            import requests
            base_url = self.hf_url.strip().rstrip("/")
            headers = {"Content-Type": "application/json"}
            if self.hf_token:
                headers["Authorization"] = f"Bearer {self.hf_token}"
            try:
                res = requests.post(f"{base_url}/embed", json={"texts": formatted_texts}, headers=headers, timeout=60)
                if res.status_code == 200:
                    data = res.json()
                    embeddings = data.get("embeddings", data)
                    if isinstance(embeddings, list) and len(embeddings) == len(formatted_texts):
                        return embeddings
            except Exception:
                pass
            
            # Per-item SSE fallback
            try:
                results = []
                for t in formatted_texts:
                    results.append(self.embed_text(t))
                if len(results) == len(formatted_texts):
                    return results
            except Exception as e:
                print(f"[embeddings] Remote HF batch embed request failed: {e}. Falling back to local embedder.")
                if self.model is None:
                    self.model = self._get_or_load_model()

        # 2. Local execution
        if self.model is None:
            self.model = self._get_or_load_model()

        import torch
        if self.tokenizer is None:
            global _CACHED_TOKENIZER
            self.tokenizer = _CACHED_TOKENIZER

        all_embeddings = []
        batch_size = 16
        with torch.no_grad():
            for i in range(0, len(formatted_texts), batch_size):
                batch = formatted_texts[i : i + batch_size]
                inputs = self.tokenizer(batch, padding=True, truncation=True, max_length=512, return_tensors="pt")
                outputs = self.model(**inputs)
                cls_rep = outputs.last_hidden_state[:, 0]
                norm_rep = torch.nn.functional.normalize(cls_rep.float(), p=2, dim=1)
                all_embeddings.extend(norm_rep.tolist())

        del formatted_texts
        return all_embeddings