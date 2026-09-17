"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import Loading from "@/components/ui/Loading";
import { useAuth } from "@/context/auth-context";

export default function DashboardShell({
  role,
  title,
  children,
}: {
  role: "patient" | "doctor";
  title: string;
  children: ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace(role === "patient" ? "/login" : "/doctor-login");
      return;
    }
    if (user.role !== role) {
      router.replace(user.role === "patient" ? "/patient/dashboard" : "/doctor/dashboard");
    }
  }, [loading, user, role, router]);

  if (loading || !user || user.role !== role) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loading label="Checking access..." />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar role={role} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar title={title} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
