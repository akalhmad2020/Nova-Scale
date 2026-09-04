import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  applyAuthenticationState,
  authenticatedBackendFetch,
} from "@/features/auth/server-client";
import { ACTIVE_TENANT_COOKIE } from "@/features/tenants/active-tenant";

export async function GET() {
  const activeTenantId = await getActiveTenantId();

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
    `/api/v1/tenants/${activeTenantId}/customers`,
    {
      method: "GET",
    },
  );

  return createBackendResponse(result);
}

export async function POST(
  request: Request,
) {
  const activeTenantId = await getActiveTenantId();

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

  const body = await request.json();

  const result = await authenticatedBackendFetch(
    `/api/v1/tenants/${activeTenantId}/customers`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    },
  );

  return createBackendResponse(result);
}

async function getActiveTenantId(): Promise<
  string | null
> {
  const cookieStore = await cookies();

  return (
    cookieStore.get(ACTIVE_TENANT_COOKIE)
      ?.value ?? null
  );
}

async function createBackendResponse(
  result: Awaited<
    ReturnType<
      typeof authenticatedBackendFetch
    >
  >,
) {
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