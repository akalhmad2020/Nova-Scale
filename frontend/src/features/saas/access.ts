import type {
  Plan,
  TenantSubscription,
} from "@/features/saas/types";

export function resolveCurrentPlan(
  plans: Plan[],
  subscription: TenantSubscription,
): Plan | null {
  return (
    plans.find(
      (plan) => plan.code === subscription.plan_code,
    ) ?? null
  );
}

export function hasAIAssistantAccess(
  plan: Plan | null,
  subscription: TenantSubscription,
): boolean {
  return (
    subscription.status === "active" &&
    plan?.entitlements.ai_assistant === true
  );
}
