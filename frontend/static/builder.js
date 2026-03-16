const STORAGE_KEY = "betapp.builderHandoff";

const statusEl = document.getElementById("builder-status");
const evaluationIdEl = document.getElementById("builder-evaluation-id");
const tierEl = document.getElementById("builder-tier");
const primaryFailureLabelEl = document.getElementById("builder-primary-failure-label");
const fastestFixLabelEl = document.getElementById("builder-fastest-fix-label");
const inputTextEl = document.getElementById("builder-input-text");
const primaryFailureEl = document.getElementById("builder-primary-failure");
const fastestFixEl = document.getElementById("builder-fastest-fix");
const deltaPreviewEl = document.getElementById("builder-delta-preview");
const signalInfoEl = document.getElementById("builder-signal-info");
const handoffJsonEl = document.getElementById("builder-handoff-json");
const reevalJsonEl = document.getElementById("builder-reeval-json");
const reuseEvaluateBtn = document.getElementById("reuse-evaluate-btn");
const clearHandoffBtn = document.getElementById("clear-handoff-btn");

function pretty(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function readHandoff() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "status error" : "status";
}

function describeBlock(block) {
  if (!block || typeof block !== "object") {
    return "missing";
  }

  return (
    block.label ||
    block.title ||
    block.reason ||
    block.summary ||
    block.action ||
    "present"
  );
}

function renderHandoff(handoff) {
  evaluationIdEl.textContent = handoff?.evaluationId || "missing";
  tierEl.textContent = handoff?.tier || "unknown";
  primaryFailureLabelEl.textContent = describeBlock(handoff?.primaryFailure);
  fastestFixLabelEl.textContent = describeBlock(handoff?.fastestFix);
  inputTextEl.textContent = handoff?.inputText || "";
  primaryFailureEl.textContent = pretty(handoff?.primaryFailure);
  fastestFixEl.textContent = pretty(handoff?.fastestFix);
  deltaPreviewEl.textContent = pretty(handoff?.deltaPreview);
  signalInfoEl.textContent = pretty(handoff?.signalInfo);
  handoffJsonEl.textContent = pretty(handoff);
}

async function reEvaluate() {
  const handoff = readHandoff();
  if (!handoff?.inputText) {
    setStatus("No Builder handoff available to re-evaluate.", true);
    return;
  }

  setStatus("Re-evaluating saved Builder handoff...");
  reuseEvaluateBtn.disabled = true;

  try {
    const apiBase = localStorage.getItem("betapp.apiBase") || "http://localhost:8000";
    const response = await fetch(`${apiBase}/app/evaluate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        input: handoff.inputText,
        tier: handoff.tier,
      }),
    });

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.detail || payload?.error || "Re-evaluate request failed");
    }

    reevalJsonEl.textContent = pretty(payload);
    setStatus("Re-evaluation complete.");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Unexpected error", true);
  } finally {
    reuseEvaluateBtn.disabled = false;
  }
}

function clearHandoff() {
  localStorage.removeItem(STORAGE_KEY);
  renderHandoff(null);
  reevalJsonEl.textContent = "{}";
  setStatus("Builder handoff cleared.");
}

const handoff = readHandoff();
if (handoff) {
  renderHandoff(handoff);
  setStatus("Builder handoff loaded.");
}

reuseEvaluateBtn.addEventListener("click", reEvaluate);
clearHandoffBtn.addEventListener("click", clearHandoff);
