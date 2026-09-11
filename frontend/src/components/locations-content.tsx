"use client";

import { CreateLocationForm } from "@/components/create-location-form";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge, formatStatus } from "@/components/ui/status-badge";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { useLocations } from "@/features/locations/hooks";

export function LocationsContent() {
  const locationsQuery = useLocations();
  const locations = locationsQuery.data ?? [];

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Network"
        title="Locations"
        description="Manage warehouses, offices, pickup points, and delivery facilities used by shipment operations."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_25rem]">
        <Surface className="min-w-0 overflow-hidden">
          <SurfaceHeader
            title="Location network"
            description="Facilities available to the active workspace"
            meta={`${locations.length} location${locations.length === 1 ? "" : "s"}`}
          />

          {locationsQuery.isPending ? (
            <div className="p-6 text-sm text-slate-500">Loading locations...</div>
          ) : locationsQuery.isError ? (
            <div className="p-6 text-sm text-rose-600">{locationsQuery.error.message}</div>
          ) : locations.length === 0 ? (
            <EmptyState
              icon="locations"
              title="No locations yet"
              description="Add at least two operational locations before creating shipment routes."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-slate-50/80 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Location</th>
                    <th className="px-5 py-3 font-semibold">Type</th>
                    <th className="px-5 py-3 font-semibold">City</th>
                    <th className="px-5 py-3 font-semibold">Code</th>
                    <th className="px-5 py-3 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {locations.map((location) => (
                    <tr key={location.id} className="transition hover:bg-slate-50/70">
                      <td className="px-6 py-4">
                        <p className="font-semibold text-slate-950">{location.name}</p>
                        <p className="mt-1 text-xs text-slate-500">
                          {location.address_line1}{location.address_line2 ? `, ${location.address_line2}` : ""}
                        </p>
                      </td>
                      <td className="px-5 py-4 text-slate-600">{formatStatus(location.type)}</td>
                      <td className="px-5 py-4 text-slate-600">
                        {location.city}, {location.country_code}
                      </td>
                      <td className="px-5 py-4 font-mono text-xs text-slate-600">{location.code}</td>
                      <td className="px-5 py-4"><StatusBadge value={location.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Surface>

        <Surface className="h-fit">
          <SurfaceHeader title="Add location" description="Expand the operating network" />
          <div className="max-h-[70vh] overflow-y-auto p-5 sm:p-6"><CreateLocationForm /></div>
        </Surface>
      </div>
    </div>
  );
}
