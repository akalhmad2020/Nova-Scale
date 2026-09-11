"use client";

import { CreateCustomerForm } from "@/components/create-customer-form";
import { EmptyState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { useCustomers } from "@/features/customers/hooks";

export function CustomersContent() {
  const customersQuery = useCustomers();
  const customers = customersQuery.data ?? [];

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Accounts"
        title="Customers"
        description="Maintain the customer accounts used across shipment execution and billing workflows."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <Surface className="min-w-0 overflow-hidden">
          <SurfaceHeader
            title="Customer directory"
            description="Accounts available to the active workspace"
            meta={`${customers.length} customer${customers.length === 1 ? "" : "s"}`}
          />

          {customersQuery.isPending ? (
            <div className="p-6 text-sm text-slate-500">Loading customers...</div>
          ) : customersQuery.isError ? (
            <div className="p-6 text-sm text-rose-600">{customersQuery.error.message}</div>
          ) : customers.length === 0 ? (
            <EmptyState
              icon="customers"
              title="No customers yet"
              description="Add a customer account to unlock shipment and invoice workflows."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-left text-sm">
                <thead className="bg-slate-50/80 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-3 font-semibold">Customer</th>
                    <th className="px-5 py-3 font-semibold">Code</th>
                    <th className="px-5 py-3 font-semibold">Contact</th>
                    <th className="px-5 py-3 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {customers.map((customer) => (
                    <tr key={customer.id} className="transition hover:bg-slate-50/70">
                      <td className="px-6 py-4">
                        <p className="font-semibold text-slate-950">{customer.name}</p>
                        <p className="mt-1 max-w-[20rem] truncate text-xs text-slate-500">
                          {customer.notes ?? "No account notes"}
                        </p>
                      </td>
                      <td className="px-5 py-4 font-mono text-xs text-slate-600">{customer.code}</td>
                      <td className="px-5 py-4 text-slate-600">
                        <p>{customer.email ?? "—"}</p>
                        {customer.phone ? <p className="mt-1 text-xs text-slate-400">{customer.phone}</p> : null}
                      </td>
                      <td className="px-5 py-4"><StatusBadge value={customer.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Surface>

        <Surface className="h-fit">
          <SurfaceHeader title="Add customer" description="Create a new account record" />
          <div className="p-5 sm:p-6"><CreateCustomerForm /></div>
        </Surface>
      </div>
    </div>
  );
}
