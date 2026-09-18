"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { X, FileWarning, ExternalLink, Lock, Bot, Trash2 } from "lucide-react";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import { fetchDocumentSignedUrl, deleteMedicalRecord } from "@/lib/services/records-service";
import { API_BASE_URL } from "@/lib/api-config";
import { pushToast } from "@/components/ui/Toast";
import type { MedicalRecord } from "@/types";

export default function RecordViewer({
  record,
  onClose,
  onDelete,
}: {
  record: MedicalRecord;
  onClose: () => void;
  onDelete?: (recordId: string) => void;
}) {
  const router = useRouter();
  const [loadingUrl, setLoadingUrl] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleOpenSecureDocument = async () => {
    setLoadingUrl(true);
    try {
      // 1. If demo file URL or direct static link exists, open it directly
      if (record.fileUrl && !record.fileUrl.startsWith("http") && !record.fileUrl.includes("/documents/")) {
        window.open(record.fileUrl, "_blank", "noopener,noreferrer");
        return;
      }

      // 2. Fetch authenticated document blob stream from backend
      try {
        const headers = await getAuthHeaders();
        const res = await fetch(`${API_BASE_URL}/documents/${record.recordId}`, {
          headers
        });

        if (res.ok) {
          const blob = await res.blob();
          if (blob.size > 100) {
            const blobUrl = URL.createObjectURL(blob);
            window.open(blobUrl, "_blank", "noopener,noreferrer");
            return;
          }
        }
      } catch (streamErr) {
        console.warn("Stream fetch notice:", streamErr);
      }

      // 3. Render secure interactive clinical preview tab
      const docHtml = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>${record.fileName} - Medical Record</title>
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8fafc; margin: 0; padding: 40px 20px; color: #1e293b; }
            .container { max-width: 680px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
            .badge { display: inline-block; padding: 4px 12px; background: #ccfbf1; color: #0f766e; border-radius: 9999px; font-size: 12px; font-weight: 600; text-transform: uppercase; margin-bottom: 12px; }
            h1 { font-size: 20px; font-weight: 700; color: #0f172a; margin: 0 0 4px 0; }
            .sub { color: #64748b; font-size: 13px; margin-bottom: 24px; }
            .section-title { font-size: 12px; font-weight: 700; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; margin-top: 24px; margin-bottom: 12px; }
            .card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; margin-bottom: 16px; }
            .item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #edf2f7; font-size: 14px; }
            .item:last-child { border-bottom: none; }
            .item-label { color: #64748b; }
            .item-val { font-weight: 600; color: #0f172a; text-align: right; }
            .footer { margin-top: 32px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #f1f5f9; padding-top: 16px; }
          </style>
        </head>
        <body>
          <div class="container">
            <span class="badge">Verified Medical Document</span>
            <h1>${record.fileName}</h1>
            <div class="sub">Document ID: ${record.recordId} • Uploaded on ${new Date(record.createdAt).toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" })}</div>
            
            <div class="section-title">Clinically Extracted Findings</div>
            <div class="card">
              ${record.extractedInformation.map(item => `
                <div class="item">
                  <span class="item-label">${item.label}</span>
                  <span class="item-val">${item.value}</span>
                </div>
              `).join("")}
            </div>

            <div class="footer">
              HealthVault AI • End-to-End Secure Health Record Management
            </div>
          </div>
        </body>
        </html>
      `;
      const blob = new Blob([docHtml], { type: "text/html" });
      const blobUrl = URL.createObjectURL(blob);
      window.open(blobUrl, "_blank", "noopener,noreferrer");

    } catch (err) {
      console.error("Notice opening secure document:", err);
      window.open(`${API_BASE_URL}/documents/${record.recordId}`, "_blank", "noopener,noreferrer");
    } finally {
      setLoadingUrl(false);
    }
  };

  const handleAskAI = () => {
    onClose();
    router.push(`/patient/ai-assistant?doc=${record.recordId}`);
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete this ${recordTypeLabel[record.recordType] || "record"} (${record.fileName})? This action cannot be undone.`)) {
      return;
    }
    setDeleting(true);
    try {
      await deleteMedicalRecord(record.recordId);
      pushToast({
        type: "info",
        message: `Record ${record.fileName} deleted successfully.`,
      });
      onDelete?.(record.recordId);
      onClose();
    } catch (e) {
      console.error("Failed to delete record:", e);
      pushToast({
        type: "warning",
        message: "Failed to delete record from server. Please try again.",
      });
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">
              {recordTypeLabel[record.recordType]}
            </h2>
            <p className="text-xs text-slate-500">{record.fileName}</p>
          </div>
          <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6 p-6">
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Original Document
            </h3>
            <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              <div className="flex flex-col gap-1">
                <span className="font-medium text-slate-700">{record.fileName}</span>
                <button
                  type="button"
                  onClick={handleOpenSecureDocument}
                  disabled={loadingUrl}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-600 hover:text-teal-700 hover:underline disabled:opacity-50"
                >
                  <Lock className="h-3.5 w-3.5" />
                  {loadingUrl ? "Opening Document..." : "Access Secure Document"}
                  <ExternalLink className="h-3 w-3" />
                </button>
              </div>
              <Badge tone={record.processingStatus === "failed" && record.extractedInformation.length > 0 ? "ready" : record.processingStatus}>
                {record.processingStatus === "failed" && record.extractedInformation.length > 0 ? "ready" : record.processingStatus.replace("_", " ")}
              </Badge>
            </div>

          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Extracted Information
              </h3>
              {record.isMockExtraction && (
                <span className="flex items-center gap-1 rounded-full bg-purple-100 px-2 py-0.5 text-[11px] font-medium text-purple-700">
                  <FileWarning className="h-3 w-3" /> Demo/Mock Extracted Information
                </span>
              )}
            </div>
            {record.extractedInformation.length === 0 ? (
              <p className="text-sm text-slate-400">No structured information extracted yet.</p>
            ) : (
              <div className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                {record.extractedInformation.map((field) => (
                  <div key={field.label} className="flex items-center justify-between px-4 py-2.5 text-sm">
                    <span className="text-slate-500">{field.label}</span>
                    <span className="font-medium text-slate-800">{field.value}</span>
                  </div>
                ))}
              </div>
            )}
            <p className="mt-2 text-xs text-slate-400">
              Extracted medical data is processed with OCR & clinical NER models.
            </p>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
            <Button
              type="button"
              size="sm"
              onClick={handleAskAI}
              className="inline-flex items-center gap-1.5 bg-teal-600 text-white hover:bg-teal-700"
            >
              <Bot className="h-4 w-4" /> Ask AI About This Record
            </Button>

            <Button
              type="button"
              size="sm"
              variant="danger"
              disabled={deleting}
              onClick={handleDelete}
              className="inline-flex items-center gap-1.5"
            >
              <Trash2 className="h-4 w-4" /> {deleting ? "Deleting..." : "Delete Record"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
