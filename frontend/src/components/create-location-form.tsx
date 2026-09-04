"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { useCreateLocation } from "@/features/locations/hooks";
import {
  createLocationSchema,
  type CreateLocationFormValues,
} from "@/features/locations/schemas";

export function CreateLocationForm() {
  const createLocationMutation =
    useCreateLocation();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateLocationFormValues>({
    resolver: zodResolver(
      createLocationSchema,
    ),
    defaultValues: {
      name: "",
      code: "",
      type: "warehouse",
      country_code: "",
      state: "",
      city: "",
      postal_code: "",
      address_line1: "",
      address_line2: "",
      contact_name: "",
      email: "",
      phone: "",
      latitude: "",
      longitude: "",
      notes: "",
    },
  });

  async function onSubmit(
    values: CreateLocationFormValues,
  ) {
    await createLocationMutation.mutateAsync({
      name: values.name.trim(),
      code: values.code.trim(),
      type: values.type,

      country_code:
        values.country_code
          .trim()
          .toUpperCase(),

      state: normalizeOptionalString(
        values.state,
      ),

      city: values.city.trim(),

      postal_code: normalizeOptionalString(
        values.postal_code,
      ),

      address_line1:
        values.address_line1.trim(),

      address_line2:
        normalizeOptionalString(
          values.address_line2,
        ),

      contact_name:
        normalizeOptionalString(
          values.contact_name,
        ),

      email: normalizeOptionalString(
        values.email,
      ),

      phone: normalizeOptionalString(
        values.phone,
      ),

      latitude: normalizeOptionalString(
        values.latitude,
      ),

      longitude: normalizeOptionalString(
        values.longitude,
      ),

      notes: normalizeOptionalString(
        values.notes,
      ),
    });

    reset();
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-5"
    >
      <div className="grid gap-4 md:grid-cols-2">
        <Field
          label="Name"
          error={errors.name?.message}
        >
          <input
            {...register("name")}
            className={inputClassName}
          />
        </Field>

        <Field
          label="Code"
          error={errors.code?.message}
        >
          <input
            {...register("code")}
            className={inputClassName}
          />
        </Field>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Field
          label="Type"
          error={errors.type?.message}
        >
          <select
            {...register("type")}
            className={inputClassName}
          >
            <option value="warehouse">
              Warehouse
            </option>
            <option value="office">
              Office
            </option>
            <option value="store">
              Store
            </option>
            <option value="pickup">
              Pickup
            </option>
            <option value="delivery">
              Delivery
            </option>
            <option value="other">
              Other
            </option>
          </select>
        </Field>

        <Field
          label="Country code"
          error={
            errors.country_code?.message
          }
        >
          <input
            placeholder="PS"
            maxLength={2}
            {...register("country_code")}
            className={inputClassName}
          />
        </Field>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Field
          label="City"
          error={errors.city?.message}
        >
          <input
            {...register("city")}
            className={inputClassName}
          />
        </Field>

        <Field
          label="State"
          error={errors.state?.message}
        >
          <input
            {...register("state")}
            className={inputClassName}
          />
        </Field>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Field
          label="Address line 1"
          error={
            errors.address_line1?.message
          }
        >
          <input
            {...register("address_line1")}
            className={inputClassName}
          />
        </Field>

        <Field
          label="Address line 2"
          error={
            errors.address_line2?.message
          }
        >
          <input
            {...register("address_line2")}
            className={inputClassName}
          />
        </Field>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Field
          label="Postal code"
          error={
            errors.postal_code?.message
          }
        >
          <input
            {...register("postal_code")}
            className={inputClassName}
          />
        </Field>

        <Field
          label="Contact name"
          error={
            errors.contact_name?.message
          }
        >
          <input
            {...register("contact_name")}
            className={inputClassName}
          />
        </Field>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Field
          label="Email"
          error={errors.email?.message}
        >
          <input
            type="email"
            {...register("email")}
            className={inputClassName}
          />
        </Field>

        <Field
          label="Phone"
          error={errors.phone?.message}
        >
          <input
            {...register("phone")}
            className={inputClassName}
          />
        </Field>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Field
          label="Latitude"
          error={
            errors.latitude?.message
          }
        >
          <input
            type="number"
            step="any"
            {...register("latitude")}
            className={inputClassName}
          />
        </Field>

        <Field
          label="Longitude"
          error={
            errors.longitude?.message
          }
        >
          <input
            type="number"
            step="any"
            {...register("longitude")}
            className={inputClassName}
          />
        </Field>
      </div>

      <Field
        label="Notes"
        error={errors.notes?.message}
      >
        <textarea
          rows={3}
          {...register("notes")}
          className={inputClassName}
        />
      </Field>

      {createLocationMutation.isError && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {createLocationMutation.error instanceof
          Error
            ? createLocationMutation.error.message
            : "Unable to create location"}
        </div>
      )}

      <button
        type="submit"
        disabled={
          createLocationMutation.isPending
        }
        className="rounded-lg bg-zinc-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {createLocationMutation.isPending
          ? "Creating..."
          : "Create location"}
      </button>
    </form>
  );
}

type FieldProps = {
  label: string;
  error?: string;
  children: React.ReactNode;
};

function Field({
  label,
  error,
  children,
}: FieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-zinc-900">
        {label}
      </span>

      {children}

      {error && (
        <span className="mt-2 block text-sm text-red-600">
          {error}
        </span>
      )}
    </label>
  );
}

function normalizeOptionalString(
  value: string | undefined,
): string | null {
  const normalized = value?.trim();

  return normalized ? normalized : null;
}

const inputClassName =
  "w-full rounded-lg border border-zinc-300 bg-white px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950";