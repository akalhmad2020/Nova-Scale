"use client";

import { CreateLocationForm } from "@/components/create-location-form";
import { useLocations } from "@/features/locations/hooks";

export function LocationsContent() {
  const locationsQuery = useLocations();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-950">
          Locations
        </h1>

        <p className="mt-1 text-sm text-zinc-600">
          Manage locations for the active tenant.
        </p>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <div className="mb-5">
          <h2 className="font-medium text-zinc-950">
            Create location
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Add a warehouse, office, pickup,
            delivery, or other location.
          </p>
        </div>

        <CreateLocationForm />
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 px-5 py-4">
          <h2 className="font-medium text-zinc-950">
            Location list
          </h2>
        </div>

        {locationsQuery.isPending && (
          <div className="p-5 text-sm text-zinc-600">
            Loading locations...
          </div>
        )}

        {locationsQuery.isError && (
          <div className="p-5 text-sm text-red-600">
            {locationsQuery.error.message}
          </div>
        )}

        {locationsQuery.data?.length === 0 && (
          <div className="p-10 text-center">
            <p className="font-medium text-zinc-900">
              No locations yet
            </p>
          </div>
        )}

        {locationsQuery.data &&
          locationsQuery.data.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-zinc-200 bg-zinc-50">
                  <tr>
                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Name
                    </th>
                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Code
                    </th>
                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Type
                    </th>
                    <th className="px-5 py-3 font-medium text-zinc-600">
                      City
                    </th>
                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Status
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {locationsQuery.data.map(
                    (location) => (
                      <tr
                        key={location.id}
                        className="border-b border-zinc-100 last:border-b-0"
                      >
                        <td className="px-5 py-4 font-medium text-zinc-950">
                          {location.name}
                        </td>

                        <td className="px-5 py-4 text-zinc-700">
                          {location.code}
                        </td>

                        <td className="px-5 py-4 text-zinc-700">
                          {location.type}
                        </td>

                        <td className="px-5 py-4 text-zinc-700">
                          {location.city}
                        </td>

                        <td className="px-5 py-4 text-zinc-700">
                          {location.status}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}
      </div>
    </div>
  );
}