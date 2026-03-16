"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { DevConsoleShell } from "@/components/dev-console-shell";
import { EvaluationEnvelopeView } from "@/components/evaluation-envelope-view";
import type { EvaluationEnvelope } from "@/lib/contracts/evaluation-envelope";
import {
  evaluateGoodEnvelopeMock,
  evaluateRiskEnvelopeMock,
  historyFallbackEnvelopeMock,
  ocrReviewEnvelopeMock,
} from "@/lib/mocks/evaluation-envelope";
import {
  type DevMode,
  getStoredApiBaseUrl,
  getStoredAuthToken,
  getStoredDevMode,
  setStoredApiBaseUrl,
  setStoredAuthToken,
  setStoredDevMode,
} from "@/lib/dev-session";

const mockOptions: Record<string, EvaluationEnvelope> = {
  evaluate_good: evaluateGoodEnvelopeMock,
  evaluate_risk: evaluateRiskEnvelopeMock,
  ocr_review: ocrReviewEnvelopeMock,
  history_fallback: historyFallbackEnvelopeMock,
};

export function DevConsoleHome() {
  const [apiBase, setApiBase] = useState("http://localhost:8000");
  const [token, setToken] = useState("");
  const [mode, setMode] = useState<DevMode>("live");
  const [activeMock, setActiveMock] = useState<keyof typeof mockOptions>("evaluate_good");
  const [connectionStatus, setConnectionStatus] = useState("Not checked yet.");

  useEffect(() => {
    setApiBase(getStoredApiBaseUrl());
    setToken(getStoredAuthToken());
    setMode(getStoredDevMode());
  }, []);

  async function checkBackend() {
    setConnectionStatus("Checking backend...");
    try {
      const response = await fetch(`${apiBase}/health`, { cache: "no-store" });
      if (!response.ok) throw new Error(`Health check failed with ${response.status}`);
      setConnectionStatus("Backend reachable.");
    } catch (error) {
      setConnectionStatus(error instanceof Error ? error.message : "Backend check failed.");
    }
  }

  function saveSettings() {
    setStoredApiBaseUrl(apiBase);
    setStoredAuthToken(token);
    setStoredDevMode(mode);
    setConnectionStatus("Saved dev settings.");
  }

  return (
    <DevConsoleShell
      title="BetApp dev home"
      subtitle="This is the developer entry point. Set runtime state once, choose live or mock mode, then move through Evaluate, OCR, Builder, and History without reconfiguring every screen."
    >
      <section className="hero-card">
        <p className="eyebrow">Workflow</p>
        <h2>Choose your next lane</h2>
        <div className="actions top-actions">
          <Link href="/evaluate" className="secondary-link">Open Evaluate</Link>
          <Link href="/evaluate/review" className="secondary-link">Open OCR Review</Link>
          <Link href="/builder" className="secondary-link">Open Builder</Link>
          <Link href="/history" className="secondary-link">Open History</Link>
        </div>
      </section>

      <section className="panel-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>Runtime controls</h2>
            <span>Developer flow settings</span>
          </div>

          <label className="field">
            <span>API base URL</span>
            <input value={apiBase} onChange={(event) => setApiBase(event.target.value)} />
          </label>

          <label className="field">
            <span>Bearer token</span>
            <input
              type="password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              placeholder="Optional for history and authenticated flows"
            />
          </label>

          <label className="field">
            <span>Mode</span>
            <select value={mode} onChange={(event) => setMode(event.target.value as DevMode)}>
              <option value="live">live backend</option>
              <option value="mock">mock envelope preview</option>
            </select>
          </label>

          <div className="actions">
            <button type="button" onClick={saveSettings}>Save settings</button>
            <button type="button" className="secondary-button" onClick={checkBackend}>Check backend</button>
          </div>

          <p className="status">{connectionStatus}</p>
        </section>

        <section className="panel result-panel">
          <div className="panel-header">
            <h2>Mock envelope browser</h2>
            <span>Use this when backend wiring is not the task</span>
          </div>

          <label className="field">
            <span>Fixture</span>
            <select
              value={activeMock}
              onChange={(event) => setActiveMock(event.target.value as keyof typeof mockOptions)}
            >
              <option value="evaluate_good">evaluate good</option>
              <option value="evaluate_risk">evaluate risk</option>
              <option value="ocr_review">ocr review</option>
              <option value="history_fallback">history fallback</option>
            </select>
          </label>

          <EvaluationEnvelopeView
            envelope={mockOptions[activeMock]}
            emptyMessage="Choose a fixture to inspect the normalized envelope."
          />
        </section>
      </section>
    </DevConsoleShell>
  );
}
