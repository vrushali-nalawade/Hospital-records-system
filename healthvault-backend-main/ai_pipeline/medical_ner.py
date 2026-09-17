"""
Health Record Locker - P2: Medical NER & Report Extractor
Step 2 of the P2 pipeline: raw OCR text -> structured medical fields with confidence.

Extracts:
1. Medications (Name, Dosage, Frequency)
2. Diagnoses & Clinical Conditions
3. Lab Reports & Diagnostics (HbA1c, Blood Sugar, CBC, Lipid, Thyroid, BP, Imaging, etc.)
4. Prescribed Date
"""

import re

# Comprehensive known medications list
KNOWN_MEDICATIONS = [
    "amlodipine", "metformin", "atorvastatin", "levothyroxine", "paracetamol",
    "ibuprofen", "azithromycin", "omeprazole", "cetirizine", "naproxen",
    "salbutamol", "ferrous sulfate", "oseltamivir", "sumatriptan", "amoxicillin",
    "ciprofloxacin", "doxycycline", "pantoprazole", "losartan", "telmisartan",
    "ranitidine", "aspirin", "clopidogrel", "rosuvastatin", "glimepiride",
    "hydrochlorothiazide", "furosemide", "prednisolone", "montelukast"
]

# Lab test reports and diagnostic indicators
KNOWN_LAB_TESTS = {
    "hba1c": "HbA1c (Glycated Hemoglobin)",
    "fbs": "Fasting Blood Sugar (FBS)",
    "ppbs": "Postprandial Blood Sugar (PPBS)",
    "glucose": "Blood Glucose",
    "blood sugar": "Blood Sugar",
    "ldl": "LDL Cholesterol",
    "hdl": "HDL Cholesterol",
    "cholesterol": "Total Cholesterol",
    "tsh": "TSH (Thyroid Stimulating Hormone)",
    "thyroid": "Thyroid Profile",
    "hb": "Hemoglobin (Hb)",
    "hemoglobin": "Hemoglobin",
    "bp": "Blood Pressure (BP)",
    "cbc": "Complete Blood Count (CBC)",
    "creatinine": "Serum Creatinine",
    "lft": "Liver Function Test (LFT)",
    "kft": "Kidney Function Test (KFT)",
    "ecg": "Electrocardiogram (ECG)",
    "x-ray": "Chest X-Ray / Radiograph",
    "xray": "Chest X-Ray",
    "ultrasound": "Ultrasound Scan",
    "usg": "Ultrasonography (USG)",
    "ct scan": "CT Scan",
    "mri": "MRI Scan",
    "platelet": "Platelet Count",
    "esr": "Erythrocyte Sedimentation Rate (ESR)",
    "crp": "C-Reactive Protein (CRP)",
    "urine": "Urine Routine & Microscopy"
}

# Known diagnoses / conditions
KNOWN_DIAGNOSES = [
    "hypertension", "diabetes", "type 2 diabetes", "fever", "gastritis",
    "asthma", "bronchitis", "pneumonia", "hypothyroidism", "hyperthyroidism",
    "hyperlipidemia", "anemia", "migraine", "urinary tract infection", "uti",
    "upper respiratory tract infection", "urti", "coronary artery disease", "cad"
]


def extract_medications(text, min_word_conf=100.0):
    results = []
    found_spans = set()
    text_lower = text.lower()

    # Tier 1: Known medications list
    for med in KNOWN_MEDICATIONS:
        pattern = rf"({med})\s*(\d+\s?(?:mg|mcg|ml|g|iu|tablets?|capsules?))?\s*([\w\s]{{1,35}}?(?:once|twice|thrice|\d+\s?times?|daily|a day|bd|tds|od|hs|qds|every\s+\d+\s+hours?))?"
        match = re.search(pattern, text_lower)
        if match:
            name = match.group(1)
            dosage = match.group(2)
            frequency = match.group(3)

            conf = 0.95 if (dosage and frequency) else (0.85 if dosage else 0.75)
            needs_review = min_word_conf < 60.0 or conf < 0.80

            results.append({
                "medication": name.title(),
                "dosage": dosage.strip() if dosage else "Standard dosage",
                "frequency": frequency.strip() if frequency else "As prescribed",
                "confidence": conf,
                "needs_review": needs_review,
                "warning": "Low OCR confidence on prescription line" if min_word_conf < 60.0 else ""
            })
            found_spans.add(match.span())

    # Tier 2: Generic pattern detection e.g. "1. Amoxicillin 500mg - 1 capsule three times daily"
    rx_patterns = [
        re.compile(r"(?:\d+\.\s*)?([A-Z][A-Za-z\-]{2,25})\s+(\d+\s?(?:mg|mcg|ml|g))\s*(?:[\-\:]\s*)?([^\n\r]+)?", re.IGNORECASE),
        re.compile(r"(?:Tab\.?|Cap\.?|Syp\.?|Inj\.?)\s+([A-Z][A-Za-z\-]{2,25})\s*(\d+\s?(?:mg|mcg|ml|g))?", re.IGNORECASE)
    ]

    for pat in rx_patterns:
        for match in pat.finditer(text):
            span = match.span()
            if any(abs(span[0] - s[0]) < 10 for s in found_spans):
                continue
            name = match.group(1).strip()
            if not name or name.lower() in [m["medication"].lower() for m in results]:
                continue
            if name.lower() in ["doctor", "patient", "name", "date", "diagnosis", "prescription", "rx", "hospital", "clinic", "tab", "cap", "syp", "inj"]:
                continue

            dosage = match.group(2) if len(match.groups()) >= 2 else None
            frequency = match.group(3) if len(match.groups()) >= 3 else None

            conf = 0.80 if dosage else 0.65
            needs_review = min_word_conf < 60.0 or conf < 0.75

            results.append({
                "medication": name.capitalize(),
                "dosage": dosage.strip() if dosage else "As indicated",
                "frequency": frequency.strip() if frequency else "As directed",
                "confidence": conf,
                "needs_review": needs_review,
                "warning": "Generic medication match — check prescription scan" if needs_review else ""
            })
            found_spans.add(span)

    return results


def extract_diagnoses(text):
    results = []
    
    # 1. Direct label pattern e.g. "Diagnosis: Hypertension" or "Impression: Type 2 Diabetes"
    label_match = re.search(r"(?:diagnosis|impression|condition|dx)[:\-]?\s*([A-Za-z0-9\s,\-/]{3,60})", text, re.IGNORECASE)
    if label_match:
        diag_str = label_match.group(1).strip()
        diag_str = re.split(r"\n|\r|Rx|Notes|Lab|Treatment|Date", diag_str)[0].strip().rstrip(".")
        if diag_str:
            results.append({
                "diagnosis": diag_str.title(),
                "confidence": 0.90,
                "needs_review": False,
                "warning": ""
            })

    # 2. Known diagnoses list search
    text_lower = text.lower()
    for d in KNOWN_DIAGNOSES:
        if d in text_lower:
            if not any(d in r["diagnosis"].lower() for r in results):
                results.append({
                    "diagnosis": d.title(),
                    "confidence": 0.85,
                    "needs_review": False,
                    "warning": ""
                })

    return results


def extract_lab_reports(text):
    results = []
    text_lower = text.lower()

    for key, display_name in KNOWN_LAB_TESTS.items():
        pattern = rf"({key})\s*[:=]?\s*(\d+(?:\.\d+)?\s*(?:%|mg/dl|g/dl|mmol/l|mmhg|/mm3|iu/l)?|[a-zA-Z0-9\s\+\-\.]+)"
        match = re.search(pattern, text_lower)
        if match:
            test_key = match.group(1).strip()
            raw_val = match.group(2).strip()
            # Trim captured text to line end
            val_clean = re.split(r"\n|\r|Rx|Diagnosis|Notes", raw_val)[0].strip()
            if len(val_clean) > 35:
                val_clean = val_clean[:35]

            results.append({
                "lab_test": display_name,
                "value": val_clean if val_clean else "Report attached / Advised",
                "confidence": 0.88 if val_clean else 0.70,
                "needs_review": False,
                "warning": ""
            })

    return results


def extract_prescribed_date(text):
    patterns = [
        r"\b(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})\b",
        r"\b(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})\b",
        r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b"
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return "10-08-2026"


def extract_medical_entities(text, word_confidences=None):
    """
    Main entry point for Medical NLP pipeline.
    Parses OCR text into structured Medications, Diagnoses, Lab Reports & Date.
    """
    avg_word_conf = 100.0
    if word_confidences and isinstance(word_confidences, list):
        scores = [c for w, c in word_confidences if isinstance(c, (int, float))]
        if scores:
            avg_word_conf = sum(scores) / len(scores)

    medications = extract_medications(text, min_word_conf=avg_word_conf)
    diagnoses = extract_diagnoses(text)
    lab_results = extract_lab_reports(text)
    prescribed_date = extract_prescribed_date(text)

    needs_review = (
        avg_word_conf < 65.0
        or any(m["needs_review"] for m in medications)
        or (len(medications) == 0 and len(diagnoses) == 0 and len(lab_results) == 0)
    )

    primary_diag = diagnoses[0]["diagnosis"] if diagnoses else None

    return {
        "medications": medications,
        "diagnoses": diagnoses,
        "lab_results": lab_results,
        "prescribed_date": prescribed_date,
        "needs_review": needs_review,
        # Legacy/Backward compatibility fields:
        "date": prescribed_date,
        "diagnosis": primary_diag,
        "diagnosis_confidence": "high" if primary_diag else "low",
        "lab_values": lab_results,
    }


if __name__ == "__main__":
    sample_text = """
    City Hospital Prescription
    Doctor Name: Dr. Arthur Vance
    Prescribed Date: 12/08/2026

    Diagnosis: Hypertension and Diabetes

    Rx:
    1. Amoxicillin 500mg - 1 capsule three times daily for 7 days
    2. Metformin 500mg once daily

    Lab Test Reports:
    HbA1c: 7.2%
    Fasting Blood Sugar: 130 mg/dl
    Chest X-Ray: Clear
    """

    res = extract_medical_entities(sample_text)
    import json
    print(json.dumps(res, indent=2))