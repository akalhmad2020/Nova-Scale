"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { getHealth } from "@/api/health";
import { CreateTenantForm } from "@/components/create-tenant-form";
import { EmptyState } from "@/components/ui/empty-state";
import { Icon } from "@/components/ui/icon";
import { MetricCard } from "@/components/ui/metric-card";
import { PageHeader } from "@/components/ui/page-header";
import { Surface, SurfaceHeader } from "@/components/ui/surface";
import { useCustomers } from "@/features/customers/hooks";
import { useLocations } from "@/features/locations/hooks";
import { useShipments } from "@/features/shipments/hooks";
import { useMyTenants } from "@/features/tenants/hooks";

export function HomeContent() {
  const [backendStatus, setBackendStatus] = useState("loading");
  const tenantsQuery = useMyTenants();
  const shipmentsQuery = useShipments();
  const customersQuery = useCustomers();
  const locationsQuery = useLocations();

  useEffect(() => {
    async function loadHealth() {
      try {
        const health = await getHealth();
        setBackendStatus(health.status);
      } catch {
        setBackendStatus("unavailable");
      }
    }

    void loadHealth();
  }, []);

  const shipmentMetrics = useMemo(() => {
    const shipments = shipmentsQuery.data ?? [];
    return {
      total: shipments.length,
      active: shipments.filter((shipment) =>
        ["ready", "in_transit"].includes(shipment.status),
      ).length,
      delivered: shipments.filter(
        (shipment) => shipment.status === "delivered",
      ).length,
    };
  }, [shipmentsQuery.data]);

  return (
    <div className="space-y-7">
      <PageHeader
        eyebrow="Operations overview"
        title="Command center"
        description="A live view of the active workspace across shipments, customers, billing, and platform health."
        actions={
          <Link
            href="/shipments"
            className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            View shipments
            <Icon name="arrow-right" className="h-4 w-4" />
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Active shipments"
          value={shipmentsQuery.isPending ? "—" : shipmentMetrics.active}
          note={`${shipmentMetrics.total} shipments in the active workspace`}
          icon="shipments"
          tone="info"
        />
        <MetricCard
          label="Delivered"
          value={shipmentsQuery.isPending ? "—" : shipmentMetrics.delivered}
          note="Completed shipment lifecycle records"
          icon="check"
          tone="success"
        />
        <MetricCard
          label="Customers"
          value={customersQuery.isPending ? "—" : customersQuery.data?.length ?? 0}
          note="Customer accounts available for operations"
          icon="customers"
        />
        <MetricCard
          label="Locations"
          value={locationsQuery.isPending ? "—" : locationsQuery.data?.length ?? 0}
          note="Operational facilities in the active network"
          icon="locations"
          tone="neutral"
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(20rem,0.6fr)]">
        <Surface>
          <SurfaceHeader
            title="Operational snapshot"
            description="Current platform and workspace signals"
            meta={
              <span className="inline-flex items-center gap-2">
                <span
                  className={`h-2 w-2 rounded-full ${
                    backendStatus === "ok" ? "bg-emerald-500" : "bg-rose-500"
                  }`}
                />
                Backend {backendStatus}
              </span>
            }
          />

          <div className="grid gap-px bg-slate-100 sm:grid-cols-3">
            <SnapshotItem
              label="Workspace memberships"
              value={tenantsQuery.data?.length ?? 0}
              description="Tenants available to this account"
            />
            <SnapshotItem
              label="In transit"
              value={
                shipmentsQuery.data?.filter(
                  (shipment) => shipment.status === "in_transit",
                ).length ?? 0
              }
              description="Shipments currently moving"
            />
            <SnapshotItem
              label="Active locations"
              value={
                locationsQuery.data?.filter((location) => location.status === "active").length ?? 0
              }
              description="Facilities available for shipment routing"
            />
          </div>

          <div className="border-t border-slate-100 p-5 sm:p-6">
            <div className="grid gap-3 sm:grid-cols-3">
              <QuickLink
                href="/shipments"
                icon="shipments"
                title="Shipment operations"
                description="Create, inspect, transition, and track shipments."
              />
              <QuickLink
                href="/billing"
                icon="billing"
                title="Billing workspace"
                description="Prepare invoices and manage invoice lifecycle."
              />
              <QuickLink
                href="/ai"
                icon="ai"
                title="NovaScale AI"
                description="Ask operational questions and propose safe actions."
              />
            </div>
          </div>
        </Surface>

        <Surface>
          <SurfaceHeader
            title="Workspaces"
            description="Your tenant memberships"
            meta={
              <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">
                {tenantsQuery.data?.length ?? 0}
              </span>
            }
          />

          {tenantsQuery.isPending ? (
            <div className="p-6 text-sm text-slate-500">Loading workspaces...</div>
          ) : tenantsQuery.isError ? (
            <div className="p-6 text-sm text-rose-600">Unable to load workspaces.</div>
          ) : tenantsQuery.data?.length ? (
            <div className="divide-y divide-slate-100">
              {tenantsQuery.data.map((tenant) => (
                <div key={tenant.id} className="flex items-center gap-3 px-5 py-4 sm:px-6">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                    <Icon name="building" className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-900">{tenant.name}</p>
                    <p className="truncate text-xs text-slate-500">{tenant.slug}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon="building"
              title="No workspace yet"
              description="Create your first tenant workspace to begin operating in NovaScale."
            />
          )}

          {tenantsQuery.data ? (
            <div className="border-t border-slate-100 p-5 sm:p-6">
              <details className="group">
                <summary className="flex cursor-pointer list-none items-center justify-between text-sm font-semibold text-slate-700">
                  Create another workspace
                  <span className="text-slate-400 transition group-open:rotate-45">+</span>
                </summary>
                <div className="mt-5">
                  <CreateTenantForm />
                </div>
              </details>
            </div>
          ) : null}
        </Surface>
      </div>
    </div>
  );
}

type SnapshotItemProps = {
  label: string;
  value: number;
  description: string;
};

function SnapshotItem({ label, value, description }: SnapshotItemProps) {
  return (
    <div className="bg-white p-5 sm:p-6">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{value}</p>
      <p className="mt-2 text-xs leading-5 text-slate-500">{description}</p>
    </div>
  );
}

type QuickLinkProps = {
  href: string;
  icon: "shipments" | "billing" | "ai";
  title: string;
  description: string;
};

function QuickLink({ href, icon, title, description }: QuickLinkProps) {
  return (
    <Link
      href={href}
      className="group rounded-xl border border-slate-200 p-4 transition hover:border-slate-300 hover:bg-slate-50"
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950 text-cyan-300">
        <Icon name={icon} className="h-4 w-4" />
      </div>
      <p className="mt-4 text-sm font-semibold text-slate-900">{title}</p>
      <p className="mt-1 text-xs leading-5 text-slate-500">{description}</p>
      <div className="mt-3 flex items-center gap-1 text-xs font-semibold text-cyan-700">
        Open
        <Icon name="arrow-right" className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />
      </div>
    </Link>
  );
}
