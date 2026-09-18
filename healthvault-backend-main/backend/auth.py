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
import json
import base64
import logging
import firebase_admin
from firebase_admin import credentials, auth as fb_auth

logger = logging.getLogger("backend")

# Initialize Firebase Admin App if valid credentials exist
_firebase_initialized = False
try:
    if not firebase_admin._apps:
        cred = None
        # 1. Check direct JSON string in environment (e.g., on Render or production env)
        if settings.FIREBASE_CREDENTIALS_JSON:
            try:
                raw_json = settings.FIREBASE_CREDENTIALS_JSON.strip()
                if raw_json.startswith("{"):
                    cred_data = json.loads(raw_json)
                else:
                    cred_data = json.loads(base64.b64decode(raw_json).decode("utf-8"))
                cred = credentials.Certificate(cred_data)
                logger.info("Firebase initialized via FIREBASE_CREDENTIALS_JSON")
            except Exception as e:
                logger.warning(f"Could not parse FIREBASE_CREDENTIALS_JSON: {e}")

        # 2. Check service account JSON file on disk
        if not cred and settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            try:
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                logger.info(f"Firebase initialized via {settings.FIREBASE_CREDENTIALS_PATH}")
            except Exception as e:
                logger.warning(f"Could not load FIREBASE_CREDENTIALS_PATH: {e}")

        # 3. Check individual env vars
        if not cred and settings.FIREBASE_CLIENT_EMAIL and settings.FIREBASE_PRIVATE_KEY and "your-private-key" not in settings.FIREBASE_PRIVATE_KEY:
            try:
                cred_dict = {
                    "type": "service_account",
                    "project_id": settings.FIREBASE_PROJECT_ID,
                    "private_key": settings.FIREBASE_PRIVATE_KEY.replace('\\n', '\n'),
                    "client_email": settings.FIREBASE_CLIENT_EMAIL,
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
                cred = credentials.Certificate(cred_dict)
                logger.info("Firebase initialized via FIREBASE_PRIVATE_KEY / FIREBASE_CLIENT_EMAIL")
            except Exception as e:
                logger.warning(f"Could not initialize Firebase via env credentials: {e}")

        # 4. Check explicit GOOGLE_APPLICATION_CREDENTIALS file
        if not cred and os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
            try:
                cred = credentials.ApplicationDefault()
                logger.info("Firebase initialized via ApplicationDefault")
            except Exception as e:
                logger.warning(f"Could not load ApplicationDefault credentials: {e}")

        if cred:
            project_kwargs = {"projectId": settings.FIREBASE_PROJECT_ID} if settings.FIREBASE_PROJECT_ID != "your-firebase-project-id" else {}
            firebase_admin.initialize_app(cred, project_kwargs)
            _firebase_initialized = True
    else:
        _firebase_initialized = True
except Exception as e:
    logger.warning(f"Firebase Admin SDK initialization skipped: {e}")
    _firebase_initialized = False

security_bearer = HTTPBearer()

class AuthUser(BaseModel):
    uid: str
    email: str
    role: str

_jwks_client: Optional[jwt.PyJWKClient] = None

def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(
            "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com",
            cache_keys=True
        )
    return _jwks_client

def _extract_role(email: str, raw_role: Optional[str]) -> str:
    if raw_role:
        return str(raw_role).upper()
    domain = email.split("@")[-1].lower() if "@" in email else ""
    allowed_doctor_domains = [d.strip().lower() for d in settings.DOCTOR_ALLOWED_EMAIL_DOMAINS.split(",") if d.strip()]
    if domain and domain in allowed_doctor_domains and domain not in PERSONAL_EMAIL_DOMAINS:
        return "DOCTOR"
    return "PATIENT"

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

    # 2. Firebase Verification using Firebase Admin SDK if fully initialized
    if _firebase_initialized:
        try:
            decoded_token = fb_auth.verify_id_token(token)
            uid = decoded_token.get("uid") or decoded_token.get("sub")
            email = decoded_token.get("email", "")
            role = _extract_role(email, decoded_token.get("role"))
            if not uid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token missing user identity"
                )
            return AuthUser(uid=uid, email=email, role=role)
        except Exception as e:
            logger.info(f"Firebase Admin verify_id_token returned error: {e}. Attempting JWKS verification...")

    # 3. Google Public JWKS cryptographic signature verification (works without service account credentials)
    try:
        jwks = _get_jwks_client()
        signing_key = jwks.get_signing_key_from_jwt(token)
        project_id = settings.FIREBASE_PROJECT_ID if settings.FIREBASE_PROJECT_ID != "your-firebase-project-id" else None
        
        decode_options = {
            "verify_signature": True,
            "verify_aud": bool(project_id),
            "verify_iss": bool(project_id)
        }
        
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}" if project_id else None,
            options=decode_options
        )
        
        uid = payload.get("user_id") or payload.get("sub") or payload.get("uid")
        email = payload.get("email", "")
        role = _extract_role(email, payload.get("role"))
        
        if not uid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing user identity"
            )
            
        return AuthUser(uid=uid, email=email, role=role)

    except jwt.PyJWTError as e:
        logger.warning(f"Google JWKS token verification failed: {e}")
        
        # 4. Fallback for offline/development or unverified decoding
        if not is_prod:
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
                uid = payload.get("user_id") or payload.get("sub") or payload.get("uid")
                email = payload.get("email", "")
                role = _extract_role(email, payload.get("role"))
                if uid:
                    return AuthUser(uid=uid, email=email, role=role)
            except Exception:
                pass
                
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification error: {str(e)}"
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
        if not patient and patient_id:
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            
        if not patient:
            if current_user.id != patient_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: patient cannot access other patient records"
                )
        else:
            if patient.id != patient_id and patient.user_id != patient_id and current_user.id != patient_id:
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
