import { cookies } from "next/headers";
import type { NextResponse } from "next/server";

import {
  ACCESS_TOKEN_COOKIE,
  clearSessionCookies,
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

type RefreshAttempt = {
  status: number;
  body: unknown;
  tokens: TokenResponse | null;
  clearAuthentication: boolean;
};

type RefreshFlight = {
  promise: Promise<RefreshAttempt>;
  expiresAt: number;
};

const REFRESH_RESULT_GRACE_MS = 30_000;

const globalRefreshState = globalThis as typeof globalThis & {
  __novascaleAuthRefreshFlights?: Map<string, RefreshFlight>;
};

const refreshFlights =
  globalRefreshState.__novascaleAuthRefreshFlights ??
  new Map<string, RefreshFlight>();

globalRefreshState.__novascaleAuthRefreshFlights =
  refreshFlights;

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
    return unauthenticatedResult();
  }

  if (accessToken) {
    const response = await fetch(
      `${env.BACKEND_API_BASE_URL}${path}`,
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
    return unauthenticatedResult();
  }

  const refreshResult =
    await refreshAuthentication(refreshToken);

  if (!refreshResult.response.ok) {
    return refreshResult;
  }

  const refreshedTokens = refreshResult.refreshedTokens;

  if (!refreshedTokens) {
    return backendFailureResult(
      502,
      "Authentication refresh returned no tokens",
    );
  }

  const response = await fetch(
    `${env.BACKEND_API_BASE_URL}${path}`,
    withBearerToken(init, refreshedTokens.access_token),
  );

  return {
    response,
    refreshedTokens,
    clearAuthentication: response.status === 401,
  };
}

export async function refreshAuthentication(
  refreshToken: string,
): Promise<AuthenticatedBackendFetchResult> {
  const attempt = await getRefreshAttempt(refreshToken);

  return {
    response: jsonResponse(attempt.body, attempt.status),
    refreshedTokens: attempt.tokens,
    clearAuthentication: attempt.clearAuthentication,
  };
}

export function applyAuthenticationState(
  response: NextResponse,
  result: AuthenticatedBackendFetchResult,
): void {
  if (result.clearAuthentication) {
    clearSessionCookies(response);
    return;
  }

  if (result.refreshedTokens) {
    setAuthCookies(
      response,
      result.refreshedTokens,
    );
  }
}

export async function readBackendResponseBody(
  response: Response,
): Promise<unknown> {
  const contentType = response.headers.get("content-type");

  if (contentType?.includes("application/json")) {
    try {
      return await response.json();
    } catch {
      return {
        detail: "Backend returned an invalid JSON response",
      };
    }
  }

  const text = await response.text();

  return {
    detail: text || "Unable to communicate with backend",
  };
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

async function getRefreshAttempt(
  refreshToken: string,
): Promise<RefreshAttempt> {
  const existing = refreshFlights.get(refreshToken);
  const now = Date.now();

  if (existing && existing.expiresAt > now) {
    return existing.promise;
  }

  const flight: RefreshFlight = {
    promise: Promise.resolve({
      status: 500,
      body: { detail: "Refresh request was not initialized" },
      tokens: null,
      clearAuthentication: false,
    }),
    expiresAt: Number.POSITIVE_INFINITY,
  };

  flight.promise = performRefresh(refreshToken).then(
    (attempt) => {
      if (attempt.tokens) {
        flight.expiresAt = Date.now() + REFRESH_RESULT_GRACE_MS;
        scheduleRefreshFlightCleanup(refreshToken, flight);
      } else {
        refreshFlights.delete(refreshToken);
      }

      return attempt;
    },
    (error: unknown) => {
      refreshFlights.delete(refreshToken);
      throw error;
    },
  );

  refreshFlights.set(refreshToken, flight);

  return flight.promise;
}

async function performRefresh(
  refreshToken: string,
): Promise<RefreshAttempt> {
  let response: Response;

  try {
    response = await fetch(
      `${env.BACKEND_API_BASE_URL}/api/v1/auth/refresh`,
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
  } catch {
    return {
      status: 503,
      body: { detail: "Authentication service unavailable" },
      tokens: null,
      clearAuthentication: false,
    };
  }

  const body = await readBackendResponseBody(response);

  if (!response.ok) {
    return {
      status: response.status,
      body,
      tokens: null,
      clearAuthentication: [400, 401, 403].includes(response.status),
    };
  }

  if (!isTokenResponse(body)) {
    return {
      status: 502,
      body: { detail: "Authentication service returned invalid tokens" },
      tokens: null,
      clearAuthentication: false,
    };
  }

  return {
    status: response.status,
    body,
    tokens: body,
    clearAuthentication: false,
  };
}

function scheduleRefreshFlightCleanup(
  refreshToken: string,
  flight: RefreshFlight,
): void {
  setTimeout(() => {
    if (refreshFlights.get(refreshToken) === flight) {
      refreshFlights.delete(refreshToken);
    }
  }, REFRESH_RESULT_GRACE_MS);
}

function isTokenResponse(
  value: unknown,
): value is TokenResponse {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;

  return (
    typeof candidate.access_token === "string" &&
    typeof candidate.refresh_token === "string" &&
    typeof candidate.token_type === "string" &&
    typeof candidate.expires_in === "number"
  );
}

function unauthenticatedResult(): AuthenticatedBackendFetchResult {
  return {
    response: jsonResponse(
      { detail: "Not authenticated" },
      401,
    ),
    refreshedTokens: null,
    clearAuthentication: true,
  };
}

function backendFailureResult(
  status: number,
  detail: string,
): AuthenticatedBackendFetchResult {
  return {
    response: jsonResponse({ detail }, status),
    refreshedTokens: null,
    clearAuthentication: false,
  };
}

function jsonResponse(
  body: unknown,
  status: number,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
    },
  });
}
