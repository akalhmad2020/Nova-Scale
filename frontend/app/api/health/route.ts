import { NextResponse } from "next/server";

import { env } from "@/lib/env";

export async function GET() {
  try {
    const response = await fetch(
      `${env.NEXT_PUBLIC_API_BASE_URL}/health`,
      {
        method: "GET",
        cache: "no-store",
      },
    );

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch {
    return NextResponse.json(
      {
        status: "unavailable",
      },
      {
        status: 503,
      },
    );
  }
}