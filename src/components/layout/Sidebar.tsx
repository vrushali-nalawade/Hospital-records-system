"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  LayoutDashboard,
  FileText,
  Upload,
  History,
  ShieldCheck,
  ListChecks,
  Bot,
  User,
  LogOut,
  Users,
  ClipboardCheck,
} from "lucide-react";
import { useAuth } from "@/context/auth-context";
import { useI18n } from "@/context/i18n-context";

const patientLinks = [
  { href: "/patient/dashboard", label: "dashboard", icon: LayoutDashboard },
  { href: "/patient/records", label: "medicalRecords", icon: FileText },
  { href: "/patient/upload", label: "uploadRecord", icon: Upload },
  { href: "/patient/history", label: "medicalHistory", icon: History },
  { href: "/patient/ai-assistant", label: "aiAssistant", icon: Bot },
  { href: "/patient/profile", label: "profile", icon: User },
] as const;

const doctorLinks = [
  { href: "/doctor/dashboard", label: "dashboard", icon: LayoutDashboard },
  { href: "/doctor/patients", label: "patients", icon: Users },
  { href: "/doctor/access-requests", label: "accessRequests", icon: ClipboardCheck },
  { href: "/doctor/profile", label: "profile", icon: User },
] as const;

export default function Sidebar({ role }: { role: "patient" | "doctor" }) {
  const pathname = usePathname();
  const { logout } = useAuth();
  const { t } = useI18n();
  const links = role === "patient" ? patientLinks : doctorLinks;

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center gap-2 border-b border-slate-200 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600 text-white font-bold">
          H
        </div>
        <span className="font-semibold text-slate-800">HealthLocker</span>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname?.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-teal-50 text-teal-700"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {t(label as never)}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-slate-200 p-3">
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-red-50 hover:text-red-600"
        >
          <LogOut className="h-4 w-4" />
          {t("logout")}
        </button>
      </div>
    </aside>
  );
}
