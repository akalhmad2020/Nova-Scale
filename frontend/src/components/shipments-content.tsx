"use client";

import Link from "next/link";

import { CreateShipmentForm } from "@/components/create-shipment-form";
import { EmptyState } from "@/components/ui/empty-state";
import { Icon } from "@/components/ui/icon";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { useShipments } from "@/features/shipments/hooks";

export function ShipmentsContent() {
  const shipmentsQuery = useShipments();

  if (shipmentsQuery.isPending) {
    return <ListSkeleton title="Shipments" />;
  }

  if (shipmentsQuery.isError) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        <p className="font-semibold">Unable to load shipments</p>
        <p className="mt-1">{shipmentsQuery.error.message}</p>
      </div>
    );
  }

  const shipments = shipmentsQuery.data ?? [];
  const activeCount = shipments.filter((shipment) =>
    ["ready", "in_transit"].includes(shipment.status),
  ).length;

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Execution"
        title="Shipments"
        description="Create shipments, monitor lifecycle state, review operational intelligence, and open each record for timeline activity."
        actions={
          <div className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-sm">
            {activeCount} active · {shipments.length} total
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <Surface className="min-w-0 overflow-hidden xl:order-1">
          <SurfaceHeader
            title="Shipment register"
            description="Operational records for the active workspace"
            meta={`${shipments.length} record${shipments.length === 1 ? "" : "s"}`}
          />

          {shipments.length === 0 ? (
            <EmptyState
              icon="shipments"
              title="No shipments yet"
              description="Create your first shipment using the setup panel. It will appear here immediately."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-slate-50/80 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Shipment</th>
                    <th className="px-5 py-3 font-semibold">Status</th>
                    <th className="px-5 py-3 font-semibold">Service</th>
                    <th className="px-5 py-3 font-semibold">Weight</th>
                    <th className="px-5 py-3 font-semibold">Reference</th>
                    <th className="px-5 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {shipments.map((shipment) => (
                    <tr key={shipment.id} className="group transition hover:bg-slate-50/70">
                      <td className="px-6 py-4">
                        <Link
                          href={`/shipments/${shipment.id}`}
                          className="font-semibold text-slate-950 transition hover:text-cyan-700"
                        >
                          {shipment.tracking_number}
                        </Link>
                        <p className="mt-1 max-w-[18rem] truncate text-xs text-slate-500">
                          {shipment.description ?? "No description"}
                        </p>
                      </td>
                      <td className="px-5 py-4">
                        <StatusBadge value={shipment.status} />
                      </td>
                      <td className="px-5 py-4 text-slate-600">
                        {formatValue(shipment.service_type)}
                      </td>
                      <td className="px-5 py-4 font-medium text-slate-700">
                        {shipment.weight} {shipment.weight_unit.toUpperCase()}
                      </td>
                      <td className="px-5 py-4 text-slate-600">
                        {shipment.reference ?? "—"}
                      </td>
                      <td className="px-5 py-4 text-right">
                        <Link
                          href={`/shipments/${shipment.id}`}
                          aria-label={`Open ${shipment.tracking_number}`}
                          className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-900"
                        >
                          <Icon name="arrow-right" className="h-4 w-4" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Surface>

        <Surface className="h-fit xl:order-2">
          <SurfaceHeader
            title="Create shipment"
            description="Start a new operational record"
          />
          <div className="p-5 sm:p-6">
            <CreateShipmentForm />
          </div>
        </Surface>
      </div>
    </div>
  );
}

function ListSkeleton({ title }: { title: string }) {
  return (
    <div className="space-y-6">
      <div>
        <div className="h-3 w-24 animate-pulse rounded bg-slate-200" />
        <div className="mt-3 h-8 w-48 animate-pulse rounded bg-slate-200" />
        <div className="mt-3 h-4 w-96 max-w-full animate-pulse rounded bg-slate-100" />
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-6">
        <p className="text-sm text-slate-500">Loading {title.toLowerCase()}...</p>
      </div>
    </div>
  );
}

function formatValue(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
