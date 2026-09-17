"use client";

import { useState } from "react";
import Link from "next/link";
import { HeartPulse } from "lucide-react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import { forgotPassword } from "@/lib/services/auth-service";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setError("Please enter your email.");
      return;
    }
    setLoading(true);
    try {
      await forgotPassword(trimmedEmail);
      setSent(true);
    } catch (err: any) {
      const msg = err?.message || "";
      if (msg.includes("user-not-found") || msg.includes("auth/user-not-found")) {
        setError("No account found with this email address.");
      } else if (msg.includes("invalid-email") || msg.includes("auth/invalid-email")) {
        setError("Please enter a valid email address format.");
      } else if (msg.includes("too-many-requests") || msg.includes("auth/too-many-requests")) {
        setError("Too many password reset requests. Please wait a few minutes and try again.");
      } else {
        setError(msg || "Could not send reset email. Please try again.");
      }
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
        <div className="mb-4 flex items-center gap-2">
          <HeartPulse className="h-5 w-5 text-teal-600" />
          <h1 className="text-xl font-semibold text-slate-900">Reset your password</h1>
        </div>
        <p className="mb-6 text-sm text-slate-500">
          Enter your account email and we&apos;ll send you a reset link.
        </p>

        {sent ? (
          <div className="space-y-4">
            <div className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-700">
              If an account exists for <strong>{email}</strong>, a password reset link has been sent to your inbox.
            </div>
            <p className="text-xs text-slate-500">
              Please check your spam or junk folder if you do not receive the email within a few minutes.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              placeholder="patient@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" className="w-full" loading={loading}>
              Send reset link
            </Button>
          </form>
        )}

        <p className="mt-6 text-center text-sm text-slate-500">
          <Link href="/login" className="font-medium text-teal-600 hover:underline">
            Back to login
          </Link>
        </p>
      </div>
    </div>
  );
}
