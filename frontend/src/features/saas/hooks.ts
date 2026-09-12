"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  changeSubscriptionPlan,
  getCurrentSubscription,
  getPlans,
} from "@/features/saas/api";
import { useActiveTenantId } from "@/features/tenants/active-hooks";
import {
  canRunTenantScopedQuery,
  getResolvedActiveTenantId,
  requireActiveTenantId,
} from "@/features/tenants/query-state";

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
  const activeTenantId = getResolvedActiveTenantId(
    activeTenantIdQuery,
  );

  return useQuery({
    queryKey: [
      "saas",
      "subscription",
      activeTenantId,
    ],
    queryFn: () => {
      requireActiveTenantId(activeTenantIdQuery);
      return getCurrentSubscription();
    },
    enabled: canRunTenantScopedQuery(activeTenantIdQuery),
    retry: false,
  });
}

export function useChangeSubscriptionPlan() {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = activeTenantIdQuery.data ?? null;

  return useMutation({
    mutationFn: changeSubscriptionPlan,
    onSuccess: async (subscription) => {
      queryClient.setQueryData(
        ["saas", "subscription", subscription.tenant_id],
        subscription,
      );

      await queryClient.invalidateQueries({
        queryKey: ["saas", "subscription", activeTenantId],
      });

      await queryClient.invalidateQueries({
        queryKey: ["ai"],
      });
    },
  });
}
