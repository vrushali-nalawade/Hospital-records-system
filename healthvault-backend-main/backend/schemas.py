from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class UserBase(BaseModel):
    email: str
    role: str

class UserCreate(UserBase):
    uid: str

class UserResponse(UserBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PatientResponse(BaseModel):
    id: str
    user_id: str
    name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class DoctorResponse(BaseModel):
    id: str
    user_id: str
    name: str
    specialty: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class DocumentUploadResponse(BaseModel):
    document_id: str
    status: str

class DocumentSignedUrlResponse(BaseModel):
    document_id: str
    signed_url: str
    expires_in: int
    storage_path: str

class DocumentResponse(BaseModel):
    document_id: str
    patient_id: str
    visit_id: Optional[str] = None
    storage_path: str
    document_type: str
    status: str
    created_at: datetime
    processed_at: Optional[datetime] = None
    needs_review: bool
    confidence: float
    
    class Config:
        from_attributes = True

class ConsentCreate(BaseModel):
    doctor_id: str
    permission: str  # VIEW_RECORDS, VIEW_DOCUMENTS, ASK_AI
    expires_at: Optional[datetime] = None

class ConsentResponse(BaseModel):
    consent_id: str
    patient_id: str
    doctor_id: str
    permission: str
    status: str = "ACTIVE"
    expires_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class AccessLogResponse(BaseModel):
    log_id: int
    actor_id: str
    patient_id: Optional[str] = None
    action: str
    timestamp: datetime
    status: str
    
    class Config:
        from_attributes = True

class AIQueryRequest(BaseModel):
    patient_id: str
    question: str

class Citation(BaseModel):
    document_id: str
    date: str
    document_type: str

class AIQueryResponse(BaseModel):
    answer: str
    sources: List[Citation]
    abstained: bool

class TimelineEvent(BaseModel):
    date: str
    event: str
    source: str

class TimelineResponse(BaseModel):
    patient_id: str
    events: List[TimelineEvent]
