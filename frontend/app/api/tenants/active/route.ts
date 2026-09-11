import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  applyAuthenticationState,
  authenticatedBackendFetch,
} from "@/features/auth/server-client";
import { ACTIVE_TENANT_COOKIE } from "@/features/tenants/active-tenant";

type ActiveTenantResponse = {
  active_tenant_id: string | null;
};

type SetActiveTenantRequest = {
  tenant_id: string;
};

type TenantSummary = {
  id: string;
};

const ACTIVE_TENANT_COOKIE_MAX_AGE = 60 * 60 * 24 * 365;

export async function GET() {
  const cookieStore = await cookies();
  const requestedTenantId =
    cookieStore.get(ACTIVE_TENANT_COOKIE)?.value ?? null;

  const result = await authenticatedBackendFetch(
    "/api/v1/tenants",
    { method: "GET" },
  );

  if (!result.response.ok) {
    return createBackendErrorResponse(result);
  }

  const tenants = await readTenantList(result.response);
  const activeTenantId = resolveActiveTenantId(
    tenants,
    requestedTenantId,
  );

  const response = NextResponse.json<ActiveTenantResponse>(
    { active_tenant_id: activeTenantId },
    { status: 200 },
  );

  applyAuthenticationState(response, result);
  persistActiveTenantCookie(response, activeTenantId);

  return response;
}

export async function POST(request: Request) {
  let body: SetActiveTenantRequest;

  try {
    body = (await request.json()) as SetActiveTenantRequest;
  } catch {
    return NextResponse.json(
      { detail: "Invalid request body" },
      { status: 400 },
    );
  }

  const tenantId = body.tenant_id?.trim();

  if (!tenantId) {
    return NextResponse.json(
      { detail: "tenant_id is required" },
      { status: 400 },
    );
  }

  const result = await authenticatedBackendFetch(
    "/api/v1/tenants",
    { method: "GET" },
  );

  if (!result.response.ok) {
    return createBackendErrorResponse(result);
  }

  const tenants = await readTenantList(result.response);
  const tenantIsAvailable = tenants.some(
    (tenant) => tenant.id === tenantId,
  );

  if (!tenantIsAvailable) {
    const response = NextResponse.json(
      { detail: "Selected workspace is not available" },
      { status: 403 },
    );

    applyAuthenticationState(response, result);
    return response;
  }

  const response = NextResponse.json<ActiveTenantResponse>(
    { active_tenant_id: tenantId },
    { status: 200 },
  );

  applyAuthenticationState(response, result);
  persistActiveTenantCookie(response, tenantId);

  return response;
}

function resolveActiveTenantId(
  tenants: TenantSummary[],
  requestedTenantId: string | null,
): string | null {
  if (tenants.length === 0) {
    return null;
  }

  if (
    requestedTenantId &&
    tenants.some((tenant) => tenant.id === requestedTenantId)
  ) {
    return requestedTenantId;
  }

  return tenants[0].id;
}

function persistActiveTenantCookie(
  response: NextResponse,
  tenantId: string | null,
): void {
  if (!tenantId) {
    response.cookies.set(ACTIVE_TENANT_COOKIE, "", {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
    return;
  }

  response.cookies.set(ACTIVE_TENANT_COOKIE, tenantId, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: ACTIVE_TENANT_COOKIE_MAX_AGE,
  });
}

async function readTenantList(
  response: Response,
): Promise<TenantSummary[]> {
  const body = (await response.json()) as unknown;

  if (!Array.isArray(body)) {
    return [];
  }

  return body.filter(
    (item): item is TenantSummary =>
      typeof item === "object" &&
      item !== null &&
      "id" in item &&
      typeof item.id === "string",
  );
}

async function createBackendErrorResponse(
  result: Awaited<
    ReturnType<typeof authenticatedBackendFetch>
  >,
) {
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
