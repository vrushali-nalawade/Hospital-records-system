"use client";

import type { MedicalRecord } from "@/types";
import { recordTypeLabel } from "@/lib/mock/mock-data";

// AI service abstraction for record understanding.
//
// This is intentionally decoupled from any specific AI provider so a real
// LLM API can be plugged in later (see askAIAboutRecords below). In DEMO
// MODE, or whenever NEXT_PUBLIC_AI_API_URL is not configured, responses are
// generated from clearly-labelled mock logic instead of a live model.
//
// SAFETY: this service must never diagnose disease, prescribe medication,
// recommend treatment, or make emergency medical decisions. It only
// summarizes and explains information already present in the patient's
// uploaded records.

const FORBIDDEN_TOPICS = [
  "diagnose",
  "diagnosis",
  "prescribe",
  "what disease do i have",
  "should i take",
  "treatment plan",
];

export function isAIConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_AI_API_URL);
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

export async function askAIAboutRecords(
  question: string,
  records: MedicalRecord[]
): Promise<{ answer: string; sourceRecordIds: string[] }> {
  const lower = question.toLowerCase();

  if (FORBIDDEN_TOPICS.some((t) => lower.includes(t))) {
    return { answer: safetyRedirect(), sourceRecordIds: [] };
  }

  if (isAIConfigured()) {
    // Real AI integration point:
    // const res = await fetch(process.env.NEXT_PUBLIC_AI_API_URL!, {
    //   method: "POST",
    //   body: JSON.stringify({ question, records }),
    // });
    // return await res.json();
  }

  // ---- DEMO AI (mock) logic below ----
  await new Promise((res) => setTimeout(res, 700));

  const sorted = [...records].sort((a, b) =>
    a.createdAt < b.createdAt ? 1 : -1
  );

  if (lower.includes("blood report") || lower.includes("blood")) {
    const rec = sorted.find((r) => r.recordType === "blood_report");
    if (rec) {
      return {
        answer: `Here's what's in your latest blood report:\n\n${summarizeRecord(
          rec
        )}\n\n_This is a summary of the values already present in your uploaded document, for your understanding only._`,
        sourceRecordIds: [rec.recordId],
      };
    }
  }

  if (lower.includes("prescription")) {
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
        answer: `Here's a summary of your discharge summary:\n\n${summarizeRecord(
          rec
        )}`,
        sourceRecordIds: [rec.recordId],
      };
    }
  }

  if (lower.includes("this month") || lower.includes("uploaded")) {
    const now = new Date();
    const thisMonth = sorted.filter((r) => {
      const d = new Date(r.createdAt);
      return (
        d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
      );
    });
    if (thisMonth.length === 0) {
      return {
        answer: "No records were uploaded this month.",
        sourceRecordIds: [],
      };
    }
    return {
      answer: `You uploaded ${thisMonth.length} record(s) this month:\n\n${thisMonth
        .map((r) => `- ${recordTypeLabel[r.recordType]} (${r.fileName})`)
        .join("\n")}`,
      sourceRecordIds: thisMonth.map((r) => r.recordId),
    };
  }

  if (lower.includes("history") || lower.includes("timeline")) {
    return {
      answer: `Here's a quick overview of your medical history, from most recent:\n\n${sorted
        .slice(0, 5)
        .map(
          (r) =>
            `- ${new Date(r.createdAt).toLocaleDateString("en-IN")}: ${
              recordTypeLabel[r.recordType]
            }`
        )
        .join("\n")}`,
      sourceRecordIds: sorted.slice(0, 5).map((r) => r.recordId),
    };
  }

  return {
    answer:
      "I can help you understand your uploaded records — try asking about a specific record type, like your latest blood report, prescription, or discharge summary. I can only explain information already present in your records.",
    sourceRecordIds: [],
  };
}
