import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { ACTIVE_TENANT_COOKIE } from "@/features/tenants/active-tenant";

type SetActiveTenantRequest = {
  tenant_id: string;
};

export async function GET() {
  const cookieStore = await cookies();

  const activeTenantId =
    cookieStore.get(ACTIVE_TENANT_COOKIE)?.value ?? null;

  return NextResponse.json(
    {
      active_tenant_id: activeTenantId,
    },
    {
      status: 200,
    },
  );
}

export async function POST(request: Request) {
  const body =
    (await request.json()) as SetActiveTenantRequest;

  if (!body.tenant_id) {
    return NextResponse.json(
      {
        detail: "tenant_id is required",
      },
      {
        status: 400,
      },
    );
  }

  const response = NextResponse.json(
    {
      active_tenant_id: body.tenant_id,
    },
    {
      status: 200,
    },
  );

  response.cookies.set(
    ACTIVE_TENANT_COOKIE,
    body.tenant_id,
    {
      httpOnly: false,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 60 * 60 * 24 * 365,
    },
  );

  return response;
}