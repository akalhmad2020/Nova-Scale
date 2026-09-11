import { NextResponse } from "next/server";

import type {
  RegisterCompanyInput,
  RegisterCompanyResponse,
} from "@/features/auth/types";
import { env } from "@/lib/env";

export async function POST(request: Request) {
  const input = (await request.json()) as RegisterCompanyInput;

  const response = await fetch(
    `${env.NEXT_PUBLIC_API_BASE_URL}/api/v1/auth/register`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(input),
      cache: "no-store",
    },
  );

  const data = await response.json();

  if (!response.ok) {
    return NextResponse.json(data, {
      status: response.status,
    });
  }

  return NextResponse.json(data as RegisterCompanyResponse, {
    status: 201,
  });
}
