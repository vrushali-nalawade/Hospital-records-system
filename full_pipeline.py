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
    print("=======================================================")
    print("[CLI] Patient Record Lookup & Processing Engine")
    print("=======================================================")
    
    # Prompt for Patient ID
    input_pid = input("Enter Patient ID to lookup (e.g. P-BATCH-0011): ").strip()
    
    if input_pid:
        # Import the helper query functions
        from db_helpers import get_patient_documents, get_entities_for_record
        docs = get_patient_documents(input_pid)
        
        if docs:
            print(f"\n[FOUND] Found {len(docs)} document(s) on file for Patient '{input_pid}':")
            for d in docs:
                doc_id = f"DOC-{d['record_id']:04d}"
                print(f"\n--- Document ID: {doc_id} ---")
                print(f"  Visit Date         : {d['visit_date']}")
                print(f"  Doctor             : {d['doctor_name']}")
                print(f"  Hospital           : {d['hospital_name'] or 'City General'}")
                print(f"  OCR Confidence     : {d['ocr_confidence']}%")
                print(f"  Image Scan Path    : {d['file_path']}")
                print(f"  Review Status      : {'Needs Verification' if d['needs_review'] else 'Verified'}")
                
                # Fetch details
                entities = get_entities_for_record(d['record_id'])
                meds = [e for e in entities if e['entity_type'] == 'Medication']
                diags = [e for e in entities if e['entity_type'] == 'Diagnosis']
                labs = [e for e in entities if e['entity_type'] == 'Lab Report']
                
                if meds:
                    print("  Medications Extracted:")
                    for m in meds:
                        warn = f" ({m['warning']})" if m['warning'] else ""
                        print(f"    • {m['medication']} {m['dosage'] or ''} - Conf: {int(m['confidence']*100)}%{warn}")
                if diags:
                    print("  Diagnoses Extracted:")
                    for g in diags:
                        print(f"    • {g['diagnosis']} - Conf: {int(g['confidence']*100)}%")
                if labs:
                    print("  Lab Reports Extracted:")
                    for l in labs:
                        print(f"    • {l['entity_name']}: {l['lab_values'] or '-'} - Conf: {int(l['confidence']*100)}%")
        else:
            print(f"\n[NOT FOUND] No records found in SQLite for Patient ID: '{input_pid}'.")
            choice = input(f"Would you like to run the OCR pipeline on a new prescription image for '{input_pid}'? (y/n): ").strip().lower()
            if choice == 'y':
                img_path = input("Enter prescription image file path (e.g. dataset/10.jpg): ").strip()
                if os.path.exists(img_path):
                    visit_val = input("Enter Visit ID (default: VIS-1001): ").strip() or "VIS-1001"
                    doc_val = input("Enter Doctor Name (default: Dr. Arthur Vance): ").strip() or "Dr. Arthur Vance"
                    res = process_medical_document(img_path, patient_id=input_pid, visit_id=visit_val, doctor_name=doc_val)
                else:
                    print(f"Error: File not found: '{img_path}'")
    else:
        # Run test image default if they just hit Enter
        test_img = "test_prescription.png" if os.path.exists("test_prescription.png") else "dataset/98.jpg"
        if os.path.exists(test_img):
            print(f"\nNo Patient ID entered. Running default test run on image '{test_img}'...")
            res = process_medical_document(test_img)
