import type { ReactNode } from "react";

import { Icon, type IconName } from "@/components/ui/icon";

type MetricCardProps = {
  label: string;
  value: ReactNode;
  note: string;
  icon: IconName;
  tone?: "neutral" | "success" | "info" | "warning";
};

const toneClasses = {
  neutral: "bg-slate-100 text-slate-600",
  success: "bg-emerald-50 text-emerald-700",
  info: "bg-cyan-50 text-cyan-700",
  warning: "bg-amber-50 text-amber-700",
} as const;

export function MetricCard({
  label,
  value,
  note,
  icon,
  tone = "neutral",
}: MetricCardProps) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">
            {label}
          </p>
          <div className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
            {value}
          </div>
        </div>
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${toneClasses[tone]}`}
        >
          <Icon name={icon} className="h-5 w-5" />
        </div>
      </div>
      <p className="mt-4 text-xs leading-5 text-slate-500">
        {note}
      </p>
    </div>
  );
}
