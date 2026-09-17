"use client";

import { useEffect, useMemo, useState } from "react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import { useAuth } from "@/context/auth-context";
import { getAccessLogsForPatient, fetchAccessLogsForPatient } from "@/lib/services/consent-service";
import type { AccessLog } from "@/types";
import { ListChecks } from "lucide-react";

export default function AccessHistoryPage() {
  const { user } = useAuth();
  const [logs, setLogs] = useState<AccessLog[]>([]);
  const [doctorFilter, setDoctorFilter] = useState("all");
  const [actionFilter, setActionFilter] = useState("all");

  useEffect(() => {
    if (!user) return;
    const loadData = async () => {
      try {
        const auditLogs = await fetchAccessLogsForPatient(user.uid);
        setLogs(auditLogs);
      } catch (e) {
        console.error("Failed to load access logs from API", e);
        setLogs(getAccessLogsForPatient(user.uid));
      }
    };
    loadData();
  }, [user]);

  const doctors = useMemo(() => Array.from(new Set(logs.map((l) => l.doctorName))), [logs]);

  const filtered = logs.filter((l) => {
    if (doctorFilter !== "all" && l.doctorName !== doctorFilter) return false;
    if (actionFilter !== "all" && l.action !== actionFilter) return false;
    return true;
  });

  return (
    <DashboardShell role="patient" title="Access History">
      <div className="mb-5 flex flex-wrap gap-3">
        <select
          value={doctorFilter}
          onChange={(e) => setDoctorFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="all">All doctors</option>
          {doctors.map((d) => <option key={d} value={d}>{d}</option>)}
        </select>
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
        >
          <option value="all">All actions</option>
          <option value="viewed">Viewed</option>
          <option value="downloaded">Downloaded</option>
          <option value="requested_access">Requested access</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={<ListChecks className="h-8 w-8" />} title="No access activity" description="Doctor access to your records will be logged here." />
      ) : (
        <Card className="overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Doctor</th>
                <th className="px-4 py-3">Record</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Consent</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map((l) => (
                <tr key={l.logId}>
                  <td className="px-4 py-3 font-medium text-slate-800">{l.doctorName}</td>
                  <td className="px-4 py-3 text-slate-600">{l.recordName ?? "—"}</td>
                  <td className="px-4 py-3 capitalize text-slate-600">{l.action.replace("_", " ")}</td>
                  <td className="px-4 py-3 text-slate-500">
                    {new Date(l.timestamp).toLocaleString("en-IN")}
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone={l.consentStatus}>{l.consentStatus}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </DashboardShell>
  );
}
