import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  applyAuthenticationState,
  authenticatedBackendFetch,
} from "@/features/auth/server-client";
import { ACTIVE_TENANT_COOKIE } from "@/features/tenants/active-tenant";

export async function GET() {
  const cookieStore = await cookies();
  const activeTenantId = cookieStore.get(
    ACTIVE_TENANT_COOKIE,
  )?.value;

  if (!activeTenantId) {
    return NextResponse.json(
      { detail: "No active tenant selected" },
      { status: 400 },
    );
  }

  const result = await authenticatedBackendFetch(
    `/api/v1/tenants/${activeTenantId}/subscription`,
    { method: "GET" },
  );

  const body = await readResponseBody(result.response);
  const response = NextResponse.json(body, {
    status: result.response.status,
  });

  applyAuthenticationState(response, result);

  return response;
}

async function readResponseBody(
  response: Response,
): Promise<unknown> {
  const contentType = response.headers.get("content-type");

  if (contentType?.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();

  return {
    detail: text || "Unable to communicate with backend",
  };
}
