import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  clearSessionCookies,
  REFRESH_TOKEN_COOKIE,
} from "@/features/auth/cookies";
import {
  applyAuthenticationState,
  readBackendResponseBody,
  refreshAuthentication,
} from "@/features/auth/server-client";

export async function POST() {
  const cookieStore = await cookies();

  const refreshToken =
    cookieStore.get(REFRESH_TOKEN_COOKIE)?.value;

  if (!refreshToken) {
    const response = NextResponse.json(
      { detail: "Not authenticated" },
      { status: 401 },
    );

    clearSessionCookies(response);
    return response;
  }

  const result = await refreshAuthentication(
    refreshToken,
  );

  if (!result.response.ok) {
    const body = await readBackendResponseBody(
      result.response,
    );
    const response = NextResponse.json(body, {
      status: result.response.status,
    });

    applyAuthenticationState(response, result);
    return response;
  }

  const response = NextResponse.json(
    { authenticated: true },
    { status: 200 },
  );

  applyAuthenticationState(response, result);

  return response;
}
