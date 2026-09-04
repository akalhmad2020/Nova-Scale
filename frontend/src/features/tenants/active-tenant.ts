import type { UserTenant } from "@/features/tenants/types";

export const ACTIVE_TENANT_COOKIE =
  "novascale_active_tenant_id";

export function resolveActiveTenant(
  tenants: UserTenant[],
  activeTenantId?: string | null,
): UserTenant | null {
  if (tenants.length === 0) {
    return null;
  }

  if (activeTenantId) {
    const activeTenant = tenants.find(
      (tenant) => tenant.id === activeTenantId,
    );

    if (activeTenant) {
      return activeTenant;
    }
  }

  return tenants[0];
}