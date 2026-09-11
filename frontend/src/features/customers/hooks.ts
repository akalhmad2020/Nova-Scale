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

export function useCustomers() {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = readyTenantId(activeTenantIdQuery);

  return useQuery({
    queryKey: ["customers", activeTenantId],
    queryFn: getCustomers,
    enabled: Boolean(activeTenantId),
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

function readyTenantId(
  query: ReturnType<typeof useActiveTenantId>,
): string | null {
  if (!query.isSuccess || query.isFetching || !query.data) {
    return null;
  }

  return query.data;
}
