"use client";

import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { DevConsoleShell } from "@/components/dev-console-shell";
import { DevPageHeader } from "@/components/dev-page-header";
import { EvaluationEnvelopeView } from "@/components/evaluation-envelope-view";
import {
  createEnvelopeFromEvaluationHistoryDetail,
  createEnvelopeFromPersistedBetDetail,
} from "@/lib/adapters/evaluation-envelope";
import {
  getEvaluationHistory,
  getEvaluationHistoryDetail,
  getPersistedBetDetail,
  getPersistedBetHistory,
} from "@/lib/api/history";
import { historyFallbackEnvelopeMock } from "@/lib/mocks/evaluation-envelope";
import { getStoredAuthToken, setStoredAuthToken } from "@/lib/dev-session";
import { useDevMode } from "@/lib/use-dev-mode";

const HANDOFF_STORAGE_KEY = "betapp.builderHandoff";

function prettyJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2);
}

export function HistoryShell() {
  const [token, setToken] = useState("");
  const [selectedBetId, setSelectedBetId] = useState<string | null>(null);
  const [selectedReplay, setSelectedReplay] = useState<Record<string, unknown> | null>(null);
  const [status, setStatus] = useState("No history detail loaded yet.");
  const mode = useDevMode();

  useEffect(() => {
    if (typeof window === "undefined") return;
    const savedToken = getStoredAuthToken();
    if (savedToken) setToken(savedToken);
  }, []);

  const persistedBetsMutation = useMutation({
    mutationFn: () => getPersistedBetHistory(token || undefined),
  });

  const persistedBetDetailMutation = useMutation({
    mutationFn: async (betId: string) => {
      if (!betId) throw new Error("Select a persisted bet first.");
      return getPersistedBetDetail(betId, token || undefined);
    },
    onSuccess: (data) => {
      setSelectedReplay((data.replay as Record<string, unknown> | null) ?? null);
      setStatus(data.replay ? "Persisted bet detail loaded." : "Bet detail loaded, but no replay payload was present.");
    },
    onError: (error) => setStatus(error instanceof Error ? error.message : "Unexpected error"),
  });

  const replayHistoryMutation = useMutation({
    mutationFn: getEvaluationHistory,
  });

  const replayDetailMutation = useMutation({
    mutationFn: (itemId: string) => getEvaluationHistoryDetail(itemId),
    onSuccess: (data) => {
      const replay = (data.item as Record<string, unknown> | undefined)?.replay as Record<string, unknown> | null;
      setSelectedReplay(replay ?? null);
      setStatus(replay ? "Replay detail loaded." : "Detail loaded, but no replay payload was present.");
    },
    onError: (error) => setStatus(error instanceof Error ? error.message : "Unexpected error"),
  });

  function saveReplayToBuilder() {
    const builderHandoff = (selectedReplay?.builderHandoff as Record<string, unknown> | undefined) ?? null;
    if (!builderHandoff || typeof window === "undefined") {
      setStatus("No replay builder handoff is loaded yet.");
      return;
    }
    window.localStorage.setItem(HANDOFF_STORAGE_KEY, JSON.stringify(builderHandoff));
    setStatus("Replay handoff saved. Open /builder to continue refinement.");
  }

  function loadPersistedBetDetailFor(betId: string) {
    if (mode === "mock") {
      setSelectedBetId("bet_mock_hist");
      setSelectedReplay({
        builderHandoff: historyFallbackEnvelopeMock.zones.actionRail.builderHandoff as Record<string, unknown> | null,
      });
      setStatus("Mock persisted history detail loaded.");
      return;
    }
    setSelectedBetId(betId);
    persistedBetDetailMutation.mutate(betId);
  }

  function rememberToken(nextToken: string) {
    setToken(nextToken);
    if (typeof window !== "undefined") setStoredAuthToken(nextToken);
  }

  const persistedEnvelope = mode === "mock"
    ? historyFallbackEnvelopeMock
    : persistedBetDetailMutation.data
    ? createEnvelopeFromPersistedBetDetail(persistedBetDetailMutation.data)
    : null;
  const replayEnvelope = mode === "mock"
    ? historyFallbackEnvelopeMock
    : replayDetailMutation.data
    ? createEnvelopeFromEvaluationHistoryDetail(replayDetailMutation.data)
    : null;

  return (
    <DevConsoleShell
      title="History replay terminal"
      subtitle="Inspect persisted history, replay context, and Builder continuation paths from one place."
    >
      <DevPageHeader
        stage="Stage 4"
        title="Replay and receipts"
        description="Persisted history is the canonical base, while legacy evaluation replay still exists as migration support."
        facts={[
          { label: "Route", value: <code>/history</code> },
          { label: "Canonical", value: <code>GET /api/bets/history</code> },
          { label: "Support", value: <code>GET /app/history</code> },
        ]}
      />

      <section className="panel-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>Persisted bet history</h2>
            <span>Canonical base: GET /api/bets/history</span>
          </div>

          {mode === "mock" ? <p className="status">Mock mode is active. This screen is rendering fallback-history fixtures instead of live API responses.</p> : null}

          <label className="field">
            <span>Bearer token</span>
            <input
              type="password"
              value={token}
              onChange={(event) => rememberToken(event.target.value)}
              placeholder="Optional for authenticated bet history"
            />
          </label>

          <div className="actions">
            <button type="button" onClick={() => persistedBetsMutation.mutate()} disabled={persistedBetsMutation.isPending || mode === "mock"}>
              {persistedBetsMutation.isPending ? "Loading..." : "Load bet history"}
            </button>
          </div>

          <p className={`status${persistedBetsMutation.isError ? " error" : ""}`}>
            {persistedBetsMutation.isError
              ? (persistedBetsMutation.error as Error).message
              : persistedBetsMutation.data
                ? `Loaded ${persistedBetsMutation.data.bets.length} persisted bet item(s).`
                : ""}
          </p>

          {mode === "mock" ? (
            <ul className="record-list">
              <li className="record-item">
                <div className="record-meta">
                  <strong>{historyFallbackEnvelopeMock.zones.inputBuilder.rawText}</strong>
                  <span>{historyFallbackEnvelopeMock.zones.evaluationSummary.label || "mock"}</span>
                </div>
                <div className="record-sub">
                  evaluationId: {historyFallbackEnvelopeMock.zones.evaluationSummary.evaluationId} | confidence: {historyFallbackEnvelopeMock.zones.evaluationSummary.confidence ?? "n/a"}
                </div>
                <div className="actions">
                  <button type="button" className="secondary-button" onClick={() => loadPersistedBetDetailFor("bet_mock_hist")}>
                    Load mock detail
                  </button>
                </div>
              </li>
            </ul>
          ) : (
          <ul className="record-list">
            {(persistedBetsMutation.data?.bets || []).map((bet) => (
              <li key={bet.id} className="record-item">
                <div className="record-meta">
                  <strong>{bet.inputText || bet.input_text}</strong>
                  <span>{bet.status}</span>
                </div>
                <div className="record-sub">
                  evaluationId: {bet.evaluationId || bet.evaluation_id || "missing"} | verdict: {bet.verdict || "n/a"} | confidence: {bet.confidence ?? "n/a"}
                </div>
                <div className="actions">
                  <button type="button" className="secondary-button" onClick={() => setSelectedBetId(bet.id)}>
                    Select bet detail
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => loadPersistedBetDetailFor(bet.id)}
                  >
                    Load bet detail
                  </button>
                </div>
              </li>
            ))}
          </ul>
          )}
        </section>

        <section className="panel result-panel">
          <div className="panel-header">
            <h2>Replay history</h2>
            <span>Dev support: GET /app/history</span>
          </div>

          <div className="actions">
            <button type="button" onClick={() => replayHistoryMutation.mutate()} disabled={replayHistoryMutation.isPending || mode === "mock"}>
              {replayHistoryMutation.isPending ? "Loading..." : "Load replay history"}
            </button>
          </div>

          <p className={`status${replayHistoryMutation.isError ? " error" : ""}`}>
            {replayHistoryMutation.isError
              ? (replayHistoryMutation.error as Error).message
              : replayHistoryMutation.data
                ? `Loaded ${replayHistoryMutation.data.items.length} replay item(s).`
                : ""}
          </p>

          {mode === "mock" ? (
            <ul className="record-list">
              <li className="record-item">
                <div className="record-meta">
                  <strong>{historyFallbackEnvelopeMock.zones.inputBuilder.rawText}</strong>
                  <span>{historyFallbackEnvelopeMock.zones.evaluationSummary.signal || "unknown"}</span>
                </div>
                <div className="record-sub">
                  {historyFallbackEnvelopeMock.zones.evaluationSummary.label || "Mock replay"} | confidence: {historyFallbackEnvelopeMock.zones.evaluationSummary.confidence ?? "n/a"}
                </div>
                <div className="actions">
                  <button type="button" className="secondary-button" onClick={() => {
                    setSelectedReplay({
                      builderHandoff: historyFallbackEnvelopeMock.zones.actionRail.builderHandoff as Record<string, unknown> | null,
                    });
                    setStatus("Mock replay detail loaded.");
                  }}>
                    Load mock replay
                  </button>
                </div>
              </li>
            </ul>
          ) : (
          <ul className="record-list">
            {(replayHistoryMutation.data?.items || []).map((item) => (
              <li key={item.id} className="record-item">
                <div className="record-meta">
                  <strong>{item.inputText}</strong>
                  <span>{item.signal || "unknown"}</span>
                </div>
                <div className="record-sub">
                  {item.label || "Unknown label"} | grade: {item.grade || "n/a"} | fragility: {item.fragilityScore ?? "n/a"}
                </div>
                <div className="actions">
                  <button type="button" className="secondary-button" onClick={() => replayDetailMutation.mutate(item.id)}>
                    Load replay detail
                  </button>
                </div>
              </li>
            ))}
          </ul>
          )}
        </section>
      </section>

      <section className="panel history-detail-panel">
        <div className="panel-header">
          <h2>Selected history detail</h2>
          <span>Replay to Builder when available</span>
        </div>

        <div className="actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              if (selectedBetId) {
                loadPersistedBetDetailFor(selectedBetId);
              } else {
                setStatus("Select a persisted bet first.");
              }
            }}
            disabled={persistedBetDetailMutation.isPending}
          >
            {persistedBetDetailMutation.isPending ? "Loading..." : "Load selected bet detail"}
          </button>
          <button type="button" onClick={saveReplayToBuilder}>
            Send replay to Builder
          </button>
        </div>

        <p className="status">{status}</p>

        <div className="result-block">
          <h3>Persisted replay envelope</h3>
          <EvaluationEnvelopeView
            envelope={persistedEnvelope}
            emptyMessage="Load a persisted bet detail to inspect the normalized replay envelope."
          />
        </div>

        <div className="result-block">
          <h3>Selected replay payload</h3>
          <pre>{prettyJson(selectedReplay ?? {})}</pre>
        </div>

        <div className="result-block">
          <h3>Legacy replay envelope</h3>
          <EvaluationEnvelopeView
            envelope={replayEnvelope}
            emptyMessage="Load a legacy replay detail to inspect the normalized envelope."
          />
        </div>
      </section>
    </DevConsoleShell>
  );
}
