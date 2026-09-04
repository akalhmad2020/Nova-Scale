"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { useCreateInvoice } from "@/features/billing/hooks";
import {
  createInvoiceSchema,
  type CreateInvoiceFormValues,
} from "@/features/billing/schemas";
import { useCustomers } from "@/features/customers/hooks";

export function CreateInvoiceForm() {
  const customersQuery = useCustomers();

  const createInvoiceMutation =
    useCreateInvoice();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateInvoiceFormValues>({
    resolver: zodResolver(
      createInvoiceSchema,
    ),
    defaultValues: {
      customer_id: "",
      invoice_number: "",
      currency: "USD",
      tax_amount: "0.00",
    },
  });

  async function onSubmit(
    values: CreateInvoiceFormValues,
  ) {
    await createInvoiceMutation.mutateAsync({
      customer_id: values.customer_id,

      invoice_number:
        values.invoice_number.trim(),

      currency:
        values.currency.trim().toUpperCase(),

      tax_amount:
        values.tax_amount.trim(),
    });

    reset({
      customer_id: "",
      invoice_number: "",
      currency: "USD",
      tax_amount: "0.00",
    });
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="space-y-5"
    >
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label
            htmlFor="invoice-customer"
            className="mb-2 block text-sm font-medium text-zinc-900"
          >
            Customer
          </label>

          <select
            id="invoice-customer"
            {...register("customer_id")}
            disabled={customersQuery.isPending}
            className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <option value="">
              Select a customer
            </option>

            {customersQuery.data?.map(
              (customer) => (
                <option
                  key={customer.id}
                  value={customer.id}
                >
                  {customer.name} —{" "}
                  {customer.code}
                </option>
              ),
            )}
          </select>

          {errors.customer_id && (
            <p className="mt-2 text-sm text-red-600">
              {errors.customer_id.message}
            </p>
          )}

          {customersQuery.isError && (
            <p className="mt-2 text-sm text-red-600">
              {customersQuery.error.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="invoice-number"
            className="mb-2 block text-sm font-medium text-zinc-900"
          >
            Invoice number
          </label>

          <input
            id="invoice-number"
            type="text"
            {...register("invoice_number")}
            placeholder="INV-001"
            className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
          />

          {errors.invoice_number && (
            <p className="mt-2 text-sm text-red-600">
              {errors.invoice_number.message}
            </p>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label
            htmlFor="invoice-currency"
            className="mb-2 block text-sm font-medium text-zinc-900"
          >
            Currency
          </label>

          <input
            id="invoice-currency"
            type="text"
            maxLength={3}
            {...register("currency")}
            className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 uppercase text-zinc-950 outline-none focus:border-zinc-950"
          />

          {errors.currency && (
            <p className="mt-2 text-sm text-red-600">
              {errors.currency.message}
            </p>
          )}
        </div>

        <div>
          <label
            htmlFor="invoice-tax"
            className="mb-2 block text-sm font-medium text-zinc-900"
          >
            Tax amount
          </label>

          <input
            id="invoice-tax"
            type="number"
            min="0"
            step="0.01"
            {...register("tax_amount")}
            className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none focus:border-zinc-950"
          />

          {errors.tax_amount && (
            <p className="mt-2 text-sm text-red-600">
              {errors.tax_amount.message}
            </p>
          )}
        </div>
      </div>

      {createInvoiceMutation.isError && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {createInvoiceMutation.error instanceof
          Error
            ? createInvoiceMutation.error.message
            : "Unable to create invoice"}
        </div>
      )}

      <button
        type="submit"
        disabled={
          createInvoiceMutation.isPending ||
          customersQuery.isPending ||
          !customersQuery.data?.length
        }
        className="rounded-lg bg-zinc-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {createInvoiceMutation.isPending
          ? "Creating..."
          : "Create invoice"}
      </button>
    </form>
  );
}