'''
index_existing_dataset.py — Comprehensive One-Time Dataset Indexer & Synchronizer
---------------------------------------------------------------------------------
Indexes existing medical datasets (JSON & SQLite) into Qdrant Cloud and Supabase PostgreSQL.
Usage:
  python scripts/index_existing_dataset.py [--dry-run]
'''

import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime
from typing import List, Dict, Any

# Ensure project root and ai_pipeline are on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AI_PIPELINE = os.path.join(PROJECT_ROOT, "ai_pipeline")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if AI_PIPELINE not in sys.path:
    sys.path.insert(0, AI_PIPELINE)

try:
    from backend.config import settings
except Exception:
    class MockSettings:
        QDRANT_URL = os.getenv("QDRANT_URL")
        QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
        DATABASE_URL = os.getenv("DATABASE_URL")
    settings = MockSettings()

from ai_pipeline.embeddings import MedicalEmbedder, adaptive_chunk_record
from ai_pipeline.vector_store import MedicalVectorStore, COLLECTION_NAME

def load_json_records(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
    return []

def load_sqlite_records(db_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(db_path):
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    records = []
    # Check if extracted_documents and medical_visits exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='extracted_documents'")
    if cur.fetchone():
        query = '''
            SELECT d.doc_id, d.visit_id, d.raw_ocr_text, d.avg_ocr_confidence, d.needs_review,
                   v.patient_id, v.visit_date, v.doctor_name
            FROM extracted_documents d
            LEFT JOIN medical_visits v ON d.visit_id = v.visit_id
        '''
        for row in cur.execute(query).fetchall():
            r = dict(row)
            doc_id = r.get("doc_id") or "DOC_UNKNOWN"
            patient_id = r.get("patient_id") or "PATIENT_UNKNOWN"
            visit_id = r.get("visit_id") or "VIS_UNKNOWN"
            date = r.get("visit_date") or "2026-08-10"
            raw_text = r.get("raw_ocr_text") or ""
            
            # Fetch entities for this doc if available
            cur2 = conn.cursor()
            cur2.execute("SELECT entity_type, entity_name, details_json, dosage, medication, diagnosis, lab_values FROM extracted_entities WHERE doc_id=?", (doc_id,))
            meds, diags, labs = [], [], []
            for erow in cur2.fetchall():
                etype = erow[0]
                ename = erow[1]
                if etype == "Medication" or erow[4]:
                    meds.append(erow[4] or ename)
                elif etype == "Diagnosis" or erow[5]:
                    diags.append(erow[5] or ename)
                elif etype == "Lab Report" or erow[6]:
                    labs.append({"test_name": ename, "value": erow[6] or ""})

            records.append({
                "patient_id": patient_id,
                "document_id": doc_id,
                "visit_id": visit_id,
                "document_type": "prescription" if "Rx" in raw_text or meds else "medical_record",
                "date": date,
                "ocr": raw_text,
                "medications": meds,
                "diagnoses": diags,
                "lab_results": labs,
                "needs_review": bool(r.get("needs_review", False)),
                "confidence": float(r.get("avg_ocr_confidence", 95.0)) / 100.0 if r.get("avg_ocr_confidence", 95.0) > 1.0 else float(r.get("avg_ocr_confidence", 0.95))
            })

    conn.close()
    return records

def index_dataset(
    qdrant_url: str = None,
    qdrant_api_key: str = None,
    pg_url: str = None,
    hf_embed_url: str = None,
    dry_run: bool = False
):
    print("=" * 70)
    print("      HEALTHVAULT AI — DATASET VECTOR & RELATIONAL INDEXER      ")
    print("=" * 70)

    # 1. Collect all dataset sources
    root_dir = os.path.abspath(os.path.join(PROJECT_ROOT, ".."))
    json_paths = [
        os.path.join(PROJECT_ROOT, "data", "test_dataset.json"),
        os.path.join(PROJECT_ROOT, "data", "batch2_patients.json"),
        os.path.join(root_dir, "data", "test_dataset.json"),
        os.path.join(root_dir, "data", "batch2_patients.json"),
        os.path.join(root_dir, "test_dataset.json"),
    ]
    sqlite_paths = [
        os.path.join(PROJECT_ROOT, "health_locker.db"),
        os.path.join(root_dir, "health_locker.db")
    ]

    all_raw_records = []
    seen_doc_ids = set()

    for jp in json_paths:
        if os.path.exists(jp):
            recs = load_json_records(jp)
            for r in recs:
                did = r.get("document_id")
                if did and did not in seen_doc_ids:
                    seen_doc_ids.add(did)
                    all_raw_records.append(r)
            print(f"[DATASET] Loaded {len(recs)} record(s) from JSON: {jp}")

    for sp in sqlite_paths:
        if os.path.exists(sp):
            recs = load_sqlite_records(sp)
            for r in recs:
                did = r.get("document_id")
                if did and did not in seen_doc_ids:
                    seen_doc_ids.add(did)
                    all_raw_records.append(r)
            print(f"[DATASET] Loaded {len(recs)} record(s) from SQLite: {sp}")

    print(f"\n[TOTAL] Unique medical documents found for indexing: {len(all_raw_records)}")
    if not all_raw_records:
        print("[WARNING] No records found to index. Exiting.")
        return

    # 2. Chunk records
    all_chunks = []
    for rec in all_raw_records:
        chunks = adaptive_chunk_record(rec)
        all_chunks.extend(chunks)

    print(f"[CHUNKING] Generated {len(all_chunks)} chunk(s) from {len(all_raw_records)} documents.")

    if dry_run:
        print("\n[DRY RUN] Verification summary:")
        print(f"  • Total Documents: {len(all_raw_records)}")
        print(f"  • Total Chunks:    {len(all_chunks)}")
        patients = set(c.get('patient_id') for c in all_chunks)
        print(f"  • Unique Patients: {len(patients)} ({sorted(list(patients))[:10]}...)")
        print("[DRY RUN COMPLETED] No cloud data was modified.")
        return

    # 3. Initialize Embedder and Vector Store
    print("\n[EMBEDDER] Initializing MedicalEmbedder (1024-d)...")
    embedder = MedicalEmbedder(hf_embedding_url=hf_embed_url)

    target_qdrant_url = qdrant_url or getattr(settings, "QDRANT_URL", None)
    target_qdrant_key = qdrant_api_key or getattr(settings, "QDRANT_API_KEY", None)

    print(f"[VECTOR STORE] Target Qdrant: {target_qdrant_url or 'Local Disk / Memory'}")
    vector_store = MedicalVectorStore(
        url=target_qdrant_url,
        api_key=target_qdrant_key,
        vector_size=1024
    )

    # 4. Generate Embeddings & Upsert to Qdrant
    cache_path = os.path.join(PROJECT_ROOT, "data", "embeddings_cache.json")
    embeddings = None
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as cf:
                cache_data = json.load(cf)
                if len(cache_data) == len(all_chunks):
                    print(f"[CACHE] Loaded {len(cache_data)} precomputed embeddings from cache!")
                    embeddings = cache_data
        except Exception:
            pass

    if embeddings is None:
        print(f"\n[INDEXING] Computing embeddings for {len(all_chunks)} chunks...")
        embeddings = embedder.embed_documents(all_chunks)
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as cf:
                json.dump(embeddings, cf)
            print(f"[CACHE] Cached {len(embeddings)} embeddings to {cache_path}")
        except Exception as ce:
            print(f"[CACHE WARNING] Could not write cache: {ce}")

    print(f"[INDEXING] Upserting {len(embeddings)} vectors into Qdrant collection '{COLLECTION_NAME}'...")
    upsert_count = vector_store.upsert_records(all_chunks, embeddings)
    print(f"[INDEXING SUCCESS] Upserted {upsert_count} points into Qdrant collection '{COLLECTION_NAME}'!")

    # 5. Synchronize into PostgreSQL if configured
    target_pg_url = pg_url or getattr(settings, "DATABASE_URL", None)
    if target_pg_url and not target_pg_url.startswith("sqlite"):
        try:
            print(f"\n[POSTGRES] Synchronizing relational records into PostgreSQL...")
            from backend.database import create_app_engine, Base
            from backend.models import User, Patient, Document, Visit
            from sqlalchemy.orm import Session

            engine = create_app_engine(target_pg_url)
            Base.metadata.create_all(bind=engine)

            with Session(engine) as session:
                for doc in all_raw_records:
                    pid = doc.get("patient_id", "P_UNKNOWN")
                    did = doc.get("document_id", "DOC_UNKNOWN")
                    vid = doc.get("visit_id")
                    
                    # Ensure patient user exists
                    uid = f"{pid}_UID"
                    if not session.query(User).filter(User.id == uid).first():
                        session.add(User(id=uid, email=f"{pid.lower()}@healthvault.local", role="PATIENT"))
                        session.commit()
                    
                    if not session.query(Patient).filter(Patient.id == pid).first():
                        session.add(Patient(id=pid, user_id=uid, name=f"Patient {pid}"))
                        session.commit()

                    if vid and not session.query(Visit).filter(Visit.visit_id == vid).first():
                        session.add(Visit(visit_id=vid, patient_id=pid, date=doc.get("date", "2026-08-10")))
                        session.commit()

                    existing_doc = session.query(Document).filter(Document.document_id == did).first()
                    if not existing_doc:
                        session.add(Document(
                            document_id=did,
                            patient_id=pid,
                            visit_id=vid,
                            storage_path=f"preindexed/{did}.json",
                            document_type=doc.get("document_type", "prescription"),
                            status="READY",
                            confidence=float(doc.get("confidence", 1.0)),
                            needs_review=bool(doc.get("needs_review", False)),
                            created_at=datetime.utcnow()
                        ))
                session.commit()
            print("[POSTGRES SUCCESS] Relational tables synchronized successfully!")
        except Exception as pg_err:
            print(f"[POSTGRES WARNING] Relational sync skipped or warning: {pg_err}")

    print("\n" + "=" * 70)
    print("        DATASET INDEXING & SYNCHRONIZATION COMPLETE!        ")
    print("=" * 70)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HealthVault AI Dataset Indexer")
    parser.add_argument("--qdrant-url", default=None, help="Qdrant Cloud URL")
    parser.add_argument("--qdrant-api-key", default=None, help="Qdrant Cloud API Key")
    parser.add_argument("--pg-url", default=None, help="PostgreSQL connection URL")
    parser.add_argument("--hf-embed-url", default=None, help="Hugging Face Embedding Endpoint")
    parser.add_argument("--dry-run", action="store_true", help="Perform dry run without modifying databases")
    args = parser.parse_args()

    index_dataset(
        qdrant_url=args.qdrant_url,
        qdrant_api_key=args.qdrant_api_key,
        pg_url=args.pg_url,
        hf_embed_url=args.hf_embed_url,
        dry_run=args.dry_run
    )
