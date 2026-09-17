"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, FileX } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import MedicalRecordCard from "@/components/records/MedicalRecordCard";
import RecordViewer from "@/components/records/RecordViewer";
import EmptyState from "@/components/ui/EmptyState";
import { useAuth } from "@/context/auth-context";
import { useI18n } from "@/context/i18n-context";
import { getRecordsForPatient, fetchRecordsForPatient } from "@/lib/services/records-service";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import type { MedicalRecord, RecordType } from "@/types";

export default function PatientRecordsPage() {
  const { user } = useAuth();
  const { t } = useI18n();
  const [records, setRecords] = useState<MedicalRecord[]>([]);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<RecordType | "all">("all");
  const [sort, setSort] = useState<"newest" | "oldest">("newest");
  const [selected, setSelected] = useState<MedicalRecord | null>(null);

  useEffect(() => {
    if (!user) return;
    const loadData = async () => {
      try {
        const recs = await fetchRecordsForPatient(user.uid);
        setRecords(recs);
      } catch (e) {
        console.error("Failed to load records from API", e);
        setRecords(getRecordsForPatient(user.uid));
      }
    };
    loadData();
  }, [user]);

  const filtered = useMemo(() => {
    let list = records;
    if (typeFilter !== "all") list = list.filter((r) => r.recordType === typeFilter);
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (r) =>
          r.fileName.toLowerCase().includes(q) ||
          recordTypeLabel[r.recordType].toLowerCase().includes(q)
      );
    }
    return [...list].sort((a, b) =>
      sort === "newest"
        ? a.createdAt < b.createdAt ? 1 : -1
        : a.createdAt > b.createdAt ? 1 : -1
    );
  }, [records, query, typeFilter, sort]);

  return (
    <DashboardShell role="patient" title={t("medicalRecords")}>
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>
        <div className="flex gap-3">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as RecordType | "all")}
            className="rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="all">{t("allTypes")}</option>
            {Object.entries(recordTypeLabel)
              .filter(([k]) => k !== "visit")
              .map(([k, v]) => (
                <option key={k} value={k}>{v}</option>
              ))}
          </select>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as "newest" | "oldest")}
            className="rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="newest">{t("sortNewest")}</option>
            <option value="oldest">{t("sortOldest")}</option>
          </select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={<FileX className="h-8 w-8" />}
          title={t("noRecordsFound")}
          description="Try a different search or filter, or upload a new record."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((r) => (
            <MedicalRecordCard key={r.recordId} record={r} onView={setSelected} />
          ))}
        </div>
      )}

      {selected && <RecordViewer record={selected} onClose={() => setSelected(null)} />}
    </DashboardShell>
  );
}
