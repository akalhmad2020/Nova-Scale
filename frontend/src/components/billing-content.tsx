"use client";

import Link from "next/link";

import { CreateInvoiceForm } from "@/components/create-invoice-form";
import { useInvoices } from "@/features/billing/hooks";
import { useCustomers } from "@/features/customers/hooks";

export function BillingContent() {
  const invoicesQuery = useInvoices();
  const customersQuery = useCustomers();

  const customersById = new Map(
    (customersQuery.data ?? []).map(
      (customer) => [
        customer.id,
        customer,
      ],
    ),
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-950">
          Billing
        </h1>

        <p className="mt-1 text-sm text-zinc-600">
          Manage invoices for the active tenant.
        </p>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <div className="mb-5">
          <h2 className="font-medium text-zinc-950">
            Create invoice
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Create a draft invoice for a customer.
          </p>
        </div>

        <CreateInvoiceForm />
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 px-5 py-4">
          <h2 className="font-medium text-zinc-950">
            Invoice list
          </h2>
        </div>

        {invoicesQuery.isPending && (
          <div className="p-5 text-sm text-zinc-600">
            Loading invoices...
          </div>
        )}

        {invoicesQuery.isError && (
          <div className="p-5 text-sm text-red-600">
            {invoicesQuery.error.message}
          </div>
        )}

        {invoicesQuery.data?.length ===
          0 && (
          <div className="p-10 text-center">
            <p className="font-medium text-zinc-900">
              No invoices yet
            </p>
          </div>
        )}

        {invoicesQuery.data &&
          invoicesQuery.data.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-zinc-200 bg-zinc-50">
                  <tr>
                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Invoice
                    </th>

                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Customer
                    </th>

                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Status
                    </th>

                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Total
                    </th>

                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Created
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {invoicesQuery.data.map(
                    (invoice) => {
                      const customer =
                        customersById.get(
                          invoice.customer_id,
                        );

                      return (
                        <tr
                          key={invoice.id}
                          className="border-b border-zinc-100 last:border-b-0"
                        >
                          <td className="px-5 py-4 font-medium text-zinc-950">
                            <Link
                              href={`/billing/${invoice.id}`}
                              className="hover:underline"
                            >
                              {
                                invoice.invoice_number
                              }
                            </Link>
                          </td>

                          <td className="px-5 py-4 text-zinc-700">
                            {customer
                              ? customer.name
                              : invoice.customer_id}
                          </td>

                          <td className="px-5 py-4 text-zinc-700">
                            {formatStatus(
                              invoice.status,
                            )}
                          </td>

                          <td className="px-5 py-4 text-zinc-700">
                            {formatMoney(
                              invoice.total_amount,
                              invoice.currency,
                            )}
                          </td>

                          <td className="px-5 py-4 text-zinc-700">
                            {formatDate(
                              invoice.created_at,
                            )}
                          </td>
                        </tr>
                      );
                    },
                  )}
                </tbody>
              </table>
            </div>
          )}
      </div>
    </div>
  );
}

function formatStatus(
  value: string,
): string {
  return value
    .split("_")
    .map(
      (part) =>
        part.charAt(0).toUpperCase() +
        part.slice(1),
    )
    .join(" ");
}

function formatMoney(
  value: string,
  currency: string,
): string {
  const amount = Number(value);

  if (!Number.isFinite(amount)) {
    return `${value} ${currency}`;
  }

  try {
    return new Intl.NumberFormat(
      undefined,
      {
        style: "currency",
        currency,
      },
    ).format(amount);
  } catch {
    return `${value} ${currency}`;
  }
}

function formatDate(
  value: string,
): string {
  return new Intl.DateTimeFormat(
    undefined,
    {
      dateStyle: "medium",
      timeStyle: "short",
    },
  ).format(new Date(value));
}