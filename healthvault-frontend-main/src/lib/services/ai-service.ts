"use client";

import type { MedicalRecord } from "@/types";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import { auth } from "@/lib/firebase/config";
import { IS_DEMO_MODE } from "@/lib/demo-mode";
import { API_BASE_URL } from "@/lib/api-config";

const API_URL = API_BASE_URL;

const FORBIDDEN_TOPICS = [
  "diagnose",
  "diagnosis",
  "prescribe",
  "what disease do i have",
  "should i take",
  "treatment plan",
];

export function isAIConfigured(): boolean {
  // If we are not in demo mode, it means backend AI is available
  return !IS_DEMO_MODE;
}

function safetyRedirect(): string {
  return (
    "I can help you understand the information already in your uploaded " +
    "records, but I can't diagnose conditions, recommend treatment, or " +
    "prescribe medication. Please discuss diagnosis or treatment decisions " +
    "with your doctor."
  );
}

function summarizeRecord(record: MedicalRecord): string {
  const fields = record.extractedInformation
    .map((f) => `- ${f.label}: ${f.value}`)
    .join("\n");
  return `**${recordTypeLabel[record.recordType]}** (${new Date(
    record.createdAt
  ).toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" })})\n${fields}`;
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

export async function askAIAboutRecords(
  question: string,
  records: MedicalRecord[],
  selectedDocumentId?: string
): Promise<{ answer: string; sourceRecordIds: string[] }> {
  // Real API RAG query flow
  if (!IS_DEMO_MODE) {
    try {
      const headers = await getAuthHeaders();
      let patientId = records[0]?.patientId || "P001";
      if (typeof window !== "undefined") {
        const raw = localStorage.getItem("hrl_demo_session");
        if (raw) {
          try {
            const session = JSON.parse(raw);
            if (session.patientId) patientId = session.patientId;
            else if (session.uid && session.uid.startsWith("P")) patientId = session.uid;
          } catch (e) {
            console.error(e);
          }
        }
      }
      
      const payload: Record<string, any> = {
        patient_id: patientId,
        question: question
      };
      if (selectedDocumentId) {
        payload.document_id = selectedDocumentId;
      }
      
      const res = await fetch(`${API_URL}/ai/query`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload)
      });
      
      if (res.ok) {
        const data = await res.json();
        return {
          answer: data.answer,
          sourceRecordIds: (data.sources || []).map((s: any) => s.document_id)
        };
      } else {
        const errJson = await res.json().catch(() => ({}));
        if (errJson.detail) {
          return {
            answer: `Server notice: ${errJson.detail}`,
            sourceRecordIds: []
          };
        }
      }
    } catch (e) {
      console.error("Failed to fetch answer from backend RAG service:", e);
    }
  }

  // ---- DEMO AI (mock) fallback logic below ----
  await new Promise((res) => setTimeout(res, 600));

  if (selectedDocumentId) {
    const targetDoc = records.find((r) => r.recordId === selectedDocumentId);
    if (targetDoc) {
      return {
        answer: `### Analysis for Document \`${targetDoc.recordId}\` (${recordTypeLabel[targetDoc.recordType]}):\n\n${summarizeRecord(targetDoc)}\n\n_Extracted directly from selected medical record._`,
        sourceRecordIds: [targetDoc.recordId]
      };
    }
  }

  const sorted = [...records].sort((a, b) =>
    a.createdAt < b.createdAt ? 1 : -1
  );
  const lower = question.toLowerCase();

  if (lower.includes("blood report") || lower.includes("blood") || lower.includes("hba1c") || lower.includes("glucose")) {
    const rec = sorted.find((r) => r.recordType === "blood_report" || r.recordType === "lab_report");
    if (rec) {
      return {
        answer: `Here's what's in your latest lab/blood report:\n\n${summarizeRecord(
          rec
        )}\n\n_This is a summary of the values already present in your uploaded document, for your understanding only._`,
        sourceRecordIds: [rec.recordId],
      };
    }
  }

  if (lower.includes("prescription") || lower.includes("medication") || lower.includes("cardiology") || lower.includes("medicine")) {
    const rec = sorted.find((r) => r.recordType === "prescription");
    if (rec) {
      return {
        answer: `Here's a summary of your most recent prescription:\n\n${summarizeRecord(
          rec
        )}`,
        sourceRecordIds: [rec.recordId],
      };
    }
  }

  if (lower.includes("discharge")) {
    const rec = sorted.find((r) => r.recordType === "discharge_summary");
    if (rec) {
      return {
        answer: `Here's a summary of your discharge details:\n\n${summarizeRecord(
          rec
        )}`,
        sourceRecordIds: [rec.recordId],
      };
    }
  }

  if (sorted.length > 0) {
    const summaries = sorted.slice(0, 3).map((r) => summarizeRecord(r)).join("\n\n---\n\n");
    return {
      answer: `Here is a summary of your recent health records:\n\n${summaries}`,
      sourceRecordIds: sorted.slice(0, 3).map((r) => r.recordId),
    };
  }

  return {
    answer: "I couldn't find any documents in your vault matching that query. Please try asking about your blood report or prescription.",
    sourceRecordIds: [],
  };
}
