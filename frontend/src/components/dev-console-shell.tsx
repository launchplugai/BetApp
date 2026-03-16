"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { useDevSession } from "@/lib/use-dev-mode";

type RouteStateSummary = {
  label: string;
  status: "idle" | "mock" | "pending" | "success" | "error";
};

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function DevConsoleShell({
  title,
  subtitle,
  routeState,
  children,
}: {
  title: string;
  subtitle: string;
  routeState?: RouteStateSummary;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const session = useDevSession();

  const navItems = [
    { href: "/", label: "Console" },
    { href: "/evaluate", label: "Evaluate" },
    { href: "/evaluate/review", label: "OCR Review" },
    { href: "/builder", label: "Builder" },
    { href: "/history", label: "History" },
  ];

  return (
    <main className="page-shell">
      <section className="console-shell-card">
        <div className="console-shell-top">
          <div>
            <p className="eyebrow">BetApp developer console</p>
            <h1>{title}</h1>
            <p className="lede">{subtitle}</p>
          </div>

          <dl className="console-status-grid">
            <div>
              <dt>Mode</dt>
              <dd>{session.mode}</dd>
            </div>
            <div>
              <dt>API base</dt>
              <dd>{session.apiBase}</dd>
            </div>
            <div>
              <dt>Route state</dt>
              <dd>
                {routeState ? (
                  <span className={`trace-pill trace-${routeState.status}`}>{routeState.label}</span>
                ) : (
                  "not set"
                )}
              </dd>
            </div>
            <div>
              <dt>Path</dt>
              <dd>{pathname}</dd>
            </div>
          </dl>
        </div>

        <nav className="console-nav" aria-label="Developer console">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`console-nav-link${isActive(pathname, item.href) ? " active" : ""}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <section className="scope-banner" aria-label="Scope distinction">
          <div>
            <p className="eyebrow">Current lane</p>
            <h2>Project dev surface</h2>
          </div>
          <p className="scope-copy">
            This console is for BetApp product work only. Chat-side workflow, heartbeat tuning, and repo-memory process work stay outside the app surface.
          </p>
        </section>
      </section>

      {children}
    </main>
  );
}
