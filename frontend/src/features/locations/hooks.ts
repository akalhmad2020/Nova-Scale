"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createLocation,
  getLocations,
} from "@/features/locations/api";
import { useActiveTenantId } from "@/features/tenants/active-hooks";

export function useLocations() {
  const activeTenantIdQuery =
    useActiveTenantId();

  return useQuery({
    queryKey: [
      "locations",
      activeTenantIdQuery.data,
    ],
    queryFn: getLocations,
    enabled: Boolean(
      activeTenantIdQuery.data,
    ),
    retry: false,
  });
}

export function useCreateLocation() {
  const queryClient = useQueryClient();

  const activeTenantIdQuery =
    useActiveTenantId();

  return useMutation({
    mutationFn: createLocation,

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "locations",
          activeTenantIdQuery.data,
        ],
      });
    },
  });
}