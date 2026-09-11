import type {
  ChangePlanInput,
  Plan,
  TenantSubscription,
} from "@/features/saas/types";

export async function getPlans(): Promise<Plan[]> {
  const response = await fetch("/api/plans", {
    method: "GET",
    cache: "no-store",
  });

  return readJsonResponse<Plan[]>(
    response,
    "Unable to load plans",
  );
}

export async function getCurrentSubscription(): Promise<TenantSubscription> {
  const response = await fetch("/api/subscription", {
    method: "GET",
    cache: "no-store",
  });

  return readJsonResponse<TenantSubscription>(
    response,
    "Unable to load workspace subscription",
  );
}

export async function changeSubscriptionPlan(
  input: ChangePlanInput,
): Promise<TenantSubscription> {
  const response = await fetch("/api/subscription/plan", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  return readJsonResponse<TenantSubscription>(
    response,
    "Unable to change workspace plan",
  );
}

async function readJsonResponse<T>(
  response: Response,
  fallback: string,
): Promise<T> {
  const data = (await response.json()) as {
    detail?: string;
  } & T;

  if (!response.ok) {
    throw new Error(data.detail ?? fallback);
  }

  return data;
}
