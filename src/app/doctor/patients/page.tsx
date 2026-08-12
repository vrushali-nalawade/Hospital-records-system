"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import { useAuth } from "@/context/auth-context";
import { MOCK_PATIENTS } from "@/lib/mock/mock-data";
import { getConsentsForDoctor, requestAccess } from "@/lib/services/consent-service";
import { pushToast } from "@/components/ui/Toast";

export default function DoctorPatientsPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [consents, setConsents] = useState(user ? getConsentsForDoctor(user.uid) : []);

  const filtered = useMemo(
    () =>
      MOCK_PATIENTS.filter(
        (p) =>
          p.fullName.toLowerCase().includes(query.toLowerCase()) ||
          p.email.toLowerCase().includes(query.toLowerCase())
      ),
    [query]
  );

  const consentFor = (patientId: string) =>
    consents.find((c) => c.patientId === patientId);

  const handleRequest = (patientId: string) => {
    if (!user) return;
    requestAccess(patientId, user.uid, user.fullName, [
      "blood_report",
      "prescription",
      "lab_report",
      "discharge_summary",
    ]);
    setConsents(getConsentsForDoctor(user.uid));
    pushToast({ type: "success", message: "Access request sent." });
  };

  return (
    <DashboardShell role="doctor" title="Patients">
      <div className="relative mb-5 w-full max-w-xs">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search patients..."
          className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((p) => {
          const consent = consentFor(p.uid);
          return (
            <Card key={p.uid} className="p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-full bg-teal-100 text-sm font-semibold text-teal-700">
                  {p.fullName.charAt(0)}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{p.fullName}</p>
                  <p className="text-xs text-slate-400">{p.email}</p>
                </div>
              </div>
              <div className="mt-3">
                {consent ? (
                  <Badge tone={consent.status}>{consent.status}</Badge>
                ) : (
                  <Badge tone="revoked">No consent</Badge>
                )}
              </div>
              <div className="mt-4 flex gap-2">
                {consent?.status === "approved" ? (
                  <Link
                    href={`/doctor/patients/${p.uid}/records`}
                    className="flex-1 rounded-lg bg-teal-600 px-3 py-2 text-center text-xs font-medium text-white hover:bg-teal-700"
                  >
                    View records
                  </Link>
                ) : (
                  <Button size="sm" className="flex-1" onClick={() => handleRequest(p.uid)} disabled={consent?.status === "pending"}>
                    {consent?.status === "pending" ? "Request pending" : "Request access"}
                  </Button>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </DashboardShell>
  );
}
