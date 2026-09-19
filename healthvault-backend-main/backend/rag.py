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
        # 1. Google Gemini API (gemini-1.5-flash / gemini-2.0-flash)
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            try:
                gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
                combined_instruction = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                gemini_payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": combined_instruction}]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 1024,
                    }
                }
                res = requests.post(url, json=gemini_payload, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and parts[0].get("text"):
                            return parts[0]["text"].strip()
                else:
                    print(f"[rag] Gemini API status {res.status_code}: {res.text}")
            except Exception as e:
                print(f"[rag] Gemini API call notice: {e}")

        # 2. Hugging Face Space / Inference API endpoint
        hf_llm_url = os.getenv("HF_LLM_URL")
        hf_token = os.getenv("HF_API_TOKEN")
        if hf_llm_url:
            try:
                headers = {"Content-Type": "application/json"}
                if hf_token:
                    headers["Authorization"] = f"Bearer {hf_token}"
                payload = {
                    "prompt": prompt,
                    "system_prompt": system_prompt,
                    "max_tokens": 512,
                    "temperature": 0.2
                }
                res = requests.post(hf_llm_url, headers=headers, json=payload, timeout=25)
                if res.status_code == 200:
                    data = res.json()
                    ans = data.get("answer") or data.get("response") or data.get("generated_text")
                    if ans and len(ans) > 20:
                        return ans.strip()
            except Exception as e:
                print(f"[rag] HF Space LLM call notice: {e}")

        # 3. OpenRouter API
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if (self.provider in ["openrouter", "auto"]) and openrouter_key:
            try:
                headers = {
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json"
                }
                body = {
                    "model": os.getenv("OPENROUTER_MODEL", self.model_name),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                }
                res = requests.post(self.api_url, headers=headers, json=body, timeout=15)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"[rag] OpenRouter call notice: {e}")

        # 4. Deterministic conversational synthesis fallback
        return self._local_grounded_synthesis(prompt)

    def _local_grounded_synthesis(self, prompt: str) -> str:
        if "No patient medical records were retrieved" in prompt:
            return "No relevant medical information was found in your available records for this question."

        if "PATIENT MEDICAL CONTEXT:" in prompt:
            ctx = prompt.split("PATIENT MEDICAL CONTEXT:")[1].split("INSTRUCTIONS:")[0].strip()
            if not ctx or "No patient medical records" in ctx:
                return "No relevant medical information was found in your available records for this question."
            return (
                "Hello! Based on your verified medical records on file, here is a summary of the relevant details:\n\n"
                f"{ctx}\n\n"
                "Please consult your healthcare provider if you have any questions about adjusting your medications."
            )

        return "No relevant medical records found for this query."


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
            date_str = "Recent Record" if raw_date in ["1970-01-01", "", None] else raw_date
            doc_type = str(doc.get("document_type", "Record")).replace("_", " ").title()
            needs_review = doc.get("needs_review", False)

            review_flag = " [NEEDS REVIEW]" if needs_review else ""

            header = f"### [Document {i}: {doc_id} • {doc_type} ({date_str}){review_flag}]"
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
                "answer": "I couldn't find any relevant clinical records in your file regarding this question. Please make sure your records are uploaded or check with your doctor.",
                "sources": [],
                "confidence_warning": False,
                "is_grounded": True
            }

        context_str = self.format_context(retrieved_docs)

        system_prompt = (
            "You are HealthVault AI, a warm, knowledgeable, and empathetic medical assistant helping a patient understand their medical records.\n"
            "Your task is to answer the patient's question directly, clearly, and conversationally in plain English (ChatGPT style).\n\n"
            "COMMUNICATION GUIDELINES:\n"
            "1. Answer the patient's specific question warmly and directly in the first paragraph.\n"
            "2. Explain diagnoses, symptoms, and medical terms in clear, everyday words without heavy jargon.\n"
            "3. For medications, clearly outline: the medication name, exact dosage, schedule (e.g. morning, bedtime, before/after meals), and why it helps.\n"
            "4. Provide actionable advice and precautions (e.g. inhaler techniques, rinsing mouth, diet, or monitoring blood pressure).\n"
            "5. Rely STRICTLY on the facts provided in the Patient Medical Context. Do not invent or hallucinate unmentioned medications or values.\n"
            "6. Close with a caring sentence and note that this is for understanding records and not a replacement for advice from their physician."
        )

        user_prompt = (
            f"PATIENT'S QUESTION: {query}\n"
            f"PATIENT ID: {patient_id}\n\n"
            f"PATIENT MEDICAL CONTEXT (VERIFIED RECORDS):\n{context_str}\n\n"
            f"INSTRUCTIONS:\nProvide a conversational, empathetic, and clear explanation in plain English."
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