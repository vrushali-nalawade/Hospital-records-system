import clsx from "clsx";

const styles: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  approved: "bg-emerald-100 text-emerald-800",
  rejected: "bg-red-100 text-red-800",
  revoked: "bg-slate-200 text-slate-700",
  expired: "bg-slate-200 text-slate-500",
  ready: "bg-emerald-100 text-emerald-800",
  uploading: "bg-blue-100 text-blue-800",
  processing: "bg-blue-100 text-blue-800",
  ocr_completed: "bg-indigo-100 text-indigo-800",
  extracted: "bg-indigo-100 text-indigo-800",
  failed: "bg-red-100 text-red-800",
  demo: "bg-purple-100 text-purple-800",
};

export default function Badge({
  children,
  tone = "pending",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium capitalize",
        styles[tone] ?? "bg-slate-100 text-slate-700"
      )}
    >
      {children}
    </span>
  );
}
