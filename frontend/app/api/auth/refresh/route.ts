import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { setAuthCookies } from "@/features/auth/cookies";
import type { TokenResponse } from "@/features/auth/types";
import { env } from "@/lib/env";

export async function POST() {
  const cookieStore = await cookies();

  const refreshToken =
    cookieStore.get("novascale_refresh_token")?.value;

  if (!refreshToken) {
    return NextResponse.json(
      { detail: "Not authenticated" },
      { status: 401 },
    );
  }

  const response = await fetch(
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

  const data = await response.json();

  if (!response.ok) {
    return NextResponse.json(data, {
      status: response.status,
    });
  }

  const tokens = data as TokenResponse;

  const nextResponse = NextResponse.json(
    { authenticated: true },
    { status: 200 },
  );

  setAuthCookies(nextResponse, tokens);

  return nextResponse;
}