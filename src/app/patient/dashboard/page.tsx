"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, ShieldCheck, Users, Activity, UploadCloud } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import { useAuth } from "@/context/auth-context";
import { getRecordsForPatient } from "@/lib/services/records-service";
import { getConsentsForPatient, getAccessLogsForPatient } from "@/lib/services/consent-service";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import type { AccessLog, Consent, MedicalRecord } from "@/types";

function StatCard({ label, value, icon: Icon }: { label: string; value: number; icon: typeof FileText }) {
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
  const [records, setRecords] = useState<MedicalRecord[]>([]);
  const [consents, setConsents] = useState<Consent[]>([]);
  const [logs, setLogs] = useState<AccessLog[]>([]);

  useEffect(() => {
    if (!user) return;
    setRecords(getRecordsForPatient(user.uid));
    setConsents(getConsentsForPatient(user.uid));
    setLogs(getAccessLogsForPatient(user.uid));
  }, [user]);

  const pending = consents.filter((c) => c.status === "pending").length;
  const active = consents.filter((c) => c.status === "approved").length;

  return (
    <DashboardShell role="patient" title="Dashboard">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">
            Welcome back, {user?.fullName?.split(" ")[0]}
          </h2>
          <p className="text-sm text-slate-500">Here&apos;s an overview of your health locker.</p>
        </div>
        <Link
          href="/patient/upload"
          className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-teal-700"
        >
          <UploadCloud className="h-4 w-4" /> Quick Upload
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Medical Records" value={records.length} icon={FileText} />
        <StatCard label="Pending Consent Requests" value={pending} icon={ShieldCheck} />
        <StatCard label="Active Doctor Access" value={active} icon={Users} />
        <StatCard label="Recent Activity" value={logs.length} icon={Activity} />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Card className="p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Recent Records</h3>
            <Link href="/patient/records" className="text-xs font-medium text-teal-600 hover:underline">
              View all
            </Link>
          </div>
          {records.length === 0 ? (
            <p className="text-sm text-slate-400">No records uploaded yet.</p>
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
          <h3 className="mb-4 text-sm font-semibold text-slate-900">Recent Activity</h3>
          {logs.length === 0 ? (
            <p className="text-sm text-slate-400">No activity yet.</p>
          ) : (
            <div className="space-y-4">
              {logs.slice(0, 5).map((l) => (
                <div key={l.logId} className="text-sm">
                  <p className="text-slate-700">
                    <span className="font-medium">{l.doctorName}</span> {l.action.replace("_", " ")}
                    {l.recordName ? ` ${l.recordName}` : ""}
                  </p>
                  <p className="text-xs text-slate-400">
                    {new Date(l.timestamp).toLocaleString("en-IN")}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </DashboardShell>
  );
}
