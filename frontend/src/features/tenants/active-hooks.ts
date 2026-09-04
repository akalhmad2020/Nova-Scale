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

export function useActiveTenantId() {
  return useQuery({
    queryKey: ["tenants", "active"],
    queryFn: getActiveTenantId,
    retry: false,
  });
}

export function useSetActiveTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: setActiveTenant,
    onSuccess: async (activeTenantId) => {
      queryClient.setQueryData(
        ["tenants", "active"],
        activeTenantId,
      );
    },
  });
}