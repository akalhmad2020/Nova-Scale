import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  applyAuthenticationState,
  authenticatedBackendFetch,
} from "@/features/auth/server-client";
import { ACTIVE_TENANT_COOKIE } from "@/features/tenants/active-tenant";

type RouteContext = {
  params: Promise<{
    conversationId: string;
  }>;
};

async function proxyConversationRequest(
  method: "GET" | "DELETE",
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

  const { conversationId } = await context.params;

  const result = await authenticatedBackendFetch(
    `/api/v1/ai/tenants/${activeTenantId}/conversations/${conversationId}`,
    { method },
  );

  if (result.response.status === 204) {
    const response = new NextResponse(null, {
      status: 204,
    });

    applyAuthenticationState(response, result);
    return response;
  }

  const responseBody = await result.response.json();
  const response = NextResponse.json(
    responseBody,
    { status: result.response.status },
  );

  applyAuthenticationState(response, result);

  return response;
}

export async function GET(
  _request: Request,
  context: RouteContext,
) {
  return proxyConversationRequest("GET", context);
}

export async function DELETE(
  _request: Request,
  context: RouteContext,
) {
  return proxyConversationRequest("DELETE", context);
}
