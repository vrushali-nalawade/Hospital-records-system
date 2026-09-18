from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)  # Firebase UID
    email = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False)  # PATIENT, DOCTOR, ADMIN
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="user", uselist=False)
    doctor = relationship("Doctor", back_populates="user", uselist=False)

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String, primary_key=True, index=True)  # P001, etc.
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="patient")
    documents = relationship("Document", back_populates="patient")
    consents = relationship("Consent", back_populates="patient")
    visits = relationship("Visit", back_populates="patient")

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(String, primary_key=True, index=True)  # D001, etc.
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="doctor")
    consents = relationship("Consent", back_populates="doctor")

class Visit(Base):
    __tablename__ = "visits"

    visit_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    date = Column(String, nullable=False)  # ISO date string e.g. "2026-07-15"
    doctor_id = Column(String, ForeignKey("doctors.id"), nullable=True)
    doctor_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="visits")
    documents = relationship("Document", back_populates="visit")

class Document(Base):
    __tablename__ = "documents"

    document_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    visit_id = Column(String, ForeignKey("visits.visit_id"), nullable=True)
    storage_path = Column(String, nullable=False)
    document_type = Column(String, nullable=False)  # prescription, lab_report, etc.
    status = Column(String, default="PROCESSING")  # UPLOADED, PROCESSING, PROCESSED, INDEXING, READY, FAILED, NEEDS_REVIEW
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    needs_review = Column(Boolean, default=False)
    confidence = Column(Float, default=1.0)

    # Relationships
    patient = relationship("Patient", back_populates="documents")
    visit = relationship("Visit", back_populates="documents")
    jobs = relationship("ProcessingJob", back_populates="document")

class Consent(Base):
    __tablename__ = "consents"

    consent_id = Column(String, primary_key=True, index=True)
    patient_id = Column(String, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String, ForeignKey("doctors.id"), nullable=False)
    permission = Column(String, nullable=False)  # VIEW_RECORDS, VIEW_DOCUMENTS, ASK_AI
    status = Column(String, default="ACTIVE")  # ACTIVE, REVOKED, EXPIRED
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    patient = relationship("Patient", back_populates="consents")
    doctor = relationship("Doctor", back_populates="consents")

class AccessLog(Base):
    __tablename__ = "access_logs"

    log_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    actor_id = Column(String, nullable=False)
    patient_id = Column(String, nullable=True)
    action = Column(String, nullable=False)  # LOGIN, DOCUMENT_UPLOAD, DOCUMENT_VIEW, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)  # ALLOWED, DENIED

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    job_id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False)
    status = Column(String, default="PENDING")
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="jobs")
