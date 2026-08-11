"""
Health Record Locker - P2: Batch Dataset Processor & Report Extractor
Scans a folder of prescription images, runs OpenCV+EasyOCR and Medical NER,
saves structured data into SQLite database, and generates a CSV summary report.

Usage:
    python batch_processor.py dataset
"""

import os
import glob
import sys
import pandas as pd

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from ocr_pipeline import run_ocr
from medical_ner import extract_medical_entities
from db_helpers import init_db, save_pipeline_result


def process_dataset_folder(folder_path="dataset", output_csv="batch_extraction_report.csv"):
    init_db()

    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        print(f"[NOTICE] Created folder '{folder_path}'. Put your prescription images in it and re-run.")
        return

    extensions = ["*.png", "*.jpg", "*.jpeg", "*.tif", "*.tiff"]
    image_files = []
    for ext in extensions:
        image_files.extend(glob.glob(os.path.join(folder_path, ext)))
        image_files.extend(glob.glob(os.path.join(folder_path, ext.upper())))
    image_files = sorted(set(image_files))

    if not image_files:
        print(f"[NOTICE] No image files found in '{folder_path}'.")
        return

    print(f"==========================================================")
    print(f"PROCESSING {len(image_files)} PRESCRIPTION IMAGES FROM '{folder_path}'")
    print(f"==========================================================\n")

    records = []
    meds_total = 0
    diags_total = 0
    labs_total = 0

    for idx, img_path in enumerate(image_files, 1):
        filename = os.path.basename(img_path)
        patient_id = f"P-BATCH-{idx:04d}"
        visit_id = f"VIS-{1000+idx}"

        try:
            # 1. OCR Engine
            ocr_res = run_ocr(img_path)
            raw_text = ocr_res["full_text"]
            ocr_conf = ocr_res["avg_confidence"]

            # 2. Medical NER & Lab Report Extractor
            ner_res = extract_medical_entities(raw_text, ocr_res.get("word_confidences"))

            # 3. Save into SQLite Database
            doc_id, needs_review = save_pipeline_result(
                patient_id=patient_id,
                visit_id=visit_id,
                doctor_name="Dr. Batch Ingestion, M.D.",
                ocr_result=ocr_res,
                ner_result=ner_res
            )

            meds_count = len(ner_res["medications"])
            diags_count = len(ner_res["diagnoses"])
            labs_count = len(ner_res["lab_results"])

            meds_total += meds_count
            diags_total += diags_count
            labs_total += labs_count

            med_names = ", ".join([m["medication"] for m in ner_res["medications"]]) if meds_count > 0 else "None detected"
            diag_names = ", ".join([d["diagnosis"] for d in ner_res["diagnoses"]]) if diags_count > 0 else "None detected"
            lab_names = ", ".join([l["lab_test"] for l in ner_res["lab_results"]]) if labs_count > 0 else "None detected"

            records.append({
                "Filename": filename,
                "Document_ID": doc_id,
                "Patient_ID": patient_id,
                "OCR_Confidence": f"{ocr_conf}%",
                "Prescribed_Date": ner_res.get("prescribed_date", "-"),
                "Medications_Extracted": meds_count,
                "Medication_List": med_names,
                "Diagnoses_Extracted": diags_count,
                "Diagnosis_List": diag_names,
                "Lab_Reports_Extracted": labs_count,
                "Lab_Report_List": lab_names,
                "Needs_Human_Review": "YES" if needs_review else "NO"
            })

            print(f"[{idx}/{len(image_files)}] {filename} -> Doc ID: {doc_id} | Conf: {ocr_conf}% | Meds: {meds_count} | Diag: {diags_count} | Lab Reports: {labs_count} | Review: {'YES' if needs_review else 'NO'}", flush=True)

        except Exception as e:
            print(f"[{idx}/{len(image_files)}] {filename} -> ERROR: {e}")
            records.append({
                "Filename": filename,
                "Document_ID": f"ERR-{idx}",
                "Patient_ID": patient_id,
                "OCR_Confidence": "0%",
                "Prescribed_Date": "-",
                "Medications_Extracted": 0,
                "Medication_List": "-",
                "Diagnoses_Extracted": 0,
                "Diagnosis_List": "-",
                "Lab_Reports_Extracted": 0,
                "Lab_Report_List": f"Error: {e}",
                "Needs_Human_Review": "YES"
            })

    if records:
        df = pd.DataFrame(records)
        df.to_csv(output_csv, index=False)
        print("\n==========================================================")
        print(f"BATCH PROCESSING COMPLETE!")
        print(f"Total Prescriptions Processed : {len(image_files)}")
        print(f"Total Medications Found       : {meds_total}")
        print(f"Total Diagnoses Found         : {diags_total}")
        print(f"Total Lab Reports Identified  : {labs_total}")
        print(f"CSV Report Saved To           : {os.path.abspath(output_csv)}")
        print("==========================================================")


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "dataset"
    process_dataset_folder(folder)