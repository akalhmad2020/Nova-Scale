import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  clearSessionCookies,
  REFRESH_TOKEN_COOKIE,
} from "@/features/auth/cookies";
import { env } from "@/lib/env";

export async function POST() {
  const cookieStore = await cookies();

  const refreshToken =
    cookieStore.get(REFRESH_TOKEN_COOKIE)?.value;

  if (refreshToken) {
    try {
      await fetch(
        `${env.BACKEND_API_BASE_URL}/api/v1/auth/logout`,
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
      // Local logout should still succeed.
    }
  }

  const response = NextResponse.json(
    { authenticated: false },
    { status: 200 },
  );

  clearSessionCookies(response);

  return response;
}
