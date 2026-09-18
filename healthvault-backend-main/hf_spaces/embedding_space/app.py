import os
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
from transformers import AutoTokenizer, AutoModel
import gradio as gr
import spaces

# 1. Initialize FastAPI app
app = FastAPI(
    title="HealthVault AI Cloud Microservice",
    description="ZeroGPU BGE-M3 embedding endpoint for HealthVault",
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

print(f"[HealthVault AI] Loading {EMBED_MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL_NAME)
model = AutoModel.from_pretrained(EMBED_MODEL_NAME)
model.eval()
print(f"[HealthVault AI] Model {EMBED_MODEL_NAME} initialized successfully!")

@spaces.GPU(duration=30)
def embed_batch_internal(texts: List[str]) -> List[List[float]]:
    """ZeroGPU batch embedder"""
    if torch.cuda.is_available() and next(model.parameters()).device.type != "cuda":
        model.to("cuda")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    inputs = tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)
        cls_rep = outputs.last_hidden_state[:, 0]
        norm_rep = torch.nn.functional.normalize(cls_rep.float(), p=2, dim=1)
        return norm_rep.cpu().tolist()

@spaces.GPU(duration=30)
def compute_single_embedding(text: str) -> str:
    """ZeroGPU Gradio UI handler"""
    if not text.strip():
        return "Please enter clinical or prescription text."
    vec = embed_batch_internal([text])[0]
    gpu_label = "NVIDIA A100 ZeroGPU ⚡" if torch.cuda.is_available() else "CPU"
    sample_preview = ", ".join(f"{v:.4f}" for v in vec[:6])
    return (
        f"✅ Vector Generated Successfully ({gpu_label})\n"
        f"• Dimensions: {len(vec)} (1024-d BGE-M3)\n"
        f"• Vector Sample: [{sample_preview}...]\n\n"
        f"REST API Endpoint: POST /embed"
    )

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int
    count: int

# 2. REST API Endpoints (Explicitly attached to FastAPI)
@app.post("/embed", response_model=EmbedResponse)
def api_embed(req: EmbedRequest):
    if not req.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")
    vectors = embed_batch_internal(req.texts)
    return {
        "embeddings": vectors,
        "dimension": len(vectors[0]),
        "count": len(vectors)
    }

@app.get("/health")
def api_health():
    return {
        "status": "ok",
        "service": "healthvault-ai-zerogpu",
        "model": EMBED_MODEL_NAME,
        "dimension": 1024
    }

# 3. Interactive Gradio UI
with gr.Blocks(title="HealthVault AI ZeroGPU BGE-M3") as demo:
    gr.Markdown("# 🏥 HealthVault AI Cloud Microservice")
    gr.Markdown("Free **Hugging Face ZeroGPU (NVIDIA A100)** accelerated vector embedding endpoint for **HealthVault Medical Locker**.")

    with gr.Row():
        with gr.Column():
            input_text = gr.Textbox(
                lines=4,
                placeholder="Enter prescription text (e.g., Metformin 500mg twice daily with meals for Type 2 Diabetes)...",
                label="Clinical Text"
            )
            submit_btn = gr.Button("⚡ Generate 1024-d BGE-M3 Embedding", variant="primary")
        with gr.Column():
            output_text = gr.Textbox(lines=6, label="Extraction & GPU Status")

    submit_btn.click(compute_single_embedding, inputs=input_text, outputs=output_text)

demo.queue()

# Mount Gradio UI at root of FastAPI
app = gr.mount_gradio_app(app, demo, path="/")
