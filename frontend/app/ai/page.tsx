import { redirect } from "next/navigation";

import { AIAssistantContent } from "@/components/ai-assistant-content";
import { AppShell } from "@/components/app-shell";
import { isAuthenticated } from "@/features/auth/server";

export default async function AIPage() {
  const authenticated =
    await isAuthenticated();

  if (!authenticated) {
    redirect("/login");
  }

  return (
    <AppShell>
      <AIAssistantContent />
    </AppShell>
  );
}