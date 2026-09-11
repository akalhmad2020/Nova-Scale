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
