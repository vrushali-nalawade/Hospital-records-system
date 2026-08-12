"use client";

import { Bell, Globe } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/context/auth-context";
import { useI18n } from "@/context/i18n-context";
import { IS_DEMO_MODE } from "@/lib/demo-mode";

export default function Topbar({ title }: { title: string }) {
  const { user } = useAuth();
  const { locale, setLocale } = useI18n();
  const [open, setOpen] = useState(false);

  const languages: { code: "en" | "hi" | "mr"; label: string }[] = [
    { code: "en", label: "English" },
    { code: "hi", label: "हिन्दी" },
    { code: "mr", label: "मराठी" },
  ];

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
        {IS_DEMO_MODE && (
          <span className="text-xs font-medium text-purple-600">Demo Mode — mock data</span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <div className="relative">
          <button
            onClick={() => setOpen((o) => !o)}
            className="flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
          >
            <Globe className="h-4 w-4" />
            {languages.find((l) => l.code === locale)?.label}
          </button>
          {open && (
            <div className="absolute right-0 z-10 mt-1 w-32 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
              {languages.map((l) => (
                <button
                  key={l.code}
                  onClick={() => {
                    setLocale(l.code);
                    setOpen(false);
                  }}
                  className="block w-full px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
                >
                  {l.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <button className="rounded-lg p-2 text-slate-500 hover:bg-slate-50">
          <Bell className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-1.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-teal-600 text-xs font-semibold text-white">
            {user?.fullName?.charAt(0) ?? "U"}
          </div>
          <span className="text-sm font-medium text-slate-700">{user?.fullName}</span>
        </div>
      </div>
    </header>
  );
}
