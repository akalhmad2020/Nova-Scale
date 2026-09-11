"use client";

import { useActiveTenantId } from "@/features/tenants/active-hooks";

export function ActiveTenantInitializer() {
  useActiveTenantId();
  return null;
}
