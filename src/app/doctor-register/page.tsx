"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Stethoscope, ShieldCheck, CheckCircle2 } from "lucide-react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { registerDoctor, validateDoctorEmailDomain, ALLOWED_DOCTOR_DOMAINS } from "@/lib/services/auth-service";
import { useAuth } from "@/context/auth-context";
import { pushToast } from "@/components/ui/Toast";

interface DoctorFormState {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
  specialization: string;
  licenseId: string;
}

const initialState: DoctorFormState = {
  fullName: "",
  email: "",
  password: "",
  confirmPassword: "",
  specialization: "",
  licenseId: "",
};

export default function DoctorRegisterPage() {
  const router = useRouter();
  const { setUser } = useAuth();
  const [form, setForm] = useState<DoctorFormState>(initialState);
  const [errors, setErrors] = useState<Partial<Record<keyof DoctorFormState, string>>>({});
  const [loading, setLoading] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const update = (key: keyof DoctorFormState, value: string) => {
    setForm((f) => ({ ...f, [key]: value }));
    if (errors[key]) {
      setErrors((errs) => ({ ...errs, [key]: undefined }));
    }
  };

  const validate = () => {
    const errs: Partial<Record<keyof DoctorFormState, string>> = {};
    if (!form.fullName.trim()) errs.fullName = "Full name is required.";
    
    const domainCheck = validateDoctorEmailDomain(form.email);
    if (!domainCheck.valid) {
      errs.email = domainCheck.error || "Valid professional email is required.";
    }

    if (form.password.length < 6) {
      errs.password = "Password must be at least 6 characters.";
    }
    if (form.confirmPassword !== form.password) {
      errs.confirmPassword = "Passwords do not match.";
    }
    if (!form.specialization.trim()) {
      errs.specialization = "Specialization/Department is required.";
    }
    if (!form.licenseId.trim()) {
      errs.licenseId = "Medical license or Provider ID is required.";
    }

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError("");
    if (!validate()) return;
    setLoading(true);
    try {
      const user = await registerDoctor({
        fullName: form.fullName,
        email: form.email,
        password: form.password,
        specialization: form.specialization,
        licenseId: form.licenseId,
      });
      setUser(user);
      pushToast({
        type: "success",
        message: `Doctor account created successfully. Welcome, ${user.fullName}!`,
      });
      router.push("/doctor/dashboard");
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Doctor registration failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <Link href="/" className="mb-6 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600 text-sm font-bold text-white">H</div>
          <span className="font-semibold text-slate-900">HealthLocker</span>
        </Link>

        <div className="mb-6 flex items-center gap-2">
          <Stethoscope className="h-6 w-6 text-teal-600" />
          <div>
            <h1 className="text-xl font-semibold text-slate-900">Doctor Registration</h1>
            <p className="text-xs text-slate-500">Create your verified healthcare provider profile</p>
          </div>
        </div>

        {/* Professional Domain Notice */}
        <div className="mb-5 rounded-xl border border-teal-100 bg-teal-50/60 p-3.5 text-xs text-teal-800">
          <div className="flex items-center gap-1.5 font-semibold text-teal-900 mb-1">
            <ShieldCheck className="h-4 w-4 text-teal-600" />
            <span>Professional Email Domain Required</span>
          </div>
          <p className="text-teal-700">
            For security and HIPAA compliance, doctor accounts must use approved hospital or institutional domains:
          </p>
          <div className="mt-1.5 flex flex-wrap gap-1.5 font-mono text-[11px]">
            {ALLOWED_DOCTOR_DOMAINS.map((d) => (
              <span key={d} className="rounded bg-teal-100/80 px-1.5 py-0.5 text-teal-900">
                @{d}
              </span>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            id="doctor-fullname"
            label="Full Name & Title"
            placeholder="Dr. Sarah Jenkins"
            value={form.fullName}
            onChange={(e) => update("fullName", e.target.value)}
            error={errors.fullName}
          />
          <Input
            id="doctor-email"
            label="Professional Email"
            type="email"
            placeholder="s.jenkins@hospital.org"
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
            error={errors.email}
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              id="doctor-specialization"
              label="Specialization"
              placeholder="e.g. Cardiology"
              value={form.specialization}
              onChange={(e) => update("specialization", e.target.value)}
              error={errors.specialization}
            />
            <Input
              id="doctor-license"
              label="License / Provider ID"
              placeholder="e.g. MED-84729"
              value={form.licenseId}
              onChange={(e) => update("licenseId", e.target.value)}
              error={errors.licenseId}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Input
              id="doctor-password"
              label="Password"
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              error={errors.password}
            />
            <Input
              id="doctor-confirm-password"
              label="Confirm Password"
              type="password"
              placeholder="••••••••"
              value={form.confirmPassword}
              onChange={(e) => update("confirmPassword", e.target.value)}
              error={errors.confirmPassword}
            />
          </div>

          {submitError && (
            <div className="rounded-lg bg-red-50 p-3 text-xs text-red-700">
              {submitError}
            </div>
          )}

          <Button type="submit" className="w-full mt-2" loading={loading}>
            Register Doctor Account
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Already registered as a doctor?{" "}
          <Link href="/doctor-login" className="font-medium text-teal-600 hover:underline">
            Log in here
          </Link>
        </p>
        <p className="mt-2 text-center text-xs text-slate-400">
          Are you a patient?{" "}
          <Link href="/register" className="font-medium text-teal-600 hover:underline">
            Patient Registration
          </Link>
        </p>
      </div>
    </div>
  );
}
