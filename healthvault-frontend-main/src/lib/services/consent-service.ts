"use client";

import { IS_DEMO_MODE } from "@/lib/demo-mode";
import { MOCK_CONSENTS, MOCK_ACCESS_LOGS } from "@/lib/mock/mock-data";
import { auth } from "@/lib/firebase/config";
import { API_BASE_URL } from "@/lib/api-config";
import type { AccessLog, Consent, ConsentStatus, RecordType } from "@/types";

const CONSENT_KEY = "hrl_demo_consents";
const LOG_KEY = "hrl_demo_access_logs";
const API_URL = API_BASE_URL;

function readConsents(): Consent[] {
  if (typeof window === "undefined") return MOCK_CONSENTS;
  const raw = localStorage.getItem(CONSENT_KEY);
  if (!raw) {
    localStorage.setItem(CONSENT_KEY, JSON.stringify(MOCK_CONSENTS));
    return MOCK_CONSENTS;
  }
  return JSON.parse(raw) as Consent[];
}

function writeConsents(items: Consent[]) {
  if (typeof window !== "undefined") {
    localStorage.setItem(CONSENT_KEY, JSON.stringify(items));
  }
}

export function readAccessLogs(): AccessLog[] {
  if (typeof window === "undefined") return MOCK_ACCESS_LOGS;
  const raw = localStorage.getItem(LOG_KEY);
  if (!raw) {
    localStorage.setItem(LOG_KEY, JSON.stringify(MOCK_ACCESS_LOGS));
    return MOCK_ACCESS_LOGS;
  }
  return JSON.parse(raw) as AccessLog[];
}

function writeAccessLogs(items: AccessLog[]) {
  if (typeof window !== "undefined") {
    localStorage.setItem(LOG_KEY, JSON.stringify(items));
  }
}

async function getAuthHeaders() {
  if (auth?.currentUser) {
    const token = await auth.currentUser.getIdToken();
    return {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json"
    };
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
    "Authorization": `Bearer ${token}`,
    "Content-Type": "application/json"
  };
}

function mapBackendConsentToFrontend(c: any): Consent {
  let perms: RecordType[] = ["prescription", "blood_report", "lab_report", "medical_image", "doctor_note", "discharge_summary"];
  if (c.permission === "VIEW_DOCUMENTS") {
    perms = ["prescription", "blood_report", "lab_report", "medical_image"];
  }
  
  return {
    consentId: c.consent_id,
    patientId: c.patient_id,
    doctorId: c.doctor_id,
    doctorName: `Dr. Doctor ${c.doctor_id}`, 
    status: "approved",
    permissions: perms,
    createdAt: c.created_at || new Date().toISOString(),
    expiresAt: c.expires_at || null
  };
}

export async function fetchConsentsForPatient(patientId: string): Promise<Consent[]> {
  if (IS_DEMO_MODE) {
    return getConsentsForPatient(patientId);
  }
  
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/consent`, { headers });
    if (res.ok) {
      const data = await res.json();
      const mapped = data.map(mapBackendConsentToFrontend);
      const localPending = readConsents().filter((c) => c.patientId === patientId && c.status === "pending");
      return [...localPending, ...mapped];
    }
  } catch (e) {
    console.error("Failed to fetch consents from backend", e);
  }
  return getConsentsForPatient(patientId);
}

export function getConsentsForPatient(patientId: string): Consent[] {
  const all = readConsents();
  const direct = all.filter((c) => c.patientId === patientId);
  if (direct.length > 0) return direct;
  
  const initialConsents: Consent[] = [
    {
      consentId: `cons-priya-${patientId.slice(0, 6)}`,
      patientId: patientId,
      doctorId: "doctor-demo-1",
      doctorName: "Dr. Priya Verma (General Physician)",
      status: "approved",
      permissions: ["blood_report", "prescription", "discharge_summary"],
      createdAt: new Date(Date.now() - 7 * 86400000).toISOString(),
      expiresAt: new Date(Date.now() + 180 * 86400000).toISOString(),
    },
    {
      consentId: `cons-rohan-${patientId.slice(0, 6)}`,
      patientId: patientId,
      doctorId: "doctor-demo-2",
      doctorName: "Dr. Rohan Deshmukh (Cardiologist)",
      status: "pending",
      permissions: ["lab_report", "prescription"],
      createdAt: new Date(Date.now() - 1 * 86400000).toISOString(),
      expiresAt: null,
    },
  ];
  writeConsents([...all, ...initialConsents]);
  return initialConsents;
}

export async function fetchConsentsForDoctor(doctorId: string): Promise<Consent[]> {
  if (IS_DEMO_MODE) {
    return getConsentsForDoctor(doctorId);
  }
  
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/consent`, { headers });
    if (res.ok) {
      const data = await res.json();
      const mapped = data.map(mapBackendConsentToFrontend);
      const localPending = readConsents().filter((c) => c.doctorId === doctorId && c.status === "pending");
      return [...localPending, ...mapped];
    }
  } catch (e) {
    console.error("Failed to fetch consents from backend", e);
  }
  return getConsentsForDoctor(doctorId);
}

export function getConsentsForDoctor(doctorId: string): Consent[] {
  return readConsents().filter((c) => c.doctorId === doctorId);
}

async function updateConsentStatusReal(
  consentId: string,
  status: ConsentStatus
): Promise<void> {
  const headers = await getAuthHeaders();
  
  if (status === "approved") {
    const pending = readConsents().find((c) => c.consentId === consentId);
    if (pending) {
      const grantPermissions = ["VIEW_DOCUMENTS", "ASK_AI", "VIEW_RECORDS"];
      for (const p of grantPermissions) {
        await fetch(`${API_URL}/consent`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            doctor_id: pending.doctorId,
            permission: p
          })
        });
      }
    }
  } else if (status === "revoked" || status === "rejected") {
    await fetch(`${API_URL}/consent/${consentId}`, {
      method: "DELETE",
      headers
    });
  }
}

export function updateConsentStatus(
  consentId: string,
  status: ConsentStatus
): Consent[] {
  if (!IS_DEMO_MODE) {
    updateConsentStatusReal(consentId, status).catch((err) => {
      console.error("Failed to sync consent update to backend:", err);
    });
  }

  const all = readConsents().map((c) =>
    c.consentId === consentId ? { ...c, status } : c
  );
  writeConsents(all);

  // Log action in access history
  const target = all.find((c) => c.consentId === consentId);
  if (target) {
    const logs = readAccessLogs();
    logs.push({
      logId: `log-${Date.now()}`,
      patientId: target.patientId,
      doctorId: target.doctorId,
      doctorName: target.doctorName,
      recordId: null,
      recordName: null,
      action: status === "approved" ? "granted_consent" : (status === "revoked" ? "revoked_consent" : "rejected_consent"),
      timestamp: new Date().toISOString(),
      consentStatus: status,
    });
    writeAccessLogs(logs);
  }

  return all;
}

export function requestAccess(
  patientId: string,
  doctorId: string,
  doctorName: string,
  permissions: RecordType[]
): Consent {
  const consent: Consent = {
    consentId: `cons-${Date.now()}`,
    patientId,
    doctorId,
    doctorName,
    status: "pending",
    permissions,
    createdAt: new Date().toISOString(),
    expiresAt: null,
  };
  const all = readConsents();
  all.push(consent);
  writeConsents(all);

  const logs = readAccessLogs();
  logs.push({
    logId: `log-${Date.now()}`,
    patientId,
    doctorId,
    doctorName,
    recordId: null,
    recordName: null,
    action: "requested_access",
    timestamp: new Date().toISOString(),
    consentStatus: "pending",
  });
  writeAccessLogs(logs);

  return consent;
}

export function logAccess(entry: Omit<AccessLog, "logId" | "timestamp">) {
  const logs = readAccessLogs();
  logs.push({
    ...entry,
    logId: `log-${Date.now()}`,
    timestamp: new Date().toISOString(),
  });
  writeAccessLogs(logs);
}

export function getAccessLogsForPatient(patientId: string): AccessLog[] {
  const all = readAccessLogs();
  const direct = all.filter((l) => l.patientId === patientId);
  if (direct.length > 0) return direct.sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));

  const initialLogs: AccessLog[] = [
    {
      logId: `log-1-${patientId.slice(0, 6)}`,
      patientId: patientId,
      doctorId: "doctor-demo-1",
      doctorName: "Dr. Priya Verma",
      recordId: "rec-1",
      recordName: "prescription_cardiology.pdf",
      action: "viewed",
      timestamp: new Date(Date.now() - 2 * 86400000).toISOString(),
      consentStatus: "approved",
    },
    {
      logId: `log-2-${patientId.slice(0, 6)}`,
      patientId: patientId,
      doctorId: "doctor-demo-1",
      doctorName: "Dr. Priya Verma",
      recordId: "rec-2",
      recordName: "blood_report_lipid.pdf",
      action: "viewed",
      timestamp: new Date(Date.now() - 5 * 86400000).toISOString(),
      consentStatus: "approved",
    },
    {
      logId: `log-3-${patientId.slice(0, 6)}`,
      patientId: patientId,
      doctorId: "doctor-demo-2",
      doctorName: "Dr. Rohan Deshmukh",
      recordId: null,
      recordName: null,
      action: "requested_access",
      timestamp: new Date(Date.now() - 1 * 86400000).toISOString(),
      consentStatus: "pending",
    },
  ];
  writeAccessLogs([...all, ...initialLogs]);
  return initialLogs;
}

export async function fetchAccessLogsForPatient(patientId: string): Promise<AccessLog[]> {
  if (IS_DEMO_MODE) {
    return getAccessLogsForPatient(patientId);
  }
  try {
    const headers = await getAuthHeaders();
    const res = await fetch(`${API_URL}/audit/me`, { headers });
    if (res.ok) {
      const data = await res.json();
      return data.map((l: any) => ({
        logId: String(l.log_id),
        patientId: l.patient_id || patientId,
        doctorId: l.actor_id,
        doctorName: l.actor_id.includes("DOCTOR") || l.actor_id.includes("D00") ? `Dr. Doctor ${l.actor_id.replace("UID", "")}` : "Patient / System",
        recordId: null,
        recordName: null,
        action: l.action.toLowerCase(),
        timestamp: l.timestamp,
        consentStatus: l.status.toLowerCase() === "allowed" ? "approved" : "rejected"
      }));
    }
  } catch (e) {
    console.error("Failed to fetch access logs from backend", e);
  }
  return getAccessLogsForPatient(patientId);
}

export function hasApprovedConsent(
  patientId: string,
  doctorId: string,
  recordType: RecordType
): boolean {
  const consent = readConsents().find(
    (c) =>
      c.patientId === patientId &&
      c.doctorId === doctorId &&
      c.status === "approved"
  );
  if (!consent) return false;
  if (consent.expiresAt && new Date(consent.expiresAt) < new Date()) return false;
  return consent.permissions.includes(recordType);
}

