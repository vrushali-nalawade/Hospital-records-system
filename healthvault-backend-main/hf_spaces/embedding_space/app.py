import os
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModel

app = FastAPI(title="HealthVault BGE-M3 Dense Embedding Microservice")

MODEL_NAME = "BAAI/bge-m3"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Loading {MODEL_NAME} on {DEVICE}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
if DEVICE == "cuda":
    model = model.half().to(DEVICE)
else:
    model = model.to(DEVICE)
model.eval()
print(f"Model {MODEL_NAME} loaded successfully!")

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int
    count: int

@app.get("/")
def health_check():
    return {"status": "ok", "model": MODEL_NAME, "device": DEVICE, "dimension": 1024}

@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest):
    if not req.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")
    
    with torch.no_grad():
        inputs = tokenizer(req.texts, padding=True, truncation=True, max_length=512, return_tensors="pt").to(DEVICE)
        outputs = model(**inputs)
        cls_rep = outputs.last_hidden_state[:, 0]
        norm_rep = torch.nn.functional.normalize(cls_rep.float(), p=2, dim=1)
        vectors = norm_rep.cpu().tolist()

    return {
        "embeddings": vectors,
        "dimension": len(vectors[0]),
        "count": len(vectors)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
