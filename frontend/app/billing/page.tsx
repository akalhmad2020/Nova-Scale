import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { BillingContent } from "@/components/billing-content";
import { isAuthenticated } from "@/features/auth/server";

export default async function BillingPage() {
  const authenticated = await isAuthenticated();

  if (!authenticated) {
    redirect("/login");
  }

  return (
    <AppShell>
      <BillingContent />
    </AppShell>
  );
}