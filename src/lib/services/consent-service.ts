"use client";

import { MOCK_CONSENTS, MOCK_ACCESS_LOGS } from "@/lib/mock/mock-data";
import type { AccessLog, Consent, ConsentStatus, RecordType } from "@/types";

const CONSENT_KEY = "hrl_demo_consents";
const LOG_KEY = "hrl_demo_access_logs";

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

export function getConsentsForPatient(patientId: string): Consent[] {
  return readConsents().filter((c) => c.patientId === patientId);
}

export function getConsentsForDoctor(doctorId: string): Consent[] {
  return readConsents().filter((c) => c.doctorId === doctorId);
}

export function updateConsentStatus(
  consentId: string,
  status: ConsentStatus
): Consent[] {
  const all = readConsents().map((c) =>
    c.consentId === consentId ? { ...c, status } : c
  );
  writeConsents(all);
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
  return readAccessLogs()
    .filter((l) => l.patientId === patientId)
    .sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1));
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
