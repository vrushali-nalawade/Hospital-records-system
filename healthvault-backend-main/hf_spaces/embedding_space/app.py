import os
import re
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModel
import gradio as gr

# Hugging Face ZeroGPU Support (Free dynamic NVIDIA A100 GPU)
try:
    import spaces
    HAS_SPACES = True
    print("[HealthVault AI] Hugging Face ZeroGPU (spaces) module detected!")
except ImportError:
    HAS_SPACES = False
    class spaces:
        @staticmethod
        def GPU(func=None, duration=60):
            def decorator(f):
                return f
            return decorator(func) if func else decorator

# 1. FastAPI REST API Core
api_app = FastAPI(
    title="HealthVault AI ZeroGPU Cloud Microservice",
    description="Free ZeroGPU (NVIDIA A100) accelerated BGE-M3 microservice for HealthVault",
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

print(f"[HealthVault AI] Loading {EMBED_MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_NAME)
model = AutoModel.from_pretrained(EMBED_MODEL_NAME)
if torch.cuda.is_available():
    model = model.half().to("cuda")
model.eval()
print(f"[HealthVault AI] Model {EMBED_MODEL_NAME} initialized successfully!")

@spaces.GPU(duration=30)
def compute_bge_m3_embedding(texts: List[str]) -> List[List[float]]:
    """
    ZeroGPU Accelerated Dense Vector Extraction (Runs on NVIDIA A100)
    """
    target_device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Ensure model weights are on active GPU during ZeroGPU execution slice
    if torch.cuda.is_available() and next(model.parameters()).device.type != "cuda":
        model.to("cuda")

    with torch.no_grad():
        inputs = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(target_device)
        
        outputs = model(**inputs)
        cls_rep = outputs.last_hidden_state[:, 0]
        norm_rep = torch.nn.functional.normalize(cls_rep.float(), p=2, dim=1)
        return norm_rep.cpu().tolist()

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int
    count: int

@api_app.get("/")
def health_check():
    return {
        "service": "HealthVault AI ZeroGPU Microservice",
        "status": "online",
        "zerogpu": HAS_SPACES,
        "model": EMBED_MODEL_NAME,
        "dimension": 1024,
        "endpoint": "POST /embed"
    }

@api_app.post("/embed", response_model=EmbedResponse)
def generate_embeddings(req: EmbedRequest):
    if not req.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")

    vectors = compute_bge_m3_embedding(req.texts)

    return {
        "embeddings": vectors,
        "dimension": len(vectors[0]),
        "count": len(vectors)
    }

# 2. Gradio Interactive UI (100% Free Gradio Space + ZeroGPU)
def interactive_demo(text: str):
    if not text.strip():
        return "Please enter clinical or prescription text."
    
    vec = compute_bge_m3_embedding([text])[0]
    gpu_status = "NVIDIA A100 ZeroGPU Active 🚀" if torch.cuda.is_available() or HAS_SPACES else "CPU Mode"
        
    return (
        f"✅ Vector Generated on {gpu_status}!\n"
        f"• Dimensions: {len(vec)} (1024-d BGE-M3)\n"
        f"• Vector Sample: [{', '.join(f'{x:.4f}' for x in vec[:6])}...]\n\n"
        f"Backend API is LIVE at: POST /embed"
    )

demo = gr.Interface(
    fn=interactive_demo,
    inputs=gr.Textbox(
        lines=4,
        placeholder="Enter prescription text (e.g., Metformin 500mg twice daily for Type 2 Diabetes)...",
        label="Clinical Text Input"
    ),
    outputs=gr.Textbox(label="ZeroGPU Vector Extraction"),
    title="⚡ HealthVault AI ZeroGPU BGE-M3 Cloud Microservice",
    description="Free ZeroGPU (NVIDIA A100) Accelerated Cloud Endpoint for HealthVault Medical Locker RAG."
)

# Mount FastAPI endpoints into the Gradio application
app = gr.mount_gradio_app(api_app, demo, path="/")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
