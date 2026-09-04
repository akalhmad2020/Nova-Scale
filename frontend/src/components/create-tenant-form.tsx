"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { useCreateTenant } from "@/features/tenants/hooks";
import {
  createTenantSchema,
  type CreateTenantFormValues,
} from "@/features/tenants/schemas";

export function CreateTenantForm() {
  const createTenantMutation = useCreateTenant();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateTenantFormValues>({
    resolver: zodResolver(createTenantSchema),
    defaultValues: {
      name: "",
      slug: "",
    },
  });

  async function onSubmit(
    values: CreateTenantFormValues,
  ) {
    await createTenantMutation.mutateAsync(values);
    reset();
  }

  return (
    <form
      className="mt-4 space-y-4"
      onSubmit={handleSubmit(onSubmit)}
    >
      <div>
        <label
          htmlFor="tenant-name"
          className="mb-2 block text-sm font-medium text-zinc-900"
        >
          Tenant name
        </label>

        <input
          id="tenant-name"
          type="text"
          {...register("name")}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none transition focus:border-zinc-950"
        />

        {errors.name && (
          <p className="mt-2 text-sm text-red-600">
            {errors.name.message}
          </p>
        )}
      </div>

      <div>
        <label
          htmlFor="tenant-slug"
          className="mb-2 block text-sm font-medium text-zinc-900"
        >
          Tenant slug
        </label>

        <input
          id="tenant-slug"
          type="text"
          {...register("slug")}
          className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none transition focus:border-zinc-950"
        />

        {errors.slug && (
          <p className="mt-2 text-sm text-red-600">
            {errors.slug.message}
          </p>
        )}
      </div>

      {createTenantMutation.isError && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {createTenantMutation.error instanceof Error
            ? createTenantMutation.error.message
            : "Unable to create tenant"}
        </p>
      )}

      <button
        type="submit"
        disabled={createTenantMutation.isPending}
        className="w-full rounded-lg bg-zinc-950 px-4 py-2.5 font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {createTenantMutation.isPending
          ? "Creating tenant..."
          : "Create tenant"}
      </button>
    </form>
  );
}