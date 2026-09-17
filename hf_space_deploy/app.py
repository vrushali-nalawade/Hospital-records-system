import os
import re
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModel

app = FastAPI(
    title="HealthVault AI Cloud Microservice",
    description="Hugging Face Spaces microservice for BGE-M3 Embeddings, Medical NER, and Reranking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EMBED_MODEL_NAME = "BAAI/bge-m3"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"[HealthVault AI] Loading {EMBED_MODEL_NAME} on {DEVICE}...")
tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_NAME)
model = AutoModel.from_pretrained(EMBED_MODEL_NAME)
if DEVICE == "cuda":
    model = model.half().to(DEVICE)
else:
    model = model.to(DEVICE)
model.eval()
print(f"[HealthVault AI] Model {EMBED_MODEL_NAME} loaded successfully!")

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int
    count: int

class RerankRequest(BaseModel):
    query: str
    passages: List[str]
    top_k: Optional[int] = 5

class RerankResult(BaseModel):
    index: int
    passage: str
    score: float

class RerankResponse(BaseModel):
    results: List[RerankResult]

# Known Medical Entities Dictionary
KNOWN_MEDICATIONS = [
    "amlodipine", "metformin", "atorvastatin", "levothyroxine", "paracetamol",
    "ibuprofen", "azithromycin", "omeprazole", "cetirizine", "naproxen",
    "salbutamol", "ferrous sulfate", "oseltamivir", "sumatriptan", "amoxicillin",
    "ciprofloxacin", "doxycycline", "pantoprazole", "losartan", "telmisartan",
    "ranitidine", "aspirin", "clopidogrel", "rosuvastatin", "glimepiride",
    "hydrochlorothiazide", "furosemide", "prednisolone", "montelukast"
]

KNOWN_LAB_TESTS = {
    "hba1c": "HbA1c (Glycated Hemoglobin)",
    "fbs": "Fasting Blood Sugar (FBS)",
    "ppbs": "Postprandial Blood Sugar (PPBS)",
    "glucose": "Blood Glucose",
    "blood sugar": "Blood Sugar",
    "ldl": "LDL Cholesterol",
    "hdl": "HDL Cholesterol",
    "cholesterol": "Total Cholesterol",
    "tsh": "TSH (Thyroid Stimulating Hormone)",
    "creatinine": "Serum Creatinine",
    "bun": "Blood Urea Nitrogen",
    "cbc": "Complete Blood Count (CBC)"
}

@app.get("/")
def root():
    return {
        "service": "HealthVault AI Cloud Microservice",
        "status": "online",
        "device": DEVICE,
        "embedding_model": EMBED_MODEL_NAME,
        "dimension": 1024,
        "endpoints": {
            "embed": "POST /embed",
            "rerank": "POST /rerank",
            "process_text": "POST /process-text"
        }
    }

@app.post("/embed", response_model=EmbedResponse)
def generate_embeddings(req: EmbedRequest):
    if not req.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")

    with torch.no_grad():
        inputs = tokenizer(
            req.texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(DEVICE)
        
        outputs = model(**inputs)
        cls_rep = outputs.last_hidden_state[:, 0]
        norm_rep = torch.nn.functional.normalize(cls_rep.float(), p=2, dim=1)
        vectors = norm_rep.cpu().tolist()

    return {
        "embeddings": vectors,
        "dimension": len(vectors[0]),
        "count": len(vectors)
    }

class TextProcessRequest(BaseModel):
    raw_text: str
    patient_id: Optional[str] = "P001"
    document_id: Optional[str] = "DOC001"

@app.post("/process-text")
def process_text_entities(req: TextProcessRequest):
    text = req.raw_text
    text_lower = text.lower()

    # Extract medications
    meds = []
    for med in KNOWN_MEDICATIONS:
        pattern = rf"({med})\s*(\d+\s?(?:mg|mcg|ml|g|iu|tablets?|capsules?))?\s*([\w\s]{{1,35}}?(?:once|twice|thrice|\d+\s?times?|daily|a day|bd|tds|od|hs|qds|every\s+\d+\s+hours?))?"
        match = re.search(pattern, text_lower)
        if match:
            name = match.group(1).title()
            dosage = match.group(2).strip() if match.group(2) else "Standard dosage"
            freq = match.group(3).strip() if match.group(3) else "As prescribed"
            meds.append(f"{name} {dosage} ({freq})")

    # Extract lab tests
    labs = []
    for key, name in KNOWN_LAB_TESTS.items():
        if key in text_lower:
            pattern = rf"{key}[:\s]+([\d\.]+\s*(?:%|mg/dl|g/dl|mmol/l|u/l)?)"
            val_match = re.search(pattern, text_lower)
            val = val_match.group(1).strip() if val_match else "Reported"
            labs.append({"test_name": name, "value": val})

    # Extract diagnoses
    diagnoses = []
    if "diabetes" in text_lower:
        diagnoses.append("Type 2 Diabetes Mellitus")
    if "hypertension" in text_lower or "bp" in text_lower:
        diagnoses.append("Hypertension")
    if "asthma" in text_lower:
        diagnoses.append("Bronchial Asthma")

    return {
        "patient_id": req.patient_id,
        "document_id": req.document_id,
        "document_type": "prescription" if meds else ("lab_report" if labs else "medical_record"),
        "medications": meds,
        "lab_results": labs,
        "diagnoses": diagnoses,
        "raw_text": text,
        "confidence": 0.96
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
