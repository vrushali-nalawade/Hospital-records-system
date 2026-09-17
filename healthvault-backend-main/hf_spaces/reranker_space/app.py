import os
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
from sentence_transformers import CrossEncoder

app = FastAPI(title="HealthVault Cross-Encoder Reranker Microservice")

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"Loading {MODEL_NAME} on {DEVICE}...")
reranker = CrossEncoder(MODEL_NAME, device=DEVICE)
print(f"Model {MODEL_NAME} loaded successfully!")

class RerankRequest(BaseModel):
    query: str
    passages: List[str]

class RerankResponse(BaseModel):
    scores: List[float]
    count: int

@app.get("/")
def health_check():
    return {"status": "ok", "model": MODEL_NAME, "device": DEVICE}

@app.post("/rerank", response_model=RerankResponse)
def rerank(req: RerankRequest):
    if not req.passages:
        return {"scores": [], "count": 0}
    
    pairs = [[req.query, p] for p in req.passages]
    scores = reranker.predict(pairs)
    score_list = [float(s) for s in scores]
    return {
        "scores": score_list,
        "count": len(score_list)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
