"use client";

import { useState } from "react";

import { Icon } from "@/components/ui/icon";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import {
  useChangeSubscriptionPlan,
  useCurrentSubscription,
  usePlans,
} from "@/features/saas/hooks";
import type { Plan, PlanCode } from "@/features/saas/types";

export function SubscriptionPlansPanel() {
  const plansQuery = usePlans();
  const subscriptionQuery = useCurrentSubscription();
  const changePlan = useChangeSubscriptionPlan();
  const [confirmationPlan, setConfirmationPlan] = useState<PlanCode | null>(null);

  const subscription = subscriptionQuery.data;
  const plans = plansQuery.data ?? [];

  async function applyPlan(planCode: PlanCode) {
    await changePlan.mutateAsync({ plan_code: planCode });
    setConfirmationPlan(null);
  }

  return (
    <Surface className="overflow-hidden">
      <SurfaceHeader
        title="Available plans"
        description="Choose the NovaScale capabilities that match this workspace."
        meta={
          subscription
            ? `${formatPlanCode(subscription.plan_code)} · ${formatStatus(subscription.status)}`
            : undefined
        }
      />

      <div className="border-b border-cyan-100 bg-cyan-50/70 px-5 py-4 text-sm leading-6 text-cyan-900 sm:px-6">
        <span className="font-semibold">Portfolio demo access.</span>{" "}
        Starter and Professional activate immediately in this environment. The provider boundary is isolated so Stripe checkout can replace instant activation later.
      </div>

      {plansQuery.isPending || subscriptionQuery.isPending ? (
        <div className="p-6 text-sm text-slate-500">
          Loading subscription and plan catalog...
        </div>
      ) : plansQuery.isError || subscriptionQuery.isError || !subscription ? (
        <div className="p-6">
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            Unable to load workspace subscription information.
          </div>
        </div>
      ) : (
        <div className="grid gap-4 p-5 sm:p-6 lg:grid-cols-3">
          {plans.map((plan) => {
            const current = subscription.plan_code === plan.code;
            const changing = changePlan.isPending && confirmationPlan === plan.code;
            const canChange =
              plan.self_service &&
              subscription.status === "active" &&
              !current;

            return (
              <PlanCard
                key={plan.code}
                plan={plan}
                current={current}
                canChange={canChange}
                changing={changing}
                awaitingConfirmation={confirmationPlan === plan.code}
                onSelect={() => setConfirmationPlan(plan.code)}
                onCancel={() => setConfirmationPlan(null)}
                onConfirm={() => void applyPlan(plan.code)}
              />
            );
          })}
        </div>
      )}

      {changePlan.isError ? (
        <div className="border-t border-rose-100 bg-rose-50 px-5 py-3.5 text-sm text-rose-700 sm:px-6">
          {changePlan.error.message}
        </div>
      ) : null}
    </Surface>
  );
}

function PlanCard({
  plan,
  current,
  canChange,
  changing,
  awaitingConfirmation,
  onSelect,
  onCancel,
  onConfirm,
}: {
  plan: Plan;
  current: boolean;
  canChange: boolean;
  changing: boolean;
  awaitingConfirmation: boolean;
  onSelect: () => void;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const capabilities = [
    { label: "NovaScale AI", included: plan.entitlements.ai_assistant },
    { label: "RAG document indexing", included: plan.entitlements.rag_indexing },
    { label: "Outbound webhooks", included: plan.entitlements.outbound_webhooks },
  ];

  const teamLimit =
    plan.entitlements.team_member_limit === null
      ? "Unlimited team members"
      : `${plan.entitlements.team_member_limit} team members`;

  return (
    <article
      className={`relative rounded-2xl border p-5 transition ${
        current
          ? "border-cyan-300 bg-cyan-50/40 shadow-[0_0_0_1px_rgba(6,182,212,0.05)]"
          : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex flex-wrap items-center gap-2">
        {current ? (
          <span className="rounded-full bg-slate-950 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-white">
            Current plan
          </span>
        ) : null}
        {plan.recommended ? (
          <span className="rounded-full bg-cyan-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-cyan-800">
            Recommended
          </span>
        ) : null}
      </div>

      <h3 className="mt-4 text-lg font-semibold tracking-tight text-slate-950">
        {plan.name}
      </h3>
      <p className="mt-2 min-h-12 text-sm leading-6 text-slate-500">
        {plan.description}
      </p>

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

      <div className="mt-6">
        {current ? (
          <button
            type="button"
            disabled
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm font-semibold text-slate-500"
          >
            Current plan
          </button>
        ) : !plan.self_service ? (
          <button
            type="button"
            disabled
            className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm font-semibold text-slate-500"
          >
            Contact sales
          </button>
        ) : awaitingConfirmation ? (
          <div className="space-y-2 rounded-xl border border-amber-200 bg-amber-50 p-3">
            <p className="text-xs leading-5 text-amber-800">
              Change this workspace to {plan.name}? Entitlements update immediately.
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onConfirm}
                disabled={changing}
                className="flex-1 rounded-lg bg-slate-950 px-3 py-2 text-xs font-semibold text-white disabled:opacity-60"
              >
                {changing ? "Applying..." : "Confirm"}
              </button>
              <button
                type="button"
                onClick={onCancel}
                disabled={changing}
                className="rounded-lg border border-amber-200 bg-white px-3 py-2 text-xs font-semibold text-amber-900 disabled:opacity-60"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={onSelect}
            disabled={!canChange}
            className="w-full rounded-xl bg-slate-950 px-3 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
          >
            {plan.code === "professional" ? "Activate Professional" : "Switch plan"}
          </button>
        )}
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
      <span className={included ? "text-slate-700" : "text-slate-400"}>
        {label}
      </span>
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
