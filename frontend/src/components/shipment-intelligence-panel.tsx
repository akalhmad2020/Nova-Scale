import { Icon } from "@/components/ui/icon";
import type {
  OperationalRiskLevel,
  OperationalSeverity,
  ShipmentOperationalAnalysis,
} from "@/features/shipments/intelligence-types";

type ShipmentIntelligencePanelProps = {
  analysis: ShipmentOperationalAnalysis;
};

export function ShipmentIntelligencePanel({
  analysis,
}: ShipmentIntelligencePanelProps) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <div className="flex flex-col gap-4 border-b border-slate-100 px-5 py-5 sm:flex-row sm:items-start sm:justify-between sm:px-6">
        <div className="flex gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-cyan-50 text-cyan-700">
            <Icon name="activity" className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-950">
              Operational intelligence
            </h2>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-500">
              Deterministic checks derived from shipment state and timeline activity.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <RiskBadge riskLevel={analysis.risk_level} />
          <SeverityBadge severity={analysis.highest_severity} />
        </div>
      </div>

      <div className="grid gap-px bg-slate-100 sm:grid-cols-3">
        <Metric label="Risk score" value={`${analysis.risk_score}/100`} />
        <Metric label="Risk level" value={formatValue(analysis.risk_level)} />
        <Metric label="Detected issues" value={String(analysis.issues.length)} />
      </div>

      <div className="p-5 sm:p-6">
        {!analysis.has_issues ? (
          <div className="flex gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-4">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
              <Icon name="check" className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-semibold text-emerald-900">
                No operational issues detected
              </p>
              <p className="mt-1 text-sm leading-6 text-emerald-700">
                Current shipment state and timeline activity are within the configured operational rules.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {analysis.issues.map((issue) => (
              <article
                key={issue.code}
                className="rounded-xl border border-slate-200 bg-slate-50/50 p-4"
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={issue.severity} />
                    <span className="font-mono text-[11px] text-slate-400">
                      {issue.code}
                    </span>
                  </div>
                  {issue.age_seconds !== null ? (
                    <span className="text-xs font-medium text-slate-500">
                      Open for {formatDuration(issue.age_seconds)}
                    </span>
                  ) : null}
                </div>

                <p className="mt-3 text-sm leading-6 text-slate-700">
                  {issue.message}
                </p>

                <div className="mt-4 rounded-lg border border-slate-200 bg-white px-3.5 py-3">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                    Recommended action
                  </p>
                  <p className="mt-1.5 text-sm leading-6 text-slate-700">
                    {issue.recommended_action}
                  </p>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white px-5 py-4 sm:px-6">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1.5 text-lg font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function RiskBadge({ riskLevel }: { riskLevel: OperationalRiskLevel }) {
  const classes =
    riskLevel === "high" || riskLevel === "critical"
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : riskLevel === "medium"
        ? "border-amber-200 bg-amber-50 text-amber-700"
        : "border-emerald-200 bg-emerald-50 text-emerald-700";

  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${classes}`}>
      {formatValue(riskLevel)} risk
    </span>
  );
}

function SeverityBadge({ severity }: { severity: OperationalSeverity }) {
  const classes = getSeverityClasses(severity);
  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${classes}`}>
      {formatValue(severity)}
    </span>
  );
}

function getSeverityClasses(severity: OperationalSeverity) {
  switch (severity) {
    case "critical":
      return "bg-rose-100 text-rose-700";
    case "warning":
      return "bg-amber-100 text-amber-700";
    case "info":
      return "bg-slate-100 text-slate-600";
  }
}

function formatDuration(totalSeconds: number) {
  const safeSeconds = Math.max(0, Math.floor(totalSeconds));
  const totalMinutes = Math.floor(safeSeconds / 60);
  const days = Math.floor(totalMinutes / (24 * 60));
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
  const minutes = totalMinutes % 60;
  const parts: string[] = [];
  if (days > 0) parts.push(`${days}d`);
  if (hours > 0 || days > 0) parts.push(`${hours}h`);
  parts.push(`${minutes}m`);
  return parts.join(" ");
}

function formatValue(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
