import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { ShipmentsContent } from "@/components/shipments-content";
import { isAuthenticated } from "@/features/auth/server";

export default async function ShipmentsPage() {
  const authenticated = await isAuthenticated();

  if (!authenticated) {
    redirect("/login");
  }

  return (
    <AppShell>
      <ShipmentsContent />
    </AppShell>
  );
}