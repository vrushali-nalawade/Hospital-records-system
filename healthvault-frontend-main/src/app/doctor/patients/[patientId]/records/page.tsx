"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import MedicalRecordCard from "@/components/records/MedicalRecordCard";
import RecordViewer from "@/components/records/RecordViewer";
import EmptyState from "@/components/ui/EmptyState";
import { useAuth } from "@/context/auth-context";
import { getRecordsForPatient, fetchRecordsForPatient } from "@/lib/services/records-service";
import { getConsentsForDoctor, fetchConsentsForDoctor, hasApprovedConsent, logAccess } from "@/lib/services/consent-service";
import { MOCK_PATIENTS } from "@/lib/mock/mock-data";
import type { Consent, MedicalRecord } from "@/types";

export default function DoctorPatientRecordsPage({
  params,
}: {
  params: Promise<{ patientId: string }>;
}) {
  const { patientId } = use(params);
  const { user } = useAuth();
  const [records, setRecords] = useState<MedicalRecord[]>([]);
  const [consent, setConsent] = useState<Consent | undefined>();
  const [selected, setSelected] = useState<MedicalRecord | null>(null);

  const patient = MOCK_PATIENTS.find((p) => p.uid === patientId);

  useEffect(() => {
    if (!user) return;
    const loadData = async () => {
      try {
        const doctorConsents = await fetchConsentsForDoctor(user.uid);
        const c = doctorConsents.find((c) => c.patientId === patientId && c.status === "approved");
        setConsent(c);
        if (c) {
          const recs = await fetchRecordsForPatient(patientId);
          const permitted = recs.filter((r) =>
            hasApprovedConsent(patientId, user.uid, r.recordType)
          );
          setRecords(permitted);
          return;
        }
      } catch (e) {
        console.error("Failed to load doctor patient records from API", e);
      }
      const cMock = getConsentsForDoctor(user.uid).find((c) => c.patientId === patientId && c.status === "approved");
      setConsent(cMock);
      if (cMock) {
        const all = getRecordsForPatient(patientId).filter((r) =>
          hasApprovedConsent(patientId, user.uid, r.recordType)
        );
        setRecords(all);
      }
    };
    loadData();
  }, [user, patientId]);

  const handleView = (record: MedicalRecord) => {
    if (user && patient) {
      logAccess({
        patientId,
        doctorId: user.uid,
        doctorName: user.fullName,
        recordId: record.recordId,
        recordName: record.fileName,
        action: "viewed",
        consentStatus: "approved",
      });
    }
    setSelected(record);
  };

  return (
    <DashboardShell role="doctor" title={`${patient?.fullName ?? "Patient"} — Records`}>
      {!consent ? (
        <EmptyState
          icon={<ShieldAlert className="h-8 w-8" />}
          title="No approved consent"
          description="You need patient-approved consent before viewing this patient's records."
          action={
            <Link href="/doctor/patients" className="text-sm font-medium text-teal-600 hover:underline">
              Back to patients
            </Link>
          }
        />
      ) : records.length === 0 ? (
        <EmptyState title="No permitted records" description="This patient has no records within your approved permissions." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {records.map((r) => (
            <MedicalRecordCard key={r.recordId} record={r} onView={handleView} />
          ))}
        </div>
      )}

      {selected && <RecordViewer record={selected} onClose={() => setSelected(null)} />}
    </DashboardShell>
  );
}
