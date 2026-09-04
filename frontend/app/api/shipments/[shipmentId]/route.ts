import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import {
  applyAuthenticationState,
  authenticatedBackendFetch,
} from "@/features/auth/server-client";
import { ACTIVE_TENANT_COOKIE } from "@/features/tenants/active-tenant";

type RouteContext = {
  params: Promise<{
    shipmentId: string;
  }>;
};

export async function GET(
  _request: Request,
  context: RouteContext,
) {
  const { shipmentId } = await context.params;

  const cookieStore = await cookies();

  const activeTenantId =
    cookieStore.get(ACTIVE_TENANT_COOKIE)?.value;

  if (!activeTenantId) {
    return NextResponse.json(
      {
        detail: "No active tenant selected",
      },
      {
        status: 400,
      },
    );
  }

  const result = await authenticatedBackendFetch(
    `/api/v1/tenants/${activeTenantId}/shipments/${shipmentId}`,
    {
      method: "GET",
    },
  );

  const data = await readResponseBody(
    result.response,
  );

  const response = NextResponse.json(
    data,
    {
      status: result.response.status,
    },
  );

  applyAuthenticationState(
    response,
    result,
  );

  return response;
}

async function readResponseBody(
  response: Response,
): Promise<unknown> {
  const contentType =
    response.headers.get("content-type");

  if (
    contentType?.includes(
      "application/json",
    )
  ) {
    return response.json();
  }

  const text = await response.text();

  return {
    detail:
      text ||
      "Unable to communicate with backend",
  };
}