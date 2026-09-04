type ActiveTenantResponse = {
  active_tenant_id: string | null;
};

type SetActiveTenantInput = {
  tenant_id: string;
};

export async function getActiveTenantId(): Promise<string | null> {
  const response = await fetch("/api/tenants/active", {
    method: "GET",
    cache: "no-store",
  });

  const data =
    (await response.json()) as ActiveTenantResponse;

  if (!response.ok) {
    throw new Error(
      "Unable to load active tenant",
    );
  }

  return data.active_tenant_id;
}

export async function setActiveTenant(
  input: SetActiveTenantInput,
): Promise<string> {
  const response = await fetch("/api/tenants/active", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  const data =
    (await response.json()) as ActiveTenantResponse;

  if (!response.ok || !data.active_tenant_id) {
    throw new Error(
      "Unable to set active tenant",
    );
  }

  return data.active_tenant_id;
}