"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import type { RecordShipmentEventInput } from "@/features/shipments/events-types";
import {
  createShipment,
  getShipment,
  getShipmentEvents,
  getShipmentOperationalAnalysis,
  getShipments,
  recordShipmentEvent,
  transitionShipmentStatus,
} from "@/features/shipments/api";
import type { TransitionShipmentStatusInput } from "@/features/shipments/types";
import { useActiveTenantId } from "@/features/tenants/active-hooks";

export function useShipments() {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = readyTenantId(activeTenantIdQuery);

  return useQuery({
    queryKey: ["shipments", activeTenantId],
    queryFn: getShipments,
    enabled: Boolean(activeTenantId),
    retry: false,
  });
}

export function useCreateShipment() {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: createShipment,
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "shipments",
          activeTenantIdQuery.data,
        ],
      });
    },
  });
}

export function useShipment(shipmentId: string) {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = readyTenantId(activeTenantIdQuery);

  return useQuery({
    queryKey: [
      "shipments",
      activeTenantId,
      shipmentId,
    ],
    queryFn: () => getShipment(shipmentId),
    enabled: Boolean(activeTenantId && shipmentId),
    retry: false,
  });
}

export function useShipmentOperationalAnalysis(
  shipmentId: string,
) {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = readyTenantId(activeTenantIdQuery);

  return useQuery({
    queryKey: [
      "shipment-intelligence",
      activeTenantId,
      shipmentId,
    ],
    queryFn: () =>
      getShipmentOperationalAnalysis(shipmentId),
    enabled: Boolean(activeTenantId && shipmentId),
    retry: false,
  });
}

export function useShipmentEvents(
  shipmentId: string,
) {
  const activeTenantIdQuery = useActiveTenantId();
  const activeTenantId = readyTenantId(activeTenantIdQuery);

  return useQuery({
    queryKey: [
      "shipment-events",
      activeTenantId,
      shipmentId,
    ],
    queryFn: () => getShipmentEvents(shipmentId),
    enabled: Boolean(activeTenantId && shipmentId),
    retry: false,
  });
}

export function useTransitionShipmentStatus(
  shipmentId: string,
) {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: (
      input: TransitionShipmentStatusInput,
    ) => transitionShipmentStatus(shipmentId, input),
    onSuccess: async () => {
      const tenantId = activeTenantIdQuery.data;

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["shipments", tenantId, shipmentId],
        }),
        queryClient.invalidateQueries({
          queryKey: ["shipments", tenantId],
        }),
        queryClient.invalidateQueries({
          queryKey: [
            "shipment-events",
            tenantId,
            shipmentId,
          ],
        }),
        queryClient.invalidateQueries({
          queryKey: [
            "shipment-intelligence",
            tenantId,
            shipmentId,
          ],
        }),
      ]);
    },
  });
}

export function useRecordShipmentEvent(
  shipmentId: string,
) {
  const queryClient = useQueryClient();
  const activeTenantIdQuery = useActiveTenantId();

  return useMutation({
    mutationFn: (input: RecordShipmentEventInput) =>
      recordShipmentEvent(shipmentId, input),
    onSuccess: async () => {
      const tenantId = activeTenantIdQuery.data;

      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: [
            "shipment-events",
            tenantId,
            shipmentId,
          ],
        }),
        queryClient.invalidateQueries({
          queryKey: [
            "shipment-intelligence",
            tenantId,
            shipmentId,
          ],
        }),
      ]);
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
