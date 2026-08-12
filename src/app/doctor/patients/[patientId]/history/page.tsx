"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import { useAuth } from "@/context/auth-context";
import { getConsentsForDoctor, hasApprovedConsent } from "@/lib/services/consent-service";
import { MOCK_PATIENTS, MOCK_TIMELINE } from "@/lib/mock/mock-data";
import type { Consent } from "@/types";

export default function DoctorPatientHistoryPage({
  params,
}: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = use(params);
  const { user } = useAuth();
  const [consent, setConsent] = useState<Consent | undefined>();

  const patient = MOCK_PATIENTS.find((p) => p.uid === patientId);

  useEffect(() => {
    if (!user) return;
    const doctorConsents = getConsentsForDoctor(user.uid);
    setConsent(doctorConsents.find((c) => c.patientId === patientId && c.status === "approved"));
  }, [user, patientId]);

  const events = consent
    ? MOCK_TIMELINE.filter(
        (e) =>
          e.patientId === patientId &&
          (e.recordType === "visit" ||
            hasApprovedConsent(patientId, user!.uid, e.recordType))
      )
    : [];

  return (
    <DashboardShell role="doctor" title={`${patient?.fullName ?? "Patient"} — Medical History`}>
      {!consent ? (
        <EmptyState
          icon={<ShieldAlert className="h-8 w-8" />}
          title="No approved consent"
          description="You need patient-approved consent before viewing this patient's history."
          action={
            <Link href="/doctor/patients" className="text-sm font-medium text-teal-600 hover:underline">
              Back to patients
            </Link>
          }
        />
      ) : events.length === 0 ? (
        <EmptyState title="No permitted history events" description="No timeline events fall within your approved permissions." />
      ) : (
        <Card className="p-6">
          <ol className="relative border-l border-slate-200 pl-6">
            {events.map((e) => (
              <li key={e.eventId} className="mb-8 last:mb-0">
                <span className="absolute -left-[7px] mt-1.5 h-3 w-3 rounded-full bg-teal-600" />
                <p className="text-xs font-medium text-slate-400">
                  {new Date(e.date).toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" })}
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-900">{e.title}</p>
                <p className="mt-1 text-sm text-slate-500">{e.summary}</p>
              </li>
            ))}
          </ol>
        </Card>
      )}
    </DashboardShell>
  );
}
