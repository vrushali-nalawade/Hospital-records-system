import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/auth-context";
import { I18nProvider } from "@/context/i18n-context";
import ToastHost from "@/components/ui/Toast";

export const metadata: Metadata = {
  title: "HealthLocker — Unified Digital Health Record Locker",
  description:
    "Securely organize, understand, and control access to your digital health records.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-slate-50 font-sans">
        <I18nProvider>
          <AuthProvider>
            {children}
            <ToastHost />
          </AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
