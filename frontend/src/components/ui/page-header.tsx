import type { ReactNode } from "react";

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: PageHeaderProps) {
  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-3xl">
        {eyebrow ? (
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-cyan-700">
            {eyebrow}
          </p>
        ) : null}

        <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
          {title}
        </h1>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          {description}
        </p>
      </div>

      {actions ? (
        <div className="flex shrink-0 items-center gap-2">
          {actions}
        </div>
      ) : null}
    </div>
  );
}
