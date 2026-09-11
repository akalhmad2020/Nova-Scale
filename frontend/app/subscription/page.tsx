import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { SubscriptionContent } from "@/components/subscription-content";
import { isAuthenticated } from "@/features/auth/server";

export default async function SubscriptionPage() {
  const authenticated = await isAuthenticated();

  if (!authenticated) {
    redirect("/login");
  }

  return (
    <AppShell>
      <SubscriptionContent />
    </AppShell>
  );
}
