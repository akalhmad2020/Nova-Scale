"use client";

import { useEffect } from "react";

import {
  useActiveTenantId,
  useSetActiveTenant,
} from "@/features/tenants/active-hooks";
import { resolveActiveTenant } from "@/features/tenants/active-tenant";
import { useMyTenants } from "@/features/tenants/hooks";

export function ActiveTenantInitializer() {
  const tenantsQuery = useMyTenants();
  const activeTenantIdQuery = useActiveTenantId();
  const setActiveTenantMutation = useSetActiveTenant();

  useEffect(() => {
    if (
      !tenantsQuery.data ||
      tenantsQuery.data.length === 0 ||
      activeTenantIdQuery.isPending
    ) {
      return;
    }

    const resolvedTenant = resolveActiveTenant(
      tenantsQuery.data,
      activeTenantIdQuery.data,
    );

    if (!resolvedTenant) {
      return;
    }

    if (
      resolvedTenant.id !== activeTenantIdQuery.data &&
      !setActiveTenantMutation.isPending
    ) {
      setActiveTenantMutation.mutate({
        tenant_id: resolvedTenant.id,
      });
    }
  }, [
    tenantsQuery.data,
    activeTenantIdQuery.data,
    activeTenantIdQuery.isPending,
    setActiveTenantMutation,
  ]);

  return null;
}