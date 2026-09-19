"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, Bot, UploadCloud, CheckCircle2, History } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import { useAuth } from "@/context/auth-context";
import { useI18n } from "@/context/i18n-context";
import { getRecordsForPatient, fetchRecordsForPatient } from "@/lib/services/records-service";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import type { MedicalRecord } from "@/types";

function StatCard({ label, value, icon: Icon }: { label: string; value: number | string; icon: typeof FileText }) {
  return (
    <Card className="flex items-center gap-4 p-5">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-teal-50 text-teal-600">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-2xl font-semibold text-slate-900">{value}</p>
        <p className="text-sm text-slate-500">{label}</p>
      </div>
    </Card>
  );
}

export default function PatientDashboardPage() {
  const { user } = useAuth();
  const { t } = useI18n();
  const [records, setRecords] = useState<MedicalRecord[]>([]);

  useEffect(() => {
    if (!user) return;
    const loadData = async () => {
      try {
        const recs = await fetchRecordsForPatient(user.uid);
        setRecords(recs);
      } catch (e) {
        console.error("Failed to load dashboard data from API", e);
        setRecords(getRecordsForPatient(user.uid));
      }
    };
    loadData();
  }, [user]);

  const prescriptionsCount = records.filter(
    (r) => r.recordType === "prescription" || (r.fileName || "").toLowerCase().includes("prescription")
  ).length;
  const reportsCount = records.filter(
    (r) => r.recordType === "lab_report" || r.recordType === "discharge_summary" || (r.fileName || "").toLowerCase().includes("report") || (r.fileName || "").toLowerCase().includes("summary")
  ).length;
  const readyCount = records.filter((r) => r.processingStatus === "ready").length;

  return (
    <DashboardShell role="patient" title={t("dashboard")}>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            {t("welcomeBack")}, {user?.fullName?.split(" ")[0]}
          </h2>
          <p className="text-sm text-slate-500">Your personal digital health locker & AI medical records assistant.</p>
        </div>
        <Link
          href="/patient/upload"
          className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-teal-700 transition-colors shadow-sm"
        >
          <UploadCloud className="h-4 w-4" /> {t("quickUpload")}
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Health Records" value={records.length} icon={FileText} />
        <StatCard label="Prescriptions" value={prescriptionsCount} icon={FileText} />
        <StatCard label="Reports & Summaries" value={reportsCount} icon={CheckCircle2} />
        <StatCard label="AI Indexed & Ready" value={readyCount} icon={Bot} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">{t("recentRecords")}</h3>
            <Link href="/patient/records" className="text-xs font-medium text-teal-600 hover:underline">
              {t("viewAll")}
            </Link>
          </div>
          {records.length === 0 ? (
            <p className="text-sm text-slate-400">{t("noRecordsYet")}</p>
          ) : (
            <div className="space-y-3">
              {records.slice(0, 5).map((r) => (
                <div key={r.recordId} className="flex items-center justify-between rounded-lg border border-slate-100 px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-slate-800">{recordTypeLabel[r.recordType]}</p>
                    <p className="text-xs text-slate-400">{r.fileName}</p>
                  </div>
                  <Badge tone={r.processingStatus}>{r.processingStatus.replace("_", " ")}</Badge>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-900">Quick AI Actions</h3>
          <div className="space-y-3">
            <Link
              href="/patient/ai-assistant"
              className="flex items-center gap-3 rounded-xl border border-teal-100 bg-teal-50/60 p-3 text-sm text-teal-900 hover:bg-teal-100/70 transition-colors"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-teal-600 text-white">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-slate-800">Ask AI Assistant</p>
                <p className="text-xs text-slate-500">Plain-English explanations of all prescriptions</p>
              </div>
            </Link>

            <Link
              href="/patient/upload"
              className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-sm text-slate-800 hover:bg-slate-100 transition-colors"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-700 text-white">
                <UploadCloud className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-slate-800">Upload New Record</p>
                <p className="text-xs text-slate-500">Scan or add PDF / Image records</p>
              </div>
            </Link>

            <Link
              href="/patient/history"
              className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-sm text-slate-800 hover:bg-slate-100 transition-colors"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-700 text-white">
                <History className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-slate-800">Medical History</p>
                <p className="text-xs text-slate-500">View chronological clinical timeline</p>
              </div>
            </Link>
          </div>
        </Card>
      </div>
    </DashboardShell>
  );
}
