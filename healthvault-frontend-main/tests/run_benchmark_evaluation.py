"""
run_benchmark_evaluation.py - Diagnostic 50-Query Benchmark Evaluator
----------------------------------------------------------------------
Executes answerable (N=42) and unanswerable (N=8) queries dynamically through
the RAG pipeline and prints a detailed diagnostic trace for unanswerable queries.
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AI_MODULE_DIR = PROJECT_ROOT / "ai"
DATA_DIR = PROJECT_ROOT / "data"

sys.path.insert(0, str(AI_MODULE_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from pipeline_api import initialize_ai_pipeline, index_patient_records
    from evaluation import MedicalEvaluator
    from rag import assess_evidence_sufficiency
except ImportError:
    from ai.pipeline_api import initialize_ai_pipeline, index_patient_records
    from ai.evaluation import MedicalEvaluator
    from ai.rag import assess_evidence_sufficiency


def load_dataset_records():
    json_files = list(DATA_DIR.glob("*.json"))
    records = []
    for f in json_files:
        if f.name == "evaluation_benchmark_50.json":
            continue
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
                if isinstance(data, list):
                    records.extend(data)
                elif isinstance(data, dict):
                    records.append(data)
        except Exception:
            pass
    return records


def load_benchmark_questions():
    bench_file = DATA_DIR / "evaluation_benchmark_50.json"
    if not bench_file.exists():
        raise FileNotFoundError(f"[ERROR] Benchmark dataset missing at {bench_file}")

    with open(bench_file, "r", encoding="utf-8") as f:
        return json.load(f)


def run_diagnostic_investigation(agents, questions):
    unanswerable_questions = [q for q in questions if not q.get("relevant_doc_ids")]

    print("\n" + "=" * 80)
    print("        UNANSWERABLE NEGATIVE QUERIES DIAGNOSTIC INVESTIGATION (N=8)")
    print("=" * 80)

    for idx, q in enumerate(unanswerable_questions, start=1):
        pid = q["patient_id"]
        query = q["query"]

        graph_res = agents.run_query(query, patient_id=pid)
        ans = graph_res.get("answer", "")
        retrieved_docs = graph_res.get("retrieved_docs", [])
        sufficiency = graph_res.get("evidence_sufficiency", {})

        ans_lower = ans.lower()
        is_abstention = any(phrase in ans_lower for phrase in [
            "no relevant information",
            "no allergy information",
            "no information",
            "not found"
        ])

        status = "PASS" if is_abstention else "FAIL"
        actual_decision = "ABSTAIN" if is_abstention else "ANSWER"

        print("-" * 50)
        print(f"Negative Query #{idx} [{q.get('id', 'Q')}]")
        print(f"Patient : {pid}")
        print(f"Query   : {query}")
        print(f"Expected: ABSTAIN")
        print(f"Actual  : {actual_decision}")
        print(f"Status  : {'✅ PASS' if status == 'PASS' else '❌ FAIL'}")

        doc_ids = [d.get("document_id") for d in retrieved_docs]
        ce_scores = [round(float(d.get("cross_encoder_score", 0.0)), 4) for d in retrieved_docs]

        if status == "FAIL":
            print(f"- Generated Answer          : {ans}")
            print(f"- Retrieved Document IDs    : {doc_ids}")
            print(f"- Cross-Encoder Scores      : {ce_scores}")
            print(f"- Evidence Sufficiency Score: {sufficiency.get('score', 'N/A')}")
            print(f"- Sufficiency Decision      : {sufficiency.get('sufficient')}")
            print(f"- Reason for Allowing Synth : {sufficiency.get('reason')}")
            print(f"- Matched Query Tokens      : {sufficiency.get('matched_tokens')}")
        else:
            print(f"- Evidence Sufficiency Score: {sufficiency.get('score', 'N/A')}")
            print(f"- Decision                  : ABSTAIN ({sufficiency.get('reason')})")

    print("-" * 50 + "\n")


def main():
    print("=" * 80)
    print("   HEALTHVAULT AI - AUDITED 50-QUERY STATISTICAL EVALUATION BENCHMARK")
    print("=" * 80)

    # 1. Initialize Pipeline & Index Records
    records = load_dataset_records()
    pipeline = initialize_ai_pipeline()

    print(f"\n[Indexing] Indexing {len(records)} medical records into Qdrant...")
    index_patient_records(records)

    # 2. Load 50 Benchmark Questions
    questions = load_benchmark_questions()
    categories_set = set(q.get("category") for q in questions if q.get("category"))
    print(f"[Benchmark] Loaded {len(questions)} evaluation questions across {len(categories_set)} clinical categories.")

    # 3. Run Experiments A, B, C & Dynamic RAG Unanswerable Query Evaluation
    evaluator = MedicalEvaluator()
    retriever = pipeline["retriever"]
    agents = pipeline["agents"]

    # Run Diagnostic Trace for the 8 Unanswerable Queries
    run_diagnostic_investigation(agents, questions)

    print("[Evaluating] Running Experiments A (Dense), B (Dense+BM25+RRF), C (Hybrid+CrossEncoder)...")
    results = evaluator.run_retrieval_experiments(retriever, questions, pipeline_agents=agents)

    # 4. Print Audited Results Table
    print("\n" + "=" * 85)
    print("                AUDITED STATISTICAL BENCHMARK RESULTS REPORT")
    print("=" * 85)
    print(f"Total Benchmark Queries : {results['total_benchmark_queries']}")
    print(f"Answerable Queries      : {results['answerable_queries_count']}")
    print(f"Unanswerable Queries    : {results['unanswerable_queries_count']}\n")

    print("--- [SECTION 1: ANSWERABLE QUERIES RETRIEVAL BENCHMARK (N=42)] ---")
    print(f"{'Experiment Pipeline':<35} | {'Recall@5':<10} | {'Precision@5':<12} | {'Custom Norm P@5':<15} | {'MRR':<8}")
    print("-" * 90)
    for exp_key in ["Experiment_A_Dense_Only", "Experiment_B_Dense_BM25_RRF", "Experiment_C_Hybrid_CrossEncoder"]:
        metrics = results[exp_key]
        print(f"{exp_key:<35} | {metrics['recall_at_5']:<10.4f} | {metrics['precision_at_5']:<12.4f} | {metrics['custom_normalized_precision_at_5']:<15.4f} | {metrics['mrr']:<8.4f}")

    print("\n## UNANSWERABLE NEGATIVE QUERY EVALUATION\n")
    unans = results["unanswerable_negative_evaluation"]
    print(f"Count: {unans['count']}\n")
    print(f"Abstention Accuracy: {unans['measured_abstention_accuracy']:.4f}")
    print(f"False Answer Rate: {unans['measured_false_answer_rate']:.4f}")
    print(f"Hallucination Rate: {unans['measured_hallucination_rate']:.4f}")

    print("\n" + "-" * 90)
    print("PER-CATEGORY BREAKDOWN (Experiment C - Answerable Queries):")
    print("-" * 90)
    print(f"{'Clinical Category':<30} | {'Count':<6} | {'Mean Recall@5':<15} | {'Mean MRR':<8}")
    print("-" * 80)
    for cat, cstats in results["per_category_breakdown"].items():
        print(f"{cat:<30} | {cstats['count']:<6} | {cstats['mean_recall_at_5']:<15.4f} | {cstats['mean_mrr']:<8.4f}")

    print("\n==================================================================")
    print("🎉 BENCHMARK EVALUATION COMPLETED SUCCESSFULLY!")
    print("==================================================================")


if __name__ == "__main__":
    main()