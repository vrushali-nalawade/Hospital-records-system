"use client";

import { useEffect, useState } from "react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import { useAuth } from "@/context/auth-context";
import { getConsentsForPatient, updateConsentStatus } from "@/lib/services/consent-service";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import type { Consent } from "@/types";
import { ShieldCheck, ShieldX } from "lucide-react";
import { pushToast } from "@/components/ui/Toast";

function ConsentCard({ consent, onAction }: { consent: Consent; onAction: (id: string, status: Consent["status"]) => void }) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-900">{consent.doctorName}</p>
          <p className="text-xs text-slate-400">
            Requested {new Date(consent.createdAt).toLocaleDateString("en-IN")}
          </p>
        </div>
        <Badge tone={consent.status}>{consent.status}</Badge>
      </div>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {consent.permissions.map((p) => (
          <span key={p} className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">
            {recordTypeLabel[p]}
          </span>
        ))}
      </div>
      {consent.expiresAt && (
        <p className="mt-2 text-xs text-slate-400">
          Expires {new Date(consent.expiresAt).toLocaleDateString("en-IN")}
        </p>
      )}
      <div className="mt-4 flex gap-2">
        {consent.status === "pending" && (
          <>
            <Button size="sm" onClick={() => onAction(consent.consentId, "approved")}>
              Grant access
            </Button>
            <Button size="sm" variant="outline" onClick={() => onAction(consent.consentId, "rejected")}>
              Reject
            </Button>
          </>
        )}
        {consent.status === "approved" && (
          <Button size="sm" variant="danger" onClick={() => onAction(consent.consentId, "revoked")}>
            Revoke access
          </Button>
        )}
      </div>
    </Card>
  );
}

export default function ConsentManagementPage() {
  const { user } = useAuth();
  const [consents, setConsents] = useState<Consent[]>([]);

  useEffect(() => {
    if (user) setConsents(getConsentsForPatient(user.uid));
  }, [user]);

  const handleAction = (id: string, status: Consent["status"]) => {
    const updated = updateConsentStatus(id, status);
    setConsents(user ? updated.filter((c) => c.patientId === user.uid) : updated);
    pushToast({
      type: status === "approved" ? "success" : "info",
      message: `Consent ${status}.`,
    });
  };

  const pending = consents.filter((c) => c.status === "pending");
  const active = consents.filter((c) => c.status === "approved");
  const others = consents.filter((c) => !["pending", "approved"].includes(c.status));

  return (
    <DashboardShell role="patient" title="Consent Management">
      <div className="space-y-8">
        <section>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
            <ShieldCheck className="h-4 w-4 text-amber-500" /> Pending Requests
          </h3>
          {pending.length === 0 ? (
            <EmptyState title="No pending requests" description="New doctor access requests will appear here." />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {pending.map((c) => <ConsentCard key={c.consentId} consent={c} onAction={handleAction} />)}
            </div>
          )}
        </section>

        <section>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
            <ShieldCheck className="h-4 w-4 text-emerald-500" /> Active Consents
          </h3>
          {active.length === 0 ? (
            <EmptyState title="No active consents" description="Approved doctor access will appear here." />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {active.map((c) => <ConsentCard key={c.consentId} consent={c} onAction={handleAction} />)}
            </div>
          )}
        </section>

        {others.length > 0 && (
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
              <ShieldX className="h-4 w-4 text-slate-400" /> Past Consents
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {others.map((c) => <ConsentCard key={c.consentId} consent={c} onAction={handleAction} />)}
            </div>
          </section>
        )}
      </div>
    </DashboardShell>
  );
}
