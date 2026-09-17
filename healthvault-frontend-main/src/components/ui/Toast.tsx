"use client";
import { useEffect, useState } from "react";
import clsx from "clsx";

export interface ToastMessage {
  id: number;
  type: "success" | "error" | "info";
  message: string;
}

let pushToastFn: ((t: Omit<ToastMessage, "id">) => void) | null = null;

export function pushToast(t: Omit<ToastMessage, "id">) {
  pushToastFn?.(t);
}

export default function ToastHost() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    pushToastFn = (t) => {
      const id = Date.now();
      setToasts((prev) => [...prev, { ...t, id }]);
      setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== id)), 3500);
    };
    return () => {
      pushToastFn = null;
    };
  }, []);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={clsx(
            "rounded-lg px-4 py-3 text-sm shadow-lg text-white min-w-[240px]",
            t.type === "success" && "bg-emerald-600",
            t.type === "error" && "bg-red-600",
            t.type === "info" && "bg-slate-800"
          )}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}
