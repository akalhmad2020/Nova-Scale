"use client";

import Link from "next/link";

import { PlanAccessCard } from "@/components/plan-access-card";
import { RecordShipmentEventForm } from "@/components/record-shipment-event-form";
import { ShipmentIntelligencePanel } from "@/components/shipment-intelligence-panel";
import { ShipmentTimeline } from "@/components/shipment-timeline";
import { Icon } from "@/components/ui/icon";
import { StatusBadge, formatStatus } from "@/components/ui/status-badge";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import {
  useShipment,
  useShipmentEvents,
  useShipmentOperationalAnalysis,
  useTransitionShipmentStatus,
} from "@/features/shipments/hooks";
import {
  hasAIAssistantAccess,
  resolveCurrentPlan,
} from "@/features/saas/access";
import {
  useCurrentSubscription,
  usePlans,
} from "@/features/saas/hooks";
import type { ShipmentStatus } from "@/features/shipments/types";

type ShipmentDetailsContentProps = {
  shipmentId: string;
};

export function ShipmentDetailsContent({
  shipmentId,
}: ShipmentDetailsContentProps) {
  const shipmentQuery = useShipment(shipmentId);
  const shipmentEventsQuery = useShipmentEvents(shipmentId);
  const transitionMutation = useTransitionShipmentStatus(shipmentId);

  if (shipmentQuery.isPending) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
        Loading shipment...
      </div>
    );
  }

  if (shipmentQuery.isError) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        {shipmentQuery.error.message}
      </div>
    );
  }

  const shipment = shipmentQuery.data;
  const nextStatus = getNextShipmentStatus(shipment.status);

  async function handleTransition() {
    if (!nextStatus) return;
    await transitionMutation.mutateAsync({ status: nextStatus });
  }

  return (
    <div className="space-y-7">
      <div>
        <Link
          href="/shipments"
          className="inline-flex items-center gap-2 text-sm font-medium text-slate-500 transition hover:text-slate-950"
        >
          <span aria-hidden>←</span>
          Shipments
        </Link>

        <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
                {shipment.tracking_number}
              </h1>
              <StatusBadge value={shipment.status} />
            </div>
            <p className="mt-2 text-sm text-slate-500">
              {shipment.reference ? `Reference ${shipment.reference}` : "No external reference"}
              <span className="mx-2 text-slate-300">•</span>
              Created {formatDateTime(shipment.created_at)}
            </p>
          </div>

          {nextStatus ? (
            <button
              type="button"
              onClick={() => void handleTransition()}
              disabled={transitionMutation.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Icon name="arrow-right" className="h-4 w-4" />
              {transitionMutation.isPending
                ? "Updating status..."
                : `Move to ${formatStatus(nextStatus)}`}
            </button>
          ) : null}
        </div>

        {transitionMutation.isError ? (
          <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {transitionMutation.error instanceof Error
              ? transitionMutation.error.message
              : "Unable to update shipment status"}
          </div>
        ) : null}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Detail label="Service" value={formatStatus(shipment.service_type)} />
        <Detail label="Weight" value={`${shipment.weight} ${shipment.weight_unit.toUpperCase()}`} />
        <Detail label="Reference" value={shipment.reference ?? "—"} />
        <Detail label="Last updated" value={formatDateTime(shipment.updated_at)} />
      </div>

      <ShipmentIntelligenceAccess shipmentId={shipmentId} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(20rem,0.75fr)]">
        <Surface>
          <SurfaceHeader
            title="Shipment timeline"
            description="Chronological operational activity"
            meta={
              shipmentEventsQuery.data
                ? `${shipmentEventsQuery.data.length} event${shipmentEventsQuery.data.length === 1 ? "" : "s"}`
                : undefined
            }
          />
          <div className="p-5 sm:p-6">
            {shipmentEventsQuery.isPending ? (
              <p className="text-sm text-slate-500">Loading shipment events...</p>
            ) : shipmentEventsQuery.isError ? (
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                {shipmentEventsQuery.error.message}
              </div>
            ) : (
              <ShipmentTimeline events={shipmentEventsQuery.data} />
            )}
          </div>
        </Surface>

        <div className="space-y-6">
          <Surface>
            <SurfaceHeader title="Record event" description="Add timeline activity" />
            <div className="p-5 sm:p-6">
              <RecordShipmentEventForm shipmentId={shipmentId} />
            </div>
          </Surface>

          <Surface>
            <SurfaceHeader title="Shipment details" description="Operational metadata" />
            <dl className="divide-y divide-slate-100 px-5 sm:px-6">
              <DetailRow label="Description" value={shipment.description ?? "—"} />
              <DetailRow label="Notes" value={shipment.notes ?? "—"} />
              <DetailRow label="Shipment ID" value={shipment.id} mono />
              <DetailRow label="Customer ID" value={shipment.customer_id} mono />
              <DetailRow label="Origin location" value={shipment.origin_location_id} mono />
              <DetailRow label="Destination location" value={shipment.destination_location_id} mono />
            </dl>
          </Surface>
        </div>
      </div>
    </div>
  );
}

function ShipmentIntelligenceAccess({
  shipmentId,
}: {
  shipmentId: string;
}) {
  const plansQuery = usePlans();
  const subscriptionQuery = useCurrentSubscription();

  if (plansQuery.isPending || subscriptionQuery.isPending) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
        Checking operational intelligence access...
      </div>
    );
  }

  if (plansQuery.isError || subscriptionQuery.isError) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-800">
        Unable to verify operational intelligence access for this workspace.
      </div>
    );
  }

  const currentPlan = resolveCurrentPlan(
    plansQuery.data,
    subscriptionQuery.data,
  );

  if (!currentPlan) {
    return null;
  }

  if (!currentPlan.entitlements.ai_assistant) {
    return (
      <PlanAccessCard
        eyebrow="Plan upgrade"
        currentPlanName={currentPlan.name}
        title="Operational intelligence is available on Professional"
        description="Upgrade the workspace to unlock shipment risk analysis and AI-assisted operational context."
        compact
      />
    );
  }

  if (
    !hasAIAssistantAccess(
      currentPlan,
      subscriptionQuery.data,
    )
  ) {
    return (
      <PlanAccessCard
        eyebrow="Subscription status"
        currentPlanName={currentPlan.name}
        title="Operational intelligence is currently paused"
        description={`This workspace plan includes operational intelligence, but the subscription is ${subscriptionQuery.data.status.replaceAll("_", " ")}.`}
        compact
      />
    );
  }

  return <ShipmentIntelligenceData shipmentId={shipmentId} />;
}

function ShipmentIntelligenceData({
  shipmentId,
}: {
  shipmentId: string;
}) {
  const query = useShipmentOperationalAnalysis(shipmentId);

  if (query.isPending) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500">
        Loading operational intelligence...
      </div>
    );
  }

  if (query.isError) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
        {query.error.message}
      </div>
    );
  }

  return <ShipmentIntelligencePanel analysis={query.data} />;
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-2 truncate text-sm font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function DetailRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="py-4">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className={`mt-1.5 break-words text-sm text-slate-700 ${mono ? "font-mono text-xs" : ""}`}>
        {value}
      </dd>
    </div>
  );
}

function getNextShipmentStatus(status: ShipmentStatus): ShipmentStatus | null {
  switch (status) {
    case "draft":
      return "ready";
    case "ready":
      return "in_transit";
    case "in_transit":
      return "delivered";
    case "delivered":
    case "cancelled":
      return null;
  }
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
