"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Users, ClipboardCheck, ShieldCheck, Activity } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import { useAuth } from "@/context/auth-context";
import { getConsentsForDoctor } from "@/lib/services/consent-service";
import { MOCK_PATIENTS } from "@/lib/mock/mock-data";
import type { Consent } from "@/types";

function StatCard({ label, value, icon: Icon }: { label: string; value: number; icon: typeof Users }) {
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

export default function DoctorDashboardPage() {
  const { user } = useAuth();
  const [consents, setConsents] = useState<Consent[]>([]);

  useEffect(() => {
    if (user) setConsents(getConsentsForDoctor(user.uid));
  }, [user]);

  const pending = consents.filter((c) => c.status === "pending").length;
  const approved = consents.filter((c) => c.status === "approved").length;

  return (
    <DashboardShell role="doctor" title="Dashboard">
      <h2 className="mb-1 text-lg font-semibold text-slate-900">
        Welcome, {user?.fullName}
      </h2>
      <p className="mb-6 text-sm text-slate-500">Here&apos;s your patient access overview.</p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Patients" value={MOCK_PATIENTS.length} icon={Users} />
        <StatCard label="Pending Access Requests" value={pending} icon={ClipboardCheck} />
        <StatCard label="Approved Access" value={approved} icon={ShieldCheck} />
        <StatCard label="Recent Activity" value={consents.length} icon={Activity} />
      </div>

      <Card className="mt-8 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-900">Your Patients</h3>
          <Link href="/doctor/patients" className="text-xs font-medium text-teal-600 hover:underline">
            View all
          </Link>
        </div>
        <div className="space-y-3">
          {MOCK_PATIENTS.map((p) => (
            <div key={p.uid} className="flex items-center justify-between rounded-lg border border-slate-100 px-4 py-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-teal-100 text-sm font-semibold text-teal-700">
                  {p.fullName.charAt(0)}
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-800">{p.fullName}</p>
                  <p className="text-xs text-slate-400">{p.email}</p>
                </div>
              </div>
              <Link
                href={`/doctor/patients/${p.uid}/records`}
                className="text-xs font-medium text-teal-600 hover:underline"
              >
                View records
              </Link>
            </div>
          ))}
        </div>
      </Card>
    </DashboardShell>
  );
}
