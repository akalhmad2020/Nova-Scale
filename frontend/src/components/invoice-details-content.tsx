"use client";

import Link from "next/link";

import { AddInvoiceLineForm } from "@/components/add-invoice-line-form";
import {
  useInvoice,
  useInvoiceLines,
  useIssueInvoice,
  useRemoveInvoiceLine,
  useVoidInvoice,
} from "@/features/billing/hooks";

type InvoiceDetailsContentProps = {
  invoiceId: string;
};

export function InvoiceDetailsContent({
  invoiceId,
}: InvoiceDetailsContentProps) {
  const invoiceQuery =
    useInvoice(invoiceId);

  const invoiceLinesQuery =
    useInvoiceLines(invoiceId);

  const removeInvoiceLineMutation =
    useRemoveInvoiceLine(invoiceId);

  const issueInvoiceMutation =
    useIssueInvoice(invoiceId);

  const voidInvoiceMutation =
    useVoidInvoice(invoiceId);

  if (invoiceQuery.isPending) {
    return (
      <p className="text-sm text-zinc-600">
        Loading invoice...
      </p>
    );
  }

  if (invoiceQuery.isError) {
    return (
      <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
        {invoiceQuery.error.message}
      </div>
    );
  }

  const invoice = invoiceQuery.data;

  const hasInvoiceLines =
    invoiceLinesQuery.isSuccess &&
    invoiceLinesQuery.data.length > 0;

  async function handleRemoveLine(
    invoiceLineId: string,
  ) {
    await removeInvoiceLineMutation.mutateAsync(
      invoiceLineId,
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/billing"
          className="text-sm text-zinc-500 hover:text-zinc-950"
        >
          ← Back to billing
        </Link>

        <p className="mt-4 text-sm text-zinc-500">
          Invoice
        </p>

        <h1 className="mt-1 text-2xl font-semibold text-zinc-950">
          {invoice.invoice_number}
        </h1>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Detail
          label="Status"
          value={formatValue(
            invoice.status,
          )}
        />

        <Detail
          label="Subtotal"
          value={formatMoney(
            invoice.subtotal,
            invoice.currency,
          )}
        />

        <Detail
          label="Tax"
          value={formatMoney(
            invoice.tax_amount,
            invoice.currency,
          )}
        />

        <Detail
          label="Total"
          value={formatMoney(
            invoice.total_amount,
            invoice.currency,
          )}
        />

        <Detail
          label="Currency"
          value={invoice.currency}
        />

        <Detail
          label="Created"
          value={formatDateTime(
            invoice.created_at,
          )}
        />
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <h2 className="font-medium text-zinc-950">
          Invoice actions
        </h2>

        <p className="mt-1 text-sm text-zinc-500">
          Manage the current state of this invoice.
        </p>

        <div className="mt-4 flex flex-wrap gap-3">
          {invoice.status === "draft" && (
            <button
              type="button"
              onClick={() =>
                issueInvoiceMutation.mutate()
              }
              disabled={
                !hasInvoiceLines ||
                issueInvoiceMutation.isPending
              }
              className="rounded-lg bg-zinc-950 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {issueInvoiceMutation.isPending
                ? "Issuing..."
                : "Issue invoice"}
            </button>
          )}

          {invoice.status === "issued" && (
            <button
              type="button"
              onClick={() =>
                voidInvoiceMutation.mutate()
              }
              disabled={
                voidInvoiceMutation.isPending
              }
              className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {voidInvoiceMutation.isPending
                ? "Voiding..."
                : "Void invoice"}
            </button>
          )}
        </div>

        {invoice.status === "draft" &&
          invoiceLinesQuery.isSuccess &&
          !hasInvoiceLines && (
            <p className="mt-3 text-sm text-amber-700">
              Add at least one invoice line before
              issuing the invoice.
            </p>
          )}

        {issueInvoiceMutation.isError && (
          <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {
              issueInvoiceMutation.error
                .message
            }
          </div>
        )}

        {voidInvoiceMutation.isError && (
          <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
            {
              voidInvoiceMutation.error
                .message
            }
          </div>
        )}
      </div>

      {invoice.status === "draft" && (
        <div className="rounded-xl border border-zinc-200 bg-white p-5">
          <h2 className="font-medium text-zinc-950">
            Add invoice line
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Add a billable item to this
            draft invoice.
          </p>

          <div className="mt-5">
            <AddInvoiceLineForm
              invoiceId={invoiceId}
            />
          </div>
        </div>
      )}

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <h2 className="font-medium text-zinc-950">
          Invoice lines
        </h2>

        <div className="mt-5">
          {invoiceLinesQuery.isPending && (
            <p className="text-sm text-zinc-500">
              Loading invoice lines...
            </p>
          )}

          {invoiceLinesQuery.isError && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              {
                invoiceLinesQuery.error
                  .message
              }
            </div>
          )}

          {invoiceLinesQuery.isSuccess &&
            invoiceLinesQuery.data.length ===
              0 && (
              <p className="text-sm text-zinc-500">
                No invoice lines yet.
              </p>
            )}

          {invoiceLinesQuery.isSuccess &&
            invoiceLinesQuery.data.length >
              0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-zinc-200 text-zinc-500">
                      <th className="pb-3 font-medium">
                        Description
                      </th>

                      <th className="pb-3 font-medium">
                        Quantity
                      </th>

                      <th className="pb-3 font-medium">
                        Unit price
                      </th>

                      <th className="pb-3 text-right font-medium">
                        Amount
                      </th>

                      {invoice.status ===
                        "draft" && (
                        <th className="pb-3 text-right font-medium">
                          Actions
                        </th>
                      )}
                    </tr>
                  </thead>

                  <tbody>
                    {invoiceLinesQuery.data.map(
                      (line) => (
                        <tr
                          key={line.id}
                          className="border-b border-zinc-100 last:border-0"
                        >
                          <td className="py-3 text-zinc-950">
                            {
                              line.description
                            }
                          </td>

                          <td className="py-3 text-zinc-700">
                            {line.quantity}
                          </td>

                          <td className="py-3 text-zinc-700">
                            {formatMoney(
                              line.unit_price,
                              invoice.currency,
                            )}
                          </td>

                          <td className="py-3 text-right font-medium text-zinc-950">
                            {formatMoney(
                              line.amount,
                              invoice.currency,
                            )}
                          </td>

                          {invoice.status ===
                            "draft" && (
                            <td className="py-3 text-right">
                              <button
                                type="button"
                                onClick={() =>
                                  handleRemoveLine(
                                    line.id,
                                  )
                                }
                                disabled={
                                  removeInvoiceLineMutation.isPending
                                }
                                className="text-sm font-medium text-red-600 transition hover:text-red-800 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                Remove
                              </button>
                            </td>
                          )}
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>

                {removeInvoiceLineMutation.isError && (
                  <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
                    {removeInvoiceLineMutation.error instanceof
                    Error
                      ? removeInvoiceLineMutation
                          .error.message
                      : "Unable to remove invoice line"}
                  </div>
                )}
              </div>
            )}
        </div>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <h2 className="font-medium text-zinc-950">
          Invoice identifiers
        </h2>

        <dl className="mt-4 space-y-3 text-sm">
          <Identifier
            label="Invoice ID"
            value={invoice.id}
          />

          <Identifier
            label="Customer ID"
            value={invoice.customer_id}
          />
        </dl>
      </div>
    </div>
  );
}

type DetailProps = {
  label: string;
  value: string;
};

function Detail({
  label,
  value,
}: DetailProps) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-4">
      <p className="text-sm text-zinc-500">
        {label}
      </p>

      <p className="mt-1 font-medium text-zinc-950">
        {value}
      </p>
    </div>
  );
}

type IdentifierProps = {
  label: string;
  value: string;
};

function Identifier({
  label,
  value,
}: IdentifierProps) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:justify-between">
      <dt className="text-zinc-500">
        {label}
      </dt>

      <dd className="break-all font-mono text-xs text-zinc-800">
        {value}
      </dd>
    </div>
  );
}

function formatValue(
  value: string,
): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase(),
    );
}

function formatMoney(
  value: string,
  currency: string,
): string {
  const amount = Number(value);

  return new Intl.NumberFormat(
    "en-US",
    {
      style: "currency",
      currency,
    },
  ).format(amount);
}

function formatDateTime(
  value: string,
): string {
  return new Intl.DateTimeFormat(
    "en-US",
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(new Date(value));
}