from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
import uuid
import os
from typing import List, Optional
from ..config import settings
from ..database import get_db
from ..models import User, Patient, Document, ProcessingJob, Consent, Doctor
from ..auth import get_current_user, verify_patient_access, check_consent
from ..storage import (
    storage_service,
    save_document,
    get_document_path,
    get_document_bytes,
    create_document_signed_url,
    MIME_MAP
)
from ..processing import run_background_ingestion
from ..audit import log_access
from ..schemas import DocumentUploadResponse, DocumentResponse, DocumentSignedUrlResponse

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    patient_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Authorize patient identity (only patients can upload for themselves, admins for any)
    patient = None
    if patient_id:
        patient = db.query(Patient).filter((Patient.id == patient_id) | (Patient.user_id == patient_id)).first()
        
    if not patient and current_user.role.upper() == "PATIENT":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        
    if not patient:
        log_access(db, current_user.id, patient_id, "DOCUMENT_UPLOAD", "DENIED")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    
    # Resolve canonical patient ID
    canonical_patient_id = patient.id
        
    if current_user.role.upper() != "ADMIN":
        if patient.user_id != current_user.id:
            log_access(db, current_user.id, canonical_patient_id, "DOCUMENT_UPLOAD", "DENIED")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: patients can only upload documents for themselves"
            )
            
    # 2. Validate file type/extension
    safe_name = file.filename or "document.pdf"
    _, ext = os.path.splitext(safe_name)
    if ext.lower() not in ALLOWED_EXTENSIONS:
        log_access(db, current_user.id, canonical_patient_id, "DOCUMENT_UPLOAD", "DENIED")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid file type. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    # 3. Validate file size
    try:
        file_content = await file.read()
    except Exception as e:
        logger.error(f"[DocumentUpload] Error reading file payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error reading uploaded file payload"
        )

    file_size = len(file_content)
    if file_size > MAX_FILE_SIZE:
        log_access(db, current_user.id, canonical_patient_id, "DOCUMENT_UPLOAD", "DENIED")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds maximum limit of 10MB"
        )
    if file_size == 0:
        log_access(db, current_user.id, canonical_patient_id, "DOCUMENT_UPLOAD", "DENIED")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)"
        )
        
    # 4. Generate unique document ID
    document_id = f"DOC_{uuid.uuid4().hex[:8].upper()}"
    
    # 5. Store file in Supabase Storage with patient-scoped path:
    # patients/{patient_id}/documents/{document_id}/{safe_filename}
    try:
        storage_path = save_document(canonical_patient_id, document_id, file_content, safe_name)
        logger.info(f"[DocumentUpload] Successfully saved document {document_id} to path {storage_path}")
    except Exception as e:
        logger.error(f"[DocumentUpload] Storage upload failed for patient {canonical_patient_id}, doc {document_id}: {e}", exc_info=True)
        log_access(db, current_user.id, canonical_patient_id, "DOCUMENT_UPLOAD", "DENIED")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store document in storage system: {str(e)}"
        )
    
    # 6. Write record to database with status = PROCESSING
    try:
        doc_record = Document(
            document_id=document_id,
            patient_id=canonical_patient_id,
            storage_path=storage_path,
            document_type="unknown",
            status="PROCESSING"
        )
        db.add(doc_record)
        
        job_record = ProcessingJob(
            job_id=f"JOB_{document_id}",
            document_id=document_id,
            status="PENDING"
        )
        db.add(job_record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[DocumentUpload] Database commit failed for doc {document_id}: {e}", exc_info=True)
        log_access(db, current_user.id, canonical_patient_id, "DOCUMENT_UPLOAD", "DENIED")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failed while recording uploaded document"
        )
    
    # 7. Log allowed upload in access audits
    log_access(db, current_user.id, canonical_patient_id, "DOCUMENT_UPLOAD", "ALLOWED")
    
    # 8. Queue document processing task in background thread
    try:
        background_tasks.add_task(
            run_background_ingestion,
            patient_id=canonical_patient_id,
            document_id=document_id,
            storage_path=storage_path
        )
    except Exception as e:
        logger.error(f"[DocumentUpload] Failed to schedule background ingestion for {document_id}: {e}")
    
    return {"document_id": document_id, "status": "processing"}

@router.get("", response_model=List[DocumentResponse])
def list_documents(
    patient_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify patient access
    if patient_id:
        verify_patient_access(patient_id, current_user, db)
        patient = db.query(Patient).filter((Patient.id == patient_id) | (Patient.user_id == patient_id)).first()
        canonical_id = patient.id if patient else patient_id
        return db.query(Document).filter(Document.patient_id == canonical_id).all()
        
    role = current_user.role.upper()
    if role == "PATIENT":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            return []
        return db.query(Document).filter(Document.patient_id == patient.id).all()
    elif role == "DOCTOR":
        # Doctors can only see documents for patients they have consent for
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            return []
        consents = db.query(Consent).filter(
            Consent.doctor_id == doctor.id, 
            Consent.status == "ACTIVE",
            Consent.permission.in_(["VIEW_DOCUMENTS", "VIEW_RECORDS"])
        ).all()
        allowed_patient_ids = [c.patient_id for c in consents]
        return db.query(Document).filter(Document.patient_id.in_(allowed_patient_ids)).all()
    elif role == "ADMIN":
        return db.query(Document).all()
        
    return []

@router.get("/{document_id}/status")
def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    # Authorize caller: Patient owns it, or Doctor has valid consent
    verify_patient_access(doc.patient_id, current_user, db)
    
    job = db.query(ProcessingJob).filter(ProcessingJob.document_id == document_id).first()
    job_status = job.status if job else None
    error_msg = job.error_message if job else None
    
    return {
        "document_id": document_id, 
        "status": doc.status,
        "job_status": job_status,
        "error_message": error_msg
    }

@router.get("/{document_id}/signed-url", response_model=DocumentSignedUrlResponse)
def get_document_signed_url(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a secure, temporary signed access URL for authorized users.
    Enforces strict patient isolation and active doctor consent rules.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    patient_id = doc.patient_id
    role = current_user.role.upper()
    
    # Check access authorization
    allowed = False
    if role == "ADMIN":
        allowed = True
    elif role == "PATIENT":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient and patient.id == patient_id:
            allowed = True
    elif role == "DOCTOR":
        if check_consent(db, current_user.id, patient_id, "VIEW_DOCUMENTS") or \
           check_consent(db, current_user.id, patient_id, "VIEW_RECORDS"):
            allowed = True
            
    if not allowed:
        log_access(db, current_user.id, patient_id, "DOCUMENT_VIEW", "DENIED")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: unauthorized to view or access this document"
        )
        
    log_access(db, current_user.id, patient_id, "DOCUMENT_VIEW", "ALLOWED")
    
    expiry_seconds = settings.SIGNED_URL_EXPIRY_SECONDS
    signed_url = create_document_signed_url(doc.storage_path, expires_in=expiry_seconds)
    
    return DocumentSignedUrlResponse(
        document_id=doc.document_id,
        signed_url=signed_url,
        expires_in=expiry_seconds,
        storage_path=doc.storage_path
    )

@router.get("/{document_id}")
def get_original_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    patient_id = doc.patient_id
    role = current_user.role.upper()
    
    # Check access permission: owner patient, or doctor with VIEW_DOCUMENTS/VIEW_RECORDS consent
    allowed = False
    if role == "ADMIN":
        allowed = True
    elif role == "PATIENT":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if patient and patient.id == patient_id:
            allowed = True
    elif role == "DOCTOR":
        if check_consent(db, current_user.id, patient_id, "VIEW_DOCUMENTS") or \
           check_consent(db, current_user.id, patient_id, "VIEW_RECORDS"):
            allowed = True
            
    if not allowed:
        log_access(db, current_user.id, patient_id, "DOCUMENT_VIEW", "DENIED")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: unauthorized to view or download this document"
        )
        
    log_access(db, current_user.id, patient_id, "DOCUMENT_VIEW", "ALLOWED")
    
    # Retrieve clean local path and return streamed response
    safe_path = get_document_path(doc.storage_path)
    filename = os.path.basename(doc.storage_path)
    _, ext = os.path.splitext(filename)
    media_type = MIME_MAP.get(ext.lower(), "application/octet-stream")
    
    return FileResponse(safe_path, media_type=media_type, filename=filename)
