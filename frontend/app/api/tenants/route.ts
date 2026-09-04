import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_TOKEN_COOKIE,
  clearAuthCookies,
  setAuthCookies,
} from "@/features/auth/cookies";
import type { TokenResponse } from "@/features/auth/types";
import type {
  CreateTenantInput,
  CreateTenantResponse,
  UserTenant,
} from "@/features/tenants/types";
import { env } from "@/lib/env";

async function fetchTenants(accessToken: string) {
  return fetch(
    `${env.NEXT_PUBLIC_API_BASE_URL}/api/v1/tenants`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
      cache: "no-store",
    },
  );
}

async function createTenant(
  accessToken: string,
  input: CreateTenantInput,
) {
  return fetch(
    `${env.NEXT_PUBLIC_API_BASE_URL}/api/v1/tenants`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
      cache: "no-store",
    },
  );
}

async function refreshTokens(refreshToken: string) {
  return fetch(
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
}

async function getAuthTokens() {
  const cookieStore = await cookies();

  return {
    accessToken:
      cookieStore.get(ACCESS_TOKEN_COOKIE)?.value,
    refreshToken:
      cookieStore.get(REFRESH_TOKEN_COOKIE)?.value,
  };
}

async function refreshSession(refreshToken: string) {
  const refreshResponse =
    await refreshTokens(refreshToken);

  const refreshData =
    await refreshResponse.json();

  if (!refreshResponse.ok) {
    return null;
  }

  return refreshData as TokenResponse;
}

function unauthenticatedResponse() {
  const response = NextResponse.json(
    { detail: "Not authenticated" },
    { status: 401 },
  );

  clearAuthCookies(response);

  return response;
}

export async function GET() {
  const {
    accessToken,
    refreshToken,
  } = await getAuthTokens();

  if (!accessToken && !refreshToken) {
    return unauthenticatedResponse();
  }

  if (accessToken) {
    const tenantsResponse =
      await fetchTenants(accessToken);

    if (tenantsResponse.status !== 401) {
      const data = await tenantsResponse.json();

      return NextResponse.json(data, {
        status: tenantsResponse.status,
      });
    }
  }

  if (!refreshToken) {
    return unauthenticatedResponse();
  }

  const tokens =
    await refreshSession(refreshToken);

  if (!tokens) {
    return unauthenticatedResponse();
  }

  const tenantsResponse = await fetchTenants(
    tokens.access_token,
  );

  const tenantsData =
    await tenantsResponse.json();

  if (!tenantsResponse.ok) {
    return NextResponse.json(
      tenantsData,
      {
        status: tenantsResponse.status,
      },
    );
  }

  const response = NextResponse.json(
    tenantsData as UserTenant[],
    {
      status: 200,
    },
  );

  setAuthCookies(response, tokens);

  return response;
}

export async function POST(request: Request) {
  const input =
    (await request.json()) as CreateTenantInput;

  const {
    accessToken,
    refreshToken,
  } = await getAuthTokens();

  if (!accessToken && !refreshToken) {
    return unauthenticatedResponse();
  }

  if (accessToken) {
    const tenantResponse =
      await createTenant(
        accessToken,
        input,
      );

    if (tenantResponse.status !== 401) {
      const data =
        await tenantResponse.json();

      return NextResponse.json(data, {
        status: tenantResponse.status,
      });
    }
  }

  if (!refreshToken) {
    return unauthenticatedResponse();
  }

  const tokens =
    await refreshSession(refreshToken);

  if (!tokens) {
    return unauthenticatedResponse();
  }

  const tenantResponse =
    await createTenant(
      tokens.access_token,
      input,
    );

  const tenantData =
    await tenantResponse.json();

  if (!tenantResponse.ok) {
    return NextResponse.json(
      tenantData,
      {
        status: tenantResponse.status,
      },
    );
  }

  const response = NextResponse.json(
    tenantData as CreateTenantResponse,
    {
      status: tenantResponse.status,
    },
  );

  setAuthCookies(response, tokens);

  return response;
}