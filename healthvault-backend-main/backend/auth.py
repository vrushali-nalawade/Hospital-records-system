from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import jwt
from typing import List, Optional
from .config import settings
from .database import get_db
from .models import User, Patient, Doctor, Consent
from sqlalchemy.orm import Session
from datetime import datetime

import os
import firebase_admin
from firebase_admin import credentials, auth as fb_auth

# Initialize Firebase Admin App if credentials exist or default app not yet initialized
_firebase_initialized = False
try:
    if not firebase_admin._apps:
        if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
        elif settings.FIREBASE_PROJECT_ID and settings.FIREBASE_PROJECT_ID != "your-firebase-project-id":
            # Initialize with default credentials / project ID
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {"projectId": settings.FIREBASE_PROJECT_ID})
            _firebase_initialized = True
    else:
        _firebase_initialized = True
except Exception:
    _firebase_initialized = False

security_bearer = HTTPBearer()

class AuthUser(BaseModel):
    uid: str
    email: str
    role: str

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security_bearer)) -> AuthUser:
    token = credentials.credentials
    is_prod = settings.ENVIRONMENT.lower() == "production"
    
    # 1. Support Mock Token for isolated testing in development only
    if token.startswith("mock_token_"):
        if is_prod:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mock token authentication is disabled in production environment"
            )
        parts = token.split("_")
        # Expected format: mock_token_{uid}_{role} (optionally with email)
        uid = "mock_uid"
        role = "PATIENT"
        email = "mock@example.com"
        
        if len(parts) > 2:
            uid = parts[2]
        if len(parts) > 3:
            role = parts[3]
        if len(parts) > 4:
            email = "_".join(parts[4:])
        else:
            email = f"{uid.lower()}@example.com"
            
        return AuthUser(uid=uid, email=email, role=role.upper())

    # 2. Firebase Verification using Firebase Admin SDK if initialized
    if _firebase_initialized:
        try:
            decoded_token = fb_auth.verify_id_token(token)
            uid = decoded_token.get("uid") or decoded_token.get("sub")
            email = decoded_token.get("email", "")
            raw_role = decoded_token.get("role")
            if raw_role:
                role = str(raw_role).upper()
            else:
                domain = email.split("@")[-1].lower() if "@" in email else ""
                allowed_doctor_domains = [d.strip().lower() for d in settings.DOCTOR_ALLOWED_EMAIL_DOMAINS.split(",") if d.strip()]
                if domain and domain in allowed_doctor_domains and domain not in PERSONAL_EMAIL_DOMAINS:
                    role = "DOCTOR"
                else:
                    role = "PATIENT"
            if not uid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing user identity"
                )
            return AuthUser(uid=uid, email=email, role=role)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Firebase token verification failed: {str(e)}"
            )

    # 3. Fallback JWT decoding when Firebase Admin SDK credentials are not configured
    try:
        # In production without initialized Firebase Admin, unverified decoding is strictly forbidden
        options = {"verify_signature": True} if is_prod else {"verify_signature": False}
        payload = jwt.decode(token, options=options)
        
        # Verify audience (firebase project id) if configured
        if "aud" in payload and settings.FIREBASE_PROJECT_ID != "your-firebase-project-id":
            if payload["aud"] != settings.FIREBASE_PROJECT_ID:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token audience"
                )
            
        uid = payload.get("sub") or payload.get("user_id") or payload.get("uid")
        email = payload.get("email", "")
        raw_role = payload.get("role")
        if raw_role:
            role = str(raw_role).upper()
        else:
            domain = email.split("@")[-1].lower() if "@" in email else ""
            allowed_doctor_domains = [d.strip().lower() for d in settings.DOCTOR_ALLOWED_EMAIL_DOMAINS.split(",") if d.strip()]
            if domain and domain in allowed_doctor_domains and domain not in PERSONAL_EMAIL_DOMAINS:
                role = "DOCTOR"
            else:
                role = "PATIENT"
        
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user identity"
            )
            
        return AuthUser(uid=uid, email=email, role=role)
        
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )

PERSONAL_EMAIL_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "protonmail.com"}

def validate_doctor_email(email: str):
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Valid professional email address is required for doctor access."
        )
    domain = email.split("@")[-1].lower()
    allowed_domains = [d.strip().lower() for d in settings.DOCTOR_ALLOWED_EMAIL_DOMAINS.split(",") if d.strip()]
    if domain in PERSONAL_EMAIL_DOMAINS or (allowed_domains and domain not in allowed_domains):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Personal email accounts (Gmail/Yahoo/etc.) are not permitted for Doctor access. Professional doctor domain required."
        )

def get_current_user(auth_user: AuthUser = Depends(verify_token), db: Session = Depends(get_db)) -> User:
    role = auth_user.role.upper()
    if role == "DOCTOR":
        validate_doctor_email(auth_user.email)

    # Fetch user from DB, create if not present (seamless login flow for MVP)
    user = db.query(User).filter(User.id == auth_user.uid).first()
    if not user and auth_user.email:
        user = db.query(User).filter(User.email == auth_user.email).first()
        if user and user.id != auth_user.uid:
            # Sync user ID with the active authenticated UID
            if user.patient:
                user.patient.user_id = auth_user.uid
            if user.doctor:
                user.doctor.user_id = auth_user.uid
            user.id = auth_user.uid
            db.commit()
            db.refresh(user)

    if not user:
        user = User(id=auth_user.uid, email=auth_user.email, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Sync email/role if they changed in token
    if user.email != auth_user.email or (user.role != role and role != "PATIENT"):
        if role == "DOCTOR":
            validate_doctor_email(auth_user.email)
        user.email = auth_user.email
        user.role = role
        db.commit()
        db.refresh(user)
        
    # Auto-provision Patient or Doctor profile if missing
    if user.role.upper() == "PATIENT":
        patient = db.query(Patient).filter(Patient.user_id == user.id).first()
        if not patient:
            # Query existing count to generate ID P001, P002, etc.
            count = db.query(Patient).count()
            patient_id = f"P{count + 1:03d}"
            name = user.email.split("@")[0].capitalize() if user.email else "Patient"
            patient = Patient(id=patient_id, user_id=user.id, name=name)
            db.add(patient)
            db.commit()
            
    elif user.role.upper() == "DOCTOR":
        doctor = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if not doctor:
            # Query existing count to generate ID D001, D002, etc.
            count = db.query(Doctor).count()
            doctor_id = f"D{count + 1:03d}"
            name = f"Dr. {user.email.split('@')[0].capitalize()}" if user.email else "Doctor"
            doctor = Doctor(id=doctor_id, user_id=user.id, name=name)
            db.add(doctor)
            db.commit()
        
    return user


class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = [r.upper() for r in allowed_roles]

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.upper() not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: insufficient permissions"
            )
        return current_user

def check_consent(db: Session, doctor_user_id: str, patient_id: str, required_permission: str) -> bool:
    """
    Checks if a doctor has valid consent to access a patient's records/documents/AI queries.
    """
    # Find doctor record
    doctor = db.query(Doctor).filter(Doctor.user_id == doctor_user_id).first()
    if not doctor:
        return False
        
    # Check if there is an active consent
    consent = db.query(Consent).filter(
        Consent.doctor_id == doctor.id,
        Consent.patient_id == patient_id,
        Consent.permission == required_permission,
        Consent.status == "ACTIVE"
    ).first()
    
    if not consent:
        return False
        
    # Check expiration
    if consent.expires_at and consent.expires_at < datetime.utcnow():
        return False
        
    return True

def verify_patient_access(patient_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Verifies that the current user is either:
    1. The patient themselves (PATIENT role and matches patient_id or user_id)
    2. An authorized doctor (DOCTOR role and has valid consent)
    3. An admin (ADMIN role)
    """
    role = current_user.role.upper()
    
    if role == "ADMIN":
        return
        
    if role == "PATIENT":
        # Get patient profile linked to this user
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient or (patient.id != patient_id and patient.user_id != patient_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: patient cannot access other patient records"
            )
        return
        
    if role == "DOCTOR":
        # Resolve canonical patient id if patient_id was passed as user_id
        target_patient = db.query(Patient).filter((Patient.id == patient_id) | (Patient.user_id == patient_id)).first()
        canonical_pid = target_patient.id if target_patient else patient_id
        
        # Check VIEW_RECORDS consent
        if not check_consent(db, current_user.id, canonical_pid, "VIEW_RECORDS") and \
           not check_consent(db, current_user.id, canonical_pid, "ASK_AI") and \
           not check_consent(db, current_user.id, canonical_pid, "VIEW_DOCUMENTS"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: doctor does not have valid consent for this patient"
            )
        return
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: invalid role"
    )
