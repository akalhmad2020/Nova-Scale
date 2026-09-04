import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_TOKEN_COOKIE,
  clearAuthCookies,
  setAuthCookies,
} from "@/features/auth/cookies";
import type {
  TokenResponse,
  User,
} from "@/features/auth/types";
import { env } from "@/lib/env";

async function fetchCurrentUser(accessToken: string) {
  return fetch(
    `${env.NEXT_PUBLIC_API_BASE_URL}/api/v1/auth/me`,
    {
      method: "GET",
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
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

async function refreshAndLoadCurrentUser(
  refreshToken: string,
) {
  const refreshResponse =
    await refreshTokens(refreshToken);

  const refreshData =
    await refreshResponse.json();

  if (!refreshResponse.ok) {
    const response = NextResponse.json(
      { detail: "Not authenticated" },
      { status: 401 },
    );

    clearAuthCookies(response);

    return response;
  }

  const tokens = refreshData as TokenResponse;

  const userResponse = await fetchCurrentUser(
    tokens.access_token,
  );

  const userData = await userResponse.json();

  if (!userResponse.ok) {
    const response = NextResponse.json(
      userData,
      {
        status: userResponse.status,
      },
    );

    clearAuthCookies(response);

    return response;
  }

  const response = NextResponse.json(
    userData as User,
    {
      status: 200,
    },
  );

  setAuthCookies(response, tokens);

  return response;
}

export async function GET() {
  const cookieStore = await cookies();

  const accessToken =
    cookieStore.get(ACCESS_TOKEN_COOKIE)?.value;

  const refreshToken =
    cookieStore.get(REFRESH_TOKEN_COOKIE)?.value;

  if (!accessToken) {
    if (!refreshToken) {
      return NextResponse.json(
        { detail: "Not authenticated" },
        { status: 401 },
      );
    }

    return refreshAndLoadCurrentUser(
      refreshToken,
    );
  }

  const userResponse =
    await fetchCurrentUser(accessToken);

  if (userResponse.status === 401) {
    if (!refreshToken) {
      const response = NextResponse.json(
        { detail: "Not authenticated" },
        { status: 401 },
      );

      clearAuthCookies(response);

      return response;
    }

    return refreshAndLoadCurrentUser(
      refreshToken,
    );
  }

  const userData = await userResponse.json();

  if (!userResponse.ok) {
    return NextResponse.json(
      userData,
      {
        status: userResponse.status,
      },
    );
  }

  return NextResponse.json(
    userData as User,
    {
      status: 200,
    },
  );
}