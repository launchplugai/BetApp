"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { getStoredApiBaseUrl, getStoredDevMode } from "@/lib/dev-session";

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function DevConsoleShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
}) {
  const pathname = usePathname();
  const apiBase = typeof window === "undefined" ? "http://localhost:8000" : getStoredApiBaseUrl();
  const mode = typeof window === "undefined" ? "live" : getStoredDevMode();

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
              <dd>{mode}</dd>
            </div>
            <div>
              <dt>API base</dt>
              <dd>{apiBase}</dd>
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
      </section>

      {children}
    </main>
  );
}
