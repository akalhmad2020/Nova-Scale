import Link from "next/link";

import { Icon } from "@/components/ui/icon";

type PlanAccessCardProps = {
  eyebrow?: string;
  currentPlanName: string;
  title: string;
  description: string;
  compact?: boolean;
};

export function PlanAccessCard({
  eyebrow = "Plan access",
  currentPlanName,
  title,
  description,
  compact = false,
}: PlanAccessCardProps) {
  return (
    <section
      className={`overflow-hidden rounded-2xl border border-cyan-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${
        compact ? "" : "min-h-[360px]"
      }`}
    >
      <div className={compact ? "p-5 sm:p-6" : "p-7 sm:p-9"}>
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700">
              <Icon name="sparkles" className="h-5 w-5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-700">
                  {eyebrow}
                </p>
                <span className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                  {currentPlanName} plan
                </span>
              </div>
              <h2 className="mt-2 text-lg font-semibold tracking-tight text-slate-950">
                {title}
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                {description}
              </p>
            </div>
          </div>

          <Link
            href="/billing#plans"
            className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            View plans
            <Icon name="arrow-right" className="h-4 w-4" />
          </Link>
        </div>

        {!compact ? (
          <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              "Shipment intelligence",
              "AI operational analysis",
              "RAG document context",
              "Controlled write actions",
            ].map((feature) => (
              <div
                key={feature}
                className="flex items-center gap-2.5 rounded-xl border border-slate-200 bg-slate-50/70 px-3.5 py-3 text-sm font-medium text-slate-700"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-cyan-100 text-cyan-700">
                  <Icon name="check" className="h-3.5 w-3.5" />
                </span>
                {feature}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  );
}
