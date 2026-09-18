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
      const signedUrl = await fetchDocumentSignedUrl(record.recordId);
      const target = signedUrl || record.fileUrl || `${API_BASE_URL}/documents/${record.recordId}`;
      if (target) {
        window.open(target, "_blank", "noopener,noreferrer");
      }
    } catch (err) {
      console.error("Error opening secure document:", err);
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
              <Badge tone={record.processingStatus}>{record.processingStatus.replace("_", " ")}</Badge>
            </div>
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
