"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createTenant,
  getMyTenants,
} from "@/features/tenants/api";

export function useMyTenants() {
  return useQuery({
    queryKey: ["tenants", "mine"],
    queryFn: getMyTenants,
    retry: false,
  });
}

export function useCreateTenant() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createTenant,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: ["tenants", "mine"],
      });
    },
  });
}