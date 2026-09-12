"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createCustomer,
  getCustomers,
} from "@/features/customers/api";
import { useActiveTenantId } from "@/features/tenants/active-hooks";
import {
  canRunTenantScopedQuery,
  getResolvedActiveTenantId,
  requireActiveTenantId,
} from "@/features/tenants/query-state";

export function useCustomers() {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = getResolvedActiveTenantId(
    activeTenantIdQuery,
  );

  return useQuery({
    queryKey: ["customers", activeTenantId],
    queryFn: () => {
      requireActiveTenantId(activeTenantIdQuery);
      return getCustomers();
    },
    enabled: canRunTenantScopedQuery(activeTenantIdQuery),
    retry: false,
  });
}

export function useCreateCustomer() {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: createCustomer,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "customers",
          activeTenantIdQuery.data,
        ],
      });
    },
  });
}
