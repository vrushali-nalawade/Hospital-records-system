"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { UploadCloud, CheckCircle2, Circle, Loader2, FileWarning, RefreshCw } from "lucide-react";
import DashboardShell from "@/components/layout/DashboardShell";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import { useAuth } from "@/context/auth-context";
import { useI18n } from "@/context/i18n-context";
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

const STAGES: { key: ProcessingStatus; labelKey: string }[] = [
  { key: "uploading", labelKey: "uploading" },
  { key: "processing", labelKey: "processingOcr" },
  { key: "ocr_completed", labelKey: "ocrCompleted" },
  { key: "extracted", labelKey: "extractingInfo" },
  { key: "ready", labelKey: "ready" },
];

export default function UploadRecordPage() {
  const { user } = useAuth();
  const { t } = useI18n();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [recordType, setRecordType] = useState<RecordType>("blood_report");
  const [error, setError] = useState("");
  const [stage, setStage] = useState<ProcessingStatus | null>(null);
  const [done, setDone] = useState(false);

  const validateFile = (f: File): string | null => {
    const ext = f.name.substring(f.name.lastIndexOf(".")).toLowerCase();
    const allowedExts = [".pdf", ".jpg", ".jpeg", ".png"];
    if (!ALLOWED_TYPES.includes(f.type) && !allowedExts.includes(ext)) {
      return "Unsupported file format. Please upload a PDF, JPG, JPEG, or PNG document.";
    }
    if (f.size === 0) return "The selected file is empty.";
    if (f.size > MAX_SIZE_MB * 1024 * 1024) return `File exceeds maximum allowed size of ${MAX_SIZE_MB}MB.`;
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
      pushToast({ type: "success", message: t("uploadSuccess") });
    } catch (err: any) {
      setError(err?.message || t("uploadFailed"));
      setStage(null);
    }
  };

  const stageIndex = stage ? STAGES.findIndex((s) => s.key === stage) : -1;

  return (
    <DashboardShell role="patient" title={t("uploadRecord")}>
      <div className="mx-auto max-w-2xl">
        <Card className="p-6">
          <div className="mb-5">
            <label className="mb-1.5 block text-sm font-medium text-slate-700">{t("recordType")}</label>
            <select
              value={recordType}
              onChange={(e) => setRecordType(e.target.value as RecordType)}
              disabled={!!stage}
              className="w-full rounded-lg border border-slate-300 px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:bg-slate-50"
            >
              {RECORD_TYPES.map((typeKey) => (
                <option key={typeKey} value={typeKey}>
                  {recordTypeLabel[typeKey]}
                </option>
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
              <p className="text-sm font-medium text-slate-700">{t("clickOrDragFile")}</p>
              <p className="mt-1 text-xs text-slate-400">{t("supportedFormats")}</p>
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
            <div className="mt-3 flex flex-col gap-2 rounded-lg bg-red-50 p-4 text-sm text-red-700">
              <div className="flex items-center gap-2 font-medium">
                <FileWarning className="h-4 w-4 shrink-0" /> {error}
              </div>
              <Button
                variant="outline"
                size="sm"
                className="mt-1 self-start text-xs border-red-200 text-red-700 hover:bg-red-100"
                onClick={handleUpload}
              >
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> {t("retry")}
              </Button>
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
                    {t("remove")}
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
                        <span className={complete || active ? "font-medium text-slate-800" : "text-slate-400"}>
                          {t(s.labelKey as never)}
                          {complete && " ✓"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}

              {!stage && !done && (
                <Button className="mt-5 w-full" onClick={handleUpload}>
                  {t("uploadRecord")}
                </Button>
              )}

              {done && (
                <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                  <Button className="flex-1" onClick={() => router.push("/patient/records")}>
                    {t("viewInRecords")}
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
                    {t("uploadAnother")}
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
