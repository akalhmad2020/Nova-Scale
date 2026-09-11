import type { ReactNode } from "react";

type SurfaceProps = {
  children: ReactNode;
  className?: string;
};

export function Surface({
  children,
  className = "",
}: SurfaceProps) {
  return (
    <section
      className={`rounded-2xl border border-slate-200/80 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${className}`}
    >
      {children}
    </section>
  );
}

type SurfaceHeaderProps = {
  title: string;
  description?: string;
  meta?: ReactNode;
};

export function SurfaceHeader({
  title,
  description,
  meta,
}: SurfaceHeaderProps) {
  return (
    <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
      <div>
        <h2 className="text-sm font-semibold text-slate-950">
          {title}
        </h2>
        {description ? (
          <p className="mt-1 text-sm text-slate-500">
            {description}
          </p>
        ) : null}
      </div>
      {meta ? (
        <div className="shrink-0 text-sm text-slate-500">
          {meta}
        </div>
      ) : null}
    </div>
  );
}
