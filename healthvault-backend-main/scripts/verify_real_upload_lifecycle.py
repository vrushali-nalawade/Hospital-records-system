import os
import sys
import time
import jwt
from datetime import datetime, timedelta
from io import BytesIO
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.database import SessionLocal
from backend.models import Document, ProcessingJob, Patient, User

def test_full_browser_upload_lifecycle():
    print("=== STARTING FULL UPLOAD LIFECYCLE VERIFICATION ===")
    
    # 1. Setup DB session and test patient
    db = SessionLocal()
    
    # Create / ensure a patient user
    user = db.query(User).filter(User.id == "browser_test_uid").first()
    if not user:
        user = User(id="browser_test_uid", email="browser_test@healthvault.local", role="PATIENT")
        db.add(user)
        db.commit()
        db.refresh(user)
        
    patient = db.query(Patient).filter(Patient.user_id == "browser_test_uid").first()
    if not patient:
        count = db.query(Patient).count()
        patient = Patient(id=f"P{count+1:03d}", user_id="browser_test_uid", name="Browser Test Patient")
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
    canonical_patient_id = patient.id
    print(f"[1] Patient resolved: patient_id={canonical_patient_id}, user_id={user.id}")
    
    # 2. Generate Auth Token
    token = jwt.encode({
        "sub": user.id,
        "user_id": user.id,
        "email": user.email,
        "role": "PATIENT",
        "exp": datetime.utcnow() + timedelta(hours=2)
    }, "secret", algorithm="HS256")
    
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(app)
    
    # 3. Prepare real sample medical document (prescription)
    sample_text = b"%PDF-1.4 sample prescription Metformin 500mg daily Type 2 Diabetes"
    file_bytes = BytesIO(sample_text)
    
    # 4. Perform POST /documents/upload
    print("\n[2] Executing POST /documents/upload ...")
    upload_res = client.post(
        "/documents/upload",
        headers=headers,
        data={"patient_id": canonical_patient_id},
        files={"file": ("test_prescription.pdf", file_bytes, "application/pdf")}
    )
    
    print(f"Upload response HTTP status: {upload_res.status_code}")
    assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
    upload_data = upload_res.json()
    doc_id = upload_data["document_id"]
    initial_status = upload_data["status"]
    print(f"Upload Response JSON: document_id={doc_id}, status={initial_status}")
    
    # 5. Check Initial Database State
    db.expire_all()
    initial_doc = db.query(Document).filter(Document.document_id == doc_id).first()
    initial_job = db.query(ProcessingJob).filter(ProcessingJob.document_id == doc_id).first()
    print(f"\n[3] Initial DB State: Document status={initial_doc.status}, Job status={initial_job.status if initial_job else 'None'}, Job ID={initial_job.job_id if initial_job else 'None'}")
    
    # 6. Simulate Frontend Polling Loop (matching records-service.ts)
    print("\n[4] Simulating Frontend Polling Loop on GET /documents/{doc_id}/status ...")
    poll_count = 0
    max_polls = 60
    final_status = None
    
    while poll_count < max_polls:
        time.sleep(1)
        poll_count += 1
        
        status_res = client.get(f"/documents/{doc_id}/status", headers=headers)
        assert status_res.status_code == 200, f"Status check failed: {status_res.text}"
        status_data = status_res.json()
        curr_status = status_data.get("status")
        job_status = status_data.get("job_status")
        
        print(f"  [Poll #{poll_count:02d}] Document Status: {curr_status} | Job Status: {job_status}")
        
        if curr_status in ["READY", "PROCESSED"] or job_status == "COMPLETED":
            final_status = "READY"
            break
        elif curr_status == "FAILED" or job_status == "FAILED":
            final_status = "FAILED"
            break
            
    # 7. Verify Final States
    db.expire_all()
    final_doc = db.query(Document).filter(Document.document_id == doc_id).first()
    final_job = db.query(ProcessingJob).filter(ProcessingJob.document_id == doc_id).first()
    
    print("\n=== FINAL VERIFICATION RESULTS ===")
    print(f"Real Document ID: {doc_id}")
    print(f"Patient ID: {canonical_patient_id}")
    print(f"Processing Job ID: {final_job.job_id if final_job else 'N/A'}")
    print(f"Final Document Status in DB: {final_doc.status}")
    print(f"Final Job Status in DB: {final_job.status if final_job else 'N/A'}")
    print(f"Job Error Message: {final_job.error_message if final_job else 'None'}")
    print(f"Extracted Document Type: {final_doc.document_type}")
    print(f"Document Confidence: {final_doc.confidence}")
    print(f"Document Processed At: {final_doc.processed_at}")
    print(f"Document Storage Path: {final_doc.storage_path}")
    
    assert final_doc.status == "READY", f"Expected READY, got {final_doc.status}"
    assert final_job.status == "COMPLETED", f"Expected COMPLETED, got {final_job.status}"
    print("\n>>> ALL VERIFICATIONS PASSED SUCCESSFULLY! <<<")
    db.close()

if __name__ == "__main__":
    test_full_browser_upload_lifecycle()
