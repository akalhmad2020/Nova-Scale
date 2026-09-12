import { NextResponse } from "next/server";

import {
  applyAuthenticationState,
  authenticatedBackendFetch,
  readBackendResponseBody,
} from "@/features/auth/server-client";

export async function GET() {
  const result = await authenticatedBackendFetch(
    "/api/v1/auth/me",
    { method: "GET" },
  );

  const body = await readBackendResponseBody(
    result.response,
  );

  const response = NextResponse.json(body, {
    status: result.response.status,
  });

  applyAuthenticationState(response, result);

  return response;
}
