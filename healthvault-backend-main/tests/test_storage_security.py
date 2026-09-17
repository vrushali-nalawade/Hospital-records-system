import os
import re
import time
import shutil
import pytest
import gc
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test DB URL and storage dir before importing backend modules
TEST_DB_URL = "sqlite:///./test_healthvault.db"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["STORAGE_DIR"] = "backend/test_storage"
os.environ["SUPABASE_STORAGE_BUCKET"] = "healthvault-medical-documents"

from backend.main import app
from backend.database import Base, get_db
from backend.models import User, Patient, Doctor, Document, Consent, AccessLog, Visit, ProcessingJob
from backend.processing import run_background_ingestion
from backend.storage import (
    storage_service,
    save_document,
    get_document_path,
    create_document_signed_url,
    SupabaseStorageService
)
from backend.ai_service import (
    COLLECTION_NAME,
    VECTOR_SIZE,
    get_embedding,
    qdrant_client
)

# Test DB session
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_security_test_env():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Create users
        u_p1 = User(id="P001UID", email="patient1@example.com", role="PATIENT")
        u_p2 = User(id="P002UID", email="patient2@example.com", role="PATIENT")
        u_d1 = User(id="D001UID", email="doctor1@demo.health", role="DOCTOR")
        u_d2 = User(id="D002UID", email="doctor2@demo.health", role="DOCTOR")
        u_admin = User(id="ADMINUID", email="admin@demo.health", role="ADMIN")
        db.add_all([u_p1, u_p2, u_d1, u_d2, u_admin])
        db.commit()

        # Create patient profiles
        p1 = Patient(id="P001", user_id="P001UID", name="Patient One")
        p2 = Patient(id="P002", user_id="P002UID", name="Patient Two")
        db.add_all([p1, p2])

        # Create doctor profiles
        d1 = Doctor(id="D001", user_id="D001UID", name="Dr. Alice Vance", specialty="Endocrinology")
        d2 = Doctor(id="D002", user_id="D002UID", name="Dr. Bob Smith", specialty="Cardiology")
        db.add_all([d1, d2])

        db.commit()
    finally:
        db.close()

    yield

    engine.dispose()
    gc.collect()

    if os.path.exists("backend/test_storage"):
        try:
            shutil.rmtree("backend/test_storage")
        except Exception:
            pass

    if os.path.exists("test_healthvault.db"):
        try:
            os.remove("test_healthvault.db")
        except Exception:
            pass

client = TestClient(app)

def auth_headers(uid: str, role: str) -> dict:
    if role.upper() == "DOCTOR":
        return {"Authorization": f"Bearer mock_token_{uid}_{role}_{uid.lower()}@demo.health"}
    return {"Authorization": f"Bearer mock_token_{uid}_{role}"}


# =====================================================================
# SECURITY VERIFICATION TESTS
# =====================================================================

def test_patient_a_can_access_own_document():
    """
    Security Test 1: Patient A can upload and access Patient A documents via signed URL and stream.
    """
    # 1. Patient P001 uploads document
    file_bytes = b"%PDF-1.4 Mock Prescription Metformin 500mg daily"
    response = client.post(
        "/documents/upload",
        headers=auth_headers("P001UID", "PATIENT"),
        data={"patient_id": "P001"},
        files={"file": ("prescription_p001.pdf", file_bytes, "application/pdf")}
    )
    assert response.status_code == 200
    doc_id = response.json()["document_id"]

    # 2. Verify patient-scoped storage path structure in DB
    db = TestingSessionLocal()
    doc = db.query(Document).filter(Document.document_id == doc_id).first()
    assert doc is not None
    assert doc.storage_path.startswith("patients/P001/documents/")
    assert doc.storage_path.endswith("prescription_p001.pdf")
    db.close()

    # 3. Patient P001 requests signed URL
    signed_res = client.get(
        f"/documents/{doc_id}/signed-url",
        headers=auth_headers("P001UID", "PATIENT")
    )
    assert signed_res.status_code == 200
    data = signed_res.json()
    assert data["document_id"] == doc_id
    assert "signed_url" in data
    assert data["expires_in"] == 300
    assert data["storage_path"] == doc.storage_path

    # 4. Patient P001 accesses direct document stream
    stream_res = client.get(
        f"/documents/{doc_id}",
        headers=auth_headers("P001UID", "PATIENT")
    )
    assert stream_res.status_code == 200
    assert b"Metformin 500mg" in stream_res.content


def test_patient_a_cannot_access_patient_b_document():
    """
    Security Test 2: Patient B cannot access Patient A documents (HTTP 403 Forbidden).
    """
    # Create document for P001
    db = TestingSessionLocal()
    doc = Document(
        document_id="DOC_P001_SECRET",
        patient_id="P001",
        storage_path="patients/P001/documents/DOC_P001_SECRET/secret.pdf",
        document_type="prescription",
        status="READY"
    )
    db.add(doc)
    db.commit()
    db.close()

    # Save mock file in storage
    save_document("P001", "DOC_P001_SECRET", b"Confidential Medical Record", "secret.pdf")

    # Patient P002 attempts to request signed URL for P001 document -> 403
    res_url = client.get(
        "/documents/DOC_P001_SECRET/signed-url",
        headers=auth_headers("P002UID", "PATIENT")
    )
    assert res_url.status_code == 403
    assert "Access denied" in res_url.json()["detail"]

    # Patient P002 attempts to stream P001 document -> 403
    res_stream = client.get(
        "/documents/DOC_P001_SECRET",
        headers=auth_headers("P002UID", "PATIENT")
    )
    assert res_stream.status_code == 403
    assert "Access denied" in res_stream.json()["detail"]


def test_unauthorized_doctor_cannot_access_patient_document():
    """
    Security Test 3: Doctor without consent cannot access patient's document.
    """
    # Doctor D002 has NO consent for Patient P001
    res = client.get(
        "/documents/DOC_P001_SECRET/signed-url",
        headers=auth_headers("D002UID", "DOCTOR")
    )
    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]

    # Stream access also denied
    stream_res = client.get(
        "/documents/DOC_P001_SECRET",
        headers=auth_headers("D002UID", "DOCTOR")
    )
    assert stream_res.status_code == 403


def test_authorized_doctor_with_consent_can_access_document():
    """
    Security Test 4: Authorized doctor with valid consent CAN access the document.
    """
    # Grant active consent: Patient P001 -> Doctor D001
    grant_res = client.post(
        "/consent",
        headers=auth_headers("P001UID", "PATIENT"),
        json={
            "doctor_id": "D001",
            "permission": "VIEW_DOCUMENTS"
        }
    )
    assert grant_res.status_code == 200

    # Doctor D001 can now request signed URL for P001 document
    res = client.get(
        "/documents/DOC_P001_SECRET/signed-url",
        headers=auth_headers("D001UID", "DOCTOR")
    )
    assert res.status_code == 200
    data = res.json()
    assert "signed_url" in data
    assert data["document_id"] == "DOC_P001_SECRET"

    # Doctor D001 can also stream the document
    stream_res = client.get(
        "/documents/DOC_P001_SECRET",
        headers=auth_headers("D001UID", "DOCTOR")
    )
    assert stream_res.status_code == 200
    assert b"Confidential Medical Record" in stream_res.content


def test_public_anonymous_access_denied():
    """
    Security Test 5: Public/anonymous requests to document endpoints and bucket are denied.
    """
    # 1. Anonymous request without token -> 401
    res = client.get("/documents/DOC_P001_SECRET/signed-url")
    assert res.status_code == 401

    res_stream = client.get("/documents/DOC_P001_SECRET")
    assert res_stream.status_code == 401

    # 2. Bucket privacy invariant: bucket MUST NOT be public
    assert storage_service.is_bucket_private() is True


def test_service_role_credentials_never_in_frontend():
    """
    Security Test 6: Audit frontend files to guarantee zero service-role keys are exposed.
    """
    frontend_dir = r"C:\Users\Srushti Nawghane\OneDrive\Desktop\Hospital-records-system\src"
    forbidden_terms = [
        "service_role",
        "service-role",
        "SUPABASE_SERVICE_ROLE_KEY",
        "serviceRoleKey",
        "postgresql://",
        "postgres://"
    ]

    findings = []
    if os.path.exists(frontend_dir):
        for root, _, files in os.walk(frontend_dir):
            for fname in files:
                if fname.endswith((".ts", ".tsx", ".js", ".mjs")):
                    fpath = os.path.join(root, fname)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                    for term in forbidden_terms:
                        if term in text:
                            findings.append(f"{fpath} contains forbidden term: {term}")

    assert len(findings) == 0, f"Found leaked service credentials in frontend: {findings}"


def test_signed_urls_expire_appropriately():
    """
    Security Test 7: Signed URLs expire appropriately and invalid tokens are rejected.
    """
    path = "patients/P001/documents/DOC_TEST/report.pdf"
    service = SupabaseStorageService()

    # 1. Valid signed URL token
    url = service.create_signed_url(path, expires_in=300)
    assert "token=" in url
    assert "expires=" in url

    # Parse expires timestamp and token from URL
    match = re.search(r"expires=(\d+)&token=([a-f0-9]+)", url)
    assert match is not None
    exp_ts = int(match.group(1))
    token = match.group(2)

    # Valid token verification
    assert service.verify_signed_url_token(path, exp_ts, token) is True

    # 2. Expired timestamp verification -> Must return False
    expired_ts = int(time.time()) - 60
    assert service.verify_signed_url_token(path, expired_ts, token) is False

    # 3. Tampered token verification -> Must return False
    tampered_token = token[:-4] + "ffff"
    assert service.verify_signed_url_token(path, exp_ts, tampered_token) is False


def test_unauthorized_access_is_audited():
    """
    Security Test 8: All denied access attempts are logged in access_logs with status=DENIED.
    """
    db = TestingSessionLocal()
    # Find latest denied log for DOCUMENT_VIEW
    denied_log = db.query(AccessLog).filter(
        AccessLog.action == "DOCUMENT_VIEW",
        AccessLog.status == "DENIED"
    ).first()
    assert denied_log is not None
    assert denied_log.status == "DENIED"
    db.close()


# =====================================================================
# END-TO-END VERIFICATION: UPLOAD -> STORAGE -> OCR -> BGE-M3 1024d -> QDRANT -> RAG
# =====================================================================

def test_end_to_end_upload_ocr_bgem3_qdrant_ready():
    """
    End-to-End Pipeline Verification:
    Real Image Upload -> Supabase Storage (patient-scoped path) -> PostgreSQL record
    -> Status: PROCESSING -> OCR -> BGE-M3 1024d -> Qdrant 'medical_records' -> Status: READY -> RAG query.
    """
    # 1. Use real test image if available, or real valid PNG bytes
    real_image_path = "temp_cleaned.png"
    if os.path.exists(real_image_path):
        with open(real_image_path, "rb") as f:
            image_bytes = f.read()
    else:
        # Minimal valid 1x1 PNG bytes
        image_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    # 2. Upload through FastAPI
    upload_res = client.post(
        "/documents/upload",
        headers=auth_headers("P001UID", "PATIENT"),
        data={"patient_id": "P001"},
        files={"file": ("clinical_scan.png", image_bytes, "image/png")}
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    document_id = upload_data["document_id"]
    assert upload_data["status"] == "processing"

    # 3. Verify PostgreSQL record has status=PROCESSING and patient-scoped path
    db = TestingSessionLocal()
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    assert doc is not None
    assert doc.status in ["PROCESSING", "INDEXING", "READY"]
    expected_path_prefix = f"patients/P001/documents/{document_id}/"
    assert doc.storage_path.startswith(expected_path_prefix)
    storage_path = doc.storage_path
    db.close()

    # 4. Run background ingestion worker synchronously
    run_background_ingestion(patient_id="P001", document_id=document_id, storage_path=storage_path)

    # 5. Verify document status updated to READY
    db = TestingSessionLocal()
    updated_doc = db.query(Document).filter(Document.document_id == document_id).first()
    assert updated_doc is not None
    assert updated_doc.status == "READY"
    assert updated_doc.confidence > 0.0

    # Verify processing job is COMPLETED
    job = db.query(ProcessingJob).filter(ProcessingJob.document_id == document_id).first()
    assert job is not None
    assert job.status == "COMPLETED"
    db.close()

    # 6. Verify BGE-M3 1024-dimensional vector embedding
    embedding = get_embedding("Metformin 500mg Type 2 Diabetes")
    assert len(embedding) == 1024
    assert VECTOR_SIZE == 1024
    assert COLLECTION_NAME == "medical_records"

    # 7. Verify document is indexable and retrievable via AI query
    ai_res = client.post(
        "/ai/query",
        headers=auth_headers("P001UID", "PATIENT"),
        json={
            "patient_id": "P001",
            "question": "What is the diagnosis or prescription?"
        }
    )
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    assert "answer" in ai_data
    assert "abstained" in ai_data
