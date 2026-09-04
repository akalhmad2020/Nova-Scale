import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  applyAuthenticationState,
  authenticatedBackendFetch,
} from "@/features/auth/server-client";
import { ACTIVE_TENANT_COOKIE } from "@/features/tenants/active-tenant";

export async function POST(
  request: Request,
) {
  const cookieStore = await cookies();

  const activeTenantId =
    cookieStore.get(
      ACTIVE_TENANT_COOKIE,
    )?.value;

  if (!activeTenantId) {
    return NextResponse.json(
      {
        detail:
          "No active tenant selected",
      },
      { status: 400 },
    );
  }

  const body = await request.json();

  const result =
    await authenticatedBackendFetch(
      `/api/v1/ai/tenants/${activeTenantId}/agent`,
      {
        method: "POST",
        headers: {
          "Content-Type":
            "application/json",
        },
        body: JSON.stringify(body),
      },
    );

  const responseBody =
    await result.response.json();

  const response =
    NextResponse.json(
      responseBody,
      {
        status:
          result.response.status,
      },
    );

  applyAuthenticationState(
    response,
    result,
  );

  return response;
}