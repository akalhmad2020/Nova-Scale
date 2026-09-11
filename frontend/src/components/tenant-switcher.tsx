"use client";

import { Icon } from "@/components/ui/icon";
import {
  useActiveTenantId,
  useSetActiveTenant,
} from "@/features/tenants/active-hooks";
import { resolveActiveTenant } from "@/features/tenants/active-tenant";
import { useMyTenants } from "@/features/tenants/hooks";

type TenantSwitcherProps = {
  variant?: "default" | "sidebar";
};

export function TenantSwitcher({
  variant = "default",
}: TenantSwitcherProps) {
  const tenantsQuery = useMyTenants();
  const activeTenantIdQuery = useActiveTenantId();
  const setActiveTenantMutation = useSetActiveTenant();

  const activeTenant = resolveActiveTenant(
    tenantsQuery.data ?? [],
    activeTenantIdQuery.data,
  );

  const sidebar = variant === "sidebar";

  if (tenantsQuery.isPending || activeTenantIdQuery.isPending) {
    return (
      <div
        className={`animate-pulse rounded-xl ${
          sidebar ? "bg-slate-900 p-3" : "bg-slate-100 p-3"
        }`}
      >
        <div className={`h-3 w-20 rounded ${sidebar ? "bg-slate-800" : "bg-slate-200"}`} />
        <div className={`mt-2 h-4 w-32 rounded ${sidebar ? "bg-slate-800" : "bg-slate-200"}`} />
      </div>
    );
  }

  if (tenantsQuery.isError || activeTenantIdQuery.isError) {
    return (
      <p className={sidebar ? "text-xs text-rose-400" : "text-sm text-rose-600"}>
        Unable to load tenant context.
      </p>
    );
  }

  if (!tenantsQuery.data?.length || !activeTenant) {
    return null;
  }

  async function handleChange(tenantId: string) {
    await setActiveTenantMutation.mutateAsync({ tenant_id: tenantId });
  }

  if (sidebar) {
    return (
      <div className="relative">
        <p className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-[0.17em] text-slate-500">
          Active workspace
        </p>
        <div className="relative">
          <Icon
            name="building"
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
          />
          <select
            aria-label="Active workspace"
            value={activeTenant.id}
            onChange={(event) => void handleChange(event.target.value)}
            disabled={setActiveTenantMutation.isPending}
            className="w-full appearance-none rounded-xl border border-slate-800 bg-slate-900 py-2.5 pl-9 pr-8 text-sm font-medium text-slate-200 outline-none transition hover:border-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {tenantsQuery.data.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.name}
              </option>
            ))}
          </select>
          <Icon
            name="chevron-down"
            className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
          />
        </div>
        <p className="mt-2 truncate px-1 text-[11px] text-slate-600">
          {activeTenant.slug}
        </p>
        {setActiveTenantMutation.isError ? (
          <p className="mt-2 px-1 text-xs text-rose-400">
            Unable to switch workspace.
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <div>
      <label
        htmlFor="tenant-switcher"
        className="mb-2 block text-sm font-medium text-slate-700"
      >
        Active workspace
      </label>
      <select
        id="tenant-switcher"
        value={activeTenant.id}
        onChange={(event) => void handleChange(event.target.value)}
        disabled={setActiveTenantMutation.isPending}
        className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-slate-950 outline-none disabled:cursor-not-allowed disabled:opacity-60"
      >
        {tenantsQuery.data.map((tenant) => (
          <option key={tenant.id} value={tenant.id}>
            {tenant.name}
          </option>
        ))}
      </select>
      <p className="mt-2 text-xs text-slate-500">{activeTenant.slug}</p>
    </div>
  );
}
