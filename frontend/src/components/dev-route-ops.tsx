"use client";

import type { ReactNode } from "react";

import type { DevMode } from "@/lib/dev-session";

export type RequestTraceStatus = "idle" | "mock" | "pending" | "success" | "error";

export type RequestTrace = {
  label: string;
  status: RequestTraceStatus;
  detail: string;
  endpoint: string;
  method?: string;
  lastEvent?: string;
};

export function DevRouteOps({
  routeLabel,
  contractLabel,
  mode,
  onModeChange,
  trace,
  children,
}: {
  routeLabel: ReactNode;
  contractLabel: ReactNode;
  mode: DevMode;
  onModeChange: (mode: DevMode) => void;
  trace: RequestTrace;
  children?: ReactNode;
}) {
  return (
    <section className="panel route-ops-panel">
      <div className="panel-header">
        <h2>Route controls</h2>
        <span>Shared operator surface</span>
      </div>

      <dl className="summary-grid compact-summary-grid">
        <div>
          <dt>Route</dt>
          <dd>{routeLabel}</dd>
        </div>
        <div>
          <dt>Contract</dt>
          <dd>{contractLabel}</dd>
        </div>
      </dl>

      <label className="field">
        <span>Route mode</span>
        <select value={mode} onChange={(event) => onModeChange(event.target.value as DevMode)}>
          <option value="live">live backend</option>
          <option value="mock">mock envelope preview</option>
        </select>
      </label>

      {children}

      <div className="trace-card">
        <div className="trace-card-top">
          <div>
            <p className="eyebrow">Request trace</p>
            <h3>{trace.label}</h3>
          </div>
          <span className={`trace-pill trace-${trace.status}`}>{trace.status}</span>
        </div>

        <dl className="trace-grid">
          <div>
            <dt>Endpoint</dt>
            <dd>
              {trace.method ? `${trace.method} ` : ""}
              {trace.endpoint}
            </dd>
          </div>
          <div>
            <dt>Last event</dt>
            <dd>{trace.lastEvent || "No activity yet."}</dd>
          </div>
        </dl>

        <p className="status trace-detail">{trace.detail}</p>
      </div>
    </section>
  );
}
