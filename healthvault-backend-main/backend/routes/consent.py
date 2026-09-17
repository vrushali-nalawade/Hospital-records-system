from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from ..database import get_db
from ..models import User, Patient, Doctor, Consent
from ..auth import get_current_user
from ..schemas import ConsentCreate, ConsentResponse
from ..audit import log_access
from typing import List

router = APIRouter(prefix="/consent", tags=["consent"])

@router.post("", response_model=ConsentResponse)
def grant_consent(
    consent_in: ConsentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only patients can grant consent
    if current_user.role.upper() != "PATIENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only patients can grant consent to doctors"
        )
        
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
        
    # Check that doctor exists
    doctor = db.query(Doctor).filter(Doctor.id == consent_in.doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found"
        )
        
    consent_id = f"CON_{uuid.uuid4().hex[:8].upper()}"
    new_consent = Consent(
        consent_id=consent_id,
        patient_id=patient.id,
        doctor_id=consent_in.doctor_id,
        permission=consent_in.permission.upper(),
        expires_at=consent_in.expires_at
    )
    db.add(new_consent)
    db.commit()
    db.refresh(new_consent)
    
    # Audit log entry
    log_access(db, current_user.id, patient.id, "CONSENT_GRANTED", "ALLOWED")
    
    return new_consent

@router.get("", response_model=List[ConsentResponse])
def list_consents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = current_user.role.upper()
    
    if role == "PATIENT":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            return []
        return db.query(Consent).filter(Consent.patient_id == patient.id).all()
        
    elif role == "DOCTOR":
        doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor:
            return []
        return db.query(Consent).filter(Consent.doctor_id == doctor.id).all()
        
    elif role == "ADMIN":
        return db.query(Consent).all()
        
    return []

@router.delete("/{consent_id}")
def revoke_consent(
    consent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    consent = db.query(Consent).filter(Consent.consent_id == consent_id).first()
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent record not found"
        )
        
    # Security check: only the granting patient (or admin) can revoke
    if current_user.role.upper() != "ADMIN":
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or consent.patient_id != patient.id:
            log_access(db, current_user.id, consent.patient_id, "CONSENT_REVOKED", "DENIED")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: you cannot revoke another patient's consent"
            )
            
    patient_id = consent.patient_id
    consent.status = "REVOKED"
    db.commit()
    
    log_access(db, current_user.id, patient_id, "CONSENT_REVOKED", "ALLOWED")
    
    return {"status": "success", "message": "Consent revoked successfully"}
