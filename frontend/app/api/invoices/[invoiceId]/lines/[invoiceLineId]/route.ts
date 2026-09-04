import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import {
  applyAuthenticationState,
  authenticatedBackendFetch,
} from "@/features/auth/server-client";
import { ACTIVE_TENANT_COOKIE } from "@/features/tenants/active-tenant";

type RouteContext = {
  params: Promise<{
    invoiceId: string;
    invoiceLineId: string;
  }>;
};

export async function DELETE(
  _request: Request,
  context: RouteContext,
) {
  const {
    invoiceId,
    invoiceLineId,
  } = await context.params;

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
    `/api/v1/tenants/${activeTenantId}/invoices/${invoiceId}/lines/${invoiceLineId}`,
    {
      method: "DELETE",
    },
  );

  if (result.response.status === 204) {
    const response = new NextResponse(null, {
      status: 204,
    });

    applyAuthenticationState(
      response,
      result,
    );

    return response;
  }

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