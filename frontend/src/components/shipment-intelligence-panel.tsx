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
    <section className="rounded-xl border border-zinc-200 bg-white p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="font-medium text-zinc-950">
            Shipment intelligence
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Deterministic operational checks based on the shipment timeline.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <RiskBadge
            riskLevel={analysis.risk_level}
          />

          <SeverityBadge
            severity={analysis.highest_severity}
          />
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between rounded-lg bg-zinc-50 px-4 py-3 text-sm">
        <span className="text-zinc-500">
          Operational risk score
        </span>

        <span className="font-medium text-zinc-950">
          {analysis.risk_score}/100
        </span>
      </div>

      {!analysis.has_issues ? (
        <div className="mt-5 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3">
          <p className="text-sm font-medium text-zinc-900">
            No operational issues detected
          </p>

          <p className="mt-1 text-sm text-zinc-500">
            The current shipment state and latest timeline activity did not trigger any operational warnings.
          </p>
        </div>
      ) : (
        <div className="mt-5 space-y-3">
          {analysis.issues.map((issue) => (
            <article
              key={issue.code}
              className="rounded-lg border border-zinc-200 p-4"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-center gap-2">
                  <SeverityBadge
                    severity={issue.severity}
                  />

                  <span className="font-mono text-xs text-zinc-500">
                    {issue.code}
                  </span>
                </div>

                {issue.age_seconds !== null && (
                  <span className="text-xs text-zinc-500">
                    Age: {formatDuration(issue.age_seconds)}
                  </span>
                )}
              </div>

              <p className="mt-3 text-sm text-zinc-800">
                {issue.message}
              </p>

              <div className="mt-3 rounded-lg bg-zinc-50 px-3 py-2.5">
                <p className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                  Recommended action
                </p>

                <p className="mt-1 text-sm text-zinc-800">
                  {issue.recommended_action}
                </p>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

type RiskBadgeProps = {
  riskLevel: OperationalRiskLevel;
};

function RiskBadge({
  riskLevel,
}: RiskBadgeProps) {
  return (
    <span className="inline-flex w-fit rounded-full bg-zinc-950 px-2.5 py-1 text-xs font-medium text-white">
      Risk: {formatValue(riskLevel)}
    </span>
  );
}

type SeverityBadgeProps = {
  severity: OperationalSeverity;
};

function SeverityBadge({
  severity,
}: SeverityBadgeProps) {
  const classes = getSeverityClasses(
    severity,
  );

  return (
    <span
      className={`inline-flex w-fit rounded-full px-2.5 py-1 text-xs font-medium ${classes}`}
    >
      {formatValue(severity)}
    </span>
  );
}

function getSeverityClasses(
  severity: OperationalSeverity,
): string {
  switch (severity) {
    case "critical":
      return "bg-red-50 text-red-700";

    case "warning":
      return "bg-amber-50 text-amber-700";

    case "info":
      return "bg-zinc-100 text-zinc-700";
  }
}

function formatDuration(
  totalSeconds: number,
): string {
  const safeSeconds = Math.max(
    0,
    Math.floor(totalSeconds),
  );

  const totalMinutes = Math.floor(
    safeSeconds / 60,
  );

  const days = Math.floor(
    totalMinutes / (24 * 60),
  );

  const hours = Math.floor(
    (totalMinutes % (24 * 60)) / 60,
  );

  const minutes = totalMinutes % 60;

  const parts: string[] = [];

  if (days > 0) {
    parts.push(`${days}d`);
  }

  if (hours > 0 || days > 0) {
    parts.push(`${hours}h`);
  }

  parts.push(`${minutes}m`);

  return parts.join(" ");
}

function formatValue(
  value: string,
): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(" ");
}
