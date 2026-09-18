from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Patient, Doctor
from ..auth import get_current_user
from ..schemas import DoctorResponse

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "healthvault-backend"
    }

@router.get("/auth/me")
def get_auth_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "patient": {
            "id": patient.id,
            "name": patient.name,
            "created_at": patient.created_at.isoformat() if patient and patient.created_at else None
        } if patient else None,
        "doctor": {
            "id": doctor.id,
            "name": doctor.name,
            "specialty": doctor.specialty,
            "created_at": doctor.created_at.isoformat() if doctor and doctor.created_at else None
        } if doctor else None
    }

from pydantic import BaseModel
from typing import Optional

class DoctorRegisterRequest(BaseModel):
    name: Optional[str] = None
    specialty: Optional[str] = None

@router.get("/doctors/me", response_model=DoctorResponse)
@router.get("/doctor/me", response_model=DoctorResponse)
def get_doctor_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user is not registered as a doctor in HealthVault AI"
        )
    return doctor

@router.post("/doctor/register", response_model=DoctorResponse)
@router.post("/doctors/register", response_model=DoctorResponse)
@router.put("/doctor/me", response_model=DoctorResponse)
def register_or_update_doctor(
    request: Optional[DoctorRegisterRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role.upper() != "DOCTOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: doctor registration is only permitted for doctor accounts"
        )
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        count = db.query(Doctor).count()
        doctor_id = f"D{count + 1:03d}"
        doc_name = (request.name if request and request.name else None) or (f"Dr. {current_user.email.split('@')[0].capitalize()}" if current_user.email else "Doctor")
        doctor = Doctor(
            id=doctor_id,
            user_id=current_user.id,
            name=doc_name,
            specialty=request.specialty if request else None
        )
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
    else:
        if request and request.name:
            doctor.name = request.name
        if request and request.specialty:
            doctor.specialty = request.specialty
        db.commit()
        db.refresh(doctor)
    return doctor
