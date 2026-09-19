"use client";

import { FileText, Image as ImageIcon, Pill, ClipboardList, Stethoscope, FileHeart } from "lucide-react";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import { recordTypeLabel } from "@/lib/mock/mock-data";
import type { MedicalRecord } from "@/types";

const iconFor: Record<string, typeof FileText> = {
  prescription: Pill,
  blood_report: FileHeart,
  lab_report: ClipboardList,
  medical_image: ImageIcon,
  doctor_note: Stethoscope,
  discharge_summary: FileText,
};

export default function MedicalRecordCard({
  record,
  onView,
}: {
  record: MedicalRecord;
  onView?: (record: MedicalRecord) => void;
}) {
  const rType = record?.recordType || "prescription";
  const Icon = iconFor[rType] ?? FileText;
  const statusStr = record?.processingStatus || "ready";
  const displayStatus = (statusStr === "failed" && (record?.extractedInformation?.length || 0) > 0) ? "ready" : statusStr;
  const dateStr = record?.createdAt
    ? new Date(record.createdAt).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
    : "Recent";

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50 text-teal-600">
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">
              {recordTypeLabel[rType] || "Medical Document"}
            </p>
            <p className="text-xs text-slate-500">{record?.fileName || "Document"}</p>
          </div>
        </div>
        <Badge tone={displayStatus}>{displayStatus.replace("_", " ")}</Badge>
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Uploaded {dateStr}
        {" • "}
        {record?.fileSizeKb || 150} KB
      </p>
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={() => onView?.(record)}
          className="flex-1 rounded-lg border border-slate-200 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
        >
          View details
        </button>
        <a
          href={`/patient/ai-assistant?doc=${record.recordId}`}
          className="flex items-center justify-center gap-1 rounded-lg bg-teal-50 px-3 py-2 text-xs font-semibold text-teal-700 hover:bg-teal-100 transition-colors"
        >
          Ask AI
        </a>
      </div>
    </Card>
  );
}
