"use client";

import { SubscriptionPlansPanel } from "@/components/subscription-plans-panel";
import { PageHeader } from "@/components/ui/page-header";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { useCurrentSubscription } from "@/features/saas/hooks";

export function SubscriptionContent() {
  const subscriptionQuery = useCurrentSubscription();
  const subscription = subscriptionQuery.data;

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Platform"
        title="Subscription"
        description="Manage the NovaScale plan, platform capabilities, and workspace access independently from customer invoicing."
      />

      <Surface>
        <SurfaceHeader
          title="Current subscription"
          description="The active SaaS plan that controls NovaScale entitlements for this workspace."
        />

        {subscriptionQuery.isPending ? (
          <div className="p-6 text-sm text-slate-500">Loading subscription...</div>
        ) : subscriptionQuery.isError || !subscription ? (
          <div className="p-6 text-sm text-rose-600">
            {subscriptionQuery.error?.message ?? "Unable to load subscription"}
          </div>
        ) : (
          <div className="grid gap-4 p-5 sm:grid-cols-2 sm:p-6 lg:grid-cols-4">
            <Metric label="Plan" value={formatValue(subscription.plan_code)} />
            <Metric label="Status" value={formatValue(subscription.status)} />
            <Metric label="Provider" value={formatProvider(subscription.provider)} />
            <Metric
              label="Renewal"
              value={subscription.current_period_end ? formatDate(subscription.current_period_end) : "Demo access"}
            />
          </div>
        )}
      </Surface>

      <SubscriptionPlansPanel />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-base font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function formatValue(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatProvider(provider: string | null) {
  if (!provider) return "Internal";
  if (provider === "portfolio") return "Portfolio demo";
  return formatValue(provider);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
    new Date(value),
  );
}
