import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  applyAuthenticationState,
  authenticatedBackendFetch,
} from "@/features/auth/server-client";
import { ACTIVE_TENANT_COOKIE } from "@/features/tenants/active-tenant";

type RouteContext = {
  params: Promise<{
    actionId: string;
  }>;
};

export async function POST(
  _request: Request,
  context: RouteContext,
) {
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

  const { actionId } = await context.params;

  const result = await authenticatedBackendFetch(
    `/api/v1/ai/tenants/${activeTenantId}/actions/${actionId}/cancel`,
    { method: "POST" },
  );

  const responseBody = await result.response.json();
  const response = NextResponse.json(
    responseBody,
    { status: result.response.status },
  );

  applyAuthenticationState(response, result);

  return response;
}
