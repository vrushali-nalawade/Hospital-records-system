import json
import os
import sys

# Ensure UTF-8 output encoding for Windows terminal compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from ocr_pipeline import run_ocr
from medical_ner import extract_medical_entities
from db_helpers import save_pipeline_result, query_patient_records

def process_medical_document(image_path, patient_id="P-94821", visit_id="VIS-1001", doctor_name="Dr. Arthur Vance, M.D."):
    """
    Person 2 Full End-to-End Pipeline:
    Uploaded Image -> Preprocessing -> OCR -> Medical NER -> SQLite DB Row
    """
    print(f"\n=======================================================")
    print(f"[P2 ENGINE] RUNNING PERSON 2 (OCR + MEDICAL NLP) PIPELINE")
    print(f"=======================================================")
    print(f"Input Document Image: {image_path}")
    print(f"Patient ID: {patient_id} | Visit ID: {visit_id}")
    
    # 1. OCR Stage
    print("\n[Step 1 & 2] Preprocessing Image & Extracting Text (OCR)...")
    ocr_result = run_ocr(image_path)
    print(f"[OK] OCR Engine Used: {ocr_result['engine']}")
    print(f"[OK] Overall OCR Confidence: {ocr_result['avg_confidence']}%")
    print(f"[OK] Cleaned Debug Image Saved: {ocr_result['cleaned_image_path']}")
    
    # 2. Medical NER Stage
    print("\n[Step 3 & 4] Running Medical NER & Confidence Scoring...")
    ner_result = extract_medical_entities(ocr_result["full_text"], ocr_result["word_confidences"])
    
    print("\n--- EXTRACTED STRUCTURED ENTITIES ---")
    print(f"Prescribed Date: {ner_result['prescribed_date']}")
    
    print("\nMedications Found:")
    for med in ner_result["medications"]:
        flag = " [NEEDS VERIFICATION]" if med["needs_review"] else " [CONFIDENT]"
        print(f"  • {med['medication']} {med['dosage']} ({med['frequency']}) - Confidence: {int(med['confidence']*100)}%{flag}")
        if med["warning"]:
            print(f"    └── {med['warning']}")
            
    print("\nDiagnoses Found:")
    for diag in ner_result["diagnoses"]:
        flag = " [NEEDS VERIFICATION]" if diag["needs_review"] else " [CONFIDENT]"
        print(f"  • {diag['diagnosis']} - Confidence: {int(diag['confidence']*100)}%{flag}")
        
    print("\nLab Results Found:")
    for lab in ner_result["lab_results"]:
        flag = " [NEEDS VERIFICATION]" if lab["needs_review"] else " [CONFIDENT]"
        print(f"  • {lab['lab_test']}: {lab['value']} - Confidence: {int(lab['confidence']*100)}%{flag}")
        if lab["warning"]:
            print(f"    └── {lab['warning']}")
            
    # 3. Database Insertion Stage
    print("\n[Step 5] Writing Structured Data to Health Locker Database...")
    doc_id, needs_review_flag = save_pipeline_result(patient_id, visit_id, doctor_name, ocr_result, ner_result)
    
    print(f"[DB SUCCESS] Database Entry Created! Document ID: {doc_id}")
    if needs_review_flag:
        print("[FLAGGED] Flagged for Human-In-The-Loop (HITL) Verification due to low-confidence fields.")
    else:
        print("[VERIFIED] All fields high confidence. Automated ingestion complete.")
        
    return {
        "doc_id": doc_id,
        "ocr_result": ocr_result,
        "ner_result": ner_result,
        "needs_review": needs_review_flag
    }

if __name__ == "__main__":
    test_img = "test_prescription.png" if os.path.exists("test_prescription.png") else "dataset/10.jpg"
    if os.path.exists(test_img):
        res = process_medical_document(test_img)
        
        print("\n=======================================================")
        print("[DATABASE QUERY] VERIFYING STORED RECORDS FROM SQLITE")
        print("=======================================================")
        records = query_patient_records("P-BATCH-0011")
        for r in records:
            doc_id, ocr_conf, review, e_type, e_name, e_details, e_conf, warning = r
            warn_str = f" | {warning}" if warning else ""
            print(f"Doc: {doc_id} | Type: {e_type:10s} | Entity: {e_name:25s} | Conf: {int(e_conf*100)}%{warn_str}")
