import type {
  CreateTenantInput,
  CreateTenantResponse,
  UserTenant,
} from "@/features/tenants/types";

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

export async function createTenant(
  input: CreateTenantInput,
): Promise<CreateTenantResponse> {
  const response = await fetch("/api/tenants", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.detail ?? "Unable to create tenant",
    );
  }

  return data as CreateTenantResponse;
}