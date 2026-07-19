"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";

const PREVIEW_LINKS = [
  { href: "/preview/dashboard", label: "Dashboard" },
  { href: "/preview/pipeline", label: "Pipeline" },
  { href: "/preview/campaigns", label: "Campaigns" },
  { href: "/preview/data-room", label: "Data Room" },
  { href: "/preview/reports", label: "Reports" },
  { href: "/preview/funding", label: "Funding" },
];

const CLIENT_LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/pipeline", label: "Pipeline" },
  { href: "/targets", label: "Targets" },
  { href: "/campaigns", label: "Campaigns" },
  { href: "/data-room", label: "Data Room" },
  { href: "/funding", label: "Funding" },
  { href: "/reports", label: "Reports" },
];

const SUPPORT_LINKS = [
  { href: "/overview", label: "Overview" },
  { href: "/alerts", label: "Alerts" },
];

export function Nav({
  variant = "preview", right,
}: {
  variant?: "preview" | "client" | "support";
  right?: React.ReactNode;
}) {
  const pathname = usePathname();
  const LINKS = variant === "client" ? CLIENT_LINKS : variant === "support" ? SUPPORT_LINKS : PREVIEW_LINKS;

  return (
    <nav className="flex items-center gap-1 border-b border-slate-800 bg-slate-950 px-6 py-3">
      <span className="mr-6 text-sm font-semibold text-slate-100">Capital Context</span>
      {LINKS.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={clsx(
            "rounded-lg px-3 py-1.5 text-sm transition",
            pathname === link.href
              ? "bg-slate-800 text-slate-100"
              : "text-slate-300 hover:bg-slate-900 hover:text-slate-200",
          )}
        >
          {link.label}
        </Link>
      ))}
      <div className="ml-auto">{right}</div>
    </nav>
  );
}
