"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { HeartPulse } from "lucide-react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { loginPatient } from "@/lib/services/auth-service";
import { useAuth } from "@/context/auth-context";
import { useI18n } from "@/context/i18n-context";
import { DEMO_CREDENTIALS, IS_DEMO_MODE } from "@/lib/demo-mode";
import { pushToast } from "@/components/ui/Toast";

export default function PatientLoginPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const { t } = useI18n();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!email || !password) {
      setError("Please enter both email and password.");
      return;
    }
    setLoading(true);
    try {
      const user = await loginPatient(email, password);
      setUser(user);
      pushToast({ type: "success", message: `Welcome back, ${user.fullName}` });
      router.push("/patient/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <Link href="/" className="mb-6 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600 text-sm font-bold text-white">H</div>
          <span className="font-semibold text-slate-900">HealthLocker</span>
        </Link>
        <div className="mb-6 flex items-center gap-2">
          <HeartPulse className="h-5 w-5 text-teal-600" />
          <h1 className="text-xl font-semibold text-slate-900">{t("patientLogin")}</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            id="email"
            label={t("email")}
            type="email"
            placeholder="patient@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            id="password"
            label={t("password")}
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex items-center justify-between text-sm">
            <Link href="/forgot-password" className="text-teal-600 hover:underline">
              Forgot password?
            </Link>
          </div>
          <Button type="submit" className="w-full" loading={loading}>
            {t("login")}
          </Button>
        </form>

        {IS_DEMO_MODE && (
          <div className="mt-5 rounded-lg bg-purple-50 p-3 text-xs text-purple-700">
            <p className="font-semibold">Demo credentials</p>
            <p>Email: {DEMO_CREDENTIALS.patient.email}</p>
            <p>Password: {DEMO_CREDENTIALS.patient.password}</p>
          </div>
        )}

        <p className="mt-6 text-center text-sm text-slate-500">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-medium text-teal-600 hover:underline">
            {t("register")}
          </Link>
        </p>
        <p className="mt-2 text-center text-sm text-slate-500">
          Are you a doctor?{" "}
          <Link href="/doctor-login" className="font-medium text-teal-600 hover:underline">
            {t("doctorLogin")}
          </Link>
        </p>
      </div>
    </div>
  );
}
