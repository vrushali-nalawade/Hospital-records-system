"use client";

import { IS_DEMO_MODE } from "@/lib/demo-mode";
import { MOCK_RECORDS } from "@/lib/mock/mock-data";
import type { MedicalRecord, ProcessingStatus, RecordType } from "@/types";

const STORE_KEY = "hrl_demo_records";

function readStore(): MedicalRecord[] {
  if (typeof window === "undefined") return MOCK_RECORDS;
  const raw = localStorage.getItem(STORE_KEY);
  if (!raw) {
    localStorage.setItem(STORE_KEY, JSON.stringify(MOCK_RECORDS));
    return MOCK_RECORDS;
  }
  return JSON.parse(raw) as MedicalRecord[];
}

function writeStore(records: MedicalRecord[]) {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORE_KEY, JSON.stringify(records));
  }
}

export function getRecordsForPatient(patientId: string): MedicalRecord[] {
  return readStore()
    .filter((r) => r.patientId === patientId)
    .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
}

export function getRecordById(recordId: string): MedicalRecord | undefined {
  return readStore().find((r) => r.recordId === recordId);
}

const DEMO_EXTRACTIONS: Record<RecordType, { label: string; value: string }[]> = {
  blood_report: [
    { label: "Report Date", value: new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" }) },
    { label: "Hemoglobin", value: "13.5 g/dL" },
    { label: "WBC", value: "6,900 /µL" },
    { label: "Platelets", value: "245,000 /µL" },
  ],
  prescription: [
    { label: "Prescribed By", value: "Dr. Priya Verma" },
    { label: "Medication", value: "Paracetamol 500mg" },
    { label: "Duration", value: "3 days" },
  ],
  lab_report: [
    { label: "Report Date", value: "Today" },
    { label: "Test Panel", value: "Lipid Profile" },
    { label: "Total Cholesterol", value: "178 mg/dL" },
  ],
  medical_image: [
    { label: "Modality", value: "X-Ray" },
    { label: "Region", value: "Chest" },
  ],
  doctor_note: [
    { label: "Doctor", value: "Dr. Priya Verma" },
    { label: "Note Summary", value: "Routine follow-up, no concerns noted." },
  ],
  discharge_summary: [
    { label: "Admission Date", value: "N/A (demo)" },
    { label: "Diagnosis (as recorded)", value: "Observation only" },
  ],
};

// Simulates: uploading -> processing -> ocr_completed -> extracted -> ready
export async function uploadRecordDemo(
  patientId: string,
  file: { name: string; size: number; type: string },
  recordType: RecordType,
  onStatus: (status: ProcessingStatus) => void
): Promise<MedicalRecord> {
  const stages: ProcessingStatus[] = [
    "uploading",
    "processing",
    "ocr_completed",
    "extracted",
    "ready",
  ];
  for (const stage of stages) {
    onStatus(stage);
    await new Promise((res) => setTimeout(res, 650));
  }

  const record: MedicalRecord = {
    recordId: `rec-${Date.now()}`,
    patientId,
    uploadedBy: patientId,
    recordType,
    fileName: file.name,
    fileUrl: `/demo-files/${file.name}`,
    fileSizeKb: Math.round(file.size / 1024),
    mimeType: file.type,
    processingStatus: "ready",
    isMockExtraction: true,
    extractedInformation: DEMO_EXTRACTIONS[recordType] ?? [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  const all = readStore();
  all.push(record);
  writeStore(all);
  return record;
}

export const isDemoRecordsMode = IS_DEMO_MODE;
