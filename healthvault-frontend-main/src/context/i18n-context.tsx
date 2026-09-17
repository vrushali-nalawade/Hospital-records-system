"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import en from "@/locales/en";
import hi from "@/locales/hi";
import mr from "@/locales/mr";
import type { Locale } from "@/types";

const dictionaries: Record<Locale, typeof en> = { en, hi, mr };

interface I18nContextValue {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: keyof typeof en) => string;
}

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const stored = localStorage.getItem("hrl_locale") as Locale | null;
    if (stored && dictionaries[stored]) setLocaleState(stored);
  }, []);

  const setLocale = (l: Locale) => {
    setLocaleState(l);
    localStorage.setItem("hrl_locale", l);
  };

  const t = (key: keyof typeof en) => dictionaries[locale][key] ?? dictionaries.en[key];

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
