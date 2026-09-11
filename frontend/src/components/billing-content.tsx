"use client";

import Link from "next/link";

import { CreateInvoiceForm } from "@/components/create-invoice-form";
import { EmptyState } from "@/components/ui/empty-state";
import { Icon } from "@/components/ui/icon";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { useInvoices } from "@/features/billing/hooks";
import { useCustomers } from "@/features/customers/hooks";

export function BillingContent() {
  const invoicesQuery = useInvoices();
  const customersQuery = useCustomers();
  const invoices = invoicesQuery.data ?? [];

  const customersById = new Map(
    (customersQuery.data ?? []).map((customer) => [customer.id, customer]),
  );

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Finance"
        title="Billing"
        description="Prepare customer invoices, review totals, and control the invoice lifecycle from draft through issue and settlement."
      />


      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <Surface className="min-w-0 overflow-hidden">
          <SurfaceHeader
            title="Invoice register"
            description="Invoices for the active workspace"
            meta={`${invoices.length} invoice${invoices.length === 1 ? "" : "s"}`}
          />

          {invoicesQuery.isPending ? (
            <div className="p-6 text-sm text-slate-500">Loading invoices...</div>
          ) : invoicesQuery.isError ? (
            <div className="p-6 text-sm text-rose-600">{invoicesQuery.error.message}</div>
          ) : invoices.length === 0 ? (
            <EmptyState
              icon="billing"
              title="No invoices yet"
              description="Create a draft invoice for a customer to begin the billing workflow."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-slate-50/80 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Invoice</th>
                    <th className="px-5 py-3 font-semibold">Customer</th>
                    <th className="px-5 py-3 font-semibold">Status</th>
                    <th className="px-5 py-3 font-semibold">Total</th>
                    <th className="px-5 py-3 font-semibold">Created</th>
                    <th className="px-5 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {invoices.map((invoice) => {
                    const customer = customersById.get(invoice.customer_id);
                    return (
                      <tr key={invoice.id} className="transition hover:bg-slate-50/70">
                        <td className="px-6 py-4">
                          <Link href={`/billing/${invoice.id}`} className="font-semibold text-slate-950 transition hover:text-cyan-700">
                            {invoice.invoice_number}
                          </Link>
                          <p className="mt-1 text-xs text-slate-500">{invoice.currency}</p>
                        </td>
                        <td className="px-5 py-4 text-slate-600">{customer?.name ?? invoice.customer_id}</td>
                        <td className="px-5 py-4"><StatusBadge value={invoice.status} /></td>
                        <td className="px-5 py-4 font-semibold tabular-nums text-slate-900">{formatMoney(invoice.total_amount, invoice.currency)}</td>
                        <td className="px-5 py-4 text-slate-600">{formatDate(invoice.created_at)}</td>
                        <td className="px-5 py-4 text-right">
                          <Link href={`/billing/${invoice.id}`} aria-label={`Open ${invoice.invoice_number}`} className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-900">
                            <Icon name="arrow-right" className="h-4 w-4" />
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Surface>

        <Surface className="h-fit">
          <SurfaceHeader title="Create invoice" description="Open a new draft invoice" />
          <div className="p-5 sm:p-6"><CreateInvoiceForm /></div>
        </Surface>
      </div>
    </div>
  );
}

function formatMoney(value: string, currency: string) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return `${value} ${currency}`;
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amount);
  } catch {
    return `${value} ${currency}`;
  }
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(new Date(value));
}
