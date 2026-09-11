"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getCurrentSubscription,
  getPlans,
} from "@/features/saas/api";
import { useActiveTenantId } from "@/features/tenants/active-hooks";

export function usePlans() {
  return useQuery({
    queryKey: ["saas", "plans"],
    queryFn: getPlans,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCurrentSubscription() {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = getReadyTenantId(
    activeTenantIdQuery.data,
    activeTenantIdQuery.isSuccess,
    activeTenantIdQuery.isFetching,
  );

  return useQuery({
    queryKey: [
      "saas",
      "subscription",
      activeTenantId,
    ],
    queryFn: getCurrentSubscription,
    enabled: Boolean(activeTenantId),
    retry: false,
  });
}

function getReadyTenantId(
  tenantId: string | null | undefined,
  isSuccess: boolean,
  isFetching: boolean,
): string | null {
  if (!isSuccess || isFetching || !tenantId) {
    return null;
  }

  return tenantId;
}
