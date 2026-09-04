import { redirect } from "next/navigation";

import { isAuthenticated } from "@/features/auth/server";

export default async function Home() {
  const authenticated = await isAuthenticated();

  if (!authenticated) {
    redirect("/login");
  }

  redirect("/dashboard");
}