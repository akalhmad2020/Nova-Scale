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
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = readyTenantId(activeTenantIdQuery);

  return useQuery({
    queryKey: ["locations", activeTenantId],
    queryFn: getLocations,
    enabled: Boolean(activeTenantId),
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

function readyTenantId(
  query: ReturnType<typeof useActiveTenantId>,
): string | null {
  if (!query.isSuccess || query.isFetching || !query.data) {
    return null;
  }

  return query.data;
}
