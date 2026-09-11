"use client";

import Link from "next/link";

import { AddInvoiceLineForm } from "@/components/add-invoice-line-form";
import { Icon } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
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
  const invoiceQuery = useInvoice(invoiceId);
  const invoiceLinesQuery = useInvoiceLines(invoiceId);
  const removeInvoiceLineMutation = useRemoveInvoiceLine(invoiceId);
  const issueInvoiceMutation = useIssueInvoice(invoiceId);
  const voidInvoiceMutation = useVoidInvoice(invoiceId);

  if (invoiceQuery.isPending) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
        Loading invoice...
      </div>
    );
  }

  if (invoiceQuery.isError) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        {invoiceQuery.error.message}
      </div>
    );
  }

  const invoice = invoiceQuery.data;
  const hasInvoiceLines =
    invoiceLinesQuery.isSuccess && invoiceLinesQuery.data.length > 0;

  async function handleRemoveLine(invoiceLineId: string) {
    await removeInvoiceLineMutation.mutateAsync(invoiceLineId);
  }

  return (
    <div className="space-y-7">
      <div>
        <Link
          href="/billing"
          className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition hover:text-slate-950"
        >
          <span aria-hidden>←</span>
          Billing
        </Link>

        <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
                {invoice.invoice_number}
              </h1>
              <StatusBadge value={invoice.status} />
            </div>
            <p className="mt-2 text-sm text-slate-500">
              Created {formatDateTime(invoice.created_at)}
              <span className="mx-2 text-slate-300">•</span>
              {invoice.currency}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {invoice.status === "draft" ? (
              <button
                type="button"
                onClick={() => issueInvoiceMutation.mutate()}
                disabled={!hasInvoiceLines || issueInvoiceMutation.isPending}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Icon name="check" className="h-4 w-4" />
                {issueInvoiceMutation.isPending ? "Issuing..." : "Issue invoice"}
              </button>
            ) : null}

            {invoice.status === "issued" ? (
              <button
                type="button"
                onClick={() => voidInvoiceMutation.mutate()}
                disabled={voidInvoiceMutation.isPending}
                className="rounded-xl border border-rose-200 bg-white px-4 py-2.5 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {voidInvoiceMutation.isPending ? "Voiding..." : "Void invoice"}
              </button>
            ) : null}
          </div>
        </div>

        {invoice.status === "draft" && invoiceLinesQuery.isSuccess && !hasInvoiceLines ? (
          <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Add at least one invoice line before issuing this invoice.
          </div>
        ) : null}

        {issueInvoiceMutation.isError || voidInvoiceMutation.isError ? (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {issueInvoiceMutation.error?.message ?? voidInvoiceMutation.error?.message}
          </div>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MoneyMetric label="Subtotal" value={invoice.subtotal} currency={invoice.currency} />
        <MoneyMetric label="Tax" value={invoice.tax_amount} currency={invoice.currency} />
        <MoneyMetric label="Total" value={invoice.total_amount} currency={invoice.currency} emphasize />
        <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Line items</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
            {invoiceLinesQuery.data?.length ?? 0}
          </p>
          <p className="mt-1 text-xs text-slate-500">Billable entries</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(20rem,0.65fr)]">
        <Surface className="overflow-hidden">
          <SurfaceHeader title="Invoice lines" description="Billable items included in this invoice" />

          {invoiceLinesQuery.isPending ? (
            <div className="p-6 text-sm text-slate-500">Loading invoice lines...</div>
          ) : invoiceLinesQuery.isError ? (
            <div className="p-6 text-sm text-rose-600">{invoiceLinesQuery.error.message}</div>
          ) : invoiceLinesQuery.data.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-sm font-semibold text-slate-800">No invoice lines yet</p>
              <p className="mt-1 text-sm text-slate-500">Add a billable item before issuing the invoice.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[660px] text-left text-sm">
                <thead className="bg-slate-50/80 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Description</th>
                    <th className="px-5 py-3 font-semibold">Quantity</th>
                    <th className="px-5 py-3 font-semibold">Unit price</th>
                    <th className="px-5 py-3 text-right font-semibold">Amount</th>
                    {invoice.status === "draft" ? <th className="px-5 py-3" /> : null}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {invoiceLinesQuery.data.map((line) => (
                    <tr key={line.id} className="transition hover:bg-slate-50/70">
                      <td className="px-6 py-4 font-medium text-slate-900">{line.description}</td>
                      <td className="px-5 py-4 text-slate-600">{line.quantity}</td>
                      <td className="px-5 py-4 text-slate-600">{formatMoney(line.unit_price, invoice.currency)}</td>
                      <td className="px-5 py-4 text-right font-semibold tabular-nums text-slate-900">
                        {formatMoney(line.amount, invoice.currency)}
                      </td>
                      {invoice.status === "draft" ? (
                        <td className="px-5 py-4 text-right">
                          <button
                            type="button"
                            onClick={() => void handleRemoveLine(line.id)}
                            disabled={removeInvoiceLineMutation.isPending}
                            className="text-xs font-semibold text-rose-600 transition hover:text-rose-800 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Remove
                          </button>
                        </td>
                      ) : null}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {removeInvoiceLineMutation.isError ? (
            <div className="border-t border-rose-100 bg-rose-50 px-6 py-3 text-sm text-rose-700">
              {removeInvoiceLineMutation.error instanceof Error
                ? removeInvoiceLineMutation.error.message
                : "Unable to remove invoice line"}
            </div>
          ) : null}
        </Surface>

        <div className="space-y-6">
          {invoice.status === "draft" ? (
            <Surface>
              <SurfaceHeader title="Add line item" description="Add a billable item to this draft" />
              <div className="p-5 sm:p-6"><AddInvoiceLineForm invoiceId={invoiceId} /></div>
            </Surface>
          ) : null}

          <Surface>
            <SurfaceHeader title="Invoice metadata" description="Record identifiers" />
            <dl className="divide-y divide-slate-100 px-5 sm:px-6">
              <MetaRow label="Invoice ID" value={invoice.id} />
              <MetaRow label="Customer ID" value={invoice.customer_id} />
              <MetaRow label="Issued" value={invoice.issued_at ? formatDateTime(invoice.issued_at) : "—"} mono={false} />
              <MetaRow label="Paid" value={invoice.paid_at ? formatDateTime(invoice.paid_at) : "—"} mono={false} />
            </dl>
          </Surface>
        </div>
      </div>
    </div>
  );
}

function MoneyMetric({
  label,
  value,
  currency,
  emphasize = false,
}: {
  label: string;
  value: string;
  currency: string;
  emphasize?: boolean;
}) {
  return (
    <div className={`rounded-2xl border p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${emphasize ? "border-cyan-200 bg-cyan-50/60" : "border-slate-200/80 bg-white"}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
        {formatMoney(value, currency)}
      </p>
    </div>
  );
}

function MetaRow({ label, value, mono = true }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="py-4">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className={`mt-1.5 break-all text-slate-700 ${mono ? "font-mono text-xs" : "text-sm"}`}>{value}</dd>
    </div>
  );
}

function formatMoney(value: string, currency: string) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return `${value} ${currency}`;
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amount);
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
