"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { useCustomers } from "@/features/customers/hooks";
import { useLocations } from "@/features/locations/hooks";
import {
  createShipmentSchema,
  type CreateShipmentFormValues,
} from "@/features/shipments/schemas";
import { useCreateShipment } from "@/features/shipments/hooks";

export function CreateShipmentForm() {
  const customersQuery = useCustomers();
  const locationsQuery = useLocations();

  const createShipmentMutation =
    useCreateShipment();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateShipmentFormValues>({
    resolver: zodResolver(
      createShipmentSchema,
    ),
    defaultValues: {
      customer_id: "",
      origin_location_id: "",
      destination_location_id: "",
      tracking_number: "",
      reference: "",
      service_type: "standard",
      description: "",
      weight: "",
      weight_unit: "kg",
      notes: "",
    },
  });

  async function onSubmit(
    values: CreateShipmentFormValues,
  ) {
    await createShipmentMutation.mutateAsync({
      customer_id: values.customer_id,
      origin_location_id:
        values.origin_location_id,
      destination_location_id:
        values.destination_location_id,

      tracking_number:
        values.tracking_number,

      reference:
        normalizeOptionalString(
          values.reference,
        ),

      service_type:
        values.service_type,

      description:
        normalizeOptionalString(
          values.description,
        ),

      weight: values.weight,
      weight_unit: values.weight_unit,

      notes:
        normalizeOptionalString(
          values.notes,
        ),
    });

    reset();
  }

  if (
    customersQuery.isPending ||
    locationsQuery.isPending
  ) {
    return (
      <p className="text-sm text-zinc-600">
        Loading shipment form...
      </p>
    );
  }

  if (
    customersQuery.isError ||
    locationsQuery.isError
  ) {
    return (
      <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
        Unable to load customers or locations.
      </div>
    );
  }

  const customers =
    customersQuery.data ?? [];

  const locations =
    locationsQuery.data ?? [];

  const canCreateShipment =
    customers.length > 0 &&
    locations.length >= 2;

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-5"
    >
      {!canCreateShipment && (
        <div className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
          You need at least one customer
          and two locations before creating
          a shipment.
        </div>
      )}

      <div>
        <label
          htmlFor="shipment-customer"
          className="mb-2 block text-sm font-medium text-zinc-900"
        >
          Customer
        </label>

        <select
          id="shipment-customer"
          {...register("customer_id")}
          className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
        >
          <option value="">
            Select customer
          </option>

          {customers.map((customer) => (
            <option
              key={customer.id}
              value={customer.id}
            >
              {customer.name} ({customer.code})
            </option>
          ))}
        </select>

        {errors.customer_id && (
          <p className="mt-2 text-sm text-red-600">
            {errors.customer_id.message}
          </p>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label
            htmlFor="shipment-origin"
            className="mb-2 block text-sm font-medium text-zinc-900"
          >
            Origin
          </label>

          <select
            id="shipment-origin"
            {...register(
              "origin_location_id",
            )}
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
          >
            <option value="">
              Select origin
            </option>

            {locations.map((location) => (
              <option
                key={location.id}
                value={location.id}
              >
                {location.name} ({location.code})
              </option>
            ))}
          </select>

          {errors.origin_location_id && (
            <p className="mt-2 text-sm text-red-600">
              {
                errors.origin_location_id
                  .message
              }
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="shipment-destination"
            className="mb-2 block text-sm font-medium text-zinc-900"
          >
            Destination
          </label>

          <select
            id="shipment-destination"
            {...register(
              "destination_location_id",
            )}
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
          >
            <option value="">
              Select destination
            </option>

            {locations.map((location) => (
              <option
                key={location.id}
                value={location.id}
              >
                {location.name} ({location.code})
              </option>
            ))}
          </select>

          {errors.destination_location_id && (
            <p className="mt-2 text-sm text-red-600">
              {
                errors.destination_location_id
                  .message
              }
            </p>
          )}
        </div>
      </div>

      <div>
        <label
          htmlFor="tracking-number"
          className="mb-2 block text-sm font-medium text-zinc-900"
        >
          Tracking number
        </label>

        <input
          id="tracking-number"
          type="text"
          {...register("tracking_number")}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
        />

        {errors.tracking_number && (
          <p className="mt-2 text-sm text-red-600">
            {errors.tracking_number.message}
          </p>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label
            htmlFor="shipment-service"
            className="mb-2 block text-sm font-medium text-zinc-900"
          >
            Service type
          </label>

          <select
            id="shipment-service"
            {...register("service_type")}
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
          >
            <option value="standard">
              Standard
            </option>

            <option value="express">
              Express
            </option>
          </select>
        </div>

        <div>
          <label
            htmlFor="shipment-reference"
            className="mb-2 block text-sm font-medium text-zinc-900"
          >
            Reference
          </label>

          <input
            id="shipment-reference"
            type="text"
            {...register("reference")}
            className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
          />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label
            htmlFor="shipment-weight"
            className="mb-2 block text-sm font-medium text-zinc-900"
          >
            Weight
          </label>

          <input
            id="shipment-weight"
            type="number"
            min="0"
            step="any"
            {...register("weight")}
            className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
          />

          {errors.weight && (
            <p className="mt-2 text-sm text-red-600">
              {errors.weight.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="shipment-weight-unit"
            className="mb-2 block text-sm font-medium text-zinc-900"
          >
            Weight unit
          </label>

          <select
            id="shipment-weight-unit"
            {...register("weight_unit")}
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
          >
            <option value="kg">
              KG
            </option>

            <option value="lb">
              LB
            </option>
          </select>
        </div>
      </div>

      <div>
        <label
          htmlFor="shipment-description"
          className="mb-2 block text-sm font-medium text-zinc-900"
        >
          Description
        </label>

        <textarea
          id="shipment-description"
          rows={3}
          {...register("description")}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
        />
      </div>

      <div>
        <label
          htmlFor="shipment-notes"
          className="mb-2 block text-sm font-medium text-zinc-900"
        >
          Notes
        </label>

        <textarea
          id="shipment-notes"
          rows={3}
          {...register("notes")}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
        />
      </div>

      {createShipmentMutation.isError && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {createShipmentMutation.error instanceof
          Error
            ? createShipmentMutation.error
                .message
            : "Unable to create shipment"}
        </div>
      )}

      <button
        type="submit"
        disabled={
          createShipmentMutation.isPending ||
          !canCreateShipment
        }
        className="rounded-lg bg-zinc-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {createShipmentMutation.isPending
          ? "Creating..."
          : "Create shipment"}
      </button>
    </form>
  );
}

function normalizeOptionalString(
  value: string | undefined,
): string | null {
  const normalized = value?.trim();

  return normalized ? normalized : null;
}