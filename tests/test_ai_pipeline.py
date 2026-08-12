"""
test_ai_pipeline.py - Functional Integration Verification & Assertion Suite
-----------------------------------------------------------------------------
Executes relational & chronological assertions, verifies Native Compiled LangGraph
StateGraph execution paths, and runs functional retrieval pipeline checks.
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Set

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AI_MODULE_DIR = PROJECT_ROOT / "ai"
DATA_DIR = PROJECT_ROOT / "data"

sys.path.insert(0, str(AI_MODULE_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from embeddings import MedicalEmbedder, adaptive_chunk_record
    from vector_store import MedicalVectorStore
    from retrieval import MedicalRetriever
    from rag import GroundedRAG
    from agents import PatientReasoningGraph
    from evaluation import MedicalEvaluator
except ImportError:
    from ai.embeddings import MedicalEmbedder, adaptive_chunk_record
    from ai.vector_store import MedicalVectorStore
    from ai.retrieval import MedicalRetriever
    from ai.rag import GroundedRAG
    from ai.agents import PatientReasoningGraph
    from ai.evaluation import MedicalEvaluator


def load_all_dataset_files() -> List[Dict[str, Any]]:
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"[ERROR] Data directory not found at: {DATA_DIR}")

    json_files = list(DATA_DIR.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"[ERROR] No '.json' files found in directory: {DATA_DIR}")

    all_records = []
    print(f"[Setup] Scanning '{DATA_DIR}'...")
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_records.extend(data)
                    print(f"  └─ Loaded {len(data)} record(s) from '{json_file.name}'")
                elif isinstance(data, dict):
                    all_records.append(data)
                    print(f"  └─ Loaded 1 record from '{json_file.name}'")
        except Exception as e:
            print(f"[Warning] Could not load '{json_file.name}': {e}")

    print(f"[Setup] Total records loaded across all files: {len(all_records)}")
    return all_records


def run_all_tests():
    print("=" * 80)
    print("   HEALTHVAULT AI - PERSON 3 FUNCTIONAL INTEGRATION VERIFICATION SUITE")
    print("=" * 80)

    records = load_all_dataset_files()

    embedder = MedicalEmbedder()
    vector_store = MedicalVectorStore(location=":memory:", vector_size=embedder.embedding_dimension)
    retriever = MedicalRetriever(embedder=embedder, vector_store=vector_store)
    rag = GroundedRAG()
    agents = PatientReasoningGraph(retriever=retriever, rag=rag)
    evaluator = MedicalEvaluator()

    all_chunks = []
    for rec in records:
        all_chunks.extend(adaptive_chunk_record(rec))

    chunk_embeddings = embedder.embed_documents(all_chunks)
    vector_store.upsert_records(all_chunks, chunk_embeddings)

    # 1. Patient Isolation Check
    print("\n--- [Test 1] Mandatory Patient Isolation Check ---")
    for pid in ["P001", "P002", "P003", "P004", "P005", "P006", "P007"]:
        res = retriever.dense_search("medication lab results prescription diagnosis", patient_id=pid, top_k=10)
        for doc in res:
            assert str(doc.get("patient_id")) == pid, f"FAILED: Leak detected! Query for {pid} returned {doc.get('patient_id')}."
    print("✅ PASSED: Zero cross-patient records retrieved.")

    # 2. P001 HbA1c Exact Value & Document Relational Assertion
    print("\n--- [Test 2] P001 HbA1c Relational & Citation Assertion ---")
    res_hba1c = agents.run_query("What was P001's latest HbA1c?", patient_id="P001")
    print(f"[Native LangGraph StateGraph Trace]: {' -> '.join(res_hba1c['node_execution_trace'])}")
    print(f"Answer:\n{res_hba1c['answer']}")
    
    ans_text = res_hba1c['answer']
    assert ("8.1" in ans_text) and ("%" in ans_text), "RELATIONAL FAILURE: 8.1% missing from answer."
    primary_source = res_hba1c['sources'][0]
    assert primary_source['document_id'] == "DOC002", f"RELATIONAL FAILURE: Expected DOC002, got {primary_source['document_id']}"
    
    doc002_rec = next(r for r in records if r.get("document_id") == "DOC002")
    expected_doc002_date = str(doc002_rec.get("date"))
    assert primary_source['date'] == expected_doc002_date, f"TEMPORAL FAILURE: Expected date {expected_doc002_date}, got {primary_source['date']}"
    print(f"✅ PASSED: Relational match verified (8.1% -> DOC002 -> {expected_doc002_date}).")

    # 3. P001 Metformin Chronological Progression Assertion
    print("\n--- [Test 3] P001 Metformin Chronological Progression Assertion ---")
    res_met = agents.run_query("How has P001's Metformin dosage changed across visits?", patient_id="P001")
    print(f"[Native LangGraph StateGraph Trace]: {' -> '.join(res_met['node_execution_trace'])}")
    print(f"Answer:\n{res_met['answer']}")

    assert "TimelineNode" in res_met['node_execution_trace'], "LANGGRAPH FAILURE: Complex query failed to route through TimelineNode."
    assert "ConsistencyNode" in res_met['node_execution_trace'], "LANGGRAPH FAILURE: Complex query failed to route through ConsistencyNode."

    idx_500 = res_met['answer'].find("500")
    idx_1000 = res_met['answer'].find("1000")
    assert idx_500 != -1 and idx_1000 != -1, "RELATIONAL FAILURE: Missing dosage values."
    assert idx_500 < idx_1000, "CHRONOLOGICAL FAILURE: 500mg should precede 1000mg in chronological timeline."
    print("✅ PASSED: Chronological order verified (500mg -> 1000mg).")

    # 4. P003 Allergy Relational Assertion
    print("\n--- [Test 4] P003 Penicillin Allergy Relational Assertion ---")
    res_alg = agents.run_query("Does P003 have a recorded allergy?", patient_id="P003")
    print(f"Answer:\n{res_alg['answer']}")
    assert "Penicillin" in res_alg['answer'], "RELATIONAL FAILURE: Expected Penicillin allergy."
    
    cited_ids = [s['document_id'] for s in res_alg['sources']]
    assert "DOC006" in cited_ids, "CITATION FAILURE: Expected DOC006 in retrieved sources for Penicillin allergy."
    
    doc006_source = next(s for s in res_alg['sources'] if s['document_id'] == "DOC006")
    doc006_rec = next(r for r in records if r.get("document_id") == "DOC006")
    expected_doc006_date = str(doc006_rec.get("date"))
    assert doc006_source['date'] == expected_doc006_date, f"TEMPORAL FAILURE: Expected date {expected_doc006_date} for DOC006."
    print(f"✅ PASSED: Penicillin allergy bound to DOC006 ({expected_doc006_date}).")

    # 5. P002 Low Confidence Review Flag Assertion
    print("\n--- [Test 5] P002 Low-Confidence Flag Assertion ---")
    res_low = agents.run_query("What medication is recorded in P002's prescription?", patient_id="P002")
    assert res_low['confidence_warning'] is True, "ASSERTION FAILED: Expected confidence_warning=True."
    print("✅ PASSED: Low confidence record (needs_review=true) flagged.")

    # 6. Functional Retrieval Pipeline Check (A vs B vs C)
    print("\n--- [Test 6] Functional Retrieval Pipeline Check (A vs B vs C) ---")
    benchmark_queries = [
        {"patient_id": "P001", "query": "What is the latest HbA1c?", "relevant_doc_ids": ["DOC002"]},
        {"patient_id": "P001", "query": "Metformin dosage changes", "relevant_doc_ids": ["DOC001", "DOC005"]},
        {"patient_id": "P003", "query": "Penicillin allergy reaction", "relevant_doc_ids": ["DOC006"]},
        {"patient_id": "P006", "query": "Atorvastatin dosage progression", "relevant_doc_ids": ["DOC010", "DOC011"]}
    ]
    exp_report = evaluator.run_retrieval_experiments(retriever, benchmark_queries)
    print(json.dumps(exp_report, indent=2))
    print("✅ PASSED: Experiments A, B, and C functional pipelines executed.")

    print("\n==================================================================")
    print("🎉 ALL FUNCTIONAL INTEGRATION VERIFICATIONS & ASSERTIONS PASSED PERFECTLY!")
    print("==================================================================")


if __name__ == "__main__":
    run_all_tests()