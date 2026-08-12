"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { UploadCloud, CheckCircle2, Circle, Loader2, FileWarning } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import { useAuth } from "@/context/auth-context";
import { uploadRecordDemo } from "@/lib/services/records-service";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import type { ProcessingStatus, RecordType } from "@/types";
import { pushToast } from "@/components/ui/Toast";

const RECORD_TYPES: RecordType[] = [
  "prescription",
  "blood_report",
  "lab_report",
  "medical_image",
  "doctor_note",
  "discharge_summary",
];

const ALLOWED_TYPES = ["application/pdf", "image/jpeg", "image/jpg", "image/png"];
const MAX_SIZE_MB = 10;

const STAGES: { key: ProcessingStatus; label: string }[] = [
  { key: "uploading", label: "Uploading" },
  { key: "processing", label: "Processing" },
  { key: "ocr_completed", label: "OCR Completed" },
  { key: "extracted", label: "Medical Information Extracted" },
  { key: "ready", label: "Ready" },
];

export default function UploadRecordPage() {
  const { user } = useAuth();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [recordType, setRecordType] = useState<RecordType>("blood_report");
  const [error, setError] = useState("");
  const [stage, setStage] = useState<ProcessingStatus | null>(null);
  const [done, setDone] = useState(false);

  const validateFile = (f: File): string | null => {
    if (!ALLOWED_TYPES.includes(f.type)) return "Unsupported file type. Please upload a PDF, JPG, JPEG, or PNG.";
    if (f.size === 0) return "The selected file is empty.";
    if (f.size > MAX_SIZE_MB * 1024 * 1024) return `File is too large. Max size is ${MAX_SIZE_MB}MB.`;
    return null;
  };

  const handleFile = (f: File | null) => {
    setError("");
    setDone(false);
    setStage(null);
    if (!f) return;
    const err = validateFile(f);
    if (err) {
      setError(err);
      setFile(null);
      return;
    }
    setFile(f);
  };

  const handleUpload = async () => {
    if (!file || !user) return;
    setError("");
    try {
      await uploadRecordDemo(user.uid, file, recordType, setStage);
      setDone(true);
      pushToast({ type: "success", message: "Record uploaded and processed." });
    } catch {
      setError("Upload failed. Please try again.");
      setStage(null);
    }
  };

  const stageIndex = stage ? STAGES.findIndex((s) => s.key === stage) : -1;

  return (
    <DashboardShell role="patient" title="Upload Record">
      <div className="mx-auto max-w-2xl">
        <Card className="p-6">
          <div className="mb-5">
            <label className="mb-1.5 block text-sm font-medium text-slate-700">Record Type</label>
            <select
              value={recordType}
              onChange={(e) => setRecordType(e.target.value as RecordType)}
              disabled={!!stage}
              className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-50"
            >
              {RECORD_TYPES.map((t) => (
                <option key={t} value={t}>{recordTypeLabel[t]}</option>
              ))}
            </select>
          </div>

          {!file && (
            <div
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                handleFile(e.dataTransfer.files?.[0] ?? null);
              }}
              className="flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-300 bg-slate-50 px-6 py-12 text-center hover:bg-slate-100"
            >
              <UploadCloud className="mb-3 h-8 w-8 text-slate-400" />
              <p className="text-sm font-medium text-slate-700">Click to select or drag & drop a file</p>
              <p className="mt-1 text-xs text-slate-400">PDF, JPG, JPEG, PNG — up to {MAX_SIZE_MB}MB</p>
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
              />
            </div>
          )}

          {error && (
            <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              <FileWarning className="h-4 w-4 shrink-0" /> {error}
            </div>
          )}

          {file && (
            <div className="mt-2">
              <div className="flex items-center justify-between rounded-lg border border-slate-200 px-4 py-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">{file.name}</p>
                  <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(0)} KB</p>
                </div>
                {!stage && (
                  <button
                    onClick={() => setFile(null)}
                    className="text-xs font-medium text-slate-500 hover:text-red-600"
                  >
                    Remove
                  </button>
                )}
              </div>

              {stage && (
                <div className="mt-5 space-y-3">
                  {STAGES.map((s, i) => {
                    const complete = i < stageIndex || (i === stageIndex && stage === "ready");
                    const active = i === stageIndex && stage !== "ready";
                    return (
                      <div key={s.key} className="flex items-center gap-3 text-sm">
                        {complete ? (
                          <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                        ) : active ? (
                          <Loader2 className="h-5 w-5 animate-spin text-teal-600" />
                        ) : (
                          <Circle className="h-5 w-5 text-slate-300" />
                        )}
                        <span className={complete || active ? "text-slate-800" : "text-slate-400"}>
                          {s.label}
                          {complete && " ✓"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {!stage && !done && (
                <Button className="mt-5 w-full" onClick={handleUpload}>
                  Upload record
                </Button>
              )}

              {done && (
                <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                  <Button className="flex-1" onClick={() => router.push("/patient/records")}>
                    View in Medical Records
                  </Button>
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => {
                      setFile(null);
                      setStage(null);
                      setDone(false);
                    }}
                  >
                    Upload another
                  </Button>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </DashboardShell>
  );
}
