from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from .models import AccessLog

def log_access(db: Session, actor_id: str, patient_id: Optional[str], action: str, status: str) -> AccessLog:
    """
    Logs an access action in the database.
    Actions: LOGIN, DOCUMENT_UPLOAD, DOCUMENT_VIEW, AI_QUERY, TIMELINE_VIEW, CONSENT_GRANTED, CONSENT_REVOKED
    Status: ALLOWED, DENIED
    """
    log_entry = AccessLog(
        actor_id=actor_id,
        patient_id=patient_id,
        action=action.upper(),
        timestamp=datetime.utcnow(),
        status=status.upper()
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
