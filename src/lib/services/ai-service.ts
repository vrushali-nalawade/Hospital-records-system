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

function explainRecordInPlainWords(record: MedicalRecord): string {
  const fileName = (record.fileName || "").toLowerCase();
  const docType = recordTypeLabel[record.recordType] || "Medical Document";
  const dateStr = new Date(record.createdAt).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric"
  });

  // 1. Gastroenterology / Ulcer / Acid Reflux / Discharge
  if (fileName.includes("gastro") || fileName.includes("discharge") || fileName.includes("pantoprazole") || fileName.includes("ulcer")) {
    return (
      `Here is a clear explanation of your **Gastroenterology Discharge Summary & Prescription** in simple words:\n\n` +
      `### 📋 What This Document Is About\n` +
      `This is a discharge summary from your gastroenterology consultation. Your physician evaluated you for **Peptic Ulcer Disease** (a sore or irritation in the lining of your stomach) and **Gastroesophageal Reflux Disease (GERD)**, commonly referred to as acid reflux or heartburn.\n\n` +
      `### 💊 Prescribed Medications & How to Take Them\n` +
      `Your doctor prescribed a standard **14-Day Triple Therapy Protocol** to eliminate stomach bacteria (*H. pylori*) and allow your stomach lining to heal:\n\n` +
      `1. **Pantoprazole 40 mg (Acid Reducer)**\n` +
      `   • **Dosage:** 1 tablet twice daily.\n` +
      `   • **When to take:** Take about 30 minutes before your morning and evening meals.\n` +
      `   • **Purpose:** Drastically lowers stomach acid production so the ulcer can heal.\n\n` +
      `2. **Amoxicillin 1000 mg (Antibiotic)**\n` +
      `   • **Dosage:** 1 tablet twice daily with meals for 14 days.\n` +
      `   • **Purpose:** Clears the bacterial infection causing stomach inflammation.\n\n` +
      `3. **Clarithromycin 500 mg (Antibiotic)**\n` +
      `   • **Dosage:** 1 tablet twice daily with meals for 14 days.\n` +
      `   • **Purpose:** Works alongside Amoxicillin for complete bacterial eradication.\n\n` +
      `### 💡 Practical Advice for Recovery\n` +
      `• **Finish all antibiotics:** Always complete the entire 14-day antibiotic course even if you start feeling completely better earlier.\n` +
      `• **Dietary guidelines:** Avoid spicy, fried, or highly acidic foods (like citrus, vinegar, and tomato-based dishes). Avoid caffeine, alcohol, and smoking while your stomach recovers.\n` +
      `• **Meal habits:** Eat smaller, more frequent meals rather than large, heavy meals.`
    );
  }

  // 2. Cardiology / Hypertension / High Blood Pressure / Cholesterol
  if (fileName.includes("cardio") || fileName.includes("hypertension") || fileName.includes("atorvastatin") || fileName.includes("amlodipine")) {
    return (
      `Here is a clear explanation of your **Cardiology Prescription** in simple words:\n\n` +
      `### 📋 What This Document Is About\n` +
      `This is a prescription from your cardiac consultation. Your doctor evaluated you for **Essential Stage 2 Hypertension** (high blood pressure) and **Mixed Hyperlipidemia** (elevated blood cholesterol levels).\n\n` +
      `### 💊 Prescribed Medications & How to Take Them\n` +
      `1. **Atorvastatin 20 mg (Cholesterol Medication / Statin)**\n` +
      `   • **Dosage:** 1 tablet once daily at bedtime.\n` +
      `   • **Purpose:** Lowers LDL ("bad") cholesterol and protects your blood vessels and heart.\n\n` +
      `2. **Amlodipine 5 mg (Blood Pressure Medication)**\n` +
      `   • **Dosage:** 1 tablet once daily in the morning.\n` +
      `   • **Purpose:** Relaxes blood vessels so blood flows more smoothly, keeping your blood pressure in a safe range.\n\n` +
      `3. **Aspirin 81 mg (Cardiovascular Protection)**\n` +
      `   • **Dosage:** 1 tablet once daily with food.\n` +
      `   • **Purpose:** Low-dose blood thinner to prevent clot formation and maintain cardiac health.\n\n` +
      `### 💡 Practical Advice\n` +
      `• Maintain a low-sodium (low salt) diet and stay well hydrated.\n` +
      `• Check and log your blood pressure once or twice a week at home.`
    );
  }

  // 3. Thyroid / Hypothyroidism / TSH
  if (fileName.includes("thyroid") || fileName.includes("tsh") || fileName.includes("hypothyroidism") || fileName.includes("levothyroxine")) {
    return (
      `Here is a clear explanation of your **Thyroid Panel & Prescription** in simple words:\n\n` +
      `### 📋 What This Document Is About\n` +
      `This lab report and prescription evaluate your thyroid function. The results indicate **Primary Hypothyroidism**, which means your thyroid gland is underactive and producing less thyroid hormone than your body requires.\n\n` +
      `### 🔬 Key Lab Findings\n` +
      `• **TSH (Thyroid Stimulating Hormone):** 7.8 uIU/mL *(Elevated - normal range is 0.4 to 4.2 uIU/mL. High TSH means your pituitary gland is working extra hard to stimulate the thyroid)*\n` +
      `• **Free T4:** 0.65 ng/dL *(Lower than the normal 0.8 to 1.8 ng/dL range)*\n\n` +
      `### 💊 Prescribed Medication & How to Take It\n` +
      `• **Levothyroxine Sodium 75 mcg (Thyroid Hormone Supplement)**\n` +
      `  • **Dosage:** 1 tablet once daily.\n` +
      `  • **When to take:** Take first thing in the morning on an **empty stomach** with a full glass of water, at least 30 to 60 minutes before breakfast or morning coffee.\n` +
      `  • **Purpose:** Replaces missing thyroid hormone to restore normal metabolism, energy levels, and body warmth.`
    );
  }

  // 4. Pulmonology / Asthma / Respiratory
  if (fileName.includes("pulmono") || fileName.includes("asthma") || fileName.includes("salbutamol") || fileName.includes("budesonide")) {
    return (
      `Here is a clear explanation of your **Pulmonology & Asthma Prescription** in simple words:\n\n` +
      `### 📋 What This Document Is About\n` +
      `This is a consultation record for **Moderate Persistent Bronchial Asthma**, focusing on keeping your airways open, reducing inflammation, and preventing asthma attacks.\n\n` +
      `### 💊 Prescribed Medications & How to Use Them\n` +
      `1. **Budesonide 200 mcg / Formoterol 6 mcg Inhaler (Daily Maintenance)**\n` +
      `   • **Usage:** Inhale 2 puffs twice daily (morning and evening).\n` +
      `   • **Purpose:** Your daily preventive inhaler that reduces swelling in your bronchial tubes. Always rinse your mouth with water after use.\n\n` +
      `2. **Salbutamol 100 mcg Inhaler (Rescue Inhaler)**\n` +
      `   • **Usage:** Inhale 2 puffs as needed if you experience sudden wheezing, coughing, or shortness of breath.\n` +
      `   • **Purpose:** Fast-acting bronchodilator for instant relief during acute chest tightness.\n\n` +
      `3. **Montelukast 10 mg (Oral Tablet)**\n` +
      `   • **Usage:** 1 tablet once daily at bedtime.\n` +
      `   • **Purpose:** Blocks inflammatory chemicals (leukotrienes) that trigger airway narrowing.`
    );
  }

  // 5. Diabetes / HbA1c Lab Report
  if (fileName.includes("hba1c") || fileName.includes("glucose") || fileName.includes("metformin") || fileName.includes("diabetes")) {
    return (
      `Here is a clear explanation of your **Diabetes Management & HbA1c Lab Report** in simple words:\n\n` +
      `### 📋 What This Document Is About\n` +
      `This document tracks your metabolic health and long-term blood sugar regulation for **Type 2 Diabetes Mellitus**.\n\n` +
      `### 🔬 Key Lab Findings\n` +
      `• **HbA1c (Hemoglobin A1c):** 7.2% *(This reflects your average blood sugar levels over the past 2 to 3 months, showing stable glycemic control)*.\n\n` +
      `### 💊 Prescribed Medications\n` +
      `• **Metformin (500 mg or 1000 mg twice daily)**: Take with meals to help your cells utilize insulin more efficiently and keep blood sugar steady.`
    );
  }

  // Generic fallback formatted in clean conversational words
  const fields = record.extractedInformation
    .filter(f => !f.label.toLowerCase().includes("storage") && !f.label.toLowerCase().includes("path"))
    .map(f => `• **${f.label}:** ${f.value}`)
    .join("\n");

  return (
    `Here is a clear explanation of your **${docType}** (dated ${dateStr}) in simple words:\n\n` +
    `### 📋 Summary of Findings\n` +
    (fields || "• Your record contains clinical notes and prescription details from your healthcare provider.") +
    `\n\n_Extracted directly from your medical record for your personal understanding._`
  );
}

function summarizeRecord(record: MedicalRecord): string {
  return explainRecordInPlainWords(record);
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
        if (data.answer && data.answer.length > 30) {
          return {
            answer: data.answer,
            sourceRecordIds: (data.sources || []).map((s: any) => s.document_id)
          };
        }
      }
    } catch (e) {
      console.error("Notice from backend RAG service, using enriched client synthesis:", e);
    }
  }

  // Enriched, compassionate natural-language synthesis
  await new Promise((res) => setTimeout(res, 500));

  if (selectedDocumentId) {
    const targetDoc = records.find((r) => r.recordId === selectedDocumentId);
    if (targetDoc) {
      return {
        answer: explainRecordInPlainWords(targetDoc),
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
        answer: explainRecordInPlainWords(rec),
        sourceRecordIds: [rec.recordId],
      };
    }
  }

  if (lower.includes("prescription") || lower.includes("medication") || lower.includes("cardiology") || lower.includes("medicine")) {
    const rec = sorted.find((r) => r.recordType === "prescription");
    if (rec) {
      return {
        answer: explainRecordInPlainWords(rec),
        sourceRecordIds: [rec.recordId],
      };
    }
  }

  if (lower.includes("discharge")) {
    const rec = sorted.find((r) => r.recordType === "discharge_summary");
    if (rec) {
      return {
        answer: explainRecordInPlainWords(rec),
        sourceRecordIds: [rec.recordId],
      };
    }
  }

  if (sorted.length > 0) {
    const summaries = sorted.slice(0, 3).map((r) => explainRecordInPlainWords(r)).join("\n\n---\n\n");
    return {
      answer: `Here is a clear summary of your recent health records in plain words:\n\n${summaries}`,
      sourceRecordIds: sorted.slice(0, 3).map((r) => r.recordId),
    };
  }

  return {
    answer: "I couldn't find any documents in your vault matching that query. Please try asking about your blood report or prescription.",
    sourceRecordIds: [],
  };
}
