import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { clearAuthCookies } from "@/features/auth/cookies";
import { env } from "@/lib/env";

export async function POST() {
  const cookieStore = await cookies();

  const refreshToken =
    cookieStore.get("novascale_refresh_token")?.value;

  if (refreshToken) {
    try {
      await fetch(
        `${env.NEXT_PUBLIC_API_BASE_URL}/api/v1/auth/logout`,
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

  clearAuthCookies(response);

  return response;
}