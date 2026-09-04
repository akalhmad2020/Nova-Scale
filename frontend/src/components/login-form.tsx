"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { useLogin } from "@/features/auth/hooks";
import {
  loginSchema,
  type LoginFormValues,
} from "@/features/auth/schemas";

export function LoginForm() {
  const router = useRouter();
  const loginMutation = useLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  async function onSubmit(values: LoginFormValues) {
    await loginMutation.mutateAsync(values);
    router.push("/dashboard");
    router.refresh();
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-50 px-6">
      <section className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-8 shadow-sm">
        <div className="mb-8">
          <p className="text-sm font-medium uppercase tracking-wider text-zinc-500">
            NovaScale
          </p>

          <h1 className="mt-2 text-3xl font-semibold text-zinc-950">
            Sign in
          </h1>

          <p className="mt-2 text-sm text-zinc-600">
            Sign in to your NovaScale account.
          </p>
        </div>

        <form
          className="space-y-5"
          onSubmit={handleSubmit(onSubmit)}
        >
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-zinc-900"
            >
              Email
            </label>

            <input
              id="email"
              type="email"
              autoComplete="email"
              {...register("email")}
              className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none transition focus:border-zinc-950"
            />

            {errors.email && (
              <p className="mt-2 text-sm text-red-600">
                {errors.email.message}
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="password"
              className="mb-2 block text-sm font-medium text-zinc-900"
            >
              Password
            </label>

            <input
              id="password"
              type="password"
              autoComplete="current-password"
              {...register("password")}
              className="w-full rounded-lg border border-zinc-300 px-3 py-2.5 text-zinc-950 outline-none transition focus:border-zinc-950"
            />

            {errors.password && (
              <p className="mt-2 text-sm text-red-600">
                {errors.password.message}
              </p>
            )}
          </div>

          {loginMutation.isError && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {loginMutation.error instanceof Error
                ? loginMutation.error.message
                : "Unable to sign in"}
            </p>
          )}

          <button
            type="submit"
            disabled={loginMutation.isPending}
            className="flex w-full items-center justify-center rounded-lg bg-zinc-950 px-4 py-2.5 font-medium text-white transition hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loginMutation.isPending
              ? "Signing in..."
              : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}