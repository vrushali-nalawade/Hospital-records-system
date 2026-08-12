"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Send, Info } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import { useAuth } from "@/context/auth-context";
import { getRecordsForPatient } from "@/lib/services/records-service";
import { askAIAboutRecords } from "@/lib/services/ai-service";
import { DEMO_AI_DISCLAIMER } from "@/lib/demo-mode";
import type { AIChatMessage, MedicalRecord } from "@/types";

const SUGGESTED_QUESTIONS = [
  "What does my latest blood report contain?",
  "Summarize my recent prescription.",
  "What medical records were uploaded this month?",
  "Show my medical history.",
  "Summarize my discharge summary.",
];

export default function AIAssistantPage() {
  const { user } = useAuth();
  const [records, setRecords] = useState<MedicalRecord[]>([]);
  const [messages, setMessages] = useState<AIChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (user) setRecords(getRecordsForPatient(user.uid));
  }, [user]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

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
      const { answer, sourceRecordIds } = await askAIAboutRecords(text, records);
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

  return (
    <DashboardShell role="patient" title="AI Health Record Assistant">
      <div className="mx-auto flex h-[calc(100vh-160px)] max-w-3xl flex-col">
        <div className="mb-3 flex items-start gap-2 rounded-lg bg-amber-50 px-4 py-3 text-xs text-amber-800">
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          {DEMO_AI_DISCLAIMER}
        </div>

        <Card className="flex flex-1 flex-col overflow-hidden">
          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-10 text-center">
                <Bot className="mb-3 h-8 w-8 text-teal-600" />
                <p className="text-sm font-medium text-slate-700">Ask about your uploaded records</p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => send(q)}
                      className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-50"
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
                      ? "max-w-[80%] rounded-lg rounded-tr-none bg-teal-600 px-4 py-2.5 text-sm text-white whitespace-pre-wrap"
                      : "max-w-[85%] rounded-lg rounded-tl-none bg-slate-100 px-4 py-2.5 text-sm text-slate-800 whitespace-pre-wrap"
                  }
                >
                  {m.content}
                  {m.sourceRecordIds && m.sourceRecordIds.length > 0 && (
                    <p className="mt-2 text-[11px] text-slate-400">
                      Source: {m.sourceRecordIds.length} record(s) from your uploads
                    </p>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="rounded-lg rounded-tl-none bg-slate-100 px-4 py-2.5 text-sm text-slate-500">
                  <span className="inline-flex gap-1">
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:0ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" />
                    <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" />
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
            className="flex items-center gap-2 border-t border-slate-200 p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about your records..."
              className="flex-1 rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </Card>
      </div>
    </DashboardShell>
  );
}
