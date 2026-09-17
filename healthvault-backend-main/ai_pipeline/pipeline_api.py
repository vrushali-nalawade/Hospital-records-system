"""
pipeline_api.py - Clean High-Level API for Backend / Person 4 Integration
-------------------------------------------------------------------------
Provides a simple, clean interface for Person 4 backend developers:
1. initialize_ai_pipeline(): Initializes models once globally (cached).
2. index_patient_records(records): Processes and indexes Person 2 JSON records into Qdrant.
3. ask_patient(patient_id, question): Queries the LangGraph RAG pipeline and returns clean JSON dicts.
"""

from typing import List, Dict, Any, Optional

try:
    from embeddings import MedicalEmbedder, adaptive_chunk_record
    from vector_store import MedicalVectorStore
    from retrieval import MedicalRetriever
    from rag import GroundedRAG
    from agents import PatientReasoningGraph
except ImportError:
    from .embeddings import MedicalEmbedder, adaptive_chunk_record
    from .vector_store import MedicalVectorStore
    from .retrieval import MedicalRetriever
    from .rag import GroundedRAG
    from .agents import PatientReasoningGraph

# Global Pipeline Instances (Initialized Once, Cached in Memory)
_PIPELINE_INSTANCES: Dict[str, Any] = {}


def initialize_ingestion_pipeline(vector_store_location: str = ":memory:") -> Dict[str, Any]:
    """
    Initializes ONLY MedicalEmbedder (BGE-M3) and MedicalVectorStore for document indexing.
    Defers Cross-Encoder, LangGraph, and RAG reasoning models until query time.
    """
    global _PIPELINE_INSTANCES
    if "embedder" not in _PIPELINE_INSTANCES:
        print("[pipeline_api] Initializing ingestion components (MedicalEmbedder + VectorStore)...")
        embedder = MedicalEmbedder()
        vector_store = MedicalVectorStore(location=vector_store_location, vector_size=embedder.embedding_dimension)
        _PIPELINE_INSTANCES["embedder"] = embedder
        _PIPELINE_INSTANCES["vector_store"] = vector_store
        print("[pipeline_api] Ingestion components initialized successfully (query models deferred).")
    return _PIPELINE_INSTANCES


def initialize_ai_pipeline(vector_store_location: str = ":memory:") -> Dict[str, Any]:
    """
    Initializes full pipeline including Cross-Encoder, RAG, and LangGraph reasoning agents.
    Called lazily only when query/reasoning endpoints are accessed.
    """
    global _PIPELINE_INSTANCES
    if "agents" in _PIPELINE_INSTANCES:
        return _PIPELINE_INSTANCES

    initialize_ingestion_pipeline(vector_store_location=vector_store_location)
    embedder = _PIPELINE_INSTANCES["embedder"]
    vector_store = _PIPELINE_INSTANCES["vector_store"]

    print("[pipeline_api] Initializing query & reasoning components (CrossEncoder + LangGraph)...")
    retriever = MedicalRetriever(embedder=embedder, vector_store=vector_store)
    rag = GroundedRAG()
    agents = PatientReasoningGraph(retriever=retriever, rag=rag)

    _PIPELINE_INSTANCES["retriever"] = retriever
    _PIPELINE_INSTANCES["rag"] = rag
    _PIPELINE_INSTANCES["agents"] = agents
    print("[pipeline_api] Full AI reasoning pipeline initialized successfully!")
    return _PIPELINE_INSTANCES


def index_patient_records(records: List[Dict[str, Any]]) -> int:
    """
    Indexes structured records from Person 2 into the Qdrant vector database.
    Initializes ONLY ingestion components (MedicalEmbedder + VectorStore).
    Input: List of Person 2 structured record dictionaries.
    Output: Number of chunks successfully indexed.
    """
    pipeline = initialize_ingestion_pipeline()
    embedder = pipeline["embedder"]
    vector_store = pipeline["vector_store"]

    all_chunks = []
    for rec in records:
        all_chunks.extend(adaptive_chunk_record(rec))

    if not all_chunks:
        return 0

    chunk_embeddings = embedder.embed_documents(all_chunks)
    count = vector_store.upsert_records(all_chunks, chunk_embeddings)
    
    # Invalidate per-patient BM25 index cache for newly updated patients if retriever was previously initialized
    if "retriever" in pipeline:
        patient_ids = set(r.get("patient_id") for r in records if r.get("patient_id"))
        for pid in patient_ids:
            if pid in pipeline["retriever"].patient_bm25_cache:
                del pipeline["retriever"].patient_bm25_cache[pid]

    return count


def ask_patient(patient_id: str, question: str) -> Dict[str, Any]:
    """
    Queries the Person 3 LangGraph RAG pipeline for a specific patient.
    
    Input:
        patient_id (str): Mandatory patient identifier (e.g. 'P001')
        question (str): Clinical question string
        
    Output (Clean JSON Dict for Backend Response):
        {
            "answer": str,
            "sources": List[Dict],
            "confidence_warning": bool,
            "is_grounded": bool,
            "reasoning_type": "simple" | "complex",
            "timeline": List[Dict] (optional),
            "trends": List[Dict] (optional),
            "consistency_warnings": List[str] (optional)
        }
    """
    if not patient_id:
        raise ValueError("patient_id is required for patient-isolated queries.")
    if not question or not question.strip():
        raise ValueError("question cannot be empty.")

    pipeline = initialize_ai_pipeline()
    agents = pipeline["agents"]

    graph_result = agents.run_query(question, patient_id=patient_id)

    # Format clean response payload for Person 4
    sources_payload = []
    for s in graph_result.get("sources", []):
        sources_payload.append({
            "document_id": s.get("document_id"),
            "visit_id": s.get("visit_id"),
            "date": s.get("date"),
            "document_type": s.get("document_type"),
            "confidence": s.get("confidence", 1.0),
            "needs_review": s.get("needs_review", False)
        })

    response = {
        "answer": graph_result.get("answer", ""),
        "sources": sources_payload,
        "confidence_warning": graph_result.get("confidence_warning", False),
        "is_grounded": graph_result.get("is_grounded", True),
        "reasoning_type": "complex" if graph_result.get("query_type") == "COMPLEX_REASONING" else "simple"
    }

    if graph_result.get("query_type") == "COMPLEX_REASONING":
        response["timeline"] = graph_result.get("timeline", [])
        response["trends"] = [t.get("summary") for t in graph_result.get("trends", [])]
        response["consistency_warnings"] = [w.get("warning") for w in graph_result.get("inconsistencies", [])]

    return response