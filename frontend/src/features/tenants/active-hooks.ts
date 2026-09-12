"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  getActiveTenantId,
  setActiveTenant,
} from "@/features/tenants/active-api";

export const ACTIVE_TENANT_QUERY_KEY = [
  "tenants",
  "active",
] as const;

export function useActiveTenantId() {
  return useQuery({
    queryKey: ACTIVE_TENANT_QUERY_KEY,
    queryFn: getActiveTenantId,
    retry: false,
    staleTime: Infinity,
  });
}

export function useSetActiveTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: setActiveTenant,
    onSuccess: (activeTenantId) => {
      queryClient.setQueryData(
        ACTIVE_TENANT_QUERY_KEY,
        activeTenantId,
      );

      removeTenantScopedQueries(queryClient);
    },
  });
}

function removeTenantScopedQueries(
  queryClient: ReturnType<typeof useQueryClient>,
): void {
  for (const queryKey of [
    ["shipments"],
    ["shipment-events"],
    ["shipment-intelligence"],
    ["customers"],
    ["locations"],
    ["invoices"],
    ["invoice"],
    ["invoice-lines"],
    ["ai"],
    ["saas", "subscription"],
  ] as const) {
    queryClient.removeQueries({ queryKey });
  }
}
