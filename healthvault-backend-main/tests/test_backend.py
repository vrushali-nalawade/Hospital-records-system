import os
import shutil
import pytest
import gc
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup test DB URL before importing database module
TEST_DB_URL = "sqlite:///./test_healthvault.db"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["STORAGE_DIR"] = "backend/test_storage"

from backend.main import app
from backend.database import Base, get_db
from backend.models import User, Patient, Doctor, Document, Consent, AccessLog, Visit
from backend.processing import run_background_ingestion

# Set up test database engine and session
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Create users
        u_p1 = User(id="P001UID", email="p001@example.com", role="PATIENT")
        u_p2 = User(id="P002UID", email="p002@example.com", role="PATIENT")
        u_d1 = User(id="D001UID", email="d001@demo.health", role="DOCTOR")
        u_d2 = User(id="D002UID", email="d002@demo.health", role="DOCTOR")
        u_admin = User(id="ADMINUID", email="admin@demo.health", role="ADMIN")
        
        db.add_all([u_p1, u_p2, u_d1, u_d2, u_admin])
        db.commit()
        
        # Create patients
        p1 = Patient(id="P001", user_id="P001UID", name="John Patient 1")
        p2 = Patient(id="P002", user_id="P002UID", name="Jane Patient 2")
        db.add_all([p1, p2])
        
        # Create doctors
        d1 = Doctor(id="D001", user_id="D001UID", name="Dr. Doctor 1", specialty="Cardiology")
        d2 = Doctor(id="D002", user_id="D002UID", name="Dr. Doctor 2", specialty="Pediatrics")
        db.add_all([d1, d2])
        
        db.commit()
    finally:
        db.close()
        
    yield
    
    # Teardown
    engine.dispose()
    
    # Force Garbage Collection to release all files held by fastapi response
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

# Helper to build mock bearer headers
def auth_headers(uid: str, role: str) -> dict:
    if role.upper() == "DOCTOR":
        return {"Authorization": f"Bearer mock_token_{uid}_{role}_{uid.lower()}@demo.health"}
    return {"Authorization": f"Bearer mock_token_{uid}_{role}"}

# =====================================================================
# TEST CASES
# =====================================================================

# 1. Health & Authentication Tests
def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "healthvault-backend"}

def test_unauthenticated_request():
    response = client.get("/patients/me")
    assert response.status_code in [401, 403]
    
def test_invalid_jwt_audience():
    # Test real JWT decoding exception by sending arbitrary token
    headers = {"Authorization": "Bearer invalid_jwt_token_format"}
    response = client.get("/patients/me", headers=headers)
    assert response.status_code == 401

# 2. Patient Profile Scoped Access Tests
def test_patient_self_access():
    headers = auth_headers("P001UID", "PATIENT")
    response = client.get("/patients/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == "P001"

def test_patient_cross_access_prevention():
    headers = auth_headers("P001UID", "PATIENT")
    response = client.get("/patients/P002", headers=headers)
    assert response.status_code == 403

def test_doctor_gmail_rejection():
    # Attempt doctor access with a personal gmail address token
    token = "mock_token_D999UID_DOCTOR_baddoctor@gmail.com"
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/audit/me", headers=headers)
    assert response.status_code == 403
    assert "Personal email accounts" in response.json()["detail"]

# 3. Doctor Access Control Tests (Without & With Consent)
def test_doctor_without_consent():
    headers = auth_headers("D001UID", "DOCTOR")
    response = client.get("/patients/P001", headers=headers)
    assert response.status_code == 403

def test_doctor_with_consent():
    p1_headers = auth_headers("P001UID", "PATIENT")
    consent_data = {
        "doctor_id": "D001",
        "permission": "VIEW_RECORDS"
    }
    response = client.post("/consent", json=consent_data, headers=p1_headers)
    assert response.status_code == 200
    consent_id = response.json()["consent_id"]
    
    # Doctor D001 should now be able to access patient P001 records
    d1_headers = auth_headers("D001UID", "DOCTOR")
    response = client.get("/patients/P001", headers=d1_headers)
    assert response.status_code == 200
    assert response.json()["id"] == "P001"
    
    # Revoke consent
    response = client.delete(f"/consent/{consent_id}", headers=p1_headers)
    assert response.status_code == 200

# 4. Document Upload Limits & Ingestion Pipeline Tests
def test_document_upload_valid():
    headers = auth_headers("P001UID", "PATIENT")
    files = {"file": ("test_prescription.pdf", b"Simulated prescription content", "application/pdf")}
    data = {"patient_id": "P001"}
    response = client.post("/documents/upload", data=data, files=files, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    doc_id = response.json()["document_id"]
    assert doc_id.startswith("DOC_")
    
    # Check status
    response = client.get(f"/documents/{doc_id}/status", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] in ["PROCESSING", "READY", "INDEXING"]

def test_document_upload_too_large():
    headers = auth_headers("P001UID", "PATIENT")
    large_content = b"x" * (11 * 1024 * 1024)
    files = {"file": ("large_file.pdf", large_content, "application/pdf")}
    data = {"patient_id": "P001"}
    response = client.post("/documents/upload", data=data, files=files, headers=headers)
    assert response.status_code == 413

def test_document_upload_invalid_type():
    headers = auth_headers("P001UID", "PATIENT")
    files = {"file": ("virus.zip", b"Dangerous zip payload", "application/zip")}
    data = {"patient_id": "P001"}
    response = client.post("/documents/upload", data=data, files=files, headers=headers)
    assert response.status_code == 422

# 5. AI Query permissions, Citations & Abstention Tests
def test_ai_query_permissions_and_abstention():
    p1_headers = auth_headers("P001UID", "PATIENT")
    query_data = {
        "patient_id": "P001",
        "question": "What is the patient's blood group?"
    }
    response = client.post("/ai/query", json=query_data, headers=p1_headers)
    assert response.status_code == 200
    assert response.json()["abstained"] is True
    assert response.json()["answer"] == "No relevant information was found in the available records."
    assert response.json()["sources"] == []

# 6. Critical Security Test Case: D001 authorized for P001, queries P002 -> 403 Forbidden
def test_cross_patient_doctor_query_prevention():
    db = TestingSessionLocal()
    try:
        # P001 grants consent to D001 for ASK_AI
        p1_headers = auth_headers("P001UID", "PATIENT")
        client.post("/consent", json={"doctor_id": "D001", "permission": "ASK_AI"}, headers=p1_headers)
        
        # D001 requests AI query for patient P002 (no consent for P002)
        d1_headers = auth_headers("D001UID", "DOCTOR")
        query_data = {
            "patient_id": "P002",
            "question": "What was the patient's latest HbA1c?"
        }
        
        response = client.post("/ai/query", json=query_data, headers=d1_headers)
        assert response.status_code == 403
        
        # Verify access logs contain DENIED audit trail
        logs = db.query(AccessLog).filter(
            AccessLog.actor_id == "D001UID",
            AccessLog.patient_id == "P002",
            AccessLog.action == "AI_QUERY"
        ).all()
        assert len(logs) > 0
        assert logs[-1].status == "DENIED"
    finally:
        db.close()

# 7. Consent Creation, Revocation & Audit Logging Tests
def test_consent_lifecycle():
    p1_headers = auth_headers("P001UID", "PATIENT")
    
    # Create consent
    consent_data = {
        "doctor_id": "D002",
        "permission": "ASK_AI"
    }
    response = client.post("/consent", json=consent_data, headers=p1_headers)
    assert response.status_code == 200
    consent_id = response.json()["consent_id"]
    
    # List consents
    response = client.get("/consent", headers=p1_headers)
    assert response.status_code == 200
    assert any(c["consent_id"] == consent_id for c in response.json())
    
    # Revoke consent
    response = client.delete(f"/consent/{consent_id}", headers=p1_headers)
    assert response.status_code == 200
    
    # Audit log check
    db = TestingSessionLocal()
    try:
        audit_records = db.query(AccessLog).filter(AccessLog.action == "CONSENT_REVOKED").all()
        assert len(audit_records) > 0
        assert audit_records[-1].status == "ALLOWED"
    finally:
        db.close()

# 8. End-to-End Integration Scenario
def test_end_to_end_scenario():
    p1_headers = auth_headers("P001UID", "PATIENT")
    d1_headers = auth_headers("D001UID", "DOCTOR")
    
    # Step 1: Upload lab report
    files = {"file": ("john_hba1c_report.pdf", b"Lab Test. HbA1c is 7.2%. Date: 2026-07-15.", "application/pdf")}
    data = {"patient_id": "P001"}
    response = client.post("/documents/upload", data=data, files=files, headers=p1_headers)
    assert response.status_code == 200
    doc_id = response.json()["document_id"]
    
    # Step 2: Manually execute ingestion synchronously
    db = TestingSessionLocal()
    try:
        db.expire_all()
        doc = db.query(Document).filter(Document.document_id == doc_id).first()
        assert doc is not None
        
        run_background_ingestion(patient_id="P001", document_id=doc_id, storage_path=doc.storage_path)
        
        db.refresh(doc)
        assert doc.status == "READY"
        
        # Step 3: Grant consent to D001 for ASK_AI and VIEW_DOCUMENTS
        client.post("/consent", json={"doctor_id": "D001", "permission": "ASK_AI"}, headers=p1_headers)
        client.post("/consent", json={"doctor_id": "D001", "permission": "VIEW_DOCUMENTS"}, headers=p1_headers)
        
        # Step 4: Doctor asks a grounded query about John's records
        query_data = {
            "patient_id": "P001",
            "question": "What is John's latest HbA1c?"
        }
        response = client.post("/ai/query", json=query_data, headers=d1_headers)
        assert response.status_code == 200
        res_json = response.json()
        assert res_json["abstained"] is False
        assert "7.2%" in res_json["answer"]
        assert len(res_json["sources"]) > 0
        assert any(s["document_id"] == doc_id for s in res_json["sources"])
        
        # Step 5: Doctor retrieves the original source document securely
        response = client.get(f"/documents/{doc_id}", headers=d1_headers)
        assert response.status_code == 200
        assert response.content == b"Lab Test. HbA1c is 7.2%. Date: 2026-07-15."
        response.close()  # EXPLICITLY close to release the file handle
        
        # Step 6: Verify Timeline endpoint Chronology
        response = client.get("/ai/timeline/P001", headers=d1_headers)
        assert response.status_code == 200
        timeline_events = response.json()["events"]
        assert len(timeline_events) > 0
        assert any(doc_id == e["source"] for e in timeline_events)
        assert any("7.2" in e["event"] for e in timeline_events)
    finally:
        db.close()

# 6. Doctor Registration, Provisioning & Vercel Preview CORS Tests
def test_doctor_registration_and_login_flow():
    # Simulate a new doctor registering with institutional domain @hospital.org
    doc_uid = "D999UID"
    doc_email = "sarah.jenkins@hospital.org"
    token = f"mock_token_{doc_uid}_DOCTOR_{doc_email}"
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Register profile
    register_payload = {
        "name": "Dr. Sarah Jenkins",
        "specialty": "Cardiology"
    }
    response = client.post("/doctor/register", json=register_payload, headers=headers)
    assert response.status_code == 200
    doc_data = response.json()
    assert doc_data["user_id"] == doc_uid
    assert doc_data["name"] == "Dr. Sarah Jenkins"
    assert doc_data["specialty"] == "Cardiology"
    assert doc_data["id"].startswith("D")
    
    # 2. Verify Doctor profile in DB
    db = TestingSessionLocal()
    try:
        user_in_db = db.query(User).filter(User.id == doc_uid).first()
        assert user_in_db is not None
        assert user_in_db.role == "DOCTOR"
        assert user_in_db.email == doc_email
        
        doctor_in_db = db.query(Doctor).filter(Doctor.user_id == doc_uid).first()
        assert doctor_in_db is not None
        assert doctor_in_db.specialty == "Cardiology"
    finally:
        db.close()
        
    # 3. Verify doctor can fetch /doctor/me and /auth/me (subsequent login verification)
    me_resp = client.get("/doctor/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["name"] == "Dr. Sarah Jenkins"
    
    auth_me_resp = client.get("/auth/me", headers=headers)
    assert auth_me_resp.status_code == 200
    assert auth_me_resp.json()["role"] == "DOCTOR"
    assert auth_me_resp.json()["doctor"]["specialty"] == "Cardiology"

def test_doctor_registration_personal_email_rejection():
    # Attempt doctor registration with personal email
    bad_token = "mock_token_DBADUID_DOCTOR_evil@gmail.com"
    headers = {"Authorization": f"Bearer {bad_token}"}
    response = client.post("/doctor/register", json={"name": "Dr. Fake"}, headers=headers)
    assert response.status_code == 403
    assert "Personal email accounts" in response.json()["detail"]

def test_vercel_preview_cors():
    # Verify that Vercel preview URLs match CORS regex without wildcard *
    preview_origin = "https://healthvault-frontend-git-main-srushtinawghane.vercel.app"
    response = client.options(
        "/documents/upload",
        headers={
            "Origin": preview_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type"
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == preview_origin
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_document_upload_empty_payload():
    headers = auth_headers("P001UID", "PATIENT")
    files = {"file": ("empty.pdf", b"", "application/pdf")}
    data = {"patient_id": "P001"}
    response = client.post("/documents/upload", data=data, files=files, headers=headers)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]
