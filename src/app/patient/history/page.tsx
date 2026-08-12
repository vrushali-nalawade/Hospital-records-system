"use client";

import { useEffect, useMemo, useState } from "react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import RecordViewer from "@/components/records/RecordViewer";
import { useAuth } from "@/context/auth-context";
import { getRecordsForPatient } from "@/lib/services/records-service";
import { MOCK_TIMELINE, recordTypeLabel } from "@/lib/mock/mock-data";
import type { MedicalRecord, TimelineEvent } from "@/types";
import { History } from "lucide-react";

export default function MedicalHistoryPage() {
  const { user } = useAuth();
  const [records, setRecords] = useState<MedicalRecord[]>([]);
  const [year, setYear] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  useEffect(() => {
    if (user) setRecords(getRecordsForPatient(user.uid));
  }, [user]);

  const [selected, setSelected] = useState<MedicalRecord | null>(null);

  // Build timeline: mock seed events + any records the patient has uploaded themselves
  const events: TimelineEvent[] = useMemo(() => {
    const fromRecords: TimelineEvent[] = records
      .filter((r) => !MOCK_TIMELINE.some((t) => t.recordId === r.recordId))
      .map((r) => ({
        eventId: `ev-${r.recordId}`,
        patientId: r.patientId,
        date: r.createdAt,
        recordType: r.recordType,
        title: `${recordTypeLabel[r.recordType]} Uploaded`,
        summary: `${r.fileName} was uploaded and processed.`,
        recordId: r.recordId,
      }));
    return [...MOCK_TIMELINE, ...fromRecords].sort((a, b) => (a.date < b.date ? 1 : -1));
  }, [records]);

  const years = useMemo(
    () => Array.from(new Set(events.map((e) => new Date(e.date).getFullYear().toString()))),
    [events]
  );

  const filtered = events.filter((e) => {
    if (year !== "all" && new Date(e.date).getFullYear().toString() !== year) return false;
    if (typeFilter !== "all" && e.recordType !== typeFilter) return false;
    return true;
  });

  return (
    <DashboardShell role="patient" title="Medical History">
      <div className="mb-5 flex flex-wrap gap-3">
        <select
          value={year}
          onChange={(e) => setYear(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="all">All years</option>
          {years.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="all">All types</option>
          {Object.entries(recordTypeLabel).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={<History className="h-8 w-8" />} title="No history events" description="Upload records to build your timeline." />
      ) : (
        <Card className="p-6">
          <ol className="relative border-l border-slate-200 pl-6">
            {filtered.map((e) => (
              <li key={e.eventId} className="mb-8 last:mb-0">
                <span className="absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full bg-teal-600" />
                <p className="text-xs font-medium text-slate-400">
                  {new Date(e.date).toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" })}
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-900">{e.title}</p>
                <p className="mt-1 text-sm text-slate-500">{e.summary}</p>
                {e.recordId && (
                  <button
                    onClick={() => {
                      const rec = records.find((r) => r.recordId === e.recordId);
                      if (rec) setSelected(rec);
                    }}
                    className="mt-2 text-xs font-medium text-teal-600 hover:underline"
                  >
                    View Record
                  </button>
                )}
              </li>
            ))}
          </ol>
        </Card>
      )}

      {selected && <RecordViewer record={selected} onClose={() => setSelected(null)} />}
    </DashboardShell>
  );
}
