import gradio as gr
import spaces
import torch
from transformers import AutoTokenizer, AutoModel

MODEL_NAME = "BAAI/bge-m3"

print(f"[HealthVault AI] Loading {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
model.eval()
print(f"[HealthVault AI] Model {MODEL_NAME} loaded successfully!")

@spaces.GPU(duration=30)
def embed(text: str):
    """
    ZeroGPU (NVIDIA A100) BGE-M3 Dense Vector Extractor
    Exposed as REST API via api_name="embed"
    """
    if not text or not str(text).strip():
        return []

    if torch.cuda.is_available() and next(model.parameters()).device.type != "cuda":
        model.to("cuda")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    inputs = tokenizer([str(text)], padding=True, truncation=True, max_length=512, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model(**inputs)
        cls_rep = outputs.last_hidden_state[:, 0]
        norm_rep = torch.nn.functional.normalize(cls_rep.float(), p=2, dim=1)
        vector = norm_rep.cpu().tolist()[0]

    return vector

demo = gr.Interface(
    fn=embed,
    inputs=gr.Textbox(
        lines=4,
        placeholder="Enter prescription or clinical text (e.g., Metformin 500mg twice daily with meals for Type 2 Diabetes)...",
        label="Clinical Text"
    ),
    outputs=gr.JSON(label="1024-d BGE-M3 Vector"),
    title="🏥 HealthVault AI BGE-M3 ZeroGPU Embedder",
    description="Free ZeroGPU (NVIDIA A100) Accelerated Cloud Vector Microservice for HealthVault Medical Locker.",
    api_name="embed"
)

if __name__ == "__main__":
    demo.launch()
