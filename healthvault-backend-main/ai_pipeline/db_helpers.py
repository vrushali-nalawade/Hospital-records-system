import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "health_locker.db"))

def init_db():
    """Initializes the health_locker.db SQLite tables if they do not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create visits table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id TEXT PRIMARY KEY,
            visit_date TEXT,
            doctor_name TEXT,
            hospital_name TEXT
        )
    """)
    
    # 2. Create records table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT,
            visit_id TEXT,
            raw_ocr_text TEXT,
            ocr_confidence REAL,
            needs_review INTEGER,
            file_path TEXT,
            doctor_name TEXT,
            hospital_name TEXT,
            created_at TEXT
        )
    """)
    
    # 3. Create extracted_entities table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extracted_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER,
            entity_type TEXT,
            entity_name TEXT,
            confidence REAL,
            warning TEXT,
            diagnosis TEXT,
            medication TEXT,
            dosage TEXT,
            entity_details TEXT,
            lab_values TEXT,
            FOREIGN KEY (record_id) REFERENCES records (id)
        )
    """)
    
    conn.commit()
    conn.close()

def save_pipeline_result(patient_id: str, visit_id: str, doctor_name: str, ocr_result: Dict[str, Any], ner_result: Dict[str, Any]) -> Tuple[str, bool]:
    """
    Saves the OCR and NER results into SQLite database and returns (doc_id, needs_review_flag).
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    prescribed_date = ner_result.get("prescribed_date") or datetime.utcnow().strftime("%Y-%m-%d")
    hospital_name = "City General Hospital"
    
    # 1. Save / Update Visit
    cursor.execute("""
        INSERT OR IGNORE INTO visits (id, visit_date, doctor_name, hospital_name)
        VALUES (?, ?, ?, ?)
    """, (visit_id, prescribed_date, doctor_name, hospital_name))
    
    # 2. Compute overall needs_review status
    needs_review = 0
    
    for med in ner_result.get("medications", []):
        if med.get("needs_review"):
            needs_review = 1
    for diag in ner_result.get("diagnoses", []):
        if diag.get("needs_review"):
            needs_review = 1
    for lab in ner_result.get("lab_results", []):
        if lab.get("needs_review"):
            needs_review = 1
            
    # If OCR confidence is too low (e.g. < 70%), flag it
    avg_ocr_conf = float(ocr_result.get("avg_confidence", 100))
    if avg_ocr_conf < 70.0:
        needs_review = 1
        
    # 3. Save Record
    file_path = ocr_result.get("cleaned_image_path") or ""
    cursor.execute("""
        INSERT INTO records (patient_id, visit_id, raw_ocr_text, ocr_confidence, needs_review, file_path, doctor_name, hospital_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (patient_id, visit_id, ocr_result.get("full_text", ""), avg_ocr_conf, needs_review, file_path, doctor_name, hospital_name, datetime.utcnow().isoformat()))
    
    record_id = cursor.lastrowid
    doc_id = f"DOC-{record_id:04d}"
    
    # 4. Save Extracted Entities
    for med in ner_result.get("medications", []):
        ent_details = f"Dosage: {med.get('dosage', '')} | Freq: {med.get('frequency', '')}"
        if med.get("warning"):
            ent_details += f" | Warning: {med.get('warning')}"
        cursor.execute("""
            INSERT INTO extracted_entities (record_id, entity_type, entity_name, confidence, warning, medication, dosage, entity_details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (record_id, "Medication", med.get("medication", ""), float(med.get("confidence", 1.0)), med.get("warning", ""), med.get("medication", ""), med.get("dosage", ""), ent_details))
        
    for diag in ner_result.get("diagnoses", []):
        cursor.execute("""
            INSERT INTO extracted_entities (record_id, entity_type, entity_name, confidence, diagnosis)
            VALUES (?, ?, ?, ?, ?)
        """, (record_id, "Diagnosis", diag.get("diagnosis", ""), float(diag.get("confidence", 1.0)), diag.get("diagnosis", "")))
        
    for lab in ner_result.get("lab_results", []):
        lab_val = str(lab.get("value", ""))
        cursor.execute("""
            INSERT INTO extracted_entities (record_id, entity_type, entity_name, confidence, warning, lab_values, entity_details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (record_id, "Lab Report", lab.get("lab_test", ""), float(lab.get("confidence", 1.0)), lab.get("warning", ""), lab_val, f"Value: {lab_val}"))
        
    conn.commit()
    conn.close()
    
    return doc_id, bool(needs_review)

def get_patient_documents(patient_id: str) -> List[Dict[str, Any]]:
    """Retrieves all documents associated with a patient."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.id AS record_id, r.patient_id, r.visit_id, r.raw_ocr_text, r.ocr_confidence, r.needs_review, r.file_path, r.doctor_name, r.hospital_name, v.visit_date
        FROM records r
        LEFT JOIN visits v ON r.visit_id = v.id
        WHERE r.patient_id = ?
    """, (patient_id,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_entities_for_record(record_id: int) -> List[Dict[str, Any]]:
    """Retrieves all extracted entities for a specific record."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT entity_type, entity_name, confidence, warning, diagnosis, medication, dosage, entity_details, lab_values
        FROM extracted_entities
        WHERE record_id = ?
    """, (record_id,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def query_patient_records(patient_id: str) -> List[Dict[str, Any]]:
    """Used in full_pipeline.py as fallback query."""
    return get_patient_documents(patient_id)
