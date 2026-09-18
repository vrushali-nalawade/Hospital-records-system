"use client";

import { useEffect, useRef, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Bot, Send, Info, FileText, Layers, Sparkles, CheckCircle2 } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import { useAuth } from "@/context/auth-context";
import { useI18n } from "@/context/i18n-context";
import { getRecordsForPatient, fetchRecordsForPatient } from "@/lib/services/records-service";
import { askAIAboutRecords } from "@/lib/services/ai-service";
import { DEMO_AI_DISCLAIMER } from "@/lib/demo-mode";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import type { AIChatMessage, MedicalRecord } from "@/types";

const GENERAL_QUESTIONS = [
  "Summarize my recent prescription.",
  "What was my latest HbA1c value?",
  "What does my latest blood report contain?",
  "Show my medical history.",
];

const DOC_SPECIFIC_QUESTIONS = [
  "Summarize this document in simple terms.",
  "What medications and dosages are prescribed here?",
  "What diagnosis is documented in this record?",
  "Are there any special instructions or warnings?",
];

function AIAssistantContent() {
  const { user } = useAuth();
  const { t } = useI18n();
  const searchParams = useSearchParams();
  const initialDocParam = searchParams.get("doc") || "all";

  const [records, setRecords] = useState<MedicalRecord[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>(initialDocParam);
  const [messages, setMessages] = useState<AIChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) return;
    const loadData = async () => {
      try {
        const recs = await fetchRecordsForPatient(user.uid);
        setRecords(recs);
      } catch (e) {
        console.error("Failed to load records for AI Assistant", e);
        setRecords(getRecordsForPatient(user.uid));
      }
    };
    loadData();
  }, [user]);

  useEffect(() => {
    const docParam = searchParams.get("doc");
    if (docParam) {
      setSelectedDocId(docParam);
    }
  }, [searchParams]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const activeRecord = records.find((r) => r.recordId === selectedDocId);

  const send = async (text: string) => {
    if (!text.trim()) return;
    setErrorState(false);
    const now = Date.now();
    const userMsg: AIChatMessage = {
      id: `u-${now}`,
      role: "user",
      content: text,
      timestamp: new Date(now).toISOString(),
    };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const docFilter = selectedDocId === "all" ? undefined : selectedDocId;
      const { answer, sourceRecordIds } = await askAIAboutRecords(text, records, docFilter);
      const replyTime = Date.now();
      setMessages((m) => [
        ...m,
        {
          id: `a-${replyTime}`,
          role: "assistant",
          content: answer,
          sourceRecordIds,
          timestamp: new Date(replyTime).toISOString(),
        },
      ]);
    } catch {
      setErrorState(true);
    } finally {
      setLoading(false);
    }
  };

  const suggestedList = selectedDocId === "all" ? GENERAL_QUESTIONS : DOC_SPECIFIC_QUESTIONS;

  return (
    <DashboardShell role="patient" title={t("aiAssistantTitle")}>
      <div className="mx-auto flex h-[calc(100vh-160px)] max-w-3xl flex-col">
        {/* Document Context Selector Header */}
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-teal-600" />
            <span className="text-xs font-semibold text-slate-700">AI Context Scope:</span>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
              className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-800 focus:border-teal-500 focus:outline-none focus:ring-1 focus:ring-teal-500"
            >
              <option value="all">🌐 All Records (Whole Medical Vault)</option>
              {records.map((r) => (
                <option key={r.recordId} value={r.recordId}>
                  📄 {r.fileName} ({recordTypeLabel[r.recordType] || r.recordType})
                </option>
              ))}
            </select>

            {activeRecord && (
              <span className="inline-flex items-center gap-1 rounded-full bg-teal-50 px-2.5 py-1 text-[11px] font-semibold text-teal-700">
                <CheckCircle2 className="h-3 w-3" /> Focused on {activeRecord.fileName}
              </span>
            )}
          </div>
        </div>

        <div className="mb-3 flex items-start gap-2 rounded-lg bg-amber-50 px-4 py-2.5 text-xs text-amber-800">
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          {DEMO_AI_DISCLAIMER}
        </div>

        <Card className="flex flex-1 flex-col overflow-hidden">
          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-teal-50 text-teal-600">
                  <Bot className="h-6 w-6" />
                </div>
                <p className="text-sm font-semibold text-slate-800">
                  {selectedDocId === "all"
                    ? "Ask AI about your medical records"
                    : `Ask AI about ${activeRecord?.fileName || "this document"}`}
                </p>
                <p className="mt-1 max-w-md text-xs text-slate-500">
                  {selectedDocId === "all"
                    ? "Ask broad questions across all your visits, prescriptions, and lab tests, or select a specific record above."
                    : `Asking questions grounded strictly in this ${recordTypeLabel[activeRecord?.recordType || "prescription"]}.`}
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {suggestedList.map((q) => (
                    <button
                      key={q}
                      onClick={() => send(q)}
                      className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-sm hover:border-teal-500 hover:bg-teal-50 hover:text-teal-700 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m) => (
              <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={
                    m.role === "user"
                      ? "max-w-[80%] rounded-2xl rounded-tr-none bg-teal-600 px-4 py-2.5 text-sm text-white whitespace-pre-wrap shadow-sm"
                      : "max-w-[85%] rounded-2xl rounded-tl-none bg-slate-100 px-4 py-2.5 text-sm text-slate-800 whitespace-pre-wrap shadow-sm"
                  }
                >
                  {m.content}
                  {m.sourceRecordIds && m.sourceRecordIds.length > 0 && (
                    <div className="mt-2.5 pt-2 border-t border-slate-200/60 text-[11px] text-slate-500 flex items-center gap-1.5">
                      <FileText className="h-3 w-3" />
                      <span className="font-semibold">{t("citations")}:</span> {m.sourceRecordIds.join(", ")}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-tl-none bg-slate-100 px-4 py-2.5 text-sm text-slate-500">
                  <span className="inline-flex gap-1 items-center">
                    <Sparkles className="h-3.5 w-3.5 text-teal-600 animate-spin" />
                    <span className="text-xs text-slate-500 ml-1">Analyzing medical context...</span>
                  </span>
                </div>
              </div>
            )}

            {errorState && (
              <p className="text-center text-xs text-red-600">
                Something went wrong reaching the AI assistant. Please try again.
              </p>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-center gap-2 border-t border-slate-200 p-3 bg-white"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                selectedDocId === "all"
                  ? "Ask about all records (e.g. 'Summarize my recent prescription')..."
                  : `Ask specifically about ${activeRecord?.fileName || "selected record"}...`
              }
              className="flex-1 rounded-xl border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-50 transition-colors shadow-sm"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </Card>
      </div>
    </DashboardShell>
  );
}

export default function AIAssistantPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-slate-500">Loading AI Assistant...</div>}>
      <AIAssistantContent />
    </Suspense>
  );
}
