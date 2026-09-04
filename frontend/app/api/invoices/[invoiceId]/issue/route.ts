import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  applyAuthenticationState,
  authenticatedBackendFetch,
} from "@/features/auth/server-client";
import { ACTIVE_TENANT_COOKIE } from "@/features/tenants/active-tenant";

type RouteContext = {
  params: Promise<{
    invoiceId: string;
  }>;
};

export async function POST(
  _request: Request,
  context: RouteContext,
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
      {
        status: 400,
      },
    );
  }

  const { invoiceId } =
    await context.params;

  const result =
    await authenticatedBackendFetch(
      `/api/v1/tenants/${activeTenantId}/invoices/${invoiceId}/issue`,
      {
        method: "POST",
      },
    );

  const body =
    await result.response.json();

  const response =
    NextResponse.json(body, {
      status: result.response.status,
    });

  applyAuthenticationState(
    response,
    result,
  );

  return response;
}