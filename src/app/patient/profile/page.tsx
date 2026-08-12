"use client";

import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import { useAuth } from "@/context/auth-context";

export default function PatientProfilePage() {
  const { user } = useAuth();
  if (!user || user.role !== "patient") return null;

  const fields: [string, string][] = [
    ["Full Name", user.fullName],
    ["Email", user.email],
    ["Phone Number", user.phone || "—"],
    ["Date of Birth", user.dateOfBirth || "—"],
    ["Gender", user.gender],
    ["Account Created", new Date(user.createdAt).toLocaleDateString("en-IN")],
  ];

  return (
    <DashboardShell role="patient" title="Profile">
      <Card className="max-w-lg p-6">
        <div className="mb-6 flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-teal-600 text-lg font-semibold text-white">
            {user.fullName.charAt(0)}
          </div>
          <div>
            <p className="font-semibold text-slate-900">{user.fullName}</p>
            <p className="text-sm text-slate-500">{user.email}</p>
          </div>
        </div>
        <dl className="divide-y divide-slate-100">
          {fields.map(([label, value]) => (
            <div key={label} className="flex items-center justify-between py-3 text-sm">
              <dt className="text-slate-500">{label}</dt>
              <dd className="font-medium capitalize text-slate-800">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>
    </DashboardShell>
  );
}
