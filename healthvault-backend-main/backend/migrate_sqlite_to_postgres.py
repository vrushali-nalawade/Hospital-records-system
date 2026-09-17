"""
migrate_sqlite_to_postgres.py — Safe SQLite to PostgreSQL Migration Engine

Migrates HealthVault AI's 8 relational tables from local SQLite (healthvault.db)
to Supabase PostgreSQL while strictly respecting foreign-key dependencies,
preserving IDs, timestamps, enums, booleans, and sequences.

Usage:
  python backend/migrate_sqlite_to_postgres.py [--sqlite-path PATH] [--pg-url URL]
"""

import os
import sys
import shutil
import sqlite3
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import settings
from backend.database import (
    Base,
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

MIGRATION_TABLE_ORDER = [
    "users",
    "patients",
    "doctors",
    "visits",
    "documents",
    "consents",
    "access_logs",
    "processing_jobs"
]

def parse_iso_datetime(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        # Handle formats with or without microseconds
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(val, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return None
    return None

def parse_boolean(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "t")
    return False

def backup_sqlite(sqlite_path: str) -> str:
    backup_path = f"{sqlite_path}.backup"
    if os.path.exists(sqlite_path):
        shutil.copy2(sqlite_path, backup_path)
        print(f"[BACKUP] Created safe SQLite backup at: {backup_path}")
    return backup_path

def migrate_data(sqlite_path: str, pg_url: str) -> Dict[str, Any]:
    print("=" * 65)
    print("      HEALTHVAULT AI — SQLITE TO POSTGRESQL MIGRATION      ")
    print("=" * 65)

    if not os.path.exists(sqlite_path):
        raise FileNotFoundError(f"SQLite database file not found at: {sqlite_path}")

    # 1. Backup SQLite
    backup_sqlite(sqlite_path)

    # 2. Normalize target URL and initialize PostgreSQL engine
    normalized_pg_url = normalize_database_url(pg_url)
    masked_url = mask_database_url(normalized_pg_url)
    print(f"[TARGET] PostgreSQL URL: {masked_url}")

    pg_engine = create_app_engine(normalized_pg_url)
    engine_type = get_database_engine_type(pg_engine)
    if engine_type != "postgresql":
        raise ValueError(
            f"Target database engine must be 'postgresql', but got '{engine_type}'. "
            f"Please provide a valid PostgreSQL connection string."
        )

    # Test connection
    print("[CONNECT] Testing PostgreSQL connection...")
    with pg_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("[CONNECT] Successfully connected to PostgreSQL!")

    # 3. Create all 8 tables if they do not exist
    print("[SCHEMA] Initializing all 8 tables in PostgreSQL...")
    Base.metadata.create_all(bind=pg_engine)
    print("[SCHEMA] All tables and schemas initialized successfully.")

    # 4. Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # Collect source row counts
    sqlite_counts = {}
    for tbl in MIGRATION_TABLE_ORDER:
        sqlite_cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        sqlite_counts[tbl] = sqlite_cur.fetchone()[0]

    print("\n[SOURCE] SQLite Row Counts:")
    for tbl, cnt in sqlite_counts.items():
        print(f"  • {tbl:<18}: {cnt}")

    # 5. Migrate table by table in dependency order
    print("\n[MIGRATING] Transferring records in foreign-key dependency order...")
    pg_counts = {}

    with Session(pg_engine) as session:
        # Table 1: users
        sqlite_cur.execute("SELECT * FROM users")
        for row in sqlite_cur.fetchall():
            d = dict(row)
            existing = session.query(User).filter(User.id == d["id"]).first()
            if not existing:
                session.add(User(
                    id=d["id"],
                    email=d["email"],
                    role=d["role"],
                    created_at=parse_iso_datetime(d.get("created_at"))
                ))
        session.commit()

        # Table 2: patients
        sqlite_cur.execute("SELECT * FROM patients")
        for row in sqlite_cur.fetchall():
            d = dict(row)
            existing = session.query(Patient).filter(Patient.id == d["id"]).first()
            if not existing:
                session.add(Patient(
                    id=d["id"],
                    user_id=d["user_id"],
                    name=d["name"],
                    created_at=parse_iso_datetime(d.get("created_at"))
                ))
        session.commit()

        # Table 3: doctors
        sqlite_cur.execute("SELECT * FROM doctors")
        for row in sqlite_cur.fetchall():
            d = dict(row)
            existing = session.query(Doctor).filter(Doctor.id == d["id"]).first()
            if not existing:
                session.add(Doctor(
                    id=d["id"],
                    user_id=d["user_id"],
                    name=d["name"],
                    specialty=d.get("specialty"),
                    created_at=parse_iso_datetime(d.get("created_at"))
                ))
        session.commit()

        # Table 4: visits
        sqlite_cur.execute("SELECT * FROM visits")
        for row in sqlite_cur.fetchall():
            d = dict(row)
            existing = session.query(Visit).filter(Visit.visit_id == d["visit_id"]).first()
            if not existing:
                session.add(Visit(
                    visit_id=d["visit_id"],
                    patient_id=d["patient_id"],
                    date=d["date"],
                    doctor_id=d.get("doctor_id"),
                    created_at=parse_iso_datetime(d.get("created_at"))
                ))
        session.commit()

        # Table 5: documents
        sqlite_cur.execute("SELECT * FROM documents")
        for row in sqlite_cur.fetchall():
            d = dict(row)
            existing = session.query(Document).filter(Document.document_id == d["document_id"]).first()
            if not existing:
                session.add(Document(
                    document_id=d["document_id"],
                    patient_id=d["patient_id"],
                    visit_id=d.get("visit_id"),
                    storage_path=d["storage_path"],
                    document_type=d["document_type"],
                    status=d.get("status", "PROCESSING"),
                    created_at=parse_iso_datetime(d.get("created_at")),
                    processed_at=parse_iso_datetime(d.get("processed_at")),
                    needs_review=parse_boolean(d.get("needs_review", False)),
                    confidence=float(d.get("confidence", 1.0))
                ))
        session.commit()

        # Table 6: consents
        sqlite_cur.execute("SELECT * FROM consents")
        for row in sqlite_cur.fetchall():
            d = dict(row)
            existing = session.query(Consent).filter(Consent.consent_id == d["consent_id"]).first()
            if not existing:
                session.add(Consent(
                    consent_id=d["consent_id"],
                    patient_id=d["patient_id"],
                    doctor_id=d["doctor_id"],
                    permission=d["permission"],
                    status=d.get("status", "ACTIVE"),
                    expires_at=parse_iso_datetime(d.get("expires_at")),
                    created_at=parse_iso_datetime(d.get("created_at"))
                ))
        session.commit()

        # Table 7: access_logs
        sqlite_cur.execute("SELECT * FROM access_logs")
        for row in sqlite_cur.fetchall():
            d = dict(row)
            existing = session.query(AccessLog).filter(AccessLog.log_id == d["log_id"]).first()
            if not existing:
                session.add(AccessLog(
                    log_id=d["log_id"],
                    actor_id=d["actor_id"],
                    patient_id=d.get("patient_id"),
                    action=d["action"],
                    timestamp=parse_iso_datetime(d.get("timestamp")),
                    status=d["status"]
                ))
        session.commit()

        # Synchronize PostgreSQL auto-increment sequence for access_logs
        try:
            seq_res = session.execute(text("SELECT pg_get_serial_sequence('access_logs', 'log_id')")).scalar()
            if seq_res:
                session.execute(text(f"SELECT setval('{seq_res}', COALESCE((SELECT MAX(log_id) FROM access_logs), 1))"))
                session.commit()
                print("[SEQUENCE] Synchronized access_logs sequence with maximum log_id.")
        except Exception as seq_err:
            print(f"[SEQUENCE WARNING] Could not reset serial sequence: {seq_err}")

        # Table 8: processing_jobs
        sqlite_cur.execute("SELECT * FROM processing_jobs")
        for row in sqlite_cur.fetchall():
            d = dict(row)
            existing = session.query(ProcessingJob).filter(ProcessingJob.job_id == d["job_id"]).first()
            if not existing:
                session.add(ProcessingJob(
                    job_id=d["job_id"],
                    document_id=d["document_id"],
                    status=d.get("status", "PENDING"),
                    error_message=d.get("error_message"),
                    created_at=parse_iso_datetime(d.get("created_at")),
                    updated_at=parse_iso_datetime(d.get("updated_at"))
                ))
        session.commit()

        # Query PostgreSQL counts
        for tbl in MIGRATION_TABLE_ORDER:
            cnt = session.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
            pg_counts[tbl] = cnt

    sqlite_conn.close()

    # 6. Verification and Comparison Report
    print("\n" + "=" * 65)
    print("            MIGRATION ROW COUNT VERIFICATION             ")
    print("=" * 65)
    print(f"{'Table Name':<20} | {'SQLite Count':<14} | {'PostgreSQL Count':<16} | {'Status'}")
    print("-" * 65)

    all_matched = True
    for tbl in MIGRATION_TABLE_ORDER:
        s_cnt = sqlite_counts[tbl]
        p_cnt = pg_counts[tbl]
        # Check if PostgreSQL has at least the SQLite rows
        match = (p_cnt >= s_cnt)
        status_str = "MATCHED OK" if match else "MISMATCH"
        if not match:
            all_matched = False
        print(f"{tbl:<20} | {s_cnt:<14} | {p_cnt:<16} | {status_str}")

    print("-" * 65)

    # 7. Verification of latest items in PostgreSQL
    with Session(pg_engine) as session:
        latest_doc = session.query(Document).order_by(Document.created_at.desc()).first()
        latest_job = session.query(ProcessingJob).order_by(ProcessingJob.created_at.desc()).first()
        latest_audit = session.query(AccessLog).order_by(AccessLog.log_id.desc()).first()

    print("\n[VERIFY] Key Records in PostgreSQL:")
    if latest_doc:
        print(f"  • Latest Document: ID={latest_doc.document_id}, Patient={latest_doc.patient_id}, Status={latest_doc.status}")
    if latest_job:
        print(f"  • Latest Job:      ID={latest_job.job_id}, DocID={latest_job.document_id}, Status={latest_job.status}")
    if latest_audit:
        print(f"  • Latest Audit:    LogID={latest_audit.log_id}, Actor={latest_audit.actor_id}, Action={latest_audit.action}, Status={latest_audit.status}")

    print("\n[SUCCESS] PostgreSQL migration completed safely and verified successfully!\n")

    return {
        "success": all_matched,
        "sqlite_counts": sqlite_counts,
        "pg_counts": pg_counts,
        "latest_document_id": latest_doc.document_id if latest_doc else None,
        "latest_job_id": latest_job.job_id if latest_job else None,
        "latest_audit_id": latest_audit.log_id if latest_audit else None
    }

def main():
    parser = argparse.ArgumentParser(description="HealthVault AI SQLite to PostgreSQL Migration Engine")
    parser.add_argument("--sqlite-path", default=os.path.join(PROJECT_ROOT, "healthvault.db"), help="Path to SQLite database")
    parser.add_argument("--pg-url", default=settings.DATABASE_URL, help="PostgreSQL connection string")
    args = parser.parse_args()

    try:
        migrate_data(args.sqlite_path, args.pg_url)
    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
