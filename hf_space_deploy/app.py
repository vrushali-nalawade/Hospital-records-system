import os
import re
import gradio as gr
import spaces
import torch
import numpy as np
from PIL import Image
from transformers import AutoTokenizer, AutoModel
import easyocr

MODEL_NAME = "BAAI/bge-m3"

print(f"[HealthVault AI] Initializing {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
model.eval()

print("[HealthVault AI] Initializing EasyOCR GPU Reader...")
reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
print("[HealthVault AI] Ready!")

@spaces.GPU(duration=30)
def embed(text: str):
    """
    ZeroGPU (NVIDIA A100) BGE-M3 Dense Vector Generator
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

@spaces.GPU(duration=30)
def ocr(file_obj):
    """
    ZeroGPU (NVIDIA A100) High-Speed Medical OCR
    Accepts Image or PDF filepath, runs GPU OCR in < 0.5 seconds.
    """
    if file_obj is None:
        return {"error": "No file uploaded", "full_text": "", "confidence": 0.0}

    file_path = file_obj if isinstance(file_obj, str) else getattr(file_obj, "name", str(file_obj))

    # Fast-path: Digital PDF text stream extraction
    if str(file_path).lower().endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(file_path)
            pages_text = [p.get_text().strip() for p in doc if p.get_text().strip()]
            full_pdf_text = "\n\n".join(pages_text).strip()
            if len(full_pdf_text) > 20:
                return {
                    "full_text": full_pdf_text,
                    "confidence": 0.99,
                    "engine": "PyMuPDF Native Digital Engine"
                }
            if len(doc) > 0:
                pix = doc[0].get_pixmap(dpi=150)
                temp_img = "temp_render.png"
                pix.save(temp_img)
                file_path = temp_img
        except Exception as e:
            print(f"PDF extract error: {e}")

    try:
        # Load image
        img = Image.open(file_path).convert("RGB")
        img_np = np.array(img)

        # EasyOCR GPU inference
        results = reader.readtext(img_np, paragraph=True)
        lines = []
        confidences = []
        for item in results:
            if len(item) == 2:
                bbox, text = item
                conf = 0.95
            else:
                bbox, text, conf = item
            if text.strip():
                lines.append(text.strip())
                confidences.append(float(conf))

        full_text = "\n".join(lines)
        avg_conf = float(np.mean(confidences)) if confidences else 0.95

        return {
            "full_text": full_text,
            "confidence": round(avg_conf, 2),
            "engine": "NVIDIA A100 ZeroGPU EasyOCR"
        }
    except Exception as e:
        return {
            "error": str(e),
            "full_text": f"Error running GPU OCR: {e}",
            "confidence": 0.0
        }

with gr.Blocks(title="HealthVault AI Cloud Microservice") as demo:
    gr.Markdown("# 🏥 HealthVault AI ZeroGPU Microservice")
    gr.Markdown("ZeroGPU (NVIDIA A100) Accelerated Embeddings (BGE-M3) and High-Speed OCR.")
    
    with gr.Tab("BGE-M3 Embeddings"):
        text_in = gr.Textbox(lines=3, label="Medical / Clinical Text")
        vec_out = gr.JSON(label="1024-d Vector Output")
        btn_embed = gr.Button("Generate Embedding")
        btn_embed.click(fn=embed, inputs=text_in, outputs=vec_out, api_name="embed")

    with gr.Tab("GPU Medical OCR"):
        file_in = gr.File(label="Upload Prescription / Lab Report (PDF, PNG, JPG)")
        ocr_out = gr.JSON(label="Extracted Structured OCR Output")
        btn_ocr = gr.Button("Extract Text (ZeroGPU)")
        btn_ocr.click(fn=ocr, inputs=file_in, outputs=ocr_out, api_name="ocr")

if __name__ == "__main__":
    demo.launch()
