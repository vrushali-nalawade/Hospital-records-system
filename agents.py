"""
agents.py - LangGraph Architecture with Evidence Sufficiency Gate
---------------------------------------------------------------
Implements an actual compiled StateGraph featuring:
- RouterNode
- RetrievalNode
- EvidenceSufficiencyNode (Assesses evidence prior to synthesis)
- AbstainNode (Safe refusal for unanswerable queries)
- TimelineNode & ConsistencyNode
- SynthesisNode & CitationValidatorNode
"""

import re
from typing import List, Dict, Any, TypedDict

try:
    from rag import assess_evidence_sufficiency
except ImportError:
    from .rag import assess_evidence_sufficiency


class AgentState(TypedDict):
    patient_id: str
    query: str
    query_type: str
    retrieved_docs: List[Dict[str, Any]]
    evidence_sufficiency: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    trends: List[Dict[str, Any]]
    inconsistencies: List[Dict[str, Any]]
    final_answer: str
    answer: str
    sources: List[Dict[str, Any]]
    confidence_warning: bool
    is_grounded: bool
    node_execution_trace: List[str]


class PatientReasoningGraph:
    """
    Native Compiled LangGraph StateGraph with Evidence Sufficiency Abstention Gate.
    """
    def __init__(self, retriever, rag):
        self.retriever = retriever
        self.rag = rag
        self.app = self._build_compiled_graph()

    def _build_compiled_graph(self):
        try:
            from langgraph.graph import StateGraph, START, END
        except ImportError:
            raise ImportError(
                "\n[ERROR] 'langgraph' package is not installed.\n"
                "Please run: pip install langgraph\n"
            )

        graph = StateGraph(AgentState)
        
        graph.add_node("RouterNode", self._router_node)
        graph.add_node("RetrievalNode", self._retrieval_node)
        graph.add_node("EvidenceSufficiencyNode", self._evidence_sufficiency_node)
        graph.add_node("AbstainNode", self._abstain_node)
        graph.add_node("TimelineNode", self._timeline_node)
        graph.add_node("ConsistencyNode", self._consistency_node)
        graph.add_node("SynthesisNode", self._synthesis_node)
        graph.add_node("CitationValidatorNode", self._citation_validator_node)

        graph.add_edge(START, "RouterNode")
        graph.add_edge("RouterNode", "RetrievalNode")
        graph.add_edge("RetrievalNode", "EvidenceSufficiencyNode")

        def route_after_evidence(state: AgentState):
            if not state.get("evidence_sufficiency", {}).get("sufficient", True):
                return "insufficient"
            return "complex" if state["query_type"] == "COMPLEX_REASONING" else "simple"

        graph.add_conditional_edges(
            "EvidenceSufficiencyNode",
            route_after_evidence,
            {
                "insufficient": "AbstainNode",
                "complex": "TimelineNode",
                "simple": "SynthesisNode"
            }
        )

        graph.add_edge("AbstainNode", "CitationValidatorNode")
        graph.add_edge("TimelineNode", "ConsistencyNode")
        graph.add_edge("ConsistencyNode", "SynthesisNode")
        graph.add_edge("SynthesisNode", "CitationValidatorNode")
        graph.add_edge("CitationValidatorNode", END)

        return graph.compile()

    def run_query(self, query: str, patient_id: str) -> Dict[str, Any]:
        initial_state = {
            "patient_id": patient_id,
            "query": query,
            "query_type": "SIMPLE_LOOKUP",
            "retrieved_docs": [],
            "evidence_sufficiency": {},
            "timeline": [],
            "trends": [],
            "inconsistencies": [],
            "final_answer": "",
            "answer": "",
            "sources": [],
            "confidence_warning": False,
            "is_grounded": True,
            "node_execution_trace": []
        }

        final_state = self.app.invoke(initial_state)
        final_state["answer"] = final_state["final_answer"]
        return final_state

    # ------------------ Node Functions ------------------
    def _router_node(self, state: AgentState) -> AgentState:
        state["node_execution_trace"].append("RouterNode")
        query_lower = state["query"].lower()
        complex_kws = ["change", "trend", "over time", "history", "progression", "inconsistent", "conflict", "dosage change", "timeline", "across visits"]
        if any(kw in query_lower for kw in complex_kws):
            state["query_type"] = "COMPLEX_REASONING"
        else:
            state["query_type"] = "SIMPLE_LOOKUP"
        return state

    def _retrieval_node(self, state: AgentState) -> AgentState:
        state["node_execution_trace"].append("RetrievalNode")
        patient_id = state["patient_id"]
        query = state["query"]

        top_k = 5 if state["query_type"] == "COMPLEX_REASONING" else 3
        docs = self.retriever.cross_encoder_rerank(query, patient_id, top_k=top_k)

        state["retrieved_docs"] = docs
        return state

    def _evidence_sufficiency_node(self, state: AgentState) -> AgentState:
        state["node_execution_trace"].append("EvidenceSufficiencyNode")
        assessment = assess_evidence_sufficiency(state["query"], state["retrieved_docs"])
        state["evidence_sufficiency"] = assessment
        return state

    def _abstain_node(self, state: AgentState) -> AgentState:
        state["node_execution_trace"].append("AbstainNode")
        query_lower = state["query"].lower()
        
        if "allergy" in query_lower or "allergic" in query_lower:
            ans = "No allergy information was found in the available records."
        else:
            ans = "No relevant information was found in the available records."

        state["final_answer"] = ans
        state["sources"] = []
        state["confidence_warning"] = False
        state["is_grounded"] = True
        return state

    def _timeline_node(self, state: AgentState) -> AgentState:
        state["node_execution_trace"].append("TimelineNode")
        docs = state["retrieved_docs"]
        if not docs:
            return state

        valid_docs = [d for d in docs if d.get("date") not in ["1970-01-01", "", None]]
        undated_docs = [d for d in docs if d.get("date") in ["1970-01-01", "", None]]
        valid_docs.sort(key=lambda x: str(x.get("date", "")))

        state["retrieved_docs"] = valid_docs + undated_docs

        timeline = []
        lab_trajectories: Dict[str, List[Dict[str, Any]]] = {}

        for d in valid_docs:
            date = str(d.get("date"))
            doc_id = str(d.get("document_id"))

            for lab in d.get("lab_results", []):
                if isinstance(lab, dict):
                    test = lab.get("lab_test", lab.get("test", "Lab"))
                    val = str(lab.get("value", ""))
                    timeline.append({"date": date, "doc_id": doc_id, "type": "LAB", "desc": f"{test} = {val}"})

                    num_match = re.search(r'(\d+(?:\.\d+)?)', val)
                    if num_match:
                        num_val = float(num_match.group(1))
                        if test not in lab_trajectories:
                            lab_trajectories[test] = []
                        lab_trajectories[test].append({"date": date, "val": num_val, "raw": val, "doc_id": doc_id})

            for m in d.get("medications", []):
                if isinstance(m, dict):
                    med = m.get("medication", "")
                    dosage = m.get("dosage", "")
                    freq = m.get("frequency", "")
                    timeline.append({"date": date, "doc_id": doc_id, "type": "MEDICATION", "desc": f"{med} {dosage} {freq}".strip()})

        trends = []
        for test, points in lab_trajectories.items():
            if len(points) >= 2:
                first, last = points[0], points[-1]
                diff = last["val"] - first["val"]
                direction = "increased" if diff > 0 else ("decreased" if diff < 0 else "remained stable")
                trends.append({
                    "test": test,
                    "summary": f"{test} {direction} from {first['raw']} ({first['date']}) [{first['doc_id']}] to {last['raw']} ({last['date']}) [{last['doc_id']}]."
                })

        state["timeline"] = timeline
        state["trends"] = trends
        return state

    def _consistency_node(self, state: AgentState) -> AgentState:
        state["node_execution_trace"].append("ConsistencyNode")
        docs = state["retrieved_docs"]
        if not docs:
            return state

        med_tracker: Dict[str, List[Dict[str, Any]]] = {}
        for d in docs:
            date = str(d.get("date", "Undated"))
            doc_id = str(d.get("document_id"))
            for m in d.get("medications", []):
                if isinstance(m, dict):
                    name = str(m.get("medication", "")).strip().capitalize()
                    dosage = str(m.get("dosage", "")).strip()
                    if name:
                        if name not in med_tracker:
                            med_tracker[name] = []
                        med_tracker[name].append({"date": date, "dosage": dosage, "doc_id": doc_id})

        inconsistencies = []
        for med, history in med_tracker.items():
            if len(history) >= 2:
                dosages = set(h["dosage"] for h in history if h["dosage"])
                if len(dosages) > 1:
                    history_desc = ", ".join([f"{h['dosage']} on {h['date']} [{h['doc_id']}]" for h in history])
                    inconsistencies.append({
                        "medication": med,
                        "warning": f"Recorded dosage for {med} changed across visits: {history_desc}. Please review source documents."
                    })

        state["inconsistencies"] = inconsistencies
        return state

    def _synthesis_node(self, state: AgentState) -> AgentState:
        state["node_execution_trace"].append("SynthesisNode")
        query = state["query"]
        patient_id = state["patient_id"]
        docs = state["retrieved_docs"]

        rag_res = self.rag.generate_answer(query, patient_id, docs)
        state["sources"] = rag_res["sources"]
        state["confidence_warning"] = rag_res["confidence_warning"]
        state["is_grounded"] = rag_res["is_grounded"]

        if state["query_type"] == "SIMPLE_LOOKUP":
            state["final_answer"] = rag_res["answer"]
            return state

        parts = ["### Longitudinal Overview\n" + rag_res["answer"]]

        if state["timeline"]:
            parts.append("### Chronological Timeline")
            for item in state["timeline"]:
                parts.append(f"- [{item['date']}] {item['desc']} (Doc: {item['doc_id']})")

        if state["trends"]:
            parts.append("### Recorded Trends")
            for t in state["trends"]:
                parts.append(f"- {t['summary']}")

        if state["inconsistencies"]:
            parts.append("### ⚠️ Consistency & Discrepancy Alerts")
            for inc in state["inconsistencies"]:
                parts.append(f"- {inc['warning']}")

        state["final_answer"] = "\n\n".join(parts)
        return state

    def _citation_validator_node(self, state: AgentState) -> AgentState:
        state["node_execution_trace"].append("CitationValidatorNode")
        cited_ids = set(re.findall(r'DOC\d+', state["final_answer"]))
        retrieved_ids = set(str(d.get("document_id", "")) for d in state["retrieved_docs"])

        invalid = cited_ids - retrieved_ids
        for bad in invalid:
            state["final_answer"] = state["final_answer"].replace(bad, "[REDACTED_CITATION]")
        return state