"use client";

import { useEffect, useState } from "react";

import { getHealth } from "@/api/health";
import { CreateTenantForm } from "@/components/create-tenant-form";
import { useMyTenants } from "@/features/tenants/hooks";

export function HomeContent() {
  const [backendStatus, setBackendStatus] =
    useState("loading");

  const tenantsQuery = useMyTenants();

  useEffect(() => {
    async function loadHealth() {
      try {
        const health = await getHealth();

        setBackendStatus(health.status);
      } catch {
        setBackendStatus("unavailable");
      }
    }

    void loadHealth();
  }, []);

  const isHealthy = backendStatus === "ok";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-zinc-950">
          Dashboard
        </h1>

        <p className="mt-1 text-sm text-zinc-600">
          Overview of your NovaScale workspace.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-zinc-200 bg-white p-5">
          <p className="text-sm text-zinc-500">
            Backend status
          </p>

          <div className="mt-2 flex items-center gap-3">
            <span
              className={`h-3 w-3 rounded-full ${
                isHealthy
                  ? "bg-green-500"
                  : "bg-red-500"
              }`}
            />

            <span className="font-medium text-zinc-900">
              {backendStatus}
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white p-5">
          <p className="text-sm text-zinc-500">
            Tenant count
          </p>

          <p className="mt-2 text-2xl font-semibold text-zinc-950">
            {tenantsQuery.data?.length ?? 0}
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-5">
        <p className="font-medium text-zinc-950">
          My tenants
        </p>

        {tenantsQuery.isPending && (
          <p className="mt-2 text-zinc-600">
            Loading tenants...
          </p>
        )}

        {tenantsQuery.isError && (
          <p className="mt-2 text-red-600">
            Unable to load tenants.
          </p>
        )}

        {tenantsQuery.data?.length === 0 && (
          <p className="mt-3 text-zinc-600">
            You are not a member of any tenant yet.
          </p>
        )}

        {tenantsQuery.data &&
          tenantsQuery.data.length > 0 && (
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {tenantsQuery.data.map((tenant) => (
                <div
                  key={tenant.id}
                  className="rounded-lg border border-zinc-200 px-4 py-3"
                >
                  <p className="font-medium text-zinc-950">
                    {tenant.name}
                  </p>

                  <p className="text-sm text-zinc-600">
                    {tenant.slug}
                  </p>
                </div>
              ))}
            </div>
          )}

        {tenantsQuery.data && (
          <div className="mt-5 border-t border-zinc-200 pt-5">
            <CreateTenantForm />
          </div>
        )}
      </div>
    </div>
  );
}