"use client";

import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { DevConsoleShell } from "@/components/dev-console-shell";
import { DevPageHeader } from "@/components/dev-page-header";
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
  const [handoff, setHandoff] = useState<BuilderHandoff | null>(null);
  const [status, setStatus] = useState("No Builder handoff saved yet.");
  const mode = useDevMode();

  useEffect(() => {
    if (mode === "mock") {
      const mockHandoff = evaluateRiskEnvelopeMock.zones.actionRail.builderHandoff as BuilderHandoff | null;
      if (mockHandoff) {
        setHandoff(mockHandoff);
        setStatus("Mock Builder handoff loaded.");
      }
      return;
    }
    const saved = readHandoff();
    if (saved) {
      setHandoff(saved);
      setStatus("Builder handoff loaded.");
    }
  }, [mode]);

  const reEvaluateMutation = useMutation({
    mutationFn: async () => {
      if (!handoff?.inputText) {
        throw new Error("No Builder handoff available to re-evaluate.");
      }
      return postEvaluate({
        input: handoff.inputText,
        tier: handoff.tier,
      });
    },
    onSuccess: () => setStatus("Re-evaluation complete."),
    onError: (error) => setStatus(error instanceof Error ? error.message : "Unexpected error"),
  });

  const handoffEnvelope = handoff ? createEnvelopeFromBuilderHandoff(handoff) : null;
  const reEvaluatedEnvelope =
    handoff && reEvaluateMutation.data
      ? createEnvelopeFromEvaluate(
          {
            input: handoff.inputText,
            tier: handoff.tier,
          },
          reEvaluateMutation.data,
        )
      : null;

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
        <section className="panel">
          <div className="panel-header">
            <h2>Current handoff</h2>
            <span>Frozen frontend state</span>
          </div>

          <p className="status">{status}</p>

          <dl className="summary-grid">
            <div>
              <dt>evaluationId</dt>
              <dd>{handoff?.evaluationId || "missing"}</dd>
            </div>
            <div>
              <dt>Tier</dt>
              <dd>{handoff?.tier || "unknown"}</dd>
            </div>
            <div>
              <dt>Primary failure</dt>
              <dd>{describeBlock((handoff?.primaryFailure as Record<string, unknown> | null) ?? null)}</dd>
            </div>
            <div>
              <dt>Fastest fix</dt>
              <dd>{describeBlock((handoff?.fastestFix as Record<string, unknown> | null) ?? null)}</dd>
            </div>
          </dl>

          <div className="result-block">
            <h3>Input text</h3>
            <pre>{handoff?.inputText || ""}</pre>
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
