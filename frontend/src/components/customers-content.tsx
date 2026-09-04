"use client";

import { CreateCustomerForm } from "@/components/create-customer-form";
import { useCustomers } from "@/features/customers/hooks";

export function CustomersContent() {
  const customersQuery = useCustomers();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-950">
          Customers
        </h1>

        <p className="mt-1 text-sm text-zinc-600">
          Manage customers for the active tenant.
        </p>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <div className="mb-5">
          <h2 className="font-medium text-zinc-950">
            Create customer
          </h2>

          <p className="mt-1 text-sm text-zinc-500">
            Add a customer to the active tenant.
          </p>
        </div>

        <CreateCustomerForm />
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 px-5 py-4">
          <h2 className="font-medium text-zinc-950">
            Customer list
          </h2>
        </div>

        {customersQuery.isPending && (
          <div className="p-5 text-sm text-zinc-600">
            Loading customers...
          </div>
        )}

        {customersQuery.isError && (
          <div className="p-5 text-sm text-red-600">
            {customersQuery.error.message}
          </div>
        )}

        {customersQuery.data?.length === 0 && (
          <div className="p-10 text-center">
            <p className="font-medium text-zinc-900">
              No customers yet
            </p>
          </div>
        )}

        {customersQuery.data &&
          customersQuery.data.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-zinc-200 bg-zinc-50">
                  <tr>
                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Name
                    </th>

                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Code
                    </th>

                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Email
                    </th>

                    <th className="px-5 py-3 font-medium text-zinc-600">
                      Status
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {customersQuery.data.map(
                    (customer) => (
                      <tr
                        key={customer.id}
                        className="border-b border-zinc-100 last:border-b-0"
                      >
                        <td className="px-5 py-4 font-medium text-zinc-950">
                          {customer.name}
                        </td>

                        <td className="px-5 py-4 text-zinc-700">
                          {customer.code}
                        </td>

                        <td className="px-5 py-4 text-zinc-700">
                          {customer.email ?? "—"}
                        </td>

                        <td className="px-5 py-4 text-zinc-700">
                          {customer.status}
                        </td>
                      </tr>
                    ),
                  )}
                </tbody>
              </table>
            </div>
          )}
      </div>
    </div>
  );
}