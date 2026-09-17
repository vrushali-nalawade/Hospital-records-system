import sqlite3
import json
import os
from typing import List, Dict, Any

DB_PATH = "health_locker.db"

def get_processed_records(patient_id: str) -> List[Dict[str, Any]]:
    """
    Standardized handoff API for Person 3 (RAG).
    Retrieves all records for a patient and normalizes them into a frozen JSON schema.
    """
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Resolve padding if patient_id is just a number
    resolved_id = str(patient_id).strip()
    if resolved_id.isdigit():
        resolved_id = f"P-BATCH-{int(resolved_id):04d}"

    # Query records with explicit visit_id
    records_query = """
        SELECT r.id AS record_id, r.patient_id, r.visit_id, r.raw_ocr_text, r.ocr_confidence, r.needs_review,
               v.visit_date
        FROM records r
        LEFT JOIN visits v ON r.visit_id = v.id
        WHERE r.patient_id = ? OR r.patient_id = ? OR r.patient_id LIKE ?
        ORDER BY r.id DESC
    """
    rows = conn.execute(records_query, (str(patient_id), resolved_id, f"%{patient_id}%")).fetchall()
    
    standardized_records = []
    
    for row in rows:
        record_id = row["record_id"]
        db_patient_id = row["patient_id"] or patient_id
        doc_id = f"DOC-{record_id:04d}"
        visit_id = f"VIS-{row['visit_id']:04d}" if row["visit_id"] else "VIS-UNKNOWN"
        visit_date = row["visit_date"] or "1970-01-01"
        
        raw_text = row["raw_ocr_text"] or ""
        ocr_conf = float(row["ocr_confidence"]) if row["ocr_confidence"] is not None else 0.0
        
        # Person 2 output confidence in 0-100 range, converting to 0.0-1.0
        if ocr_conf > 1.0:
            ocr_conf = round(ocr_conf / 100.0, 2)
            
        needs_review = bool(row["needs_review"])
        
        # Fetch entities
        entities = conn.execute("""
            SELECT entity_type, entity_name, confidence, warning,
                   diagnosis, medication, dosage, entity_details, lab_values
            FROM extracted_entities
            WHERE record_id = ?
        """, (record_id,)).fetchall()
        
        medications = []
        diagnoses = []
        lab_results = []
        
        for ent in entities:
            ent_type = ent["entity_type"]
            ent_conf = float(ent["confidence"]) if ent["confidence"] is not None else 0.90
            
            # Map back to structured fields based on the type
            if ent_type == "Medication":
                details = ent["entity_details"] or ""
                freq = "As directed"
                if "Freq:" in details:
                    freq = details.split("Freq:")[-1].strip()
                
                medications.append({
                    "name": ent["medication"] or ent["entity_name"] or "",
                    "dosage": ent["dosage"] or "Standard dosage",
                    "frequency": freq,
                    "confidence": ent_conf
                })
                
            elif ent_type == "Diagnosis":
                diagnoses.append({
                    "condition": ent["diagnosis"] or ent["entity_name"] or "",
                    "confidence": ent_conf
                })
                
            elif ent_type == "Lab Report":
                val_str = str(ent["lab_values"] or ent["entity_details"] or "")
                clean_val = val_str.replace("Value: ", "").strip()
                
                # Basic parsing to split value and unit (e.g. "7.2 %", "130 mg/dl")
                val_parts = clean_val.split(" ")
                num_val = val_parts[0] if val_parts else clean_val
                unit = " ".join(val_parts[1:]) if len(val_parts) > 1 else ""
                
                # Attempt to cast numeric value to float safely
                try:
                    num_val_float = float(num_val)
                    num_val = num_val_float
                except ValueError:
                    pass
                
                lab_results.append({
                    "test": ent["entity_name"] or "",
                    "value": num_val,
                    "unit": unit,
                    "date": visit_date,
                    "confidence": ent_conf
                })
        
        # Construct the frozen output schema
        standardized_records.append({
            "patient_id": db_patient_id,
            "document_id": doc_id,
            "visit_id": visit_id,
            "document_type": "medical_record",
            "date": visit_date,
            "ocr": {
                "text": raw_text,
                "confidence": ocr_conf
            },
            "medications": medications,
            "diagnoses": diagnoses,
            "lab_results": lab_results,
            "procedures": [],
            "allergies": [],
            "needs_review": needs_review
        })

    conn.close()
    return standardized_records


if __name__ == "__main__":
    # Test handoff API
    import sys
    test_pid = sys.argv[1] if len(sys.argv) > 1 else "1"
    records = get_processed_records(test_pid)
    
    # Write to a file instead of print
    with open("my_test_output.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
        
    print(f"--- Saved API Output to my_test_output.json ---")
