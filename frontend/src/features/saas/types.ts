export type PlanCode =
  | "starter"
  | "professional"
  | "enterprise";

export type SubscriptionStatus =
  | "active"
  | "past_due"
  | "canceled"
  | "suspended";

export type PlanEntitlements = {
  ai_assistant: boolean;
  rag_indexing: boolean;
  outbound_webhooks: boolean;
  team_member_limit: number | null;
};

export type Plan = {
  code: PlanCode;
  name: string;
  description: string;
  display_order: number;
  recommended: boolean;
  self_service: boolean;
  entitlements: PlanEntitlements;
};

export type TenantSubscription = {
  id: string;
  tenant_id: string;
  plan_code: PlanCode;
  status: SubscriptionStatus;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  provider: string | null;
  created_at: string;
  updated_at: string;
};

export type ChangePlanInput = {
  plan_code: PlanCode;
};
