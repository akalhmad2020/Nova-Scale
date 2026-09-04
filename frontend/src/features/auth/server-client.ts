import { cookies } from "next/headers";
import type { NextResponse } from "next/server";

import {
  ACCESS_TOKEN_COOKIE,
  clearAuthCookies,
  REFRESH_TOKEN_COOKIE,
  setAuthCookies,
} from "@/features/auth/cookies";
import type { TokenResponse } from "@/features/auth/types";
import { env } from "@/lib/env";

type AuthenticatedBackendFetchResult = {
  response: Response;
  refreshedTokens: TokenResponse | null;
  clearAuthentication: boolean;
};

export async function authenticatedBackendFetch(
  path: string,
  init?: RequestInit,
): Promise<AuthenticatedBackendFetchResult> {
  const cookieStore = await cookies();

  const accessToken =
    cookieStore.get(ACCESS_TOKEN_COOKIE)?.value;

  const refreshToken =
    cookieStore.get(REFRESH_TOKEN_COOKIE)?.value;

  if (!accessToken && !refreshToken) {
    return {
      response: new Response(null, {
        status: 401,
      }),
      refreshedTokens: null,
      clearAuthentication: true,
    };
  }

  if (accessToken) {
    const response = await fetch(
      `${env.NEXT_PUBLIC_API_BASE_URL}${path}`,
      withBearerToken(init, accessToken),
    );

    if (response.status !== 401) {
      return {
        response,
        refreshedTokens: null,
        clearAuthentication: false,
      };
    }
  }

  if (!refreshToken) {
    return {
      response: new Response(null, {
        status: 401,
      }),
      refreshedTokens: null,
      clearAuthentication: true,
    };
  }

  const refreshResponse = await fetch(
    `${env.NEXT_PUBLIC_API_BASE_URL}/api/v1/auth/refresh`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
      cache: "no-store",
    },
  );

  if (!refreshResponse.ok) {
    return {
      response: refreshResponse,
      refreshedTokens: null,
      clearAuthentication: true,
    };
  }

  const tokens =
    (await refreshResponse.json()) as TokenResponse;

  const response = await fetch(
    `${env.NEXT_PUBLIC_API_BASE_URL}${path}`,
    withBearerToken(init, tokens.access_token),
  );

  return {
    response,
    refreshedTokens: tokens,
    clearAuthentication: response.status === 401,
  };
}

export function applyAuthenticationState(
  response: NextResponse,
  result: AuthenticatedBackendFetchResult,
): void {
  if (result.clearAuthentication) {
    clearAuthCookies(response);
    return;
  }

  if (result.refreshedTokens) {
    setAuthCookies(
      response,
      result.refreshedTokens,
    );
  }
}

function withBearerToken(
  init: RequestInit | undefined,
  accessToken: string,
): RequestInit {
  const headers = new Headers(init?.headers);

  headers.set(
    "Authorization",
    `Bearer ${accessToken}`,
  );

  return {
    ...init,
    headers,
    cache: "no-store",
  };
}