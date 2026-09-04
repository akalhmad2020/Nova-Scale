"use client";

import {
  useActiveTenantId,
  useSetActiveTenant,
} from "@/features/tenants/active-hooks";
import { resolveActiveTenant } from "@/features/tenants/active-tenant";
import { useMyTenants } from "@/features/tenants/hooks";

export function TenantSwitcher() {
  const tenantsQuery = useMyTenants();
  const activeTenantIdQuery = useActiveTenantId();
  const setActiveTenantMutation = useSetActiveTenant();

  const activeTenant = resolveActiveTenant(
    tenantsQuery.data ?? [],
    activeTenantIdQuery.data,
  );

  if (
    tenantsQuery.isPending ||
    activeTenantIdQuery.isPending
  ) {
    return (
      <p className="text-sm text-zinc-500">
        Loading tenant...
      </p>
    );
  }

  if (
    tenantsQuery.isError ||
    activeTenantIdQuery.isError
  ) {
    return (
      <p className="text-sm text-red-600">
        Unable to load tenant context.
      </p>
    );
  }

  if (!tenantsQuery.data?.length || !activeTenant) {
    return null;
  }

  async function handleChange(
    tenantId: string,
  ) {
    await setActiveTenantMutation.mutateAsync({
      tenant_id: tenantId,
    });
  }

  return (
    <div>
      <label
        htmlFor="tenant-switcher"
        className="mb-2 block text-sm font-medium text-zinc-900"
      >
        Active tenant
      </label>

      <select
        id="tenant-switcher"
        value={activeTenant.id}
        onChange={(event) => {
          void handleChange(event.target.value);
        }}
        disabled={setActiveTenantMutation.isPending}
        className="w-full rounded-lg border border-zinc-300 bg-white px-3 py-2.5 text-zinc-950 outline-none transition focus:border-zinc-950 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {tenantsQuery.data.map((tenant) => (
          <option
            key={tenant.id}
            value={tenant.id}
          >
            {tenant.name}
          </option>
        ))}
      </select>

      <p className="mt-2 text-sm text-zinc-500">
        {activeTenant.slug}
      </p>

      {setActiveTenantMutation.isError && (
        <p className="mt-2 text-sm text-red-600">
          Unable to change active tenant.
        </p>
      )}
    </div>
  );
}