"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { Icon } from "@/components/ui/icon";
import { useLogin } from "@/features/auth/hooks";
import {
  loginSchema,
  type LoginFormValues,
} from "@/features/auth/schemas";

type LoginFormProps = {
  showRegistrationSuccess?: boolean;
};

export function LoginForm({
  showRegistrationSuccess = false,
}: LoginFormProps) {
  const router = useRouter();
  const loginMutation = useLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginFormValues) {
    await loginMutation.mutateAsync(values);
    router.push("/dashboard");
    router.refresh();
  }

  return (
    <main className="grid min-h-screen bg-white lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden bg-slate-950 px-12 py-14 text-white lg:flex lg:flex-col lg:justify-between xl:px-16">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute bottom-24 left-16 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl" />

        <div className="relative">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-500 text-slate-950">
              <Icon name="shipments" className="h-5 w-5" />
            </div>
            <div>
              <p className="text-lg font-semibold tracking-tight">NovaScale</p>
              <p className="text-xs text-slate-400">Shipping & logistics operations</p>
            </div>
          </div>
        </div>

        <div className="relative max-w-xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">
            Operations, connected
          </p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight xl:text-5xl">
            Run shipping operations from one command center.
          </h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-slate-400">
            Manage shipments, customers, billing, operational intelligence, and safe AI-assisted actions with tenant-aware controls.
          </p>

          <div className="mt-10 grid gap-3 sm:grid-cols-2">
            {[
              "Tenant-isolated operations",
              "Shipment intelligence",
              "Controlled AI actions",
              "Billing workflows",
            ].map((item) => (
              <div key={item} className="flex items-center gap-3 text-sm text-slate-300">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-300">
                  <Icon name="check" className="h-3.5 w-3.5" />
                </span>
                {item}
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-slate-600">
          NovaScale operational platform
        </p>
      </section>

      <section className="flex min-h-screen items-center justify-center bg-slate-50 px-5 py-10 sm:px-8">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-cyan-300">
              <Icon name="shipments" className="h-5 w-5" />
            </div>
            <div>
              <p className="font-semibold text-slate-950">NovaScale</p>
              <p className="text-xs text-slate-500">Logistics command center</p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] sm:p-8">
            <div className="mb-7">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-700">
                Secure workspace access
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                Welcome back
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Sign in to continue to your NovaScale workspace.
              </p>
            </div>

            {showRegistrationSuccess ? (
              <div className="mb-5 flex gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-3 text-sm text-emerald-800">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                  <Icon name="check" className="h-3.5 w-3.5" />
                </span>
                <div>
                  <p className="font-medium">Workspace created successfully.</p>
                  <p className="mt-0.5 text-emerald-700">
                    Sign in with the account you just created.
                  </p>
                </div>
              </div>
            ) : null}

            <form className="space-y-5" onSubmit={handleSubmit(onSubmit)}>
              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-700">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@company.com"
                  {...register("email")}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-950 outline-none placeholder:text-slate-400"
                />
                {errors.email ? (
                  <p className="mt-2 text-sm text-rose-600">{errors.email.message}</p>
                ) : null}
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-medium text-slate-700">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  {...register("password")}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-950 outline-none"
                />
                {errors.password ? (
                  <p className="mt-2 text-sm text-rose-600">{errors.password.message}</p>
                ) : null}
              </div>

              {loginMutation.isError ? (
                <div className="flex gap-3 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-3 text-sm text-rose-700">
                  <Icon name="warning" className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>
                    {loginMutation.error instanceof Error
                      ? loginMutation.error.message
                      : "Unable to sign in"}
                  </p>
                </div>
              ) : null}

              <button
                type="submit"
                disabled={loginMutation.isPending}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loginMutation.isPending ? "Signing in..." : "Sign in"}
                {!loginMutation.isPending ? (
                  <Icon name="arrow-right" className="h-4 w-4" />
                ) : null}
              </button>
            </form>

            <div className="mt-6 border-t border-slate-100 pt-5 text-center">
              <p className="text-sm text-slate-500">
                New to NovaScale?{" "}
                <Link
                  href="/signup"
                  className="font-semibold text-cyan-700 transition hover:text-cyan-800"
                >
                  Create your workspace
                </Link>
              </p>
            </div>
          </div>

          <p className="mt-5 text-center text-xs leading-5 text-slate-400">
            Access is scoped to your authorized tenants and roles.
          </p>
        </div>
      </section>
    </main>
  );
}
