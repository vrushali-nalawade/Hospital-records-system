"use client";

import { useEffect, useState } from "react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import { useAuth } from "@/context/auth-context";
import { getConsentsForDoctor } from "@/lib/services/consent-service";
import { MOCK_PATIENTS, recordTypeLabel } from "@/lib/mock/mock-data";
import type { Consent } from "@/types";
import { ClipboardCheck } from "lucide-react";

export default function DoctorAccessRequestsPage() {
  const { user } = useAuth();
  const [consents, setConsents] = useState<Consent[]>([]);

  useEffect(() => {
    if (user) setConsents(getConsentsForDoctor(user.uid));
  }, [user]);

  const patientName = (id: string) => MOCK_PATIENTS.find((p) => p.uid === id)?.fullName ?? "Unknown patient";

  return (
    <DashboardShell role="doctor" title="Access Requests">
      {consents.length === 0 ? (
        <EmptyState icon={<ClipboardCheck className="h-8 w-8" />} title="No access requests yet" description="Requests you send to patients will appear here with their status." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {consents.map((c) => (
            <Card key={c.consentId} className="p-5">
              <div className="flex items-start justify-between">
                <p className="text-sm font-semibold text-slate-900">{patientName(c.patientId)}</p>
                <Badge tone={c.status}>{c.status}</Badge>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {c.permissions.map((p) => (
                  <span key={p} className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">
                    {recordTypeLabel[p]}
                  </span>
                ))}
              </div>
              <p className="mt-3 text-xs text-slate-400">
                Requested {new Date(c.createdAt).toLocaleDateString("en-IN")}
              </p>
            </Card>
          ))}
        </div>
      )}
    </DashboardShell>
  );
}
