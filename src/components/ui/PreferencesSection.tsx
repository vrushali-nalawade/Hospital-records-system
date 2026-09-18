"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/context/i18n-context";
import { pushToast } from "@/components/ui/Toast";
import type { Locale } from "@/types";

export default function PreferencesSection() {
  const { locale, setLocale, t } = useI18n();
  const [theme, setThemeState] = useState<"light" | "dark" | "system">("light");
  const [notifications, setNotificationsState] = useState<boolean>(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const storedTheme = (localStorage.getItem("hrl_theme") as "light" | "dark" | "system") || "light";
      const storedNotifs = localStorage.getItem("hrl_notifications") !== "false";
      setThemeState(storedTheme);
      setNotificationsState(storedNotifs);
      applyTheme(storedTheme);
    }
  }, []);

  const applyTheme = (th: "light" | "dark" | "system") => {
    const isDark = th === "dark" || (th === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
    if (isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  const handleThemeChange = (th: "light" | "dark" | "system") => {
    setThemeState(th);
    localStorage.setItem("hrl_theme", th);
    applyTheme(th);
    pushToast({ type: "info", message: `Theme changed to ${th}` });
  };

  const handleNotificationsToggle = (enabled: boolean) => {
    setNotificationsState(enabled);
    localStorage.setItem("hrl_notifications", String(enabled));
    pushToast({
      type: "info",
      message: `Push notifications ${enabled ? "enabled" : "disabled"}`,
    });
  };

  return (
    <div className="mt-6 border-t border-slate-200 pt-6">
      <h3 className="mb-4 text-base font-semibold text-slate-900">{t("preferences")}</h3>
      <div className="space-y-4 text-sm">
        {/* Language Selection */}
        <div className="flex items-center justify-between">
          <label className="font-medium text-slate-700">{t("language")}</label>
          <select
            value={locale}
            onChange={(e) => {
              const l = e.target.value as Locale;
              setLocale(l);
              pushToast({ type: "info", message: `Language updated to ${l.toUpperCase()}` });
            }}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="en">English</option>
            <option value="hi">हिन्दी (Hindi)</option>
            <option value="mr">मराठी (Marathi)</option>
          </select>
        </div>

        {/* Theme Selection */}
        <div className="flex items-center justify-between">
          <label className="font-medium text-slate-700">{t("theme")}</label>
          <select
            value={theme}
            onChange={(e) => handleThemeChange(e.target.value as "light" | "dark" | "system")}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="light">{t("lightTheme")}</option>
            <option value="dark">{t("darkTheme")}</option>
            <option value="system">{t("systemTheme")}</option>
          </select>
        </div>

        {/* Notifications Toggle */}
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-slate-700">{t("notifications")}</p>
          </div>
          <button
            type="button"
            onClick={() => handleNotificationsToggle(!notifications)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
              notifications ? "bg-teal-600" : "bg-slate-300"
            }`}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                notifications ? "translate-x-5" : "translate-x-0"
              }`}
            />
          </button>
        </div>
      </div>
    </div>
  );
}
