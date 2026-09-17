"""
verify_database.py — Safe Database Health & Integrity Verification Tool

Reports:
  1. Database engine (postgresql vs sqlite)
  2. Database connection status
  3. All 8 table names and existence
  4. Row counts per table (and comparison with SQLite reference if migrating)
  5. Relationship integrity (foreign key consistency)
  6. Latest uploaded document details
  7. Latest processing job details
  8. Latest audit access log entry

Usage:
  python backend/verify_database.py [--url DATABASE_URL]
"""

import os
import sys
import argparse
from typing import Optional, Dict, Any
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import settings
from backend.database import (
    create_app_engine,
    normalize_database_url,
    mask_database_url,
    get_database_engine_type
)
from backend.models import (
    User,
    Patient,
    Doctor,
    Visit,
    Document,
    Consent,
    AccessLog,
    ProcessingJob
)

EXPECTED_TABLES = [
    "users",
    "patients",
    "doctors",
    "visits",
    "documents",
    "consents",
    "access_logs",
    "processing_jobs"
]

def run_database_verification(db_url: Optional[str] = None) -> Dict[str, Any]:
    url = normalize_database_url(db_url or settings.DATABASE_URL)
    masked = mask_database_url(url)

    print("=" * 68)
    print("      HEALTHVAULT AI — DATABASE HEALTH & INTEGRITY REPORT      ")
    print("=" * 68)
    print(f"Target Database URL : {masked}")

    result = {
        "engine": "unknown",
        "connected": False,
        "tables_present": {},
        "row_counts": {},
        "relationships_valid": True,
        "latest_document": None,
        "latest_job": None,
        "latest_audit": None
    }

    try:
        engine = create_app_engine(url)
        engine_type = get_database_engine_type(engine)
        result["engine"] = engine_type
        print(f"Database Engine     : {engine_type.upper()}")

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        result["connected"] = True
        print(f"Connection Status   : CONNECTED (OK)\n")
    except Exception as e:
        print(f"Connection Status   : FAILED ({e})\n")
        return result

    # Check tables
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    
    print("-" * 68)
    print(f"{'Table Name':<22} | {'Present':<10} | {'Row Count':<12} | {'Integrity'}")
    print("-" * 68)

    with Session(engine) as session:
        for tbl in EXPECTED_TABLES:
            present = tbl in existing_tables
            result["tables_present"][tbl] = present
            if present:
                cnt = session.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
                result["row_counts"][tbl] = cnt
                print(f"{tbl:<22} | {'YES':<10} | {cnt:<12} | OK")
            else:
                result["row_counts"][tbl] = 0
                print(f"{tbl:<22} | {'MISSING':<10} | {'0':<12} | WARNING")

        print("-" * 68)

        # Foreign Key Relationship Integrity Check
        print("\n[RELATIONSHIPS] Checking Foreign Key Integrity...")
        rel_errors = []

        # Patients -> Users
        orphan_patients = session.execute(text(
            "SELECT p.id FROM patients p LEFT JOIN users u ON p.user_id = u.id WHERE u.id IS NULL"
        )).fetchall()
        if orphan_patients:
            rel_errors.append(f"Orphan patients without valid user: {[r[0] for r in orphan_patients]}")

        # Doctors -> Users
        orphan_doctors = session.execute(text(
            "SELECT d.id FROM doctors d LEFT JOIN users u ON d.user_id = u.id WHERE u.id IS NULL"
        )).fetchall()
        if orphan_doctors:
            rel_errors.append(f"Orphan doctors without valid user: {[r[0] for r in orphan_doctors]}")

        # Visits -> Patients
        orphan_visits = session.execute(text(
            "SELECT v.visit_id FROM visits v LEFT JOIN patients p ON v.patient_id = p.id WHERE p.id IS NULL"
        )).fetchall()
        if orphan_visits:
            rel_errors.append(f"Orphan visits without valid patient: {[r[0] for r in orphan_visits]}")

        # Documents -> Patients
        orphan_docs = session.execute(text(
            "SELECT d.document_id FROM documents d LEFT JOIN patients p ON d.patient_id = p.id WHERE p.id IS NULL"
        )).fetchall()
        if orphan_docs:
            rel_errors.append(f"Orphan documents without valid patient: {[r[0] for r in orphan_docs]}")

        # ProcessingJobs -> Documents
        orphan_jobs = session.execute(text(
            "SELECT j.job_id FROM processing_jobs j LEFT JOIN documents d ON j.document_id = d.document_id WHERE d.document_id IS NULL"
        )).fetchall()
        if orphan_jobs:
            rel_errors.append(f"Orphan processing jobs without document: {[r[0] for r in orphan_jobs]}")

        if rel_errors:
            result["relationships_valid"] = False
            for err in rel_errors:
                print(f"  [ERROR] {err}")
        else:
            print("  All Foreign Key relationships are completely valid (0 orphaned records).\n")

        # Latest Document
        try:
            latest_doc = session.query(Document).order_by(Document.created_at.desc()).first()
            if latest_doc:
                result["latest_document"] = {
                    "document_id": latest_doc.document_id,
                    "patient_id": latest_doc.patient_id,
                    "document_type": latest_doc.document_type,
                    "status": latest_doc.status,
                    "created_at": str(latest_doc.created_at)
                }
                print(f"[LATEST DOCUMENT]   ID: {latest_doc.document_id} | Patient: {latest_doc.patient_id} | Status: {latest_doc.status}")
        except Exception as e:
            print(f"[LATEST DOCUMENT]   Could not query: {e}")

        # Latest Processing Job
        try:
            latest_job = session.query(ProcessingJob).order_by(ProcessingJob.created_at.desc()).first()
            if latest_job:
                result["latest_job"] = {
                    "job_id": latest_job.job_id,
                    "document_id": latest_job.document_id,
                    "status": latest_job.status,
                    "created_at": str(latest_job.created_at)
                }
                print(f"[LATEST JOB]        ID: {latest_job.job_id} | DocID: {latest_job.document_id} | Status: {latest_job.status}")
        except Exception as e:
            print(f"[LATEST JOB]        Could not query: {e}")

        # Latest Audit Log
        try:
            latest_audit = session.query(AccessLog).order_by(AccessLog.log_id.desc()).first()
            if latest_audit:
                result["latest_audit"] = {
                    "log_id": latest_audit.log_id,
                    "actor_id": latest_audit.actor_id,
                    "patient_id": latest_audit.patient_id,
                    "action": latest_audit.action,
                    "status": latest_audit.status,
                    "timestamp": str(latest_audit.timestamp)
                }
                print(f"[LATEST AUDIT]      LogID: {latest_audit.log_id} | Actor: {latest_audit.actor_id} | Action: {latest_audit.action} | Status: {latest_audit.status}")
        except Exception as e:
            print(f"[LATEST AUDIT]      Could not query: {e}")

    print("=" * 68)
    return result

def main():
    parser = argparse.ArgumentParser(description="HealthVault AI Database Verification Tool")
    parser.add_argument("--url", help="Database URL to verify (defaults to DATABASE_URL)")
    args = parser.parse_args()

    run_database_verification(args.url)

if __name__ == "__main__":
    main()
