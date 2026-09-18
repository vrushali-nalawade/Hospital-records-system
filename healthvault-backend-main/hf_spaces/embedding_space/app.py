import os
import re
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModel
import gradio as gr

# 1. FastAPI REST API Core
api_app = FastAPI(
    title="HealthVault AI Cloud Microservice",
    description="Free Gradio + FastAPI microservice hosting BGE-M3 for HealthVault",
    version="1.0.0"
)

api_app.add_middleware(
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
print(f"[HealthVault AI] Model {EMBED_MODEL_NAME} loaded successfully on {DEVICE}!")

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int
    count: int

@api_app.post("/embed", response_model=EmbedResponse)
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

# 2. Gradio Interactive UI (100% Free Gradio Space SDK)
def interactive_demo(text: str):
    if not text.strip():
        return "Please enter a clinical note or prescription text."
    
    with torch.no_grad():
        inputs = tokenizer([text], padding=True, truncation=True, max_length=512, return_tensors="pt").to(DEVICE)
        outputs = model(**inputs)
        cls_rep = outputs.last_hidden_state[:, 0]
        norm_rep = torch.nn.functional.normalize(cls_rep.float(), p=2, dim=1)
        vec = norm_rep.cpu().tolist()[0]
        
    return (
        f"✅ Vector Generated Successfully!\n"
        f"• Dimensions: {len(vec)} (1024-d BGE-M3)\n"
        f"• Device: {DEVICE}\n"
        f"• Vector Sample: [{', '.join(f'{x:.4f}' for x in vec[:6])}...]\n\n"
        f"API Endpoint is LIVE at: POST /embed"
    )

demo = gr.Interface(
    fn=interactive_demo,
    inputs=gr.Textbox(
        lines=4,
        placeholder="Enter prescription text (e.g., Metformin 500mg twice daily for Type 2 Diabetes)...",
        label="Clinical Text Input"
    ),
    outputs=gr.Textbox(label="Vector Extraction Result"),
    title="🏥 HealthVault AI BGE-M3 Cloud Microservice",
    description="Free Gradio + FastAPI Cloud Endpoint for HealthVault Medical Locker RAG. Use `POST /embed` from your backend."
)

# Mount FastAPI endpoints into the Gradio application
app = gr.mount_gradio_app(api_app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
