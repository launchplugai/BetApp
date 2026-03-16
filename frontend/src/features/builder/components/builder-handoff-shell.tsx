"use client";

import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { DevConsoleShell } from "@/components/dev-console-shell";
import { DevPageHeader } from "@/components/dev-page-header";
import { DevRouteOps } from "@/components/dev-route-ops";
import { EvaluationEnvelopeView } from "@/components/evaluation-envelope-view";
import { postEvaluate } from "@/lib/api/evaluate";
import type { BuilderHandoff } from "@/lib/contracts/evaluate";
import {
  createEnvelopeFromBuilderHandoff,
  createEnvelopeFromEvaluate,
} from "@/lib/adapters/evaluation-envelope";
import { evaluateRiskEnvelopeMock } from "@/lib/mocks/evaluation-envelope";
import { useDevMode } from "@/lib/use-dev-mode";

const STORAGE_KEY = "betapp.builderHandoff";
const API_BASE_KEY = "betapp.apiBase";

function readHandoff(): BuilderHandoff | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as BuilderHandoff) : null;
  } catch {
    return null;
  }
}

function describeBlock(block: Record<string, unknown> | null | undefined): string {
  if (!block) return "missing";
  const candidates = ["label", "title", "reason", "summary", "action"] as const;
  for (const key of candidates) {
    const value = block[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return "present";
}

export function BuilderHandoffShell() {
  const [handoff, setHandoff] = useState<BuilderHandoff | null>(() => readHandoff());
  const [status, setStatus] = useState(() => (readHandoff() ? "Builder handoff loaded." : "No Builder handoff saved yet."));
  const { mode, setMode } = useDevMode();
  const activeHandoff = useMemo(() => {
    if (mode === "mock") {
      return (evaluateRiskEnvelopeMock.zones.actionRail.builderHandoff as BuilderHandoff | null) ?? null;
    }
    return handoff;
  }, [handoff, mode]);
  const displayStatus = mode === "mock" ? "Mock Builder handoff loaded." : status;

  const reEvaluateMutation = useMutation({
    mutationFn: async () => {
      if (!activeHandoff?.inputText) {
        throw new Error("No Builder handoff available to re-evaluate.");
      }
      return postEvaluate({
        input: activeHandoff.inputText,
        tier: activeHandoff.tier,
      });
    },
    onSuccess: () => setStatus("Re-evaluation complete."),
    onError: (error) => setStatus(error instanceof Error ? error.message : "Unexpected error"),
  });

  const handoffEnvelope = activeHandoff ? createEnvelopeFromBuilderHandoff(activeHandoff) : null;
  const reEvaluatedEnvelope =
    activeHandoff && reEvaluateMutation.data
      ? createEnvelopeFromEvaluate(
          {
            input: activeHandoff.inputText,
            tier: activeHandoff.tier,
          },
          reEvaluateMutation.data,
        )
      : null;
  const trace =
    mode === "mock"
      ? {
          label: "Fixture-driven Builder preview",
          status: "mock" as const,
          detail: "Rendering the mock Builder handoff without a live re-evaluation.",
          endpoint: "/builder",
          method: "local",
          lastEvent: "Mock Builder handoff loaded from the envelope fixture.",
        }
      : reEvaluateMutation.isPending
        ? {
            label: "Builder re-evaluation in flight",
            status: "pending" as const,
            detail: "Re-running the saved Builder handoff through the frozen Evaluate contract.",
            endpoint: "/app/evaluate",
            method: "POST",
            lastEvent: "Waiting for Builder re-evaluation response.",
          }
        : reEvaluateMutation.isError
          ? {
              label: "Builder re-evaluation failed",
              status: "error" as const,
              detail: status,
              endpoint: "/app/evaluate",
              method: "POST",
              lastEvent: "Latest Builder re-evaluation returned an error.",
            }
          : reEvaluateMutation.data
            ? {
                label: "Builder re-evaluation ready",
                status: "success" as const,
                detail: `Saved handoff re-evaluated as ${reEvaluateMutation.data.evaluationId || "missing-id"}.`,
                endpoint: "/app/evaluate",
                method: "POST",
                lastEvent: "Latest Builder re-evaluation response normalized into an envelope.",
              }
            : {
                label: "Builder route idle",
                status: "idle" as const,
                detail: activeHandoff ? "A Builder handoff is loaded and ready for inspection or re-evaluation." : "Load a saved Builder handoff or switch to mock mode.",
                endpoint: "/builder",
                method: "local",
                lastEvent: displayStatus,
              };

  function clearHandoff() {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
      window.localStorage.removeItem(API_BASE_KEY);
    }
    setHandoff(null);
    setStatus("Builder handoff cleared.");
  }

  return (
    <DevConsoleShell
      title="Builder handoff terminal"
      subtitle="Continue from saved evaluation state instead of resetting context, and inspect the Builder envelope."
      routeState={{ status: trace.status, label: trace.label }}
    >
      <DevPageHeader
        stage="Stage 3"
        title="Builder handoff"
        description="This screen is state-first today and lets us inspect the continuation seam before we formalize a dedicated backend handoff contract."
        facts={[
          { label: "Route", value: <code>/builder</code> },
          { label: "Source", value: <code>localStorage builderHandoff</code> },
          { label: "Action", value: <code>re-evaluate saved context</code> },
        ]}
      />

      <section className="panel-grid">
        <div className="panel-stack">
        <DevRouteOps
          routeLabel={<code>/builder</code>}
          contractLabel={<code>localStorage builderHandoff + POST /app/evaluate</code>}
          mode={mode}
          onModeChange={setMode}
          trace={trace}
        />

        <section className="panel">
          <div className="panel-header">
            <h2>Current handoff</h2>
            <span>Frozen frontend state</span>
          </div>

          <p className="status">{displayStatus}</p>

          <dl className="summary-grid">
            <div>
              <dt>evaluationId</dt>
              <dd>{activeHandoff?.evaluationId || "missing"}</dd>
            </div>
            <div>
              <dt>Tier</dt>
              <dd>{activeHandoff?.tier || "unknown"}</dd>
            </div>
            <div>
              <dt>Primary failure</dt>
              <dd>{describeBlock((activeHandoff?.primaryFailure as Record<string, unknown> | null) ?? null)}</dd>
            </div>
            <div>
              <dt>Fastest fix</dt>
              <dd>{describeBlock((activeHandoff?.fastestFix as Record<string, unknown> | null) ?? null)}</dd>
            </div>
          </dl>

          <div className="result-block">
            <h3>Input text</h3>
            <pre>{activeHandoff?.inputText || ""}</pre>
          </div>

          <div className="actions">
            <button type="button" onClick={() => reEvaluateMutation.mutate()} disabled={reEvaluateMutation.isPending || mode === "mock"}>
              {reEvaluateMutation.isPending ? "Re-evaluating..." : "Re-evaluate this handoff"}
            </button>
            <button type="button" className="secondary-button" onClick={clearHandoff}>
              Clear handoff
            </button>
          </div>
        </section>
        </div>

        <section className="panel result-panel">
          <div className="panel-header">
            <h2>EvaluationEnvelope view</h2>
            <span>Builder continuation contract</span>
          </div>

          <div className="result-block">
            <h3>Saved Builder envelope</h3>
            <EvaluationEnvelopeView
              envelope={handoffEnvelope}
              emptyMessage="No Builder handoff saved yet."
            />
          </div>

          <div className="result-block">
            <h3>Latest re-evaluation envelope</h3>
            <EvaluationEnvelopeView
              envelope={reEvaluatedEnvelope}
              emptyMessage="Run a re-evaluation to inspect the normalized response."
            />
          </div>
        </section>
      </section>
    </DevConsoleShell>
  );
}
