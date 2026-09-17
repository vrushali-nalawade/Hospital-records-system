"""
inspect_database.py — Safe Read-Only Database Inspection Tool for HealthVault AI

Supports inspecting both SQLite and PostgreSQL (Supabase) relational databases.
Strictly read-only; never exposes database passwords, Firebase private keys, or API tokens.

Usage:
  python backend/inspect_database.py
  python backend/inspect_database.py --sqlite
  python backend/inspect_database.py --url postgresql://user:pass@host:5432/postgres
"""

import os
import sys
import argparse
from typing import Optional
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
from backend.models import Document, ProcessingJob, AccessLog

SENSITIVE_FIELD_NAMES = {
    "password", "secret", "token", "key", "private_key",
    "firebase_private_key", "credentials"
}

def sanitize_row(row_dict: dict) -> dict:
    sanitized = {}
    for k, v in row_dict.items():
        if any(s in k.lower() for s in SENSITIVE_FIELD_NAMES):
            sanitized[k] = "[REDACTED]"
        else:
            sanitized[k] = v
    return sanitized

def inspect_database(target_url: Optional[str] = None):
    url = normalize_database_url(target_url or settings.DATABASE_URL)
    masked_url = mask_database_url(url)
    
    print("=" * 65)
    print("        HEALTHVAULT AI — READ-ONLY DATABASE INSPECTION        ")
    print("=" * 65)
    print(f"Connection Target : {masked_url}")

    try:
        engine = create_app_engine(url)
        engine_type = get_database_engine_type(engine)
        print(f"Database Engine   : {engine_type.upper()}")

        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"Connection Status : CONNECTED OK\n")
    except Exception as e:
        print(f"Connection Status : FAILED ({e})\n")
        return

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    # Sort with expected healthvault tables first
    expected_tables = [
        "users", "patients", "doctors", "visits",
        "documents", "consents", "access_logs", "processing_jobs"
    ]
    sorted_tables = [t for t in expected_tables if t in table_names] + [t for t in table_names if t not in expected_tables]

    print(f"Total Relational Tables: {len(sorted_tables)}")
    print(f"Tables List: {', '.join(sorted_tables)}\n")

    with Session(engine) as session:
        for table in sorted_tables:
            print("-" * 65)
            print(f"TABLE: {table}")
            print("-" * 65)
            
            columns = inspector.get_columns(table)
            pk_constraint = inspector.get_pk_constraint(table)
            pk_cols = set(pk_constraint.get("constrained_columns", [])) if pk_constraint else set()
            
            for col in columns:
                col_name = col["name"]
                col_type = str(col["type"])
                null_flag = "" if col.get("nullable", True) else " NOT NULL"
                pk_flag = " [PRIMARY KEY]" if col_name in pk_cols else ""
                print(f"  • {col_name:<22} {col_type:<16}{null_flag}{pk_flag}")

            # Get row count safely
            try:
                count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            except Exception as err:
                count = f"Error: {err}"
            print(f"\n  Total Records: {count}")

            if isinstance(count, int) and count > 0:
                try:
                    # Query latest 5 rows
                    first_col = columns[0]["name"] if columns else "1"
                    rows = session.execute(text(f"SELECT * FROM {table} ORDER BY {first_col} DESC LIMIT 5")).mappings().fetchall()
                    print(f"  Latest {len(rows)} Rows:")
                    for row in rows:
                        row_dict = sanitize_row(dict(row))
                        print("   ", row_dict)
                except Exception as row_err:
                    print(f"  [Error previewing rows: {row_err}]")
            print()

        # Detailed trace of latest uploaded document
        if "documents" in sorted_tables:
            try:
                latest_doc = session.query(Document).order_by(Document.created_at.desc()).first()
                if latest_doc:
                    print("=" * 65)
                    print("LATEST UPLOADED DOCUMENT TRACE")
                    print("=" * 65)
                    print(f"  document_id         : {latest_doc.document_id}")
                    print(f"  patient_id          : {latest_doc.patient_id}")
                    print(f"  visit_id            : {latest_doc.visit_id}")
                    print(f"  storage_path        : {latest_doc.storage_path}")
                    print(f"  document_type       : {latest_doc.document_type}")
                    print(f"  status              : {latest_doc.status}")
                    print(f"  created_at          : {latest_doc.created_at}")
                    print(f"  processed_at        : {latest_doc.processed_at}")
                    print(f"  needs_review        : {latest_doc.needs_review}")
                    print(f"  confidence          : {latest_doc.confidence}")
                    print()
            except Exception as doc_err:
                print(f"[Could not query latest document: {doc_err}]")

        # Detailed trace of latest processing job
        if "processing_jobs" in sorted_tables:
            try:
                latest_job = session.query(ProcessingJob).order_by(ProcessingJob.created_at.desc()).first()
                if latest_job:
                    print("=" * 65)
                    print("LATEST PROCESSING JOB TRACE")
                    print("=" * 65)
                    print(f"  job_id              : {latest_job.job_id}")
                    print(f"  document_id         : {latest_job.document_id}")
                    print(f"  status              : {latest_job.status}")
                    print(f"  error_message       : {latest_job.error_message}")
                    print(f"  created_at          : {latest_job.created_at}")
                    print(f"  updated_at          : {latest_job.updated_at}")
                    print()
            except Exception as job_err:
                print(f"[Could not query latest processing job: {job_err}]")

        # Detailed trace of latest audit log
        if "access_logs" in sorted_tables:
            try:
                latest_log = session.query(AccessLog).order_by(AccessLog.log_id.desc()).first()
                if latest_log:
                    print("=" * 65)
                    print("LATEST AUDIT ACCESS LOG TRACE")
                    print("=" * 65)
                    print(f"  log_id              : {latest_log.log_id}")
                    print(f"  actor_id            : {latest_log.actor_id}")
                    print(f"  patient_id          : {latest_log.patient_id}")
                    print(f"  action              : {latest_log.action}")
                    print(f"  timestamp           : {latest_log.timestamp}")
                    print(f"  status              : {latest_log.status}")
                    print()
            except Exception as log_err:
                print(f"[Could not query latest audit log: {log_err}]")

def main():
    parser = argparse.ArgumentParser(description="HealthVault AI Read-Only Database Inspection Tool")
    parser.add_argument("--sqlite", action="store_true", help="Inspect local SQLite database (healthvault.db)")
    parser.add_argument("--url", help="Inspect specific database URL (PostgreSQL or SQLite)")
    args = parser.parse_args()

    if args.sqlite:
        sqlite_file = os.path.join(PROJECT_ROOT, "healthvault.db")
        target_url = f"sqlite:///{sqlite_file}"
    elif args.url:
        target_url = args.url
    else:
        target_url = settings.DATABASE_URL

    inspect_database(target_url)

if __name__ == "__main__":
    main()
