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
import {
  canRunTenantScopedQuery,
  getResolvedActiveTenantId,
  requireActiveTenantId,
} from "@/features/tenants/query-state";

export function useLocations() {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = getResolvedActiveTenantId(
    activeTenantIdQuery,
  );

  return useQuery({
    queryKey: ["locations", activeTenantId],
    queryFn: () => {
      requireActiveTenantId(activeTenantIdQuery);
      return getLocations();
    },
    enabled: canRunTenantScopedQuery(activeTenantIdQuery),
    retry: false,
  });
}

export function useCreateLocation() {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

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
