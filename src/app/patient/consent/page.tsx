"use client";

import { useEffect, useState } from "react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import { useAuth } from "@/context/auth-context";
import { useI18n } from "@/context/i18n-context";
import { getConsentsForPatient, fetchConsentsForPatient, updateConsentStatus } from "@/lib/services/consent-service";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import type { Consent } from "@/types";
import { ShieldCheck, ShieldX, AlertTriangle } from "lucide-react";
import { pushToast } from "@/components/ui/Toast";

function ConsentCard({
  consent,
  onAction,
  onRequestRevoke,
}: {
  consent: Consent;
  onAction: (id: string, status: Consent["status"]) => void;
  onRequestRevoke: (consent: Consent) => void;
}) {
  const { t } = useI18n();

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
              {t("grantConsent")}
            </Button>
            <Button size="sm" variant="outline" onClick={() => onAction(consent.consentId, "rejected")}>
              Reject
            </Button>
          </>
        )}
        {consent.status === "approved" && (
          <Button size="sm" variant="danger" onClick={() => onRequestRevoke(consent)}>
            {t("revokeAccess")}
          </Button>
        )}
      </div>
    </Card>
  );
}

export default function ConsentManagementPage() {
  const { user } = useAuth();
  const { t } = useI18n();
  const [consents, setConsents] = useState<Consent[]>([]);
  const [revokeTarget, setRevokeTarget] = useState<Consent | null>(null);

  useEffect(() => {
    if (!user) return;
    const loadData = async () => {
      try {
        const cons = await fetchConsentsForPatient(user.uid);
        setConsents(cons);
      } catch (e) {
        console.error("Failed to load consents from API", e);
        setConsents(getConsentsForPatient(user.uid));
      }
    };
    loadData();
  }, [user]);

  const handleAction = async (id: string, status: Consent["status"]) => {
    const updated = updateConsentStatus(id, status);
    setConsents(user ? updated.filter((c) => c.patientId === user.uid) : updated);
    pushToast({
      type: status === "approved" ? "success" : "info",
      message: `Consent ${status}.`,
    });
    if (user) {
      try {
        const cons = await fetchConsentsForPatient(user.uid);
        setConsents(cons);
      } catch (e) {
        console.error("Failed to refresh consents after action", e);
      }
    }
  };

  const confirmRevocation = () => {
    if (!revokeTarget) return;
    handleAction(revokeTarget.consentId, "revoked");
    setRevokeTarget(null);
  };

  const pending = consents.filter((c) => c.status === "pending");
  const active = consents.filter((c) => c.status === "approved");
  const others = consents.filter((c) => !["pending", "approved"].includes(c.status));

  return (
    <DashboardShell role="patient" title={t("consentManagement")}>
      <div className="space-y-8">
        <section>
          <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
            <ShieldCheck className="h-4 w-4 text-amber-500" /> Pending Requests
          </h3>
          {pending.length === 0 ? (
            <EmptyState title="No pending requests" description="New doctor access requests will appear here." />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {pending.map((c) => (
                <ConsentCard key={c.consentId} consent={c} onAction={handleAction} onRequestRevoke={setRevokeTarget} />
              ))}
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
              {active.map((c) => (
                <ConsentCard key={c.consentId} consent={c} onAction={handleAction} onRequestRevoke={setRevokeTarget} />
              ))}
            </div>
          )}
        </section>

        {others.length > 0 && (
          <section>
            <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
              <ShieldX className="h-4 w-4 text-slate-400" /> Past Consents
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {others.map((c) => (
                <ConsentCard key={c.consentId} consent={c} onAction={handleAction} onRequestRevoke={setRevokeTarget} />
              ))}
            </div>
          </section>
        )}
      </div>

      {/* Revocation Confirmation Modal */}
      {revokeTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
          <Card className="max-w-md p-6">
            <div className="flex items-center gap-3 text-red-600">
              <AlertTriangle className="h-6 w-6 shrink-0" />
              <h3 className="text-lg font-semibold text-slate-900">{t("confirmRevokeTitle")}</h3>
            </div>
            <p className="mt-3 text-sm text-slate-600">{t("confirmRevokeText")}</p>
            <div className="mt-6 flex justify-end gap-3">
              <Button variant="outline" onClick={() => setRevokeTarget(null)}>
                {t("cancel")}
              </Button>
              <Button variant="danger" onClick={confirmRevocation}>
                {t("revokeAccess")}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </DashboardShell>
  );
}
