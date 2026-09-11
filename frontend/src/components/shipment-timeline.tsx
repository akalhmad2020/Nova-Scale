"use client";

import { Icon } from "@/components/ui/icon";
import { useLocations } from "@/features/locations/hooks";
import type { ShipmentEvent } from "@/features/shipments/events-types";

const EVENT_LABELS: Record<ShipmentEvent["event_type"], string> = {
  created: "Shipment created",
  status_changed: "Status changed",
  picked_up: "Picked up",
  arrived_at_location: "Arrived at location",
  departed_location: "Departed location",
  note_added: "Note added",
};

export function ShipmentTimeline({ events }: { events: ShipmentEvent[] }) {
  const locationsQuery = useLocations();

  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-5 py-8 text-center">
        <p className="text-sm font-medium text-slate-700">No timeline activity yet</p>
        <p className="mt-1 text-xs text-slate-500">Operational events will appear here as the shipment progresses.</p>
      </div>
    );
  }

  const locations = locationsQuery.data ?? [];

  return (
    <div className="relative space-y-0">
      <div className="absolute bottom-3 left-[0.95rem] top-3 w-px bg-slate-200" />
      {events.map((event, index) => {
        const location = event.location_id
          ? locations.find((item) => item.id === event.location_id)
          : null;

        return (
          <div key={event.id} className="relative grid grid-cols-[2rem_minmax(0,1fr)] gap-3 pb-6 last:pb-0">
            <div className="relative z-10 flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-sm">
              <Icon
                name={event.event_type === "status_changed" ? "activity" : "check"}
                className="h-3.5 w-3.5"
              />
            </div>

            <div className={index === 0 ? "rounded-xl border border-slate-200 bg-slate-50/50 p-4" : "pt-1"}>
              <div className="flex flex-wrap items-center gap-2">
                <p className="text-sm font-semibold text-slate-900">{EVENT_LABELS[event.event_type]}</p>
                {event.status ? (
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                    {formatStatus(event.status)}
                  </span>
                ) : null}
              </div>

              {event.description ? (
                <p className="mt-1.5 text-sm leading-6 text-slate-600">{event.description}</p>
              ) : null}

              {event.location_id ? (
                <p className="mt-1.5 text-xs text-slate-500">
                  {location ? `${location.name} · ${location.city}` : `Location ${event.location_id}`}
                </p>
              ) : null}

              <p className="mt-2 text-[11px] font-medium uppercase tracking-wide text-slate-400">
                {formatDate(event.occurred_at)}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function formatStatus(status: ShipmentEvent["status"]) {
  if (!status) return "";
  return status
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
