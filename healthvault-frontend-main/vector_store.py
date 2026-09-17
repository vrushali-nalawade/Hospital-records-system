"""
vector_store.py - Qdrant Vector Store with Mandatory Patient Isolation
---------------------------------------------------------------------
Stores BGE-M3 1024-d embeddings and enforces patient filtering at the database layer.
"""

from typing import List, Dict, Any, Optional

try:
    from embeddings import format_record_for_embedding
except ImportError:
    from .embeddings import format_record_for_embedding

COLLECTION_NAME = "medical_records"


class MedicalVectorStore:

    def __init__(self, location: str = ":memory:", vector_size: int = 1024):
        self.location = location
        self.vector_size = vector_size
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import VectorParams, Distance

            if self.location == ":memory:":
                self.client = QdrantClient(location=":memory:")
            else:
                self.client = QdrantClient(path=self.location)

            collections = [c.name for c in self.client.get_collections().collections]
            if COLLECTION_NAME in collections:
                col_info = self.client.get_collection(COLLECTION_NAME)
                existing_size = getattr(col_info.config.params.vectors, "size", None)
                if existing_size and existing_size != self.vector_size:
                    print(f"[vector_store] Detected incompatible vector size ({existing_size} != {self.vector_size}). Re-creating collection '{COLLECTION_NAME}'.")
                    self.client.delete_collection(COLLECTION_NAME)
                    self.client.create_collection(
                        collection_name=COLLECTION_NAME,
                        vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
                    )
            else:
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE)
                )
                print(f"[vector_store] Initialized Qdrant collection '{COLLECTION_NAME}' (dim={self.vector_size})")

        except ImportError:
            raise ImportError(
                "\n[ERROR] 'qdrant-client' is not installed.\n"
                "Please run: pip install qdrant-client\n"
            )
        except Exception as e:
            raise RuntimeError(f"[ERROR] Failed to initialize Qdrant client: {str(e)}")

    def upsert_records(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunk count ({len(chunks)}) does not match embeddings count ({len(embeddings)})")

        from qdrant_client.models import PointStruct

        points = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            doc_id = chunk.get("document_id", f"DOC-{i:03d}")
            patient_id = chunk.get("patient_id", "P_UNKNOWN")
            chunk_id = chunk.get("chunk_id", f"{doc_id}_c0")

            payload = {
                "patient_id": patient_id,
                "document_id": doc_id,
                "visit_id": chunk.get("visit_id", ""),
                "document_type": chunk.get("document_type", "Medical Document"),
                "date": chunk.get("date", "UNKNOWN_DATE"),
                "ocr": chunk.get("ocr", chunk.get("text", "")),
                "medications": chunk.get("medications", []),
                "diagnoses": chunk.get("diagnoses", []),
                "lab_results": chunk.get("lab_results", []),
                "allergies": chunk.get("allergies", []),
                "procedures": chunk.get("procedures", []),
                "needs_review": chunk.get("needs_review", False),
                "confidence": chunk.get("confidence", 1.0),
                "searchable_text": chunk.get("searchable_text", ""),
                "chunk_id": chunk_id
            }

            point_id = hash(f"{patient_id}_{chunk_id}") % (2**63 - 1)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=emb,
                    payload=payload
                )
            )

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        print(f"[vector_store] Successfully upserted {len(points)} record chunk(s) into Qdrant.")
        return len(points)

    def search_patient_records(
        self,
        patient_id: str,
        query_vector: List[float],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        if not patient_id:
            raise ValueError("patient_id is mandatory for patient-scoped vector search.")

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        patient_filter = Filter(
            must=[
                FieldCondition(
                    key="patient_id",
                    match=MatchValue(value=patient_id)
                )
            ]
        )

        results = []
        if hasattr(self.client, "search"):
            search_result = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=patient_filter,
                limit=top_k
            )
            for hit in search_result:
                doc_data = dict(hit.payload)
                doc_data["vector_score"] = float(hit.score)
                results.append(doc_data)
        elif hasattr(self.client, "query_points"):
            search_result = self.client.query_points(
                collection_name=COLLECTION_NAME,
                query=query_vector,
                query_filter=patient_filter,
                limit=top_k
            )
            for point in search_result.points:
                doc_data = dict(point.payload)
                doc_data["vector_score"] = float(point.score) if hasattr(point, "score") else 1.0
                results.append(doc_data)

        return results

    def get_all_patient_records(self, patient_id: str) -> List[Dict[str, Any]]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        patient_filter = Filter(
            must=[
                FieldCondition(
                    key="patient_id",
                    match=MatchValue(value=patient_id)
                )
            ]
        )

        records, _ = self.client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=patient_filter,
            limit=500
        )

        return [dict(point.payload) for point in records]