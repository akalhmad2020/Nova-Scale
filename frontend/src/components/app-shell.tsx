"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { ActiveTenantInitializer } from "@/components/active-tenant-initializer";
import { TenantSwitcher } from "@/components/tenant-switcher";
import {
  useCurrentUser,
  useLogout,
} from "@/features/auth/hooks";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({
  children,
}: AppShellProps) {
  const router = useRouter();

  const currentUser = useCurrentUser();
  const logoutMutation = useLogout();

  async function handleLogout() {
    await logoutMutation.mutateAsync();

    router.push("/login");
    router.refresh();
  }

  return (
    <div className="min-h-screen bg-zinc-50">
      <ActiveTenantInitializer />

      <div className="flex min-h-screen">
        <aside className="flex w-64 flex-col border-r border-zinc-200 bg-white">
          <div className="border-b border-zinc-200 px-6 py-5">
            <p className="text-lg font-semibold text-zinc-950">
              NovaScale
            </p>

            <p className="mt-1 text-xs text-zinc-500">
              Shipping & Logistics
            </p>
          </div>

          <div className="border-b border-zinc-200 p-4">
            <TenantSwitcher />
          </div>

          <nav className="flex-1 p-4">
            <div className="space-y-1">
              <Link
                href="/dashboard"
                className="block rounded-lg bg-zinc-100 px-3 py-2 text-sm font-medium text-zinc-950"
              >
                Dashboard
              </Link>

              <Link
                href="/shipments"
                className="block rounded-lg px-3 py-2 text-sm text-zinc-700 transition hover:bg-zinc-100 hover:text-zinc-950"
              >
                Shipments
                </Link>

              <Link
              href="/customers"
              className="block rounded-lg px-3 py-2 text-sm text-zinc-700 transition hover:bg-zinc-100 hover:text-zinc-950"
              >
              Customers
              </Link>

              <Link
  href="/locations"
  className="block rounded-lg px-3 py-2 text-sm text-zinc-700 transition hover:bg-zinc-100 hover:text-zinc-950"
>
  Locations
</Link>

              <Link
                  href="/billing"
                  className="block rounded-lg px-3 py-2 text-sm text-zinc-700 transition hover:bg-zinc-100 hover:text-zinc-950"
                >
                Billing
                </Link>

              <Link href="/ai">
  AI Assistant
</Link>
            </div>
          </nav>

          <div className="border-t border-zinc-200 p-4">
            {currentUser.isPending && (
              <p className="text-sm text-zinc-500">
                Loading user...
              </p>
            )}

            {currentUser.data && (
              <div className="mb-3 min-w-0">
                <p className="truncate text-sm font-medium text-zinc-950">
                  {currentUser.data.first_name}{" "}
                  {currentUser.data.last_name}
                </p>

                <p className="truncate text-xs text-zinc-500">
                  {currentUser.data.email}
                </p>
              </div>
            )}

            <button
              type="button"
              onClick={handleLogout}
              disabled={logoutMutation.isPending}
              className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-900 transition hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {logoutMutation.isPending
                ? "Signing out..."
                : "Sign out"}
            </button>

            {logoutMutation.isError && (
              <p className="mt-2 text-xs text-red-600">
                Unable to sign out.
              </p>
            )}
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex h-16 items-center justify-between border-b border-zinc-200 bg-white px-6">
            <p className="text-sm font-medium text-zinc-950">
              Dashboard
            </p>

            <p className="text-sm text-zinc-500">
              NovaScale
            </p>
          </header>

          <main className="flex-1 p-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}