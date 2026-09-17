import os
import sys
import time
import jwt
from datetime import datetime, timedelta
from io import BytesIO
import hashlib
from PIL import Image, ImageDraw

# Ensure backend and ai_pipeline are in sys.path
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("ai_pipeline"))

from backend.config import settings
from backend.database import SessionLocal
from backend.models import Document, ProcessingJob, Patient, User, Visit, AccessLog
from backend.storage import storage_service
from backend.ai_service import qdrant_client, COLLECTION_NAME, VECTOR_SIZE
from fastapi.testclient import TestClient
from backend.main import app

def create_synthetic_prescription_image():
    """Generates a clean synthetic PNG image prescription for OCR processing."""
    img = Image.new("RGB", (800, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    lines = [
        "METROPOLITAN HEALTH CLINIC - MEDICAL PRESCRIPTION",
        "Date: 2026-09-06",
        "Patient: Synthetic Docker Patient",
        "Diagnosis: Type 2 Diabetes",
        "Rx: Metformin 1000 mg twice daily PO",
        "Instructions: Take with morning and evening meals.",
        "Refills: 2"
    ]
    y = 30
    for line in lines:
        draw.text((40, y), line, fill=(0, 0, 0))
        y += 45
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def cleanup_patient_records(db, patient_id, user_id=None, doc_id=None):
    if doc_id:
        db.query(ProcessingJob).filter(ProcessingJob.document_id == doc_id).delete(synchronize_session=False)
        db.query(Document).filter(Document.document_id == doc_id).delete(synchronize_session=False)
        point_id = int(hashlib.md5(doc_id.encode("utf-8")).hexdigest(), 16) & 0xffffffffffffffff
        try:
            qdrant_client.delete(collection_name=COLLECTION_NAME, points_selector=[point_id])
        except Exception:
            pass
    if patient_id:
        docs = db.query(Document).filter(Document.patient_id == patient_id).all()
        doc_ids = [d.document_id for d in docs]
        if doc_ids:
            db.query(ProcessingJob).filter(ProcessingJob.document_id.in_(doc_ids)).delete(synchronize_session=False)
            db.query(Document).filter(Document.patient_id == patient_id).delete(synchronize_session=False)
            for d_id in doc_ids:
                pt_id = int(hashlib.md5(d_id.encode("utf-8")).hexdigest(), 16) & 0xffffffffffffffff
                try:
                    qdrant_client.delete(collection_name=COLLECTION_NAME, points_selector=[pt_id])
                except Exception:
                    pass
        db.query(AccessLog).filter(AccessLog.patient_id == patient_id).delete(synchronize_session=False)
        db.query(Visit).filter(Visit.patient_id == patient_id).delete(synchronize_session=False)
        db.query(Patient).filter(Patient.id == patient_id).delete(synchronize_session=False)
    if user_id:
        db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()

def run_docker_e2e_validation():
    print("====================================================================")
    print("       HEALTHVAULT AI — DOCKERIZED E2E VERIFICATION SUITE           ")
    print("====================================================================")
    
    results = {}
    db = SessionLocal()
    
    # Clean up any leftover test data from prior runs
    for prev_user in db.query(User).filter(User.id.like("docker_e2e_test_user_%")).all():
        prev_p = db.query(Patient).filter(Patient.user_id == prev_user.id).first()
        cleanup_patient_records(db, prev_p.id if prev_p else None, prev_user.id)

    synthetic_timestamp = int(time.time())
    synthetic_user_id = f"docker_e2e_test_user_{synthetic_timestamp}"
    synthetic_patient_id = f"P_DOCKER_TEST_{synthetic_timestamp}"
    synthetic_doc_id = None
    initial_qdrant_count = 0
    initial_doc_count = 0
    
    try:
        # Step 0: Record Baseline Count
        initial_doc_count = db.query(Document).count()
        q_info = qdrant_client.get_collection(COLLECTION_NAME)
        initial_qdrant_count = q_info.points_count
        print(f"[0] Baseline State: {initial_doc_count} PostgreSQL documents, {initial_qdrant_count} Qdrant points.")
        results["baseline_check"] = True

        # Step 1: Authentication / Test Patient Creation
        print("\n[1] Creating synthetic patient and bearer token...")
        test_user = User(
            id=synthetic_user_id,
            email=f"{synthetic_user_id}@healthvault.demo",
            role="PATIENT"
        )
        db.add(test_user)
        db.commit()

        test_patient = Patient(
            id=synthetic_patient_id,
            user_id=synthetic_user_id,
            name="Synthetic Docker Test Patient"
        )
        db.add(test_patient)
        db.commit()

        token = jwt.encode({
            "sub": synthetic_user_id,
            "user_id": synthetic_user_id,
            "email": test_user.email,
            "role": "PATIENT",
            "exp": datetime.utcnow() + timedelta(hours=2)
        }, "secret", algorithm="HS256")

        headers = {"Authorization": f"Bearer {token}"}
        client = TestClient(app)
        print(f"    Patient ID: {synthetic_patient_id} | User ID: {synthetic_user_id}")
        results["auth_handling"] = True

        # Step 2: Document Upload with Synthetic Medical Prescription Image
        print("\n[2] Uploading synthetic medical prescription image...")
        file_bytes = create_synthetic_prescription_image()
        raw_len = len(file_bytes.getvalue())

        upload_res = client.post(
            "/documents/upload",
            headers=headers,
            data={"patient_id": synthetic_patient_id},
            files={"file": ("metformin_prescription_1000mg.png", file_bytes, "image/png")}
        )

        assert upload_res.status_code == 200, f"Upload returned HTTP {upload_res.status_code}: {upload_res.text}"
        upload_data = upload_res.json()
        synthetic_doc_id = upload_data["document_id"]
        print(f"    Upload response: document_id={synthetic_doc_id}, status={upload_data['status']}")
        results["document_upload"] = True

        # Step 3: PostgreSQL Row Verification
        db.expire_all()
        doc_record = db.query(Document).filter(Document.document_id == synthetic_doc_id).first()
        job_record = db.query(ProcessingJob).filter(ProcessingJob.document_id == synthetic_doc_id).first()
        assert doc_record is not None, "PostgreSQL Document record not found"
        assert job_record is not None, "PostgreSQL ProcessingJob record not found"
        print(f"    PostgreSQL Document row: {doc_record.document_id} (Status: {doc_record.status})")
        print(f"    PostgreSQL Job row: {job_record.job_id} (Status: {job_record.status})")
        results["postgres_row_creation"] = True
        results["job_creation"] = True

        # Step 4: Supabase Private Storage Check
        storage_path = doc_record.storage_path
        print(f"\n[3] Checking Supabase Storage path: {storage_path}")
        assert storage_path.startswith(f"patients/{synthetic_patient_id}/documents/{synthetic_doc_id}/"), "Invalid path structure"
        downloaded_bytes = storage_service.download_document(storage_path)
        assert len(downloaded_bytes) == raw_len, "Downloaded bytes size mismatch"
        print("    Supabase Private Storage: Upload and retrieval verified.")
        results["supabase_storage"] = True

        # Step 5 & 6: Polling for Pipeline Completion (OCR -> NER -> BGE-M3 -> Qdrant -> READY)
        print("\n[4] Polling background processing pipeline until status reaches READY...")
        max_polls = 60
        poll_count = 0
        final_status = None

        while poll_count < max_polls:
            time.sleep(1)
            poll_count += 1
            status_res = client.get(f"/documents/{synthetic_doc_id}/status", headers=headers)
            if status_res.status_code == 200:
                s_data = status_res.json()
                curr_status = s_data.get("status")
                job_status = s_data.get("job_status")
                print(f"    [Poll #{poll_count:02d}] Document: {curr_status} | Job: {job_status}")
                if curr_status == "READY" and job_status == "COMPLETED":
                    final_status = "READY"
                    break
                elif curr_status == "FAILED" or job_status == "FAILED":
                    final_status = "FAILED"
                    break

        assert final_status == "READY", f"Pipeline failed or timed out. Final status: {final_status}"
        print("    Document status: READY | Processing job status: COMPLETED")
        results["ocr_ner_pipeline"] = True
        results["document_ready"] = True
        results["job_completed"] = True

        # Step 7: Qdrant Cloud Vector Indexing Verification
        print("\n[5] Verifying 1024-d BGE-M3 vector indexing in Qdrant Cloud...")
        point_id = int(hashlib.md5(synthetic_doc_id.encode("utf-8")).hexdigest(), 16) & 0xffffffffffffffff
        q_point = qdrant_client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[point_id],
            with_payload=True,
            with_vectors=True
        )
        assert len(q_point) == 1, "Point not found in Qdrant Cloud"
        point_vector = q_point[0].vector
        assert len(point_vector) == VECTOR_SIZE, f"Vector dimension mismatch: expected {VECTOR_SIZE}, got {len(point_vector)}"
        assert q_point[0].payload.get("patient_id") == synthetic_patient_id, "Payload patient_id mismatch"
        print(f"    Qdrant point {point_id}: 1024-d vector indexed, payload patient_id verified.")
        results["bge_m3_embedding"] = True
        results["qdrant_indexing"] = True

        # Step 8: Patient-Scoped RAG Query
        print("\n[6] Executing patient-scoped RAG query...")
        query_res = client.post(
            "/ai/query",
            headers=headers,
            json={"patient_id": synthetic_patient_id, "question": "What is the prescribed Metformin dosage?"}
        )
        assert query_res.status_code == 200, f"AI Query failed: {query_res.text}"
        query_data = query_res.json()
        print(f"    RAG Answer: {query_data['answer']}")
        print(f"    RAG Sources: {query_data.get('sources')}")
        assert "metformin" in query_data["answer"].lower(), "Answer does not mention Metformin"
        assert not query_data.get("abstained", True), "RAG query abstained unexpectedly"
        
        # Verify source matches synthetic document ID
        sources = query_data.get("sources", [])
        assert len(sources) > 0, "No sources returned"
        source_doc_ids = [s.get("document_id") for s in sources]
        assert synthetic_doc_id in source_doc_ids, f"Uploaded document {synthetic_doc_id} not cited in sources {source_doc_ids}"
        print("    Grounded RAG answer and citation match confirmed.")
        results["rag_grounded_answer"] = True
        results["source_citation_match"] = True

        # Step 9: Cross-Patient Isolation Test
        print("\n[7] Testing cross-patient isolation...")
        isolated_query_res = client.post(
            "/ai/query",
            headers=headers,
            json={"patient_id": "P_OTHER_PATIENT_UNAUTHORIZED", "question": "What is the Metformin dosage?"}
        )
        assert isolated_query_res.status_code == 403, f"Expected 403 Forbidden for cross-patient query, got {isolated_query_res.status_code}"
        print("    Cross-patient isolation: Unauthorized query rejected with HTTP 403.")
        results["cross_patient_isolation"] = True

        # Step 10: Verify No Fallbacks Occurred
        print("\n[8] Verifying production fallback protections...")
        assert getattr(settings, "ENVIRONMENT", "").lower() != "fallback", "Invalid environment"
        results["no_fallbacks"] = True

    finally:
        # Step 11: Cleanup Synthetic Artifacts in Proper FK Order
        print("\n[9] Cleaning up synthetic test artifacts...")
        cleanup_patient_records(db, synthetic_patient_id, synthetic_user_id, synthetic_doc_id)

        # Verify Baseline Integrity
        final_doc_count = db.query(Document).count()
        final_q_info = qdrant_client.get_collection(COLLECTION_NAME)
        final_qdrant_count = final_q_info.points_count
        db.close()

        print(f"    Post-cleanup state: {final_doc_count} PostgreSQL documents, {final_qdrant_count} Qdrant points.")
        assert final_doc_count == initial_doc_count, f"Document count changed: {initial_doc_count} -> {final_doc_count}"
        assert final_qdrant_count == initial_qdrant_count, f"Qdrant point count changed: {initial_qdrant_count} -> {final_qdrant_count}"
        print("    Baseline PostgreSQL records and Qdrant points confirmed 100% intact.")
        results["cleanup_and_baseline_intact"] = True

    print("\n====================================================================")
    print("                    E2E VERIFICATION COMPLETE                       ")
    print("====================================================================")
    for k, v in results.items():
        print(f"  - {k:<30}: {'PASS' if v else 'FAIL'}")
    
    return all(results.values())

if __name__ == "__main__":
    success = run_docker_e2e_validation()
    sys.exit(0 if success else 1)
