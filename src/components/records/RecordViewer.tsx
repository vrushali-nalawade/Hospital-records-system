"use client";

import { X, FileWarning } from "lucide-react";
import Badge from "@/components/ui/Badge";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import type { MedicalRecord } from "@/types";

export default function RecordViewer({
  record,
  onClose,
}: {
  record: MedicalRecord;
  onClose: () => void;
}) {
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
              <span>{record.fileName}</span>
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
              This information is a demo/mock extraction and does not represent actual medical analysis.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
