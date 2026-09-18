from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Patient
from ..auth import get_current_user, check_consent
from ..schemas import AIQueryRequest, AIQueryResponse, TimelineResponse
from ..ai_service import ask_patient_question, get_patient_timeline
from ..audit import log_access

router = APIRouter(prefix="/ai", tags=["ai"])

def verify_ai_access(patient_id: str, current_user: User, db: Session, required_permission: str):
    role = current_user.role.upper()
    if role == "ADMIN":
        return
        
    if role == "PATIENT":
        # Patients can only query their own records
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or (patient.id != patient_id and patient.user_id != patient_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: patients can only query their own AI records"
            )
        return
        
    if role == "DOCTOR":
        # Resolve canonical patient id if patient_id was passed as user_id
        target_patient = db.query(Patient).filter((Patient.id == patient_id) | (Patient.user_id == patient_id)).first()
        canonical_pid = target_patient.id if target_patient else patient_id
        
        # Doctors must have explicit consent to ask AI or view records
        if not check_consent(db, current_user.id, canonical_pid, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requesting doctor does not have '{required_permission}' consent for this patient"
            )
        return
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: invalid role configuration"
    )

@router.post("/query", response_model=AIQueryResponse)
def query_patient_ai(
    query_in: AIQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    raw_patient_id = query_in.patient_id
    question = query_in.question
    
    # 1. Enforce strict patient security scoping
    try:
        verify_ai_access(raw_patient_id, current_user, db, "ASK_AI")
    except HTTPException as e:
        log_access(db, current_user.id, raw_patient_id, "AI_QUERY", "DENIED")
        raise e
        
    # Resolve canonical patient ID
    patient = db.query(Patient).filter((Patient.id == raw_patient_id) | (Patient.user_id == raw_patient_id)).first()
    canonical_id = patient.id if patient else raw_patient_id
    
    log_access(db, current_user.id, canonical_id, "AI_QUERY", "ALLOWED")
    
    # 2. Call Qdrant hybrid retrieval + RAG pipeline
    result = ask_patient_question(canonical_id, question, document_id=query_in.document_id)
    return result

@router.get("/timeline/{patient_id}", response_model=TimelineResponse)
def get_patient_timeline_events(
    patient_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = current_user.role.upper()
    allowed = False
    
    patient = db.query(Patient).filter((Patient.id == patient_id) | (Patient.user_id == patient_id)).first()
    canonical_id = patient.id if patient else patient_id
    
    # 1. Validate ownership or consent permissions
    if role == "ADMIN":
        allowed = True
    elif role == "PATIENT":
        user_patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if user_patient and (user_patient.id == canonical_id or user_patient.user_id == patient_id):
            allowed = True
    elif role == "DOCTOR":
        # Doctors need either VIEW_RECORDS or ASK_AI consent to see the medical event timeline
        if check_consent(db, current_user.id, canonical_id, "VIEW_RECORDS") or \
           check_consent(db, current_user.id, canonical_id, "ASK_AI"):
            allowed = True
            
    if not allowed:
        log_access(db, current_user.id, canonical_id, "TIMELINE_VIEW", "DENIED")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: unauthorized to view timeline events for this patient"
        )
        
    log_access(db, current_user.id, canonical_id, "TIMELINE_VIEW", "ALLOWED")
    
    # 2. Get longitudinal timeline from indexing layer
    timeline = get_patient_timeline(canonical_id)
    return timeline
