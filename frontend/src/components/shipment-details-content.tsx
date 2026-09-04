"use client";

import { ShipmentTimeline } from "@/components/shipment-timeline";
import { RecordShipmentEventForm } from "@/components/record-shipment-event-form";
import {
  useShipment,
  useShipmentEvents,
  useTransitionShipmentStatus,
} from "@/features/shipments/hooks";
import type {
  ShipmentStatus,
} from "@/features/shipments/types";

type ShipmentDetailsContentProps = {
  shipmentId: string;
};

export function ShipmentDetailsContent({
  shipmentId,
}: ShipmentDetailsContentProps) {
  const shipmentQuery =
    useShipment(shipmentId);

  const shipmentEventsQuery =
    useShipmentEvents(shipmentId);

  const transitionMutation =
    useTransitionShipmentStatus(
      shipmentId,
    );

  if (shipmentQuery.isPending) {
    return (
      <p className="text-sm text-zinc-600">
        Loading shipment...
      </p>
    );
  }

  if (shipmentQuery.isError) {
    return (
      <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
        {shipmentQuery.error.message}
      </div>
    );
  }

  const shipment = shipmentQuery.data;

  const nextStatus =
    getNextShipmentStatus(
      shipment.status,
    );

  async function handleTransition() {
    if (!nextStatus) {
      return;
    }

    await transitionMutation.mutateAsync({
      status: nextStatus,
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-zinc-500">
          Shipment
        </p>

        <h1 className="mt-1 text-2xl font-semibold text-zinc-950">
          {shipment.tracking_number}
        </h1>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-zinc-500">
              Current status
            </p>

            <p className="mt-1 text-lg font-medium text-zinc-950">
              {formatValue(
                shipment.status,
              )}
            </p>
          </div>

          {nextStatus && (
            <button
              type="button"
              onClick={
                handleTransition
              }
              disabled={
                transitionMutation.isPending
              }
              className="rounded-lg bg-zinc-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {transitionMutation.isPending
                ? "Updating..."
                : `Move to ${formatValue(
                    nextStatus,
                  )}`}
            </button>
          )}
        </div>

        {transitionMutation.isError && (
          <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {transitionMutation.error instanceof
            Error
              ? transitionMutation.error
                  .message
              : "Unable to update shipment status"}
          </div>
        )}

        {!nextStatus &&
          shipment.status ===
            "delivered" && (
            <p className="mt-4 text-sm text-zinc-500">
              This shipment has been
              delivered.
            </p>
          )}

        {!nextStatus &&
          shipment.status ===
            "cancelled" && (
            <p className="mt-4 text-sm text-zinc-500">
              This shipment has been
              cancelled.
            </p>
          )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Detail
          label="Service"
          value={formatValue(
            shipment.service_type,
          )}
        />

        <Detail
          label="Weight"
          value={`${shipment.weight} ${shipment.weight_unit.toUpperCase()}`}
        />

        <Detail
          label="Reference"
          value={
            shipment.reference ?? "—"
          }
        />

        <Detail
          label="Description"
          value={
            shipment.description ?? "—"
          }
        />

        <Detail
          label="Notes"
          value={shipment.notes ?? "—"}
        />

        <Detail
          label="Created"
          value={formatDateTime(
            shipment.created_at,
          )}
        />
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
  <h2 className="font-medium text-zinc-950">
    Record shipment event
  </h2>

  <p className="mt-1 text-sm text-zinc-500">
    Add an operational event to this shipment.
  </p>

  <div className="mt-5">
    <RecordShipmentEventForm
      shipmentId={shipmentId}
    />
  </div>
</div>

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <h2 className="font-medium text-zinc-950">
          Shipment timeline
        </h2>

        <div className="mt-5">
          {shipmentEventsQuery.isPending && (
            <p className="text-sm text-zinc-500">
              Loading shipment events...
            </p>
          )}

          {shipmentEventsQuery.isError && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              {shipmentEventsQuery.error.message}
            </div>
          )}

          {shipmentEventsQuery.isSuccess && (
            <ShipmentTimeline
              events={
                shipmentEventsQuery.data
              }
            />
          )}
        </div>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <h2 className="font-medium text-zinc-950">
          Shipment identifiers
        </h2>

        <dl className="mt-4 space-y-3 text-sm">
          <Identifier
            label="Shipment ID"
            value={shipment.id}
          />

          <Identifier
            label="Customer ID"
            value={shipment.customer_id}
          />

          <Identifier
            label="Origin location ID"
            value={
              shipment.origin_location_id
            }
          />

          <Identifier
            label="Destination location ID"
            value={
              shipment.destination_location_id
            }
          />
        </dl>
      </div>
    </div>
  );
}

type DetailProps = {
  label: string;
  value: string;
};

function Detail({
  label,
  value,
}: DetailProps) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5">
      <p className="text-sm text-zinc-500">
        {label}
      </p>

      <p className="mt-2 font-medium text-zinc-950">
        {value}
      </p>
    </div>
  );
}

function Identifier({
  label,
  value,
}: DetailProps) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:justify-between">
      <dt className="text-zinc-500">
        {label}
      </dt>

      <dd className="break-all font-mono text-xs text-zinc-800">
        {value}
      </dd>
    </div>
  );
}

function getNextShipmentStatus(
  status: ShipmentStatus,
): ShipmentStatus | null {
  switch (status) {
    case "draft":
      return "ready";

    case "ready":
      return "in_transit";

    case "in_transit":
      return "delivered";

    case "delivered":
    case "cancelled":
      return null;
  }
}

function formatValue(
  value: string,
): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(" ");
}

function formatDateTime(
  value: string,
): string {
  return new Intl.DateTimeFormat(
    undefined,
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(new Date(value));
}