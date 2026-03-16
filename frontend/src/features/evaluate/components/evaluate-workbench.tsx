"use client";

import { useMutation } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

import { DevConsoleShell } from "@/components/dev-console-shell";
import { DevPageHeader } from "@/components/dev-page-header";
import { EvaluationEnvelopeView } from "@/components/evaluation-envelope-view";
import { postEvaluate } from "@/lib/api/evaluate";
import type { EvaluateRequest, EvaluateResponse } from "@/lib/contracts/evaluate";
import { createEnvelopeFromEvaluate } from "@/lib/adapters/evaluation-envelope";
import { evaluateGoodEnvelopeMock, evaluateRiskEnvelopeMock } from "@/lib/mocks/evaluation-envelope";
import { useDevMode } from "@/lib/use-dev-mode";

const DEFAULT_TIER = "BETTER";
const MOCK_OPTIONS = {
  evaluate_good: evaluateGoodEnvelopeMock,
  evaluate_risk: evaluateRiskEnvelopeMock,
} as const;

export function EvaluateWorkbench() {
  const [input, setInput] = useState("");
  const [tier, setTier] = useState(DEFAULT_TIER);
  const [mockFixture, setMockFixture] = useState<keyof typeof MOCK_OPTIONS>("evaluate_good");
  const mode = useDevMode();

  const evaluateMutation = useMutation({
    mutationFn: postEvaluate,
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    evaluateMutation.mutate({
      input,
      tier,
    });
  }

  const result = evaluateMutation.data;
  const request: EvaluateRequest | null = result ? { input, tier } : null;
  const liveEnvelope = result && request ? createEnvelopeFromEvaluate(request, result) : null;
  const envelope = mode === "mock" ? MOCK_OPTIONS[mockFixture] : liveEnvelope;

  return (
    <DevConsoleShell
      title="Evaluate contract terminal"
      subtitle="Run the frozen Evaluate contract and inspect the normalized envelope without reopening backend boundaries."
    >
      <DevPageHeader
        stage="Stage 1"
        title="Evaluate-first workbench"
        description="This screen exists to verify the Evaluate contract, the normalization adapter, and the Builder handoff path."
        facts={[
          { label: "Route", value: <code>/evaluate</code> },
          { label: "Contract", value: <code>POST /app/evaluate</code> },
          { label: "Output", value: <code>evaluationId + builderHandoff</code> },
        ]}
      />

      <section className="panel-grid">
        <form className="panel" onSubmit={handleSubmit}>
          <div className="panel-header">
            <h2>Evaluate text input</h2>
            <span>Contract: POST /app/evaluate</span>
          </div>

          {mode === "mock" ? (
            <>
              <p className="status">Mock mode is active. This screen is rendering fixture-driven Evaluate envelopes.</p>
              <label className="field">
                <span>Mock fixture</span>
                <select value={mockFixture} onChange={(event) => setMockFixture(event.target.value as keyof typeof MOCK_OPTIONS)}>
                  <option value="evaluate_good">evaluate good</option>
                  <option value="evaluate_risk">evaluate risk</option>
                </select>
              </label>
            </>
          ) : null}

          <label className="field">
            <span>Slip text</span>
            <textarea
              name="input"
              rows={10}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Paste a parlay or ticket text here"
              required
            />
          </label>

          <label className="field">
            <span>Tier</span>
            <select value={tier} onChange={(event) => setTier(event.target.value)}>
              <option value="GOOD">GOOD</option>
              <option value="BETTER">BETTER</option>
              <option value="BEST">BEST</option>
            </select>
          </label>

          <div className="actions">
            <button type="submit" disabled={evaluateMutation.isPending || mode === "mock"}>
              {evaluateMutation.isPending ? "Evaluating..." : "Evaluate"}
            </button>
          </div>

          {evaluateMutation.isError ? (
            <p className="status error">
              {(evaluateMutation.error as Error).message || "Request failed"}
            </p>
          ) : null}
        </form>

        <EvaluateResultPanel result={mode === "mock" ? undefined : result} envelope={envelope} />
      </section>
    </DevConsoleShell>
  );
}

function EvaluateResultPanel({
  result,
  envelope,
}: {
  result: EvaluateResponse | undefined;
  envelope: ReturnType<typeof createEnvelopeFromEvaluate> | null;
}) {
  return (
    <section className="panel result-panel">
      <div className="panel-header">
        <h2>EvaluationEnvelope view</h2>
        <span>Adapter-backed UI contract</span>
      </div>

      {result ? (
        <>
          <dl className="summary-grid">
            <div>
              <dt>evaluationId</dt>
              <dd>{result.evaluationId || "missing"}</dd>
            </div>
            <div>
              <dt>Tier</dt>
              <dd>{result.builderHandoff?.tier || String(result.input?.tier || "unknown")}</dd>
            </div>
            <div>
              <dt>Builder handoff</dt>
              <dd>{result.builderHandoff ? "ready" : "missing"}</dd>
            </div>
            <div>
              <dt>Protocols</dt>
              <dd>{result.triggeredProtocols.length}</dd>
            </div>
          </dl>

          <div className="result-block">
            <h3>5-zone envelope</h3>
            <EvaluationEnvelopeView
              envelope={envelope}
              emptyMessage="Run an evaluation to inspect the normalized envelope."
            />
          </div>
        </>
      ) : (
        <EvaluationEnvelopeView
          envelope={envelope}
          emptyMessage={envelope ? "Mock Evaluate envelope loaded." : "Run an evaluation to inspect the normalized envelope."}
        />
      )}
    </section>
  );
}
