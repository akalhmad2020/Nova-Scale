import { Icon } from "@/components/ui/icon";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import {
  useCurrentSubscription,
  usePlans,
} from "@/features/saas/hooks";
import type { Plan } from "@/features/saas/types";

export function SubscriptionPlansPanel() {
  const plansQuery = usePlans();
  const subscriptionQuery = useCurrentSubscription();

  return (
    <div id="plans" className="scroll-mt-6">
      <Surface className="overflow-hidden">
        <SurfaceHeader
          title="Workspace plan"
          description="Capabilities are enforced by the backend entitlement catalog."
          meta={
            subscriptionQuery.data
              ? `${formatPlanCode(subscriptionQuery.data.plan_code)} · ${formatStatus(subscriptionQuery.data.status)}`
              : undefined
          }
        />

        {plansQuery.isPending || subscriptionQuery.isPending ? (
          <div className="p-6 text-sm text-slate-500">
            Loading subscription and plan catalog...
          </div>
        ) : plansQuery.isError || subscriptionQuery.isError ? (
          <div className="p-6">
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
              Unable to load workspace plan information. Billing operations remain available.
            </div>
          </div>
        ) : (
          <div className="grid gap-4 p-5 sm:p-6 md:grid-cols-3">
            {plansQuery.data.map((plan) => (
              <PlanCard
                key={plan.code}
                plan={plan}
                current={subscriptionQuery.data.plan_code === plan.code}
              />
            ))}
          </div>
        )}

        <div className="border-t border-slate-100 bg-slate-50/70 px-5 py-3.5 text-xs leading-5 text-slate-500 sm:px-6">
          Plan changes are not self-service yet. Provider-backed upgrades will be wired into the
          production billing flow rather than simulated in the UI.
        </div>
      </Surface>
    </div>
  );
}

function PlanCard({
  plan,
  current,
}: {
  plan: Plan;
  current: boolean;
}) {
  const teamLimit =
    plan.entitlements.team_member_limit === null
      ? "Unlimited team members"
      : `${plan.entitlements.team_member_limit} team members`;

  const capabilities = [
    {
      label: "NovaScale AI",
      included: plan.entitlements.ai_assistant,
    },
    {
      label: "RAG document indexing",
      included: plan.entitlements.rag_indexing,
    },
    {
      label: "Outbound webhooks",
      included: plan.entitlements.outbound_webhooks,
    },
  ];

  return (
    <article
      className={`relative rounded-2xl border p-5 ${
        plan.recommended
          ? "border-cyan-300 bg-cyan-50/30 shadow-[0_10px_30px_rgba(8,145,178,0.08)]"
          : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex min-h-7 items-center justify-between gap-2">
        {plan.recommended ? (
          <span className="rounded-full bg-cyan-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-cyan-800">
            Recommended
          </span>
        ) : (
          <span />
        )}
        {current ? (
          <span className="rounded-full bg-slate-950 px-2.5 py-1 text-[11px] font-semibold text-white">
            Current plan
          </span>
        ) : null}
      </div>

      <h3 className="mt-4 text-lg font-semibold text-slate-950">{plan.name}</h3>
      <p className="mt-2 min-h-12 text-sm leading-6 text-slate-500">{plan.description}</p>

      <div className="mt-5 space-y-2.5 border-t border-slate-200/80 pt-4">
        <CapabilityRow label="Core shipping workspace" included />
        {capabilities.map((capability) => (
          <CapabilityRow
            key={capability.label}
            label={capability.label}
            included={capability.included}
          />
        ))}
        <CapabilityRow label={teamLimit} included />
      </div>
    </article>
  );
}

function CapabilityRow({
  label,
  included,
}: {
  label: string;
  included: boolean;
}) {
  return (
    <div className="flex items-center gap-2.5 text-sm">
      <span
        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${
          included
            ? "bg-emerald-100 text-emerald-700"
            : "bg-slate-100 text-slate-400"
        }`}
      >
        {included ? (
          <Icon name="check" className="h-3 w-3" />
        ) : (
          <span className="text-[10px] font-bold">—</span>
        )}
      </span>
      <span className={included ? "text-slate-700" : "text-slate-400"}>{label}</span>
    </div>
  );
}

function formatPlanCode(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatStatus(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
