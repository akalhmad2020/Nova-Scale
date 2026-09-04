import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { LocationsContent } from "@/components/locations-content";
import { isAuthenticated } from "@/features/auth/server";

export default async function LocationsPage() {
  const authenticated = await isAuthenticated();

  if (!authenticated) {
    redirect("/login");
  }

  return (
    <AppShell>
      <LocationsContent />
    </AppShell>
  );
}