"use client";
import Link from "next/link";
import {
  ArrowUpRight,
  Graph,
  Stack,
  ArrowLeft,
  Flask,
} from "@phosphor-icons/react";
export function Shell({
  children,
  caseView = false,
}: {
  children: React.ReactNode;
  caseView?: boolean;
}) {
  return (
    <div className="app-shell">
      <aside className="rail">
        <Link href="/" className="brand-icon" aria-label="Corridor home">
          <Graph size={26} weight="bold" />
        </Link>
        <Link href="/" className="rail-item active" aria-label="Review queue">
          <Stack size={23} />
        </Link>
        <span className="rail-bottom" title="Synthetic demonstration">
          <Flask size={21} />
        </span>
      </aside>
      <div className="app-main">
        <header className="topbar">
          <Link href="/" className="wordmark">
            corridor<span className="brand-dot">.</span>
          </Link>
          <span className="top-divider" />
          <span className="top-context">Investigation workspace</span>
          <span className="synthetic">
            <Flask size={14} /> Synthetic data
          </span>
          <a
            className="docs-link"
            href="/api-docs"
            target="_blank"
            rel="noreferrer"
          >
            API docs <ArrowUpRight size={14} />
          </a>
        </header>
        {caseView && (
          <Link href="/" className="back-link">
            <ArrowLeft size={15} /> Review queue
          </Link>
        )}
        {children}
      </div>
    </div>
  );
}
export function Badge({ value }: { value?: string | null }) {
  const v = value ?? "OPEN";
  return <span className={"badge " + v.toLowerCase()}>{v}</span>;
}
