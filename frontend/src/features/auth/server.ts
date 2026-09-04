import { cookies } from "next/headers";

export async function isAuthenticated(): Promise<boolean> {
  const cookieStore = await cookies();

  const accessToken =
    cookieStore.get("novascale_access_token")?.value;

  const refreshToken =
    cookieStore.get("novascale_refresh_token")?.value;

  return Boolean(accessToken || refreshToken);
}