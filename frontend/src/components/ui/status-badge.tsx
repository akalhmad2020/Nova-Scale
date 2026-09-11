type StatusBadgeProps = {
  value: string;
};

const POSITIVE = new Set([
  "active",
  "delivered",
  "paid",
  "ready",
  "success",
  "executed",
]);

const INFO = new Set([
  "in_transit",
  "issued",
  "draft",
  "pending_confirmation",
  "executing",
]);

const NEGATIVE = new Set([
  "cancelled",
  "void",
  "inactive",
  "failed",
]);

export function StatusBadge({
  value,
}: StatusBadgeProps) {
  let classes =
    "border-slate-200 bg-slate-50 text-slate-700";

  if (POSITIVE.has(value)) {
    classes =
      "border-emerald-200 bg-emerald-50 text-emerald-700";
  } else if (INFO.has(value)) {
    classes =
      "border-cyan-200 bg-cyan-50 text-cyan-800";
  } else if (NEGATIVE.has(value)) {
    classes =
      "border-rose-200 bg-rose-50 text-rose-700";
  }

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${classes}`}
    >
      {formatStatus(value)}
    </span>
  );
}

export function formatStatus(value: string) {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(" ");
}
