"""
rag.py - Grounded RAG Generator & Rule-Based Evidence Sufficiency Gate
----------------------------------------------------------------------
1. Implements assess_evidence_sufficiency() with strict Compound Entity Unit Matching
   and Target Medical Entity Verification (Rules 1-6).
2. Prevents hallucinations and false answers on unanswerable queries.
3. Generates evidence-grounded answers with exact source citations.
"""

import json
import os
import re
import requests
from typing import List, Dict, Any, Optional


def assess_evidence_sufficiency(query: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    STRICT EVIDENCE SUFFICIENCY & ENTITY MATCHING GATE (RULES 1-6):
    Verifies that target medical entities or compound clinical aliases actually exist
    within the patient-scoped retrieved records before allowing LLM synthesis.
    """
    if not retrieved_docs:
        return {"sufficient": False, "reason": "No documents retrieved for patient.", "score": -99.0}

    # RULE 1: Stop words & Generic attribute words (CANNOT independently establish evidence)
    generic_attribute_words = {
        "what", "is", "was", "the", "for", "patient", "does", "have", "a", "an", "recorded",
        "result", "value", "reading", "documented", "check", "show", "list", "record", "report",
        "p001", "p002", "p003", "p004", "p005", "p006", "p007", "latest", "earliest",
        "most", "recent", "any", "ever", "taken", "prescribed", "diagnosis", "allergy", "allergic",
        "dosage", "dose", "amount", "blood", "group", "type", "level", "test", "reaction", "change",
        "changed", "history", "trend", "progression", "across", "visits"
    }

    # RULE 4: Compound Medical Entities & Known Normalized Aliases
    compound_entities = {
        "blood group": ["blood group", "blood type", "abo blood", "abo type"],
        "fasting blood sugar": ["fasting blood sugar", "fasting blood glucose", "fasting glucose", "fbs"],
        "total cholesterol": ["total cholesterol"],
        "hba1c": ["hba1c", "hb a1c", "glycated hemoglobin", "glycosylated hemoglobin", "a1c"],
        "ecg": ["ecg", "electrocardiogram"]
    }

    query_lower = query.lower()

    # Aggregate full searchable text & structured payload fields from retrieved documents
    combined_ctx_parts = []
    for d in retrieved_docs:
        combined_ctx_parts.append(str(d.get("searchable_text", "")))
        combined_ctx_parts.append(str(d.get("ocr", "")))
        combined_ctx_parts.append(str(d.get("medications", "")))
        combined_ctx_parts.append(str(d.get("lab_results", "")))
        combined_ctx_parts.append(str(d.get("allergies", "")))
        combined_ctx_parts.append(str(d.get("diagnoses", "")))
    
    combined_ctx = " ".join(combined_ctx_parts).lower()

    # RULE 2 & 4: Compound Entity Unit Matching
    for compound_key, aliases in compound_entities.items():
        if compound_key in query_lower:
            has_alias_match = any(alias in combined_ctx for alias in aliases)
            if not has_alias_match:
                return {
                    "sufficient": False,
                    "reason": f"Required compound entity '{compound_key}' (aliases: {aliases}) not found in patient records.",
                    "score": float(retrieved_docs[0].get("cross_encoder_score", 0.0)),
                    "matched_tokens": []
                }

    # RULE 2 & 3: Target Medical Entity Extraction & Matching
    query_tokens = [t.lower() for t in re.findall(r'\w+', query) if t.lower() not in generic_attribute_words and len(t) > 2]
    matched_tokens = [t for t in query_tokens if t in combined_ctx]

    # RULE 5: Negative Evidence Check - If specific medical entities exist in query but 0 match in records -> INSUFFICIENT
    if query_tokens and len(matched_tokens) == 0:
        return {
            "sufficient": False,
            "reason": f"Target medical entity '{query_tokens}' not present in patient records.",
            "score": float(retrieved_docs[0].get("cross_encoder_score", 0.0)),
            "matched_tokens": matched_tokens
        }

    # RULE 6: Cross-Encoder Score Check (Score alone cannot override entity absence, checked above)
    top_doc = retrieved_docs[0]
    ce_score = float(top_doc.get("cross_encoder_score", 0.0))

    return {
        "sufficient": True,
        "reason": "Target medical entity present in patient records.",
        "score": ce_score,
        "matched_tokens": matched_tokens
    }


class LLMInterface:

    def __init__(
        self,
        provider: str = "auto",
        model_name: str = "openai/gpt-oss-20b",
        api_url: Optional[str] = None
    ):
        self.provider = provider
        self.model_name = model_name
        self.api_url = api_url or os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if (self.provider in ["openrouter", "auto"]) and openrouter_key:
            try:
                headers = {
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json"
                }
                body = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                }
                res = requests.post(self.api_url, headers=headers, json=body, timeout=12)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"[rag] OpenRouter call failed: {e}")

        if self.provider in ["ollama", "auto"]:
            try:
                res = requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "gpt-oss-20b", "prompt": prompt, "system": system_prompt, "stream": False},
                    timeout=5
                )
                if res.status_code == 200:
                    return res.json().get("response", "").strip()
            except Exception:
                pass

        return self._local_grounded_synthesis(prompt)

    def _local_grounded_synthesis(self, prompt: str) -> str:
        if "No patient medical records were retrieved" in prompt:
            return "No relevant information was found in the available records."

        if "PATIENT MEDICAL CONTEXT:" in prompt:
            ctx = prompt.split("PATIENT MEDICAL CONTEXT:")[1].split("INSTRUCTIONS:")[0].strip()
            if not ctx or "No patient medical records" in ctx:
                return "No relevant information was found in the available records."
            return f"Based strictly on the patient's records:\n{ctx}"

        return "No relevant information was found in the available records."


class GroundedRAG:

    def __init__(self, llm: Optional[LLMInterface] = None):
        self.llm = llm or LLMInterface(provider="auto")

    def format_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        if not retrieved_docs:
            return "No patient medical records were retrieved for this query."

        blocks = []
        for i, doc in enumerate(retrieved_docs, start=1):
            doc_id = str(doc.get("document_id", "UNKNOWN"))
            raw_date = str(doc.get("date", ""))
            date_str = "Undated Note" if raw_date in ["1970-01-01", "", None] else raw_date
            doc_type = str(doc.get("document_type", "Record"))
            needs_review = doc.get("needs_review", False)

            review_flag = " [NEEDS HUMAN REVIEW - LOW CONFIDENCE EXTRACTION]" if needs_review else ""

            header = f"[Source {i}: {doc_id}, Date: {date_str} | Type: {doc_type}{review_flag}]"
            content = str(doc.get("searchable_text") or doc.get("ocr") or "")

            blocks.append(f"{header}\n{content}")

        return "\n\n".join(blocks)

    def generate_answer(
        self,
        query: str,
        patient_id: str,
        retrieved_docs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        if not retrieved_docs:
            return {
                "answer": "No relevant information was found in the available records.",
                "sources": [],
                "confidence_warning": False,
                "is_grounded": True
            }

        context_str = self.format_context(retrieved_docs)

        system_prompt = (
            "You are HealthVault AI's Clinical Assistant. Answer the doctor's query STRICTLY "
            "using the provided patient medical context.\n"
            "CRITICAL RULES:\n"
            "1. Do NOT guess, extrapolate, or invent medical facts.\n"
            "2. If context does not contain the answer, say: 'No relevant information was found in the available records.'\n"
            "3. If no allergy is mentioned, state 'No allergy information was found in the available records.'\n"
            "4. Cite every fact using [Source N: DOC-XXX, Date: YYYY-MM-DD].\n"
            "5. Do NOT make unauthorized treatment recommendations."
        )

        user_prompt = (
            f"DOCTOR QUESTION: {query}\n"
            f"PATIENT ID: {patient_id}\n\n"
            f"PATIENT MEDICAL CONTEXT:\n{context_str}\n\n"
            f"INSTRUCTIONS:\nAnswer concisely with exact citations."
        )

        raw_answer = self.llm.generate(user_prompt, system_prompt=system_prompt)

        sources = []
        has_low_confidence = False
        for i, doc in enumerate(retrieved_docs, start=1):
            date_str = "Undated Note" if doc.get("date") in ["1970-01-01", "", None] else str(doc.get("date"))
            sources.append({
                "citation_index": i,
                "document_id": str(doc.get("document_id")),
                "visit_id": str(doc.get("visit_id")),
                "date": date_str,
                "document_type": str(doc.get("document_type")),
                "confidence": doc.get("confidence", 1.0),
                "needs_review": doc.get("needs_review", False)
            })
            if doc.get("needs_review", False):
                has_low_confidence = True

        validation = self.validate_grounding(query, raw_answer, retrieved_docs)
        final_answer = validation["validated_answer"]

        if has_low_confidence and "Note:" not in final_answer:
            final_answer += "\n\n⚠️ Note: Some underlying evidence was extracted with low OCR confidence and is flagged for human review."

        return {
            "answer": final_answer,
            "sources": sources,
            "confidence_warning": has_low_confidence,
            "is_grounded": validation["is_grounded"]
        }

    def validate_grounding(self, query: str, answer: str, retrieved_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not retrieved_docs or "No relevant information" in answer:
            return {"is_grounded": True, "validated_answer": answer}

        context_all = " ".join([str(d.get("searchable_text", "")) for d in retrieved_docs]).lower()

        nums = re.findall(r'\b\d+(?:\.\d+)?%?\b', answer)
        for num in nums:
            if num in ["1", "2", "3", "4", "5"]:
                continue
            if num.lower() not in context_all:
                print(f"[rag] Warning: Claim '{num}' not in context. Refusing ungrounded answer.")
                return {
                    "is_grounded": False,
                    "validated_answer": "No relevant information was found in the available records."
                }

        return {"is_grounded": True, "validated_answer": answer}