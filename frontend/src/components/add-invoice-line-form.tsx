"use client";

import {
  useForm,
} from "react-hook-form";

import { useAddInvoiceLine } from "@/features/billing/hooks";
import type {
  AddInvoiceLineInput,
} from "@/features/billing/types";

type AddInvoiceLineFormProps = {
  invoiceId: string;
};

type FormValues = {
  shipment_id: string;
  description: string;
  quantity: string;
  unit_price: string;
};

export function AddInvoiceLineForm({
  invoiceId,
}: AddInvoiceLineFormProps) {
  const addInvoiceLineMutation =
    useAddInvoiceLine(invoiceId);

  const {
    register,
    handleSubmit,
    reset,
    formState: {
      errors,
    },
  } = useForm<FormValues>({
    defaultValues: {
      shipment_id: "",
      description: "",
      quantity: "1.0000",
      unit_price: "0.00",
    },
  });

  async function onSubmit(
    values: FormValues,
  ) {
    const input: AddInvoiceLineInput = {
      shipment_id:
        values.shipment_id.trim() ||
        null,
      description:
        values.description.trim(),
      quantity:
        values.quantity.trim(),
      unit_price:
        values.unit_price.trim(),
    };

    await addInvoiceLineMutation.mutateAsync(
      input,
    );

    reset({
      shipment_id: "",
      description: "",
      quantity: "1.0000",
      unit_price: "0.00",
    });
  }

  return (
    <form
      onSubmit={handleSubmit(
        onSubmit,
      )}
      className="space-y-4"
    >
      <div>
        <label
          htmlFor="description"
          className="block text-sm font-medium text-slate-700"
        >
          Description
        </label>

        <input
          id="description"
          {...register(
            "description",
            {
              required:
                "Description is required",
              maxLength: {
                value: 500,
                message:
                  "Description is too long",
              },
            },
          )}
          className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-cyan-600"
        />

        {errors.description && (
          <p className="mt-1 text-sm text-rose-600">
            {errors.description.message}
          </p>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="quantity"
            className="block text-sm font-medium text-slate-700"
          >
            Quantity
          </label>

          <input
            id="quantity"
            type="number"
            step="0.0001"
            min="0.0001"
            {...register(
              "quantity",
              {
                required:
                  "Quantity is required",
              },
            )}
            className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-cyan-600"
          />
        </div>

        <div>
          <label
            htmlFor="unit_price"
            className="block text-sm font-medium text-slate-700"
          >
            Unit price
          </label>

          <input
            id="unit_price"
            type="number"
            step="0.01"
            min="0"
            {...register(
              "unit_price",
              {
                required:
                  "Unit price is required",
              },
            )}
            className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-cyan-600"
          />
        </div>
      </div>

      <div>
        <label
          htmlFor="shipment_id"
          className="block text-sm font-medium text-slate-700"
        >
          Shipment ID
        </label>

        <input
          id="shipment_id"
          {...register(
            "shipment_id",
          )}
          placeholder="Optional"
          className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none focus:border-cyan-600"
        />

        <p className="mt-1 text-xs text-slate-500">
          Optional. Leave empty if this line
          is not linked to a shipment.
        </p>
      </div>

      {addInvoiceLineMutation.isError && (
        <div className="rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {addInvoiceLineMutation.error instanceof Error
            ? addInvoiceLineMutation.error.message
            : "Unable to add invoice line"}
        </div>
      )}

      <button
        type="submit"
        disabled={
          addInvoiceLineMutation.isPending
        }
        className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {addInvoiceLineMutation.isPending
          ? "Adding..."
          : "Add invoice line"}
      </button>
    </form>
  );
}
