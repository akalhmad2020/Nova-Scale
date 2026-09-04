import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { InvoiceDetailsContent } from "@/components/invoice-details-content";
import { isAuthenticated } from "@/features/auth/server";

type InvoicePageProps = {
  params: Promise<{
    invoiceId: string;
  }>;
};

export default async function InvoicePage({
  params,
}: InvoicePageProps) {
  const authenticated =
    await isAuthenticated();

  if (!authenticated) {
    redirect("/login");
  }

  const { invoiceId } = await params;

  return (
    <AppShell>
      <InvoiceDetailsContent
        invoiceId={invoiceId}
      />
    </AppShell>
  );
}