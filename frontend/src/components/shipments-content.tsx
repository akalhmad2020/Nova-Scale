"use client";

import { useShipments } from "@/features/shipments/hooks";
import { CreateShipmentForm } from "@/components/create-shipment-form";
import Link from "next/link";

export function ShipmentsContent() {
  const shipmentsQuery = useShipments();

  if (shipmentsQuery.isPending) {
    return (
      <p className="text-sm text-zinc-600">
        Loading shipments...
      </p>
    );
  }

  if (shipmentsQuery.isError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5">
        <p className="text-sm font-medium text-red-700">
          Unable to load shipments.
        </p>

        <p className="mt-1 text-sm text-red-600">
          {shipmentsQuery.error.message}
        </p>
      </div>
    );
  }

  const shipments = shipmentsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-950">
          Shipments
        </h1>

        <div className="rounded-xl border border-zinc-200 bg-white p-5">
  <div className="mb-5">
    <h2 className="font-medium text-zinc-950">
      Create shipment
    </h2>

    <p className="mt-1 text-sm text-zinc-500">
      Create a shipment for the active tenant.
    </p>
  </div>

  <CreateShipmentForm />
</div>

        <p className="mt-1 text-sm text-zinc-600">
          Shipments for the active tenant.
        </p>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 px-5 py-4">
          <p className="font-medium text-zinc-950">
            Shipment list
          </p>

          <p className="mt-1 text-sm text-zinc-500">
            {shipments.length} shipment
            {shipments.length === 1 ? "" : "s"}
          </p>
        </div>

        {shipments.length === 0 ? (
          <div className="px-5 py-10 text-center">
            <p className="font-medium text-zinc-900">
              No shipments yet
            </p>

            <p className="mt-1 text-sm text-zinc-500">
              Shipments created for this tenant will appear here.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-zinc-200 bg-zinc-50">
                <tr>
                  <th className="px-5 py-3 font-medium text-zinc-600">
                    Tracking number
                  </th>

                  <th className="px-5 py-3 font-medium text-zinc-600">
                    Status
                  </th>

                  <th className="px-5 py-3 font-medium text-zinc-600">
                    Service
                  </th>

                  <th className="px-5 py-3 font-medium text-zinc-600">
                    Weight
                  </th>

                  <th className="px-5 py-3 font-medium text-zinc-600">
                    Reference
                  </th>
                </tr>
              </thead>

              <tbody>
                {shipments.map((shipment) => (
                  <tr
                    key={shipment.id}
                    className="border-b border-zinc-100 last:border-b-0"
                  >
                    <td className="px-5 py-4 font-medium text-zinc-950">
                      <Link
  href={`/shipments/${shipment.id}`}
  className="font-medium text-zinc-950 hover:underline"
>
  {shipment.tracking_number}
</Link>
                    </td>

                    <td className="px-5 py-4 text-zinc-700">
                      {formatShipmentStatus(
                        shipment.status,
                      )}
                    </td>

                    <td className="px-5 py-4 text-zinc-700">
                      {formatServiceType(
                        shipment.service_type,
                      )}
                    </td>

                    <td className="px-5 py-4 text-zinc-700">
                      {shipment.weight}{" "}
                      {shipment.weight_unit.toUpperCase()}
                    </td>

                    <td className="px-5 py-4 text-zinc-700">
                      {shipment.reference ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function formatShipmentStatus(
  status: string,
): string {
  return status
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(" ");
}

function formatServiceType(
  serviceType: string,
): string {
  return (
    serviceType.charAt(0).toUpperCase() +
    serviceType.slice(1)
  );
}