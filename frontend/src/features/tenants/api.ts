import type { UserTenant } from "@/features/tenants/types";

export async function getMyTenants(): Promise<UserTenant[]> {
  const response = await fetch("/api/tenants", {
    method: "GET",
    cache: "no-store",
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ?? "Unable to load tenants",
    );
  }

  return data as UserTenant[];
}