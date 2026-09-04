import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { HomeContent } from "@/components/home-content";
import { isAuthenticated } from "@/features/auth/server";

export default async function DashboardPage() {
  const authenticated = await isAuthenticated();

  if (!authenticated) {
    redirect("/login");
  }

  return (
    <AppShell>
      <HomeContent />
    </AppShell>
  );
}