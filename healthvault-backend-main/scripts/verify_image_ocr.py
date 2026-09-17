import os
import sys
import time
import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.database import SessionLocal
from backend.models import Document, ProcessingJob, Patient, User

def test_image_ocr_upload():
    print("=== STARTING IMAGE OCR UPLOAD VERIFICATION ===")
    db = SessionLocal()
    patient = db.query(Patient).filter(Patient.user_id == "browser_test_uid").first()
    canonical_patient_id = patient.id
    
    token = jwt.encode({
        "sub": "browser_test_uid",
        "user_id": "browser_test_uid",
        "email": "browser_test@healthvault.local",
        "role": "PATIENT",
        "exp": datetime.utcnow() + timedelta(hours=2)
    }, "secret", algorithm="HS256")
    
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app)
    
    # Read temp_cleaned.png or create an image with text
    img_path = "temp_cleaned.png"
    if not os.path.exists(img_path):
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (400, 150), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((20, 30), "Rx: Metformin 500mg twice daily\nDiagnosis: Type 2 Diabetes", fill=(0, 0, 0))
        img.save("temp_test_rx.png")
        img_path = "temp_test_rx.png"
        
    with open(img_path, "rb") as f:
        img_bytes = f.read()
        
    upload_res = client.post(
        "/documents/upload",
        headers=headers,
        data={"patient_id": canonical_patient_id},
        files={"file": ("prescription_rx.png", img_bytes, "image/png")}
    )
    
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    doc_id = upload_res.json()["document_id"]
    print(f"Uploaded Image: doc_id={doc_id}")
    
    # Poll status
    poll_count = 0
    final_status = None
    while poll_count < 60:
        time.sleep(1)
        poll_count += 1
        res = client.get(f"/documents/{doc_id}/status", headers=headers)
        data = res.json()
        print(f"Poll #{poll_count}: status={data.get('status')} job_status={data.get('job_status')}")
        if data.get("status") == "READY":
            final_status = "READY"
            break
            
    db.expire_all()
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    job = db.query(ProcessingJob).filter(ProcessingJob.document_id == doc_id).first()
    
    print(f"Final Image Doc Status: {doc.status}, Job Status: {job.status}")
    assert doc.status == "READY"
    assert job.status == "COMPLETED"
    print("=== IMAGE OCR VERIFICATION COMPLETED SUCCESSFULLY ===")
    db.close()

if __name__ == "__main__":
    test_image_ocr_upload()
