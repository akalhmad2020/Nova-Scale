"use client";

import { useState } from "react";

import { useLocations } from "@/features/locations/hooks";
import type {
  ShipmentEventType,
} from "@/features/shipments/events-types";
import { useRecordShipmentEvent } from "@/features/shipments/hooks";

type RecordShipmentEventFormProps = {
  shipmentId: string;
};

const MANUAL_EVENT_TYPES: Array<{
  value: ShipmentEventType;
  label: string;
}> = [
  {
    value: "note_added",
    label: "Note added",
  },
  {
    value: "picked_up",
    label: "Picked up",
  },
  {
    value: "arrived_at_location",
    label: "Arrived at location",
  },
  {
    value: "departed_location",
    label: "Departed location",
  },
];

export function RecordShipmentEventForm({
  shipmentId,
}: RecordShipmentEventFormProps) {
  const mutation =
    useRecordShipmentEvent(shipmentId);

  const locationsQuery =
    useLocations();

  const [eventType, setEventType] =
    useState<ShipmentEventType>(
      "note_added",
    );

  const [
    description,
    setDescription,
  ] = useState("");

  const [
    locationId,
    setLocationId,
  ] = useState("");

  const activeLocations =
    locationsQuery.data?.filter(
      (location) =>
        location.status === "active",
    ) ?? [];

  const locationRequired =
    eventType ===
      "arrived_at_location" ||
    eventType ===
      "departed_location";

  const showLocation =
    eventType !== "note_added";

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (
      locationRequired &&
      !locationId
    ) {
      return;
    }

    await mutation.mutateAsync({
      event_type: eventType,
      occurred_at:
        new Date().toISOString(),
      description:
        description.trim() || null,
      status: null,
      location_id:
        showLocation && locationId
          ? locationId
          : null,
      metadata: null,
    });

    setDescription("");
    setLocationId("");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <div>
        <label
          htmlFor="shipment-event-type"
          className="block text-sm font-medium text-zinc-700"
        >
          Event type
        </label>

        <select
          id="shipment-event-type"
          value={eventType}
          onChange={(event) => {
            const nextEventType =
              event.target
                .value as ShipmentEventType;

            setEventType(
              nextEventType,
            );

            if (
              nextEventType ===
              "note_added"
            ) {
              setLocationId("");
            }
          }}
          className="mt-2 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950"
        >
          {MANUAL_EVENT_TYPES.map(
            (eventTypeOption) => (
              <option
                key={
                  eventTypeOption.value
                }
                value={
                  eventTypeOption.value
                }
              >
                {
                  eventTypeOption.label
                }
              </option>
            ),
          )}
        </select>
      </div>

      {showLocation && (
        <div>
          <label
            htmlFor="shipment-event-location"
            className="block text-sm font-medium text-zinc-700"
          >
            Location
            {locationRequired
              ? " *"
              : ""}
          </label>

          {locationsQuery.isPending && (
            <p className="mt-2 text-sm text-zinc-500">
              Loading locations...
            </p>
          )}

          {locationsQuery.isError && (
            <div className="mt-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              {
                locationsQuery.error
                  .message
              }
            </div>
          )}

          {locationsQuery.isSuccess && (
            <select
              id="shipment-event-location"
              value={locationId}
              onChange={(event) =>
                setLocationId(
                  event.target.value,
                )
              }
              required={
                locationRequired
              }
              className="mt-2 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950"
            >
              <option value="">
                {locationRequired
                  ? "Select a location"
                  : "No location"}
              </option>

              {activeLocations.map(
                (location) => (
                  <option
                    key={location.id}
                    value={
                      location.id
                    }
                  >
                    {location.name} —{" "}
                    {location.city}
                  </option>
                ),
              )}
            </select>
          )}

          {locationsQuery.isSuccess &&
            activeLocations.length ===
              0 && (
              <p className="mt-2 text-sm text-zinc-500">
                No active locations
                available.
              </p>
            )}
        </div>
      )}

      <div>
        <label
          htmlFor="shipment-event-description"
          className="block text-sm font-medium text-zinc-700"
        >
          Description
        </label>

        <textarea
          id="shipment-event-description"
          value={description}
          onChange={(event) =>
            setDescription(
              event.target.value,
            )
          }
          rows={3}
          maxLength={2000}
          placeholder="Add event details..."
          className="mt-2 w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-950"
        />
      </div>

      {mutation.isError && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {mutation.error instanceof
          Error
            ? mutation.error.message
            : "Unable to record shipment event"}
        </div>
      )}

      {mutation.isSuccess && (
        <div className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">
          Shipment event recorded.
        </div>
      )}

      <button
        type="submit"
        disabled={
          mutation.isPending ||
          (showLocation &&
            locationsQuery.isPending) ||
          (locationRequired &&
            !locationId)
        }
        className="rounded-lg bg-zinc-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {mutation.isPending
          ? "Recording..."
          : "Record event"}
      </button>
    </form>
  );
}