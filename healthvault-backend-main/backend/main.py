from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from .config import settings
from .database import engine, Base, get_db
from .models import User, Patient, AccessLog
from .auth import get_current_user
from .schemas import AccessLogResponse
from .routes import auth, patients, documents, consent, ai

# Limit PyTorch CPU worker threads to 1 to eliminate GIL CPU starvation on Replit
try:
    import torch
    torch.set_num_threads(1)
except Exception:
    pass

# Initialize database tables (PostgreSQL or SQLite fallback)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    import logging
    logging.getLogger("backend").warning(f"Could not connect to database on startup: {e}")

app = FastAPI(
    title="HealthVault AI Backend",
    description="Secure backend and integration layer for HealthVault AI (Person 4)",
    version="1.0.0"
)

# CORS Policy configuration (allowing active frontend origins and safe Vercel preview deployments)
import logging
logger = logging.getLogger("backend")
logger.info(f"Configured CORS Allowed Origins: {settings.cors_origins}")
logger.info("Configured CORS Allowed Origin Regex: ^https://([a-zA-Z0-9_-]+\\.)*vercel\\.app$")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https://([a-zA-Z0-9_-]+\.)*vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    if settings.ENVIRONMENT.lower() == "production" and request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Mount APIRouters
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(documents.router)
app.include_router(consent.router)
app.include_router(ai.router)

@app.get("/", tags=["root"])
def root():
    return {
        "status": "online",
        "service": "HealthVault AI Backend",
        "version": "1.0.0",
        "health": "/health",
        "docs": "/docs"
    }

# Expose global audit history log endpoint
@app.get("/audit/me", response_model=List[AccessLogResponse], tags=["audit"])
def get_my_audit_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = current_user.role.upper()
    
    if role == "PATIENT":
        # Patients can see access history relating to their records
        patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient:
            return []
        return db.query(AccessLog).filter(AccessLog.patient_id == patient.id).all()
        
    elif role == "DOCTOR":
        # Doctors can see history of actions they performed
        return db.query(AccessLog).filter(AccessLog.actor_id == current_user.id).all()
        
    elif role == "ADMIN":
        # Admin can view all system logs
        return db.query(AccessLog).all()
        
    return []
