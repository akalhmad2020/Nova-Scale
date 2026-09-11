"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { useForm, useWatch } from "react-hook-form";

import { Icon } from "@/components/ui/icon";
import { useRegisterCompany } from "@/features/auth/hooks";
import {
  registerSchema,
  type RegisterFormValues,
} from "@/features/auth/schemas";
import type { RegisterCompanyInput } from "@/features/auth/types";

const inputClassName =
  "w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-cyan-500 focus:ring-4 focus:ring-cyan-500/10 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500";

function toWorkspaceSlug(value: string): string {
  return value
    .normalize("NFKC")
    .trim()
    .toLocaleLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);
}

export function SignupForm() {
  const router = useRouter();
  const registerMutation = useRegisterCompany();
  const [slugWasEdited, setSlugWasEdited] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      email: "",
      company_name: "",
      company_slug: "",
      password: "",
      confirm_password: "",
    },
  });

  const companyName = useWatch({
    control,
    name: "company_name",
    defaultValue: "",
  });

  useEffect(() => {
    if (slugWasEdited) {
      return;
    }

    setValue("company_slug", toWorkspaceSlug(companyName), {
      shouldValidate: false,
      shouldDirty: Boolean(companyName),
    });
  }, [companyName, setValue, slugWasEdited]);

  async function onSubmit(values: RegisterFormValues) {
    const input: RegisterCompanyInput = {
      email: values.email,
      password: values.password,
      first_name: values.first_name,
      last_name: values.last_name,
      company_name: values.company_name,
      company_slug: values.company_slug,
    };

    await registerMutation.mutateAsync(input);

    router.push("/login?registered=1");
    router.refresh();
  }

  const companySlugRegistration = register("company_slug");

  return (
    <main className="grid min-h-screen bg-white lg:grid-cols-[0.9fr_1.1fr]">
      <section className="relative hidden overflow-hidden bg-slate-950 px-12 py-14 text-white lg:flex lg:flex-col lg:justify-between xl:px-16">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute bottom-24 left-16 h-64 w-64 rounded-full bg-blue-500/10 blur-3xl" />

        <div className="relative">
          <Link href="/login" className="inline-flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-500 text-slate-950">
              <Icon name="shipments" className="h-5 w-5" />
            </div>

            <div>
              <p className="text-lg font-semibold tracking-tight">
                NovaScale
              </p>
              <p className="text-xs text-slate-400">
                Shipping & logistics operations
              </p>
            </div>
          </Link>
        </div>

        <div className="relative max-w-xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-cyan-300">
            Build your operations workspace
          </p>

          <h1 className="mt-4 text-4xl font-semibold leading-tight tracking-tight xl:text-5xl">
            Start with a tenant-isolated logistics command center.
          </h1>

          <p className="mt-5 max-w-lg text-base leading-7 text-slate-400">
            Create your company workspace and owner account together.
            NovaScale keeps operational data, permissions, billing, and AI
            actions scoped to the right tenant from day one.
          </p>

          <div className="mt-10 space-y-4">
            {[
              {
                title: "Company workspace",
                description:
                  "A dedicated tenant for your logistics operations.",
              },
              {
                title: "Owner access",
                description:
                  "Your first account receives the workspace owner role.",
              },
              {
                title: "Operational foundation",
                description:
                  "Ledger and authorization foundations are created with the workspace.",
              },
            ].map((item) => (
              <div key={item.title} className="flex gap-3">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-300">
                  <Icon name="check" className="h-4 w-4" />
                </span>

                <div>
                  <p className="text-sm font-medium text-slate-200">
                    {item.title}
                  </p>
                  <p className="mt-0.5 text-sm leading-6 text-slate-500">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <p className="relative text-xs text-slate-600">
          NovaScale operational platform
        </p>
      </section>

      <section className="flex min-h-screen items-center justify-center bg-slate-50 px-5 py-10 sm:px-8 lg:py-12">
        <div className="w-full max-w-2xl">
          <div className="mb-8 flex items-center justify-between gap-4 lg:hidden">
            <Link href="/login" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-950 text-cyan-300">
                <Icon name="shipments" className="h-5 w-5" />
              </div>

              <div>
                <p className="font-semibold text-slate-950">
                  NovaScale
                </p>
                <p className="text-xs text-slate-500">
                  Logistics command center
                </p>
              </div>
            </Link>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] sm:p-8">
            <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-cyan-700">
                  New workspace
                </p>

                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950">
                  Create your NovaScale account
                </h2>

                <p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">
                  Set up the company workspace and the owner account used to
                  manage it.
                </p>
              </div>

              <Link
                href="/login"
                className="inline-flex shrink-0 items-center gap-2 text-sm font-semibold text-slate-600 transition hover:text-slate-950"
              >
                Sign in
                <Icon name="arrow-right" className="h-4 w-4" />
              </Link>
            </div>

            <form
              className="space-y-6"
              onSubmit={handleSubmit(onSubmit)}
            >
              <fieldset
                disabled={registerMutation.isPending}
                className="space-y-6"
              >
                <div>
                  <p className="mb-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                    Account owner
                  </p>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field
                      label="First name"
                      error={errors.first_name?.message}
                    >
                      <input
                        type="text"
                        autoComplete="given-name"
                        {...register("first_name")}
                        className={inputClassName}
                      />
                    </Field>

                    <Field
                      label="Last name"
                      error={errors.last_name?.message}
                    >
                      <input
                        type="text"
                        autoComplete="family-name"
                        {...register("last_name")}
                        className={inputClassName}
                      />
                    </Field>
                  </div>

                  <div className="mt-4">
                    <Field
                      label="Work email"
                      error={errors.email?.message}
                    >
                      <input
                        type="email"
                        autoComplete="email"
                        placeholder="you@company.com"
                        {...register("email")}
                        className={inputClassName}
                      />
                    </Field>
                  </div>
                </div>

                <div className="border-t border-slate-100 pt-6">
                  <p className="mb-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                    Company workspace
                  </p>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field
                      label="Company name"
                      error={errors.company_name?.message}
                    >
                      <input
                        type="text"
                        autoComplete="organization"
                        placeholder="Acme Logistics"
                        {...register("company_name")}
                        className={inputClassName}
                      />
                    </Field>

                    <Field
                      label="Workspace identifier"
                      error={errors.company_slug?.message}
                      hint="Generated from the company name. You can edit it."
                    >
                      <input
                        type="text"
                        autoCapitalize="none"
                        spellCheck={false}
                        placeholder="acme-logistics"
                        {...companySlugRegistration}
                        onChange={(event) => {
                          setSlugWasEdited(true);
                          companySlugRegistration.onChange(event);
                        }}
                        className={`${inputClassName} font-mono text-[13px]`}
                      />
                    </Field>
                  </div>
                </div>

                <div className="border-t border-slate-100 pt-6">
                  <p className="mb-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                    Security
                  </p>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field
                      label="Password"
                      error={errors.password?.message}
                      hint="Use at least 12 characters."
                    >
                      <input
                        type="password"
                        autoComplete="new-password"
                        {...register("password")}
                        className={inputClassName}
                      />
                    </Field>

                    <Field
                      label="Confirm password"
                      error={errors.confirm_password?.message}
                    >
                      <input
                        type="password"
                        autoComplete="new-password"
                        {...register("confirm_password")}
                        className={inputClassName}
                      />
                    </Field>
                  </div>
                </div>
              </fieldset>

              {registerMutation.isError ? (
                <div className="flex gap-3 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-3 text-sm text-rose-700">
                  <Icon
                    name="warning"
                    className="mt-0.5 h-4 w-4 shrink-0"
                  />

                  <div>
                    <p className="font-medium">
                      Workspace could not be created.
                    </p>

                    <p className="mt-0.5">
                      {registerMutation.error instanceof Error
                        ? registerMutation.error.message
                        : "Please review your details and try again."}
                    </p>
                  </div>
                </div>
              ) : null}

              <button
                type="submit"
                disabled={registerMutation.isPending}
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {registerMutation.isPending
                  ? "Creating workspace..."
                  : "Create workspace"}

                {!registerMutation.isPending ? (
                  <Icon
                    name="arrow-right"
                    className="h-4 w-4"
                  />
                ) : null}
              </button>
            </form>

            <p className="mt-5 text-center text-xs leading-5 text-slate-400">
              Already have access?{" "}
              <Link
                href="/login"
                className="font-semibold text-slate-600 transition hover:text-slate-950"
              >
                Sign in to your workspace
              </Link>
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

type FieldProps = {
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
};

function Field({
  label,
  error,
  hint,
  children,
}: FieldProps) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">
        {label}
      </span>

      {children}

      {error ? (
        <span className="mt-2 block text-sm text-rose-600">
          {error}
        </span>
      ) : hint ? (
        <span className="mt-2 block text-xs leading-5 text-slate-400">
          {hint}
        </span>
      ) : null}
    </label>
  );
}