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
  const activeTenantIdQuery =
    useActiveTenantId();

  return useQuery({
    queryKey: [
      "customers",
      activeTenantIdQuery.data,
    ],
    queryFn: getCustomers,
    enabled: Boolean(
      activeTenantIdQuery.data,
    ),
    retry: false,
  });
}

export function useCreateCustomer() {
  const queryClient = useQueryClient();

  const activeTenantIdQuery =
    useActiveTenantId();

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