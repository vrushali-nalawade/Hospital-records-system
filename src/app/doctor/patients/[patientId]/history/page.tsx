"use client";

import { use, useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import { useAuth } from "@/context/auth-context";
import { getConsentsForDoctor, fetchConsentsForDoctor, hasApprovedConsent } from "@/lib/services/consent-service";
import { IS_DEMO_MODE } from "@/lib/demo-mode";
import { auth } from "@/lib/firebase/config";
import { API_BASE_URL } from "@/lib/api-config";
import type { TimelineEvent } from "@/types";
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
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);

  const patient = MOCK_PATIENTS.find((p) => p.uid === patientId);

  useEffect(() => {
    if (!user) return;
    const loadData = async () => {
      try {
        const doctorConsents = await fetchConsentsForDoctor(user.uid);
        const c = doctorConsents.find((c) => c.patientId === patientId && c.status === "approved");
        setConsent(c);
        if (c && !IS_DEMO_MODE) {
          const token = await auth?.currentUser?.getIdToken();
          const res = await fetch(`${API_BASE_URL}/ai/timeline/${patientId}`, {
            headers: {
              "Authorization": `Bearer ${token}`
            }
          });
          if (res.ok) {
            const data = await res.json();
            const mapped = data.events.map((e: any, idx: number) => ({
              eventId: `ev-${idx}-${e.source}`,
              patientId: patientId,
              date: e.date,
              recordType: e.event.toLowerCase().includes("prescription") ? "prescription" : (e.event.toLowerCase().includes("lab") ? "lab_report" : "prescription"),
              title: e.event,
              summary: `Source record: ${e.source}`,
              recordId: e.source
            }));
            setTimelineEvents(mapped);
            return;
          }
        }
      } catch (err) {
        console.error("Failed to load doctor patient timeline from API", err);
        if (IS_DEMO_MODE) {
          const doctorConsentsMock = getConsentsForDoctor(user.uid);
          setConsent(doctorConsentsMock.find((c) => c.patientId === patientId && c.status === "approved"));
          setTimelineEvents([]);
        }
      }
    };
    loadData();
  }, [user, patientId]);

  const events = useMemo(() => {
    if (!consent) return [];
    if (!IS_DEMO_MODE) {
      return timelineEvents;
    }
    return MOCK_TIMELINE.filter(
      (e) =>
        e.patientId === patientId &&
        (e.recordType === "visit" ||
          hasApprovedConsent(patientId, user!.uid, e.recordType))
    );
  }, [consent, timelineEvents, patientId, user]);

  return (
    <DashboardShell role="doctor" title={`${patient?.fullName ?? "Patient"} â€” Medical History`}>
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

