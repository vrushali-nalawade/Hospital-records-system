"use client";

import { IS_DEMO_MODE } from "@/lib/demo-mode";
import { MOCK_RECORDS } from "@/lib/mock/mock-data";
import { auth } from "@/lib/firebase/config";
import { API_BASE_URL } from "@/lib/api-config";
import type { MedicalRecord, ProcessingStatus, RecordType, ExtractedField } from "@/types";

const STORE_KEY = "hrl_demo_records";
const API_URL = API_BASE_URL;

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

async function getAuthHeaders() {
  if (auth) {
    if (!auth.currentUser && typeof (auth as any).authStateReady === "function") {
      try {
        await (auth as any).authStateReady();
      } catch (e) {
        console.error("Error waiting for auth state ready:", e);
      }
    }
    if (auth.currentUser) {
      const token = await auth.currentUser.getIdToken();
      return {
        "Authorization": `Bearer ${token}`
      };
    }
  }
  let token = "mock_token_P001UID_PATIENT";
  if (typeof window !== "undefined") {
    const raw = localStorage.getItem("hrl_demo_session");
    if (raw) {
      try {
        const session = JSON.parse(raw);
        const role = (session.role || "patient").toUpperCase();
        const uid = session.uid || (role === "PATIENT" ? "P001UID" : "D001UID");
        const email = session.email || (role === "PATIENT" ? "patient@demo.health" : "doctor@demo.health");
        token = `mock_token_${uid}_${role}_${email}`;
      } catch (e) {
        console.error(e);
      }
    }
  }
  return {
    "Authorization": `Bearer ${token}`
  };
}

function mapBackendDocType(type: string): RecordType {
  const t = type.toLowerCase();
  if (t.includes("prescription")) return "prescription";
  if (t.includes("blood")) return "blood_report";
  if (t.includes("lab")) return "lab_report";
  if (t.includes("image") || t.includes("xray") || t.includes("x-ray")) return "medical_image";
  if (t.includes("note")) return "doctor_note";
  if (t.includes("discharge")) return "discharge_summary";
  return "prescription"; 
}

function mapBackendStatus(status: string): ProcessingStatus {
  const s = status.toUpperCase();
  if (s === "PROCESSING" || s === "INDEXING" || s === "UPLOADED" || s === "PENDING") return "processing";
  if (s === "READY" || s === "PROCESSED") return "ready";
  if (s === "FAILED") return "failed";
  return "ready";
}

function mapDocumentToMedicalRecord(doc: any): MedicalRecord {
  return {
    recordId: doc.document_id,
    patientId: doc.patient_id,
    uploadedBy: doc.patient_id,
    recordType: mapBackendDocType(doc.document_type),
    fileName: doc.storage_path.split(/[\\/]/).pop() || `${doc.document_id}.pdf`,
    fileUrl: `${API_URL}/documents/${doc.document_id}`,
    fileSizeKb: 250, 
    mimeType: doc.storage_path.endsWith(".pdf") ? "application/pdf" : "image/jpeg",
    processingStatus: mapBackendStatus(doc.status),
    extractedInformation: [
      { label: "Confidence", value: `${(doc.confidence * 100).toFixed(0)}%` },
      { label: "Needs Review", value: doc.needs_review ? "Yes" : "No" },
      { label: "Storage Path", value: doc.storage_path }
    ],
    isMockExtraction: false,
    createdAt: doc.created_at || new Date().toISOString(),
    updatedAt: doc.processed_at || doc.created_at || new Date().toISOString()
  };
}

export async function fetchRecordsForPatient(patientId: string): Promise<MedicalRecord[]> {
  if (IS_DEMO_MODE) {
    return getRecordsForPatient(patientId);
  }
  
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/documents?patient_id=${patientId}`, {
      headers
    });
    
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data)) {
        return data.map(mapDocumentToMedicalRecord);
      }
    }
  } catch (e) {
    console.error("Failed to fetch documents from FastAPI backend, falling back to local records", e);
  }
  
  return getRecordsForPatient(patientId);
}

export function getRecordsForPatient(patientId: string): MedicalRecord[] {
  return readStore()
    .filter((r) => r.patientId === patientId)
    .sort((a, b) => (a.createdAt < b.createdAt ? 1 : -1));
}

export const fetchPatientRecords = fetchRecordsForPatient;
export const getPatientRecords = getRecordsForPatient;

export async function fetchRecordById(recordId: string): Promise<MedicalRecord | undefined> {
  if (IS_DEMO_MODE) {
    return getRecordById(recordId);
  }
  
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/documents`, { headers });
    if (res.ok) {
      const data = await res.json();
      const match = data.find((d: any) => d.document_id === recordId);
      if (match) return mapDocumentToMedicalRecord(match);
    }
  } catch (e) {
    console.error("Failed to fetch record by id", e);
  }
  return getRecordById(recordId);
}

export function getRecordById(recordId: string): MedicalRecord | undefined {
  return readStore().find((r) => r.recordId === recordId);
}

const DEMO_EXTRACTIONS: Record<RecordType, { label: string; value: string }[]> = {
  blood_report: [
    { label: "Report Date", value: new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" }) },
    { label: "Hemoglobin", value: "13.5 g/dL" },
    { label: "WBC", value: "6,900 /uL" },
    { label: "Platelets", value: "245,000 /uL" },
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

export async function uploadRecordDemo(
  patientId: string,
  file: { name: string; size: number; type: string } | File,
  recordType: RecordType,
  onStatus: (status: ProcessingStatus) => void
): Promise<MedicalRecord> {
  // If in real mode, upload to the actual FastAPI backend
  if (!IS_DEMO_MODE && file instanceof File) {
    onStatus("uploading");
    
    try {
      const headers = await getAuthHeaders();
      const formData = new FormData();
      formData.append("file", file);
      formData.append("patient_id", patientId);
      
      let uploadRes: Response;
      try {
        uploadRes = await fetch(`${API_URL}/documents/upload`, {
          method: "POST",
          headers: {
            "Authorization": headers["Authorization"]
          },
          body: formData
        });
      } catch (fetchErr: any) {
        throw new Error(
          `Connection to server failed (${API_URL}). Please verify network connection or origin configuration.`
        );
      }
      
      if (!uploadRes.ok) {
        const errData = await uploadRes.json().catch(() => ({}));
        throw new Error(errData.detail || `File upload failed (HTTP ${uploadRes.status})`);
      }
      
      const uploadData = await uploadRes.json();
      const docId = uploadData.document_id;
      
      // Poll document status until it is ready or failed
      onStatus("processing");
      let status: ProcessingStatus = "processing";
      let pollCount = 0;
      const maxPolls = 120; // 120s timeout to allow real EasyOCR + BGE-M3 model on CPU
      let docReady = false;
      let showedOcr = false;
      
      while (pollCount < maxPolls) {
        await new Promise((res) => setTimeout(res, 1000));
        pollCount++;
        
        try {
          const statusRes = await fetch(`${API_URL}/documents/${docId}/status`, {
            headers: {
              "Authorization": headers["Authorization"]
            }
          });
          
          if (statusRes.ok) {
            const statusData = await statusRes.json();
            const apiStatus = (statusData.status || "").toUpperCase();
            const jobStatus = (statusData.job_status || "").toUpperCase();
            
            if (apiStatus === "INDEXING" || jobStatus === "INDEXING") {
              if (!showedOcr) {
                onStatus("ocr_completed");
                showedOcr = true;
              }
            } else if (apiStatus === "READY" || apiStatus === "PROCESSED" || jobStatus === "COMPLETED") {
              status = "ready";
              docReady = true;
              onStatus("ocr_completed");
              await new Promise((res) => setTimeout(res, 400));
              onStatus("extracted");
              await new Promise((res) => setTimeout(res, 400));
              onStatus("ready");
              break;
            } else if (apiStatus === "FAILED" || jobStatus === "FAILED") {
              status = "failed";
              onStatus("failed");
              throw new Error(statusData.error_message || "Document ingestion failed");
            }
          }
        } catch (pollErr: any) {
          if (pollErr?.message && (pollErr.message.includes("failed") || pollErr.message.includes("Failed"))) {
            throw pollErr;
          }
        }
      }
      
      if (!docReady && status !== "ready") {
        const finalStatusRes = await fetch(`${API_URL}/documents/${docId}/status`, {
          headers: { "Authorization": headers["Authorization"] }
        }).catch(() => null);
        if (finalStatusRes?.ok) {
          const finalData = await finalStatusRes.json();
          const finalStatus = (finalData.status || "").toUpperCase();
          if (finalStatus === "READY" || finalStatus === "PROCESSED") {
            status = "ready";
            onStatus("ocr_completed");
            await new Promise((res) => setTimeout(res, 300));
            onStatus("extracted");
            await new Promise((res) => setTimeout(res, 300));
            onStatus("ready");
          } else {
            throw new Error("Document processing timeout. Document is still processing in the background.");
          }
        } else {
          throw new Error("Document processing status check failed.");
        }
      }
      
      const recordDetails = await fetchRecordById(docId);
      if (recordDetails) return recordDetails;
      
      return {
        recordId: docId,
        patientId,
        uploadedBy: patientId,
        recordType,
        fileName: file.name,
        fileUrl: `${API_URL}/documents/${docId}`,
        fileSizeKb: Math.round(file.size / 1024),
        mimeType: file.type,
        processingStatus: status,
        extractedInformation: [],
        isMockExtraction: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString()
      };
      
    } catch (e) {
      onStatus("failed");
      console.error(e);
      throw e;
    }
  }

  // Demo Fallback
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

export async function fetchDocumentSignedUrl(documentId: string): Promise<string | null> {
  if (IS_DEMO_MODE) {
    return null;
  }
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/documents/${documentId}/signed-url`, { headers });
    if (res.ok) {
      const data = await res.json();
      return data.signed_url;
    }
  } catch (e) {
    console.error("Failed to fetch signed URL", e);
  }
  return null;
}
