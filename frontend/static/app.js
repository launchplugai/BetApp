const form = document.getElementById("evaluate-form");
const statusEl = document.getElementById("status");
const submitBtn = document.getElementById("submit-btn");
const apiBaseEl = document.getElementById("api-base");
const inputEl = document.getElementById("input");
const tierEl = document.getElementById("tier");
const evaluationIdEl = document.getElementById("evaluation-id");
const builderReadyEl = document.getElementById("builder-ready");
const protocolCountEl = document.getElementById("protocol-count");
const resultTierEl = document.getElementById("result-tier");
const builderHandoffEl = document.getElementById("builder-handoff");
const responseJsonEl = document.getElementById("response-json");
const STORAGE_KEY = "betapp.builderHandoff";

function pretty(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "status error" : "status";
}

function renderResult(data) {
  evaluationIdEl.textContent = data.evaluationId || "missing";
  builderReadyEl.textContent = data.builderHandoff ? "ready" : "missing";
  protocolCountEl.textContent = String(Array.isArray(data.triggeredProtocols) ? data.triggeredProtocols.length : 0);
  resultTierEl.textContent =
    data.builderHandoff?.tier || data.input?.tier || data.evaluation?.tier || "unknown";
  builderHandoffEl.textContent = pretty(data.builderHandoff);
  responseJsonEl.textContent = pretty(data);
}

function normalizeBuilderHandoff(data) {
  const handoff = data.builderHandoff || {};
  return {
    evaluationId: data.evaluationId || handoff.evaluationId || null,
    inputText: handoff.inputText || data.input?.input || inputEl.value.trim(),
    tier: handoff.tier || data.input?.tier || tierEl.value,
    primaryFailure: data.primaryFailure || handoff.primaryFailure || null,
    fastestFix: handoff.fastestFix || null,
    deltaPreview: data.deltaPreview || handoff.deltaPreview || null,
    signalInfo: data.signalInfo || handoff.signalInfo || null,
  };
}

function persistBuilderHandoff(data) {
  const handoff = normalizeBuilderHandoff(data);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(handoff));
  localStorage.setItem("betapp.apiBase", apiBaseEl.value);
}

async function evaluate(event) {
  event.preventDefault();
  setStatus("Evaluating...");
  submitBtn.disabled = true;

  try {
    const response = await fetch(`${apiBaseEl.value}/app/evaluate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        input: inputEl.value.trim(),
        tier: tierEl.value,
      }),
    });

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.detail || payload?.error || "Evaluate request failed");
    }

    renderResult(payload);
    persistBuilderHandoff(payload);
    setStatus("Evaluation complete.");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Unexpected error", true);
  } finally {
    submitBtn.disabled = false;
  }
}

form.addEventListener("submit", evaluate);
