import { redirect } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { ShipmentDetailsContent } from "@/components/shipment-details-content";
import { isAuthenticated } from "@/features/auth/server";

type ShipmentPageProps = {
  params: Promise<{
    shipmentId: string;
  }>;
};

export default async function ShipmentPage({
  params,
}: ShipmentPageProps) {
  const authenticated =
    await isAuthenticated();

  if (!authenticated) {
    redirect("/login");
  }

  const { shipmentId } = await params;

  return (
    <AppShell>
      <ShipmentDetailsContent
        shipmentId={shipmentId}
      />
    </AppShell>
  );
}