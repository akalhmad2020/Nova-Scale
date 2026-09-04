import { NextResponse } from "next/server";

import { setAuthCookies } from "@/features/auth/cookies";
import type {
  LoginCredentials,
  TokenResponse,
} from "@/features/auth/types";
import { env } from "@/lib/env";

export async function POST(request: Request) {
  const credentials =
    (await request.json()) as LoginCredentials;

  const response = await fetch(
    `${env.NEXT_PUBLIC_API_BASE_URL}/api/v1/auth/login`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(credentials),
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