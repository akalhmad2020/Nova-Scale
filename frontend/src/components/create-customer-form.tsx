"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { useCreateCustomer } from "@/features/customers/hooks";
import {
  createCustomerSchema,
  type CreateCustomerFormValues,
} from "@/features/customers/schemas";

export function CreateCustomerForm() {
  const createCustomerMutation =
    useCreateCustomer();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateCustomerFormValues>({
    resolver: zodResolver(
      createCustomerSchema,
    ),
    defaultValues: {
      name: "",
      code: "",
      email: "",
      phone: "",
      notes: "",
    },
  });

  async function onSubmit(
    values: CreateCustomerFormValues,
  ) {
    await createCustomerMutation.mutateAsync({
      name: values.name.trim(),
      code: values.code.trim(),

      email: normalizeOptionalString(
        values.email,
      ),

      phone: normalizeOptionalString(
        values.phone,
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
        <div>
          <label
            htmlFor="customer-name"
            className="mb-2 block text-sm font-medium text-slate-900"
          >
            Name
          </label>

          <input
            id="customer-name"
            type="text"
            {...register("name")}
            className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-slate-950 outline-none focus:border-cyan-600"
          />

          {errors.name && (
            <p className="mt-2 text-sm text-rose-600">
              {errors.name.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="customer-code"
            className="mb-2 block text-sm font-medium text-slate-900"
          >
            Code
          </label>

          <input
            id="customer-code"
            type="text"
            {...register("code")}
            className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-slate-950 outline-none focus:border-cyan-600"
          />

          {errors.code && (
            <p className="mt-2 text-sm text-rose-600">
              {errors.code.message}
            </p>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label
            htmlFor="customer-email"
            className="mb-2 block text-sm font-medium text-slate-900"
          >
            Email
          </label>

          <input
            id="customer-email"
            type="email"
            {...register("email")}
            className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-slate-950 outline-none focus:border-cyan-600"
          />

          {errors.email && (
            <p className="mt-2 text-sm text-rose-600">
              {errors.email.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="customer-phone"
            className="mb-2 block text-sm font-medium text-slate-900"
          >
            Phone
          </label>

          <input
            id="customer-phone"
            type="text"
            {...register("phone")}
            className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-slate-950 outline-none focus:border-cyan-600"
          />
        </div>
      </div>

      <div>
        <label
          htmlFor="customer-notes"
          className="mb-2 block text-sm font-medium text-slate-900"
        >
          Notes
        </label>

        <textarea
          id="customer-notes"
          rows={3}
          {...register("notes")}
          className="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-slate-950 outline-none focus:border-cyan-600"
        />
      </div>

      {createCustomerMutation.isError && (
        <div className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {createCustomerMutation.error instanceof
          Error
            ? createCustomerMutation.error.message
            : "Unable to create customer"}
        </div>
      )}

      <button
        type="submit"
        disabled={
          createCustomerMutation.isPending
        }
        className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {createCustomerMutation.isPending
          ? "Creating..."
          : "Create customer"}
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
