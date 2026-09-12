"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { ActiveTenantInitializer } from "@/components/active-tenant-initializer";
import { TenantSwitcher } from "@/components/tenant-switcher";
import { Icon, type IconName } from "@/components/ui/icon";
import {
  useCurrentUser,
  useLogout,
} from "@/features/auth/hooks";

type AppShellProps = {
  children: ReactNode;
};

type NavigationItem = {
  href: string;
  label: string;
  description: string;
  icon: IconName;
};

const NAVIGATION: NavigationItem[] = [
  {
    href: "/dashboard",
    label: "Overview",
    description: "Workspace health",
    icon: "dashboard",
  },
  {
    href: "/shipments",
    label: "Shipments",
    description: "Execution & tracking",
    icon: "shipments",
  },
  {
    href: "/customers",
    label: "Customers",
    description: "Accounts & contacts",
    icon: "customers",
  },
  {
    href: "/locations",
    label: "Locations",
    description: "Network & facilities",
    icon: "locations",
  },
  {
    href: "/billing",
    label: "Billing",
    description: "Invoices & revenue",
    icon: "billing",
  },
  {
    href: "/subscription",
    label: "Subscription",
    description: "Plan & platform access",
    icon: "billing",
  },
  {
    href: "/ai",
    label: "NovaScale AI",
    description: "Operational copilot",
    icon: "ai",
  },
];

export function AppShell({
  children,
}: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const currentUser = useCurrentUser();
  const logoutMutation = useLogout();

  const activeItem =
    NAVIGATION.find((item) => isActivePath(pathname, item.href)) ??
    NAVIGATION[0];

  async function handleLogout() {
    await logoutMutation.mutateAsync();
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <ActiveTenantInitializer />

      <div className="flex min-h-screen">
        <aside className="hidden w-72 shrink-0 flex-col border-r border-slate-800 bg-slate-950 text-slate-100 lg:flex">
          <SidebarContent
            pathname={pathname}
            currentUser={currentUser.data}
            isUserLoading={currentUser.isPending}
            isLoggingOut={logoutMutation.isPending}
            logoutError={logoutMutation.isError}
            onLogout={handleLogout}
          />
        </aside>

        {mobileOpen ? (
          <div className="fixed inset-0 z-50 lg:hidden">
            <button
              type="button"
              aria-label="Close navigation"
              className="absolute inset-0 bg-slate-950/45 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />
            <aside className="relative flex h-full w-[19rem] max-w-[86vw] flex-col border-r border-slate-800 bg-slate-950 text-slate-100 shadow-2xl">
              <button
                type="button"
                aria-label="Close navigation"
                onClick={() => setMobileOpen(false)}
                className="absolute right-4 top-5 rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white"
              >
                <Icon name="close" className="h-5 w-5" />
              </button>
              <SidebarContent
                pathname={pathname}
                currentUser={currentUser.data}
                isUserLoading={currentUser.isPending}
                isLoggingOut={logoutMutation.isPending}
                logoutError={logoutMutation.isError}
                onLogout={handleLogout}
                onNavigate={() => setMobileOpen(false)}
              />
            </aside>
          </div>
        ) : null}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200/80 bg-white/95 px-4 backdrop-blur sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <button
                type="button"
                aria-label="Open navigation"
                onClick={() => setMobileOpen(true)}
                className="rounded-lg border border-slate-200 p-2 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950 lg:hidden"
              >
                <Icon name="menu" className="h-5 w-5" />
              </button>

              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-950">
                  {activeItem.label}
                </p>
                <p className="hidden text-xs text-slate-500 sm:block">
                  {activeItem.description}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 sm:flex">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                Operations online
              </div>

              {currentUser.data ? (
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white shadow-sm">
                  {getInitials(
                    currentUser.data.first_name,
                    currentUser.data.last_name,
                  )}
                </div>
              ) : null}
            </div>
          </header>

          <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
            <div className="mx-auto w-full max-w-[1440px]">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

type SidebarContentProps = {
  pathname: string;
  currentUser:
    | {
        first_name: string;
        last_name: string;
        email: string;
      }
    | undefined;
  isUserLoading: boolean;
  isLoggingOut: boolean;
  logoutError: boolean;
  onLogout: () => Promise<void>;
  onNavigate?: () => void;
};

function SidebarContent({
  pathname,
  currentUser,
  isUserLoading,
  isLoggingOut,
  logoutError,
  onLogout,
  onNavigate,
}: SidebarContentProps) {
  return (
    <>
      <div className="border-b border-slate-800 px-5 py-5">
        <Link
          href="/dashboard"
          onClick={onNavigate}
          className="flex items-center gap-3"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500 text-slate-950 shadow-[0_0_24px_rgba(6,182,212,0.18)]">
            <Icon name="shipments" className="h-5 w-5" />
          </div>
          <div>
            <p className="text-base font-semibold tracking-tight text-white">
              NovaScale
            </p>
            <p className="text-xs text-slate-400">
              Logistics command center
            </p>
          </div>
        </Link>
      </div>

      <div className="border-b border-slate-800 px-4 py-4">
        <TenantSwitcher variant="sidebar" />
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-5">
        <p className="px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Workspace
        </p>
        <div className="mt-3 space-y-1">
          {NAVIGATION.map((item) => {
            const active = isActivePath(pathname, item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onNavigate}
                className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 transition ${
                  active
                    ? "bg-slate-800 text-white shadow-sm"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-100"
                }`}
              >
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-lg transition ${
                    active
                      ? "bg-cyan-500/15 text-cyan-300"
                      : "bg-slate-900 text-slate-500 group-hover:text-slate-300"
                  }`}
                >
                  <Icon name={item.icon} className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {item.label}
                  </p>
                  <p className="truncate text-[11px] text-slate-500 group-hover:text-slate-400">
                    {item.description}
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      </nav>

      <div className="border-t border-slate-800 p-4">
        <div className="rounded-xl bg-slate-900 p-3">
          {isUserLoading ? (
            <p className="text-xs text-slate-500">Loading account...</p>
          ) : currentUser ? (
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-slate-200">
                {getInitials(currentUser.first_name, currentUser.last_name)}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-100">
                  {currentUser.first_name} {currentUser.last_name}
                </p>
                <p className="truncate text-xs text-slate-500">
                  {currentUser.email}
                </p>
              </div>
            </div>
          ) : null}

          <button
            type="button"
            onClick={() => void onLogout()}
            disabled={isLoggingOut}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs font-medium text-slate-300 transition hover:border-slate-600 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Icon name="logout" className="h-4 w-4" />
            {isLoggingOut ? "Signing out..." : "Sign out"}
          </button>

          {logoutError ? (
            <p className="mt-2 text-xs text-rose-400">
              Unable to sign out.
            </p>
          ) : null}
        </div>
      </div>
    </>
  );
}

function isActivePath(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function getInitials(firstName: string, lastName: string) {
  const first = firstName.trim().charAt(0);
  const last = lastName.trim().charAt(0);
  return `${first}${last}`.toUpperCase() || "NS";
}
