import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { CustomersContent } from "@/components/customers-content";
import { isAuthenticated } from "@/features/auth/server";

export default async function CustomersPage() {
  const authenticated = await isAuthenticated();

  if (!authenticated) {
    redirect("/login");
  }

  return (
    <AppShell>
      <CustomersContent />
    </AppShell>
  );
}