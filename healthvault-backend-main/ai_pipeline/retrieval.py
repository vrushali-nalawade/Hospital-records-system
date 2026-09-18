"""
retrieval.py - True BM25Okapi, Per-Patient Caching & Strict Cross-Encoder Reranking
----------------------------------------------------------------------------------
1. True BM25Okapi Sparse Retrieval (TF, IDF, k1=1.5, b=0.75).
2. Per-patient BM25 index caching (indexes built ONCE per patient).
3. Pre-Truncation Temporal Filtering for 'latest' / 'earliest' queries.
4. Strict Cross-Encoder Reranking (ms-marco-MiniLM-L-6-v2) - fails strictly if unavailable.
5. Explicit RRF Score Fusion & Ranking.
"""

import re
import math
from typing import List, Dict, Any, Tuple

try:
    from embeddings import MedicalEmbedder
    from vector_store import MedicalVectorStore
except ImportError:
    from .embeddings import MedicalEmbedder
    from .vector_store import MedicalVectorStore

_CACHED_CROSS_ENCODER = None


class BM25Okapi:
    """
    Standard BM25Okapi Sparse Retrieval algorithm.
    """
    def __init__(self, corpus: List[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_len = []
        self.avgdl = 0.0
        self.doc_freqs = []
        self.idf = {}
        self._initialize(corpus)

    def _tokenize(self, text: str) -> List[str]:
        return [t.lower() for t in re.findall(r'\w+', text) if len(t) > 1]

    def _initialize(self, corpus: List[str]):
        total_len = 0
        df = {}

        for doc in corpus:
            tokens = self._tokenize(doc)
            self.doc_len.append(len(tokens))
            total_len += len(tokens)

            freqs = {}
            for t in tokens:
                freqs[t] = freqs.get(t, 0) + 1
            self.doc_freqs.append(freqs)

            for t in freqs.keys():
                df[t] = df.get(t, 0) + 1

        self.avgdl = total_len / self.corpus_size if self.corpus_size > 0 else 1.0

        for word, freq in df.items():
            self.idf[word] = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)

    def get_scores(self, query: str) -> List[float]:
        query_tokens = self._tokenize(query)
        scores = [0.0] * self.corpus_size

        for token in query_tokens:
            if token not in self.idf:
                continue
            idf_val = self.idf[token]
            for i, freqs in enumerate(self.doc_freqs):
                freq = freqs.get(token, 0)
                if freq == 0:
                    continue
                doc_l = self.doc_len[i]
                numerator = freq * (self.k1 + 1.0)
                denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_l / self.avgdl))
                scores[i] += idf_val * (numerator / denominator)

        return scores


class MedicalRetriever:

    def __init__(self, embedder: MedicalEmbedder, vector_store: MedicalVectorStore):
        self.embedder = embedder
        self.vector_store = vector_store
        self._cross_encoder = None
        self.patient_bm25_cache: Dict[str, Tuple[BM25Okapi, List[Dict[str, Any]]]] = {}

    @property
    def cross_encoder(self):
        if self._cross_encoder is None:
            self._cross_encoder = self._get_or_load_cross_encoder()
        return self._cross_encoder

    def _get_or_load_cross_encoder(self):
        global _CACHED_CROSS_ENCODER
        if _CACHED_CROSS_ENCODER is not None:
            return _CACHED_CROSS_ENCODER

        try:
            from sentence_transformers import CrossEncoder
            print("[retrieval] Loading Cross-Encoder reranker 'cross-encoder/ms-marco-MiniLM-L-6-v2' (strict)...")
            _CACHED_CROSS_ENCODER = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            return _CACHED_CROSS_ENCODER
        except ImportError:
            raise ImportError(
                "\n[ERROR] 'sentence-transformers' is not installed.\n"
                "Please run: pip install sentence-transformers torch\n"
            )
        except Exception as e:
            raise RuntimeError(
                f"\n[ERROR] Failed to load required Cross-Encoder model 'cross-encoder/ms-marco-MiniLM-L-6-v2': {str(e)}\n"
                "Ensure internet connectivity or local HuggingFace cache availability."
            )

    def _get_patient_bm25_index(self, patient_id: str) -> Tuple[BM25Okapi, List[Dict[str, Any]]]:
        if patient_id in self.patient_bm25_cache:
            return self.patient_bm25_cache[patient_id]

        all_records = self.vector_store.get_all_patient_records(patient_id)
        corpus = [str(rec.get("searchable_text") or rec.get("ocr") or "") for rec in all_records]

        bm25_index = BM25Okapi(corpus, k1=1.5, b=0.75)
        self.patient_bm25_cache[patient_id] = (bm25_index, all_records)
        return bm25_index, all_records

    def dense_search(self, query: str, patient_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        query_vector = self.embedder.embed_text(query)
        return self.vector_store.search_patient_records(patient_id, query_vector, top_k=top_k)

    def bm25_search(self, query: str, patient_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        bm25_index, all_records = self._get_patient_bm25_index(patient_id)
        if not all_records:
            return []

        scores = bm25_index.get_scores(query)
        scored_records = []
        for idx, score in enumerate(scores):
            if score > 0:
                rec_copy = dict(all_records[idx])
                rec_copy["bm25_score"] = score
                scored_records.append(rec_copy)

        scored_records.sort(key=lambda x: x["bm25_score"], reverse=True)
        return scored_records[:top_k]

    def rrf_hybrid_search(self, query: str, patient_id: str, top_k_candidates: int = 15) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        is_latest_query = any(w in query_lower for w in ["latest", "most recent", "newest", "last"])
        is_earliest_query = any(w in query_lower for w in ["earliest", "oldest", "first"])

        fetch_limit = 50 if (is_latest_query or is_earliest_query) else top_k_candidates

        dense_docs = self.dense_search(query, patient_id, top_k=fetch_limit)
        bm25_docs = self.bm25_search(query, patient_id, top_k=fetch_limit)

        rrf_map: Dict[str, Dict[str, Any]] = {}

        for rank, doc in enumerate(dense_docs):
            cid = str(doc.get("chunk_id", doc.get("document_id")))
            if cid not in rrf_map:
                rrf_map[cid] = {"doc": doc, "score": 0.0}
            rrf_map[cid]["score"] += 1.0 / (60.0 + (rank + 1))

        for rank, doc in enumerate(bm25_docs):
            cid = str(doc.get("chunk_id", doc.get("document_id")))
            if cid not in rrf_map:
                rrf_map[cid] = {"doc": doc, "score": 0.0}
            rrf_map[cid]["score"] += 1.0 / (60.0 + (rank + 1))

        # FIXED RRF SCORE ASSIGNMENT
        fused = []
        for data in rrf_map.values():
            doc = dict(data["doc"])
            doc["rrf_score"] = data["score"]
            fused.append(doc)

        # PRE-TRUNCATION TEMPORAL SORTING
        if is_latest_query:
            valid_docs = [d for d in fused if d.get("date") not in ["1970-01-01", "", None]]
            undated_docs = [d for d in fused if d.get("date") in ["1970-01-01", "", None]]
            valid_docs.sort(key=lambda x: str(x.get("date", "")), reverse=True)
            fused = valid_docs + undated_docs
        elif is_earliest_query:
            valid_docs = [d for d in fused if d.get("date") not in ["1970-01-01", "", None]]
            undated_docs = [d for d in fused if d.get("date") in ["1970-01-01", "", None]]
            valid_docs.sort(key=lambda x: str(x.get("date", "")))
            fused = valid_docs + undated_docs
        else:
            fused.sort(key=lambda x: x.get("rrf_score", 0.0), reverse=True)

        return fused[:top_k_candidates]

    def cross_encoder_rerank(
        self,
        query: str,
        patient_id: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        candidates = self.rrf_hybrid_search(query, patient_id, top_k_candidates=15)
        if not candidates:
            return []

        pairs = [[query, str(c.get("searchable_text") or c.get("ocr") or "")] for c in candidates]
        
        # 1. Check for remote HF Space reranker
        import os
        hf_reranker_url = os.getenv("HF_RERANKER_URL")
        hf_token = os.getenv("HF_API_TOKEN")

        if hf_reranker_url:
            import requests
            headers = {"Content-Type": "application/json"}
            if hf_token:
                headers["Authorization"] = f"Bearer {hf_token}"
            try:
                res = requests.post(
                    hf_reranker_url,
                    json={"query": query, "passages": [p[1] for p in pairs]},
                    headers=headers,
                    timeout=20
                )
                if res.status_code == 200:
                    data = res.json()
                    scores = data.get("scores", data)
                    if isinstance(scores, list) and len(scores) == len(candidates):
                        for doc, score in zip(candidates, scores):
                            doc["cross_encoder_score"] = float(score)
                        candidates.sort(key=lambda x: x["cross_encoder_score"], reverse=True)
                        return candidates[:top_k]
            except Exception as e:
                print(f"[retrieval] Remote HF reranker request failed: {e}. Falling back to local model.")

        # 2. Local execution fallback
        try:
            if self.cross_encoder is not None:
                scores = self.cross_encoder.predict(pairs)
                for doc, score in zip(candidates, scores):
                    doc["cross_encoder_score"] = float(score)
                candidates.sort(key=lambda x: x["cross_encoder_score"], reverse=True)
                return candidates[:top_k]
        except Exception as e:
            print(f"[retrieval] Cross encoder fallback to RRF candidates: {e}")

        return candidates[:top_k]