"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import {
  createShipment,
  getShipment,
  getShipmentEvents,
  getShipments,
  recordShipmentEvent,
  transitionShipmentStatus,
} from "@/features/shipments/api";
import type { TransitionShipmentStatusInput } from "@/features/shipments/types";
import { useActiveTenantId } from "@/features/tenants/active-hooks";

import type {
  RecordShipmentEventInput,
} from "@/features/shipments/events-types";

export function useShipments() {
  const activeTenantIdQuery =
    useActiveTenantId();

  return useQuery({
    queryKey: [
      "shipments",
      activeTenantIdQuery.data,
    ],
    queryFn: getShipments,
    enabled: Boolean(
      activeTenantIdQuery.data,
    ),
    retry: false,
  });
}

export function useCreateShipment() {
  const queryClient = useQueryClient();

  const activeTenantIdQuery =
    useActiveTenantId();

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

export function useShipment(
  shipmentId: string,
) {
  const activeTenantIdQuery =
    useActiveTenantId();

  return useQuery({
    queryKey: [
      "shipments",
      activeTenantIdQuery.data,
      shipmentId,
    ],
    queryFn: () =>
      getShipment(shipmentId),
    enabled: Boolean(
      activeTenantIdQuery.data &&
        shipmentId,
    ),
    retry: false,
  });
}

export function useShipmentEvents(
  shipmentId: string,
) {
  const activeTenantIdQuery =
    useActiveTenantId();

  return useQuery({
    queryKey: [
      "shipment-events",
      activeTenantIdQuery.data,
      shipmentId,
    ],
    queryFn: () =>
      getShipmentEvents(shipmentId),
    enabled: Boolean(
      activeTenantIdQuery.data &&
        shipmentId,
    ),
    retry: false,
  });
}

export function useTransitionShipmentStatus(
  shipmentId: string,
) {
  const queryClient = useQueryClient();

  const activeTenantIdQuery =
    useActiveTenantId();

  return useMutation({
    mutationFn: (
      input: TransitionShipmentStatusInput,
    ) =>
      transitionShipmentStatus(
        shipmentId,
        input,
      ),

    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: [
            "shipments",
            activeTenantIdQuery.data,
            shipmentId,
          ],
        }),

        queryClient.invalidateQueries({
          queryKey: [
            "shipments",
            activeTenantIdQuery.data,
          ],
        }),

        queryClient.invalidateQueries({
          queryKey: [
            "shipment-events",
            activeTenantIdQuery.data,
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

  const activeTenantIdQuery =
    useActiveTenantId();

  return useMutation({
    mutationFn: (
      input: RecordShipmentEventInput,
    ) =>
      recordShipmentEvent(
        shipmentId,
        input,
      ),

    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: [
          "shipment-events",
          activeTenantIdQuery.data,
          shipmentId,
        ],
      });
    },
  });
}