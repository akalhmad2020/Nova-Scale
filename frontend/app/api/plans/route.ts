import { NextResponse } from "next/server";

import { env } from "@/lib/env";

export async function GET() {
  const backendResponse = await fetch(
    `${env.NEXT_PUBLIC_API_BASE_URL}/api/v1/plans`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  const body = await readResponseBody(backendResponse);

  return NextResponse.json(body, {
    status: backendResponse.status,
  });
}

async function readResponseBody(
  response: Response,
): Promise<unknown> {
  const contentType = response.headers.get("content-type");

  if (contentType?.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();

  return {
    detail: text || "Unable to communicate with backend",
  };
}
