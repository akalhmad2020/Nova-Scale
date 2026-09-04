import type { NextResponse } from "next/server";

import type { TokenResponse } from "@/features/auth/types";

export const ACCESS_TOKEN_COOKIE =
  "novascale_access_token";

export const REFRESH_TOKEN_COOKIE =
  "novascale_refresh_token";

export function setAuthCookies(
  response: NextResponse,
  tokens: TokenResponse,
) {
  response.cookies.set(
    ACCESS_TOKEN_COOKIE,
    tokens.access_token,
    {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: tokens.expires_in,
    },
  );

  response.cookies.set(
    REFRESH_TOKEN_COOKIE,
    tokens.refresh_token,
    {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
    },
  );
}

export function clearAuthCookies(
  response: NextResponse,
) {
  response.cookies.set(
    ACCESS_TOKEN_COOKIE,
    "",
    {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    },
  );

  response.cookies.set(
    REFRESH_TOKEN_COOKIE,
    "",
    {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    },
  );
}