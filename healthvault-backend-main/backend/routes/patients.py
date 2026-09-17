from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, Patient
from ..auth import get_current_user, verify_patient_access
from ..schemas import PatientResponse

router = APIRouter(prefix="/patients", tags=["patients"])

@router.get("/me", response_model=PatientResponse)
def get_patient_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Retrieve the patient linked to the authenticated user's ID
    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user is not registered as a patient in HealthVault AI"
        )
    return patient

@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_by_id(
    patient_id: str,
    db: Session = Depends(get_db),
    _ = Depends(verify_patient_access)  # Access check dependency
):
    patient = db.query(Patient).filter((Patient.id == patient_id) | (Patient.user_id == patient_id)).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient profile not found"
        )
    return patient
