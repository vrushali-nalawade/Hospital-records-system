import Link from "next/link";
import {
  ShieldCheck,
  FileStack,
  Bot,
  Users,
  Lock,
  UploadCloud,
  ScanEye,
  KeyRound,
} from "lucide-react";

const features = [
  {
    icon: FileStack,
    title: "One place for every record",
    desc: "Prescriptions, lab reports, scans, and discharge summaries — organized in a single secure locker.",
  },
  {
    icon: ScanEye,
    title: "AI record understanding",
    desc: "Ask questions about your own uploaded records in plain language, without a diagnosis attached.",
  },
  {
    icon: KeyRound,
    title: "You control access",
    desc: "Grant, restrict, or revoke a doctor's access to specific record types, any time.",
  },
  {
    icon: Lock,
    title: "Built with security in mind",
    desc: "Role-based access, consent-gated records, and a full access history for every view.",
  },
];

const steps = [
  {
    n: "01",
    title: "Create your locker",
    desc: "Register as a patient in minutes and set up your secure health record locker.",
  },
  {
    n: "02",
    title: "Upload your records",
    desc: "Add prescriptions, reports, and scans. OCR extracts key details automatically.",
  },
  {
    n: "03",
    title: "Understand & share",
    desc: "Ask the AI assistant about your records, and grant doctors access when you choose to.",
  },
];

export default function LandingPage() {
  return (
    <div className="flex-1 bg-white">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600 text-sm font-bold text-white">
              H
            </div>
            <span className="font-semibold text-slate-900">HealthLocker</span>
          </div>
          <nav className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex">
            <a href="#features" className="hover:text-slate-900">Features</a>
            <a href="#how-it-works" className="hover:text-slate-900">How it works</a>
            <a href="#privacy" className="hover:text-slate-900">Privacy</a>
            <a href="#ai" className="hover:text-slate-900">AI Understanding</a>
          </nav>
          <div className="flex items-center gap-3">
            <Link
              href="/doctor-login"
              className="hidden rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 sm:block"
            >
              Doctor Login
            </Link>
            <Link
              href="/login"
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Patient Login
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700"
            >
              Register
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <div className="grid items-center gap-12 md:grid-cols-2">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700">
              <ShieldCheck className="h-3.5 w-3.5" /> Unified Digital Health Record Locker
            </span>
            <h1 className="mt-5 text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">
              Securely organize, understand, and control access to your{" "}
              <span className="text-teal-600">digital health records</span>.
            </h1>
            <p className="mt-5 max-w-lg text-lg text-slate-600">
              One locker for prescriptions, reports, and scans — with AI that helps you
              understand what&apos;s in them, and consent tools that keep you in charge of
              who can see what.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/register"
                className="rounded-lg bg-teal-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-teal-700"
              >
                Create your locker
              </Link>
              <Link
                href="/doctor-login"
                className="rounded-lg border border-slate-300 px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                I&apos;m a doctor
              </Link>
            </div>
            <p className="mt-4 text-xs text-slate-400">
              Demo build — uses mock data when Firebase / AI / OCR credentials are not configured.
            </p>
          </div>
          <div className="relative">
            <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-teal-50 to-white p-6 shadow-sm">
              <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-700">
                <UploadCloud className="h-4 w-4 text-teal-600" /> Blood Report — Ready
              </div>
              <div className="space-y-2 text-sm">
                {[
                  ["Hemoglobin", "13.2 g/dL"],
                  ["WBC", "7,200 /µL"],
                  ["Platelets", "250,000 /µL"],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between rounded-lg bg-white px-3 py-2 shadow-sm">
                    <span className="text-slate-500">{k}</span>
                    <span className="font-medium text-slate-800">{v}</span>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-xs text-slate-400">Demo/Mock Extracted Information</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="border-t border-slate-100 bg-slate-50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-2xl font-bold text-slate-900">Everything your records need</h2>
          <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {features.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="rounded-xl border border-slate-200 bg-white p-6">
                <Icon className="h-6 w-6 text-teal-600" />
                <h3 className="mt-4 text-sm font-semibold text-slate-900">{title}</h3>
                <p className="mt-2 text-sm text-slate-500">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-2xl font-bold text-slate-900">How it works</h2>
          <div className="mt-10 grid gap-8 md:grid-cols-3">
            {steps.map((s) => (
              <div key={s.n} className="relative rounded-xl border border-slate-200 p-6">
                <span className="text-3xl font-bold text-teal-100">{s.n}</span>
                <h3 className="mt-3 text-sm font-semibold text-slate-900">{s.title}</h3>
                <p className="mt-2 text-sm text-slate-500">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Privacy */}
      <section id="privacy" className="border-t border-slate-100 bg-slate-900 py-20 text-white">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid items-center gap-10 md:grid-cols-2">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-teal-300">
                <Lock className="h-3.5 w-3.5" /> Privacy & Security
              </span>
              <h2 className="mt-4 text-2xl font-bold">Consent-gated, not open by default</h2>
              <p className="mt-3 max-w-md text-sm text-slate-300">
                Doctors only see records you&apos;ve approved. Every view is logged in your
                access history, and you can revoke access at any time.
              </p>
            </div>
            <ul className="space-y-3 text-sm text-slate-200">
              <li className="flex items-center gap-3 rounded-lg bg-white/5 p-3">
                <ShieldCheck className="h-4 w-4 text-teal-300" /> Role-based access for patients and doctors
              </li>
              <li className="flex items-center gap-3 rounded-lg bg-white/5 p-3">
                <Users className="h-4 w-4 text-teal-300" /> Explicit consent required before any doctor access
              </li>
              <li className="flex items-center gap-3 rounded-lg bg-white/5 p-3">
                <FileStack className="h-4 w-4 text-teal-300" /> Full access history for every record view
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* AI understanding */}
      <section id="ai" className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid items-center gap-10 md:grid-cols-2">
            <div className="order-2 md:order-1 rounded-xl border border-slate-200 bg-slate-50 p-6">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700">
                <Bot className="h-4 w-4 text-teal-600" /> AI Health Record Assistant
              </div>
              <div className="space-y-2">
                <div className="ml-auto max-w-[80%] rounded-lg rounded-tr-none bg-teal-600 px-3 py-2 text-sm text-white">
                  What does my latest blood report contain?
                </div>
                <div className="max-w-[85%] rounded-lg rounded-tl-none bg-white px-3 py-2 text-sm text-slate-700 shadow-sm">
                  Your latest blood report (10 Aug 2026) shows Hemoglobin 13.2 g/dL, WBC 7,200 /µL...
                </div>
              </div>
              <p className="mt-3 text-xs text-slate-400">
                AI-generated information is for record understanding only and is not medical advice.
              </p>
            </div>
            <div className="order-1 md:order-2">
              <span className="inline-flex items-center gap-2 rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-700">
                <Bot className="h-3.5 w-3.5" /> AI Record Understanding
              </span>
              <h2 className="mt-4 text-2xl font-bold text-slate-900">
                Understand your records, in plain language
              </h2>
              <p className="mt-3 max-w-md text-sm text-slate-600">
                Ask about a report and get a summary of what&apos;s already written in it. The
                assistant never diagnoses, prescribes, or replaces your doctor.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-slate-50 py-10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 text-sm text-slate-500 md:flex-row">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-teal-600 text-[10px] font-bold text-white">H</div>
            <span>HealthLocker — Academic demo project</span>
          </div>
          <p>No real patient data is used in this demo.</p>
        </div>
      </footer>
    </div>
  );
}
