import type { SVGProps } from "react";

export type IconName =
  | "dashboard"
  | "shipments"
  | "customers"
  | "locations"
  | "billing"
  | "ai"
  | "menu"
  | "close"
  | "arrow-right"
  | "check"
  | "warning"
  | "activity"
  | "building"
  | "sparkles"
  | "logout"
  | "plus"
  | "chevron-down";

type IconProps = SVGProps<SVGSVGElement> & {
  name: IconName;
};

export function Icon({
  name,
  className = "h-5 w-5",
  ...props
}: IconProps) {
  const common = {
    className,
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    viewBox: "0 0 24 24",
    "aria-hidden": true,
    ...props,
  } as const;

  switch (name) {
    case "dashboard":
      return (
        <svg {...common}>
          <path d="M4 4h6v6H4zM14 4h6v4h-6zM14 12h6v8h-6zM4 14h6v6H4z" />
        </svg>
      );
    case "shipments":
      return (
        <svg {...common}>
          <path d="M3.5 7.5 12 3l8.5 4.5L12 12z" />
          <path d="M3.5 7.5V16L12 21l8.5-5V7.5M12 12v9" />
        </svg>
      );
    case "customers":
      return (
        <svg {...common}>
          <path d="M16 20v-1.5A4.5 4.5 0 0 0 11.5 14h-3A4.5 4.5 0 0 0 4 18.5V20" />
          <circle cx="10" cy="7" r="3" />
          <path d="M17 11a3 3 0 0 0 0-6M19.5 20v-1.5a4.5 4.5 0 0 0-2.6-4.08" />
        </svg>
      );
    case "locations":
      return (
        <svg {...common}>
          <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z" />
          <circle cx="12" cy="10" r="2.5" />
        </svg>
      );
    case "billing":
      return (
        <svg {...common}>
          <path d="M6 3h12v18l-3-2-3 2-3-2-3 2z" />
          <path d="M9 8h6M9 12h6M9 16h3" />
        </svg>
      );
    case "ai":
      return (
        <svg {...common}>
          <path d="m12 3 1.4 4.1L17.5 8.5l-4.1 1.4L12 14l-1.4-4.1-4.1-1.4 4.1-1.4z" />
          <path d="m18 13 .8 2.2L21 16l-2.2.8L18 19l-.8-2.2L15 16l2.2-.8z" />
        </svg>
      );
    case "menu":
      return (
        <svg {...common}>
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      );
    case "close":
      return (
        <svg {...common}>
          <path d="m6 6 12 12M18 6 6 18" />
        </svg>
      );
    case "arrow-right":
      return (
        <svg {...common}>
          <path d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      );
    case "check":
      return (
        <svg {...common}>
          <path d="m5 12 4 4L19 6" />
        </svg>
      );
    case "warning":
      return (
        <svg {...common}>
          <path d="M12 4 3.5 19h17z" />
          <path d="M12 9v4M12 16h.01" />
        </svg>
      );
    case "activity":
      return (
        <svg {...common}>
          <path d="M3 12h4l2.2-5 4.2 10 2.1-5H21" />
        </svg>
      );
    case "building":
      return (
        <svg {...common}>
          <path d="M4 21V5l8-3 8 3v16M8 8h2M14 8h2M8 12h2M14 12h2M8 16h2M14 16h2" />
        </svg>
      );
    case "sparkles":
      return (
        <svg {...common}>
          <path d="m9 3 1.1 3.4L13.5 7.5l-3.4 1.1L9 12l-1.1-3.4-3.4-1.1 3.4-1.1zM17 12l.8 2.2L20 15l-2.2.8L17 18l-.8-2.2L14 15l2.2-.8z" />
        </svg>
      );
    case "logout":
      return (
        <svg {...common}>
          <path d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10" />
        </svg>
      );
    case "plus":
      return (
        <svg {...common}>
          <path d="M12 5v14M5 12h14" />
        </svg>
      );
    case "chevron-down":
      return (
        <svg {...common}>
          <path d="m7 10 5 5 5-5" />
        </svg>
      );
  }
}
