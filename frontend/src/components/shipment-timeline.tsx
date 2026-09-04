"use client";

import { useLocations } from "@/features/locations/hooks";
import type { ShipmentEvent } from "@/features/shipments/events-types";

type ShipmentTimelineProps = {
  events: ShipmentEvent[];
};

const EVENT_LABELS: Record<
  ShipmentEvent["event_type"],
  string
> = {
  created: "Shipment created",
  status_changed: "Status changed",
  picked_up: "Picked up",
  arrived_at_location: "Arrived at location",
  departed_location: "Departed location",
  note_added: "Note added",
};

export function ShipmentTimeline({
  events,
}: ShipmentTimelineProps) {
  const locationsQuery = useLocations();

  if (events.length === 0) {
    return (
      <p className="text-sm text-zinc-500">
        No shipment events yet.
      </p>
    );
  }

  const locations =
    locationsQuery.data ?? [];

  return (
    <div className="space-y-6">
      {events.map((event) => {
        const location =
          event.location_id
            ? locations.find(
                (item) =>
                  item.id ===
                  event.location_id,
              )
            : null;

        return (
          <div
            key={event.id}
            className="border-l-2 border-zinc-200 pl-4"
          >
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-medium text-zinc-950">
                {
                  EVENT_LABELS[
                    event.event_type
                  ]
                }
              </p>

              {event.status ? (
                <span className="rounded bg-zinc-100 px-2 py-1 text-xs text-zinc-700">
                  {formatStatus(
                    event.status,
                  )}
                </span>
              ) : null}
            </div>

            {event.description ? (
              <p className="mt-2 text-sm text-zinc-600">
                {event.description}
              </p>
            ) : null}

            {event.location_id ? (
              <p className="mt-2 text-sm text-zinc-600">
                Location:{" "}
                {location
                  ? `${location.name} — ${location.city}`
                  : event.location_id}
              </p>
            ) : null}

            <p className="mt-2 text-xs text-zinc-500">
              {formatDate(
                event.occurred_at,
              )}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function formatStatus(
  status: ShipmentEvent["status"],
): string {
  if (!status) {
    return "";
  }

  return status
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(" ");
}

function formatDate(
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