const HANDOFF_STORAGE_KEY = "betapp.builderHandoff";

const apiBaseEl = document.getElementById("api-base");
const authTokenEl = document.getElementById("auth-token");
const loadBetsBtn = document.getElementById("load-bets-btn");
const loadReplayBtn = document.getElementById("load-replay-btn");
const loadBetDetailBtn = document.getElementById("load-bet-detail-btn");
const sendToBuilderBtn = document.getElementById("send-to-builder-btn");
const betsStatusEl = document.getElementById("bets-status");
const replayStatusEl = document.getElementById("replay-status");
const detailStatusEl = document.getElementById("detail-status");
const betsListEl = document.getElementById("bets-list");
const replayListEl = document.getElementById("replay-list");
const historySummaryEl = document.getElementById("history-summary");
const historyReplayEl = document.getElementById("history-replay");
const historyDetailJsonEl = document.getElementById("history-detail-json");

let selectedReplay = null;
let selectedBetId = null;

function pretty(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function setStatus(el, message, isError = false) {
  el.textContent = message;
  el.className = isError ? "status error" : "status";
}

function clearList(el) {
  el.innerHTML = "";
}

function itemButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.className = "secondary-button";
  button.addEventListener("click", onClick);
  return button;
}

function renderPersistedBets(data) {
  clearList(betsListEl);
  const bets = Array.isArray(data?.bets) ? data.bets : [];
  if (!bets.length) {
    setStatus(betsStatusEl, "No persisted bets returned.");
    return;
  }

  setStatus(betsStatusEl, `Loaded ${bets.length} persisted bet item(s).`);
  bets.forEach((bet) => {
    const li = document.createElement("li");
    li.className = "record-item";

    const meta = document.createElement("div");
    meta.className = "record-meta";
    meta.innerHTML = `<strong>${bet.input_text || "Untitled bet"}</strong><span>${bet.status || "pending"}</span>`;

    const sub = document.createElement("div");
    sub.className = "record-sub";
    sub.textContent = `evaluation_id: ${bet.evaluation_id || "missing"} | verdict: ${bet.verdict || "n/a"} | confidence: ${bet.confidence ?? "n/a"}`;

    const actions = document.createElement("div");
    actions.className = "actions";
    actions.appendChild(
      itemButton("Select bet detail", () => {
        selectedBetId = bet.id;
        setStatus(detailStatusEl, `Selected persisted bet ${bet.id}. Load detail when ready.`);
      })
    );
    actions.appendChild(
      itemButton("Load bet detail", () => {
        selectedBetId = bet.id;
        loadPersistedBetDetail();
      })
    );

    li.append(meta, sub, actions);
    betsListEl.appendChild(li);
  });
}

function renderReplayList(data) {
  clearList(replayListEl);
  const items = Array.isArray(data?.items) ? data.items : [];
  if (!items.length) {
    setStatus(replayStatusEl, "No replay items returned.");
    return;
  }

  setStatus(replayStatusEl, `Loaded ${items.length} replay item(s).`);
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "record-item";

    const meta = document.createElement("div");
    meta.className = "record-meta";
    meta.innerHTML = `<strong>${item.inputText || "Untitled evaluation"}</strong><span>${item.signal || "unknown"}</span>`;

    const sub = document.createElement("div");
    sub.className = "record-sub";
    sub.textContent = `${item.label || "Unknown label"} | grade: ${item.grade || "n/a"} | fragility: ${item.fragilityScore ?? "n/a"}`;

    const actions = document.createElement("div");
    actions.className = "actions";
    actions.appendChild(
      itemButton("Load replay detail", () => loadReplayDetail(item.id))
    );

    li.append(meta, sub, actions);
    replayListEl.appendChild(li);
  });
}

function renderSelectedDetail(data) {
  const item = data?.item || null;
  const replay = item?.replay || null;
  selectedReplay = replay;
  historySummaryEl.textContent = pretty({
    id: item?.id,
    inputText: item?.inputText,
    signal: item?.signal,
    label: item?.label,
    grade: item?.grade,
    fragilityScore: item?.fragilityScore,
  });
  historyReplayEl.textContent = pretty(replay);
  historyDetailJsonEl.textContent = pretty(data);
  setStatus(detailStatusEl, replay ? "Replay detail loaded." : "Detail loaded, but no replay payload was present.");
}

async function loadPersistedBets() {
  setStatus(betsStatusEl, "Loading persisted bet history...");
  try {
    const headers = {};
    if (authTokenEl.value.trim()) {
      headers.Authorization = `Bearer ${authTokenEl.value.trim()}`;
      localStorage.setItem("betapp.authToken", authTokenEl.value.trim());
    }
    localStorage.setItem("betapp.apiBase", apiBaseEl.value);

    const response = await fetch(`${apiBaseEl.value}/api/bets/history`, {
      headers,
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.detail || payload?.error || "Bet history request failed");
    }
    renderPersistedBets(payload);
  } catch (error) {
    setStatus(betsStatusEl, error instanceof Error ? error.message : "Unexpected error", true);
  }
}

async function loadPersistedBetDetail() {
  if (!selectedBetId) {
    setStatus(detailStatusEl, "Select a persisted bet first.", true);
    return;
  }

  setStatus(detailStatusEl, "Loading persisted bet detail...");
  try {
    const headers = {};
    if (authTokenEl.value.trim()) {
      headers.Authorization = `Bearer ${authTokenEl.value.trim()}`;
    }

    const response = await fetch(`${apiBaseEl.value}/api/bets/${selectedBetId}`, {
      headers,
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.detail || payload?.error || "Bet detail request failed");
    }
    renderSelectedDetail({ item: payload, source: "persistedBet" });
  } catch (error) {
    setStatus(detailStatusEl, error instanceof Error ? error.message : "Unexpected error", true);
  }
}

async function loadReplayHistory() {
  setStatus(replayStatusEl, "Loading replay history...");
  try {
    localStorage.setItem("betapp.apiBase", apiBaseEl.value);
    const response = await fetch(`${apiBaseEl.value}/app/history`);
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.detail || payload?.error || "Replay history request failed");
    }
    renderReplayList(payload);
  } catch (error) {
    setStatus(replayStatusEl, error instanceof Error ? error.message : "Unexpected error", true);
  }
}

async function loadReplayDetail(itemId) {
  setStatus(detailStatusEl, "Loading replay detail...");
  try {
    const response = await fetch(`${apiBaseEl.value}/app/history/${itemId}`);
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.detail || payload?.error || "Replay detail request failed");
    }
    renderSelectedDetail(payload);
  } catch (error) {
    setStatus(detailStatusEl, error instanceof Error ? error.message : "Unexpected error", true);
  }
}

function sendToBuilder() {
  if (!selectedReplay?.builderHandoff) {
    setStatus(detailStatusEl, "No replay builder handoff is loaded yet.", true);
    return;
  }
  localStorage.setItem(HANDOFF_STORAGE_KEY, JSON.stringify(selectedReplay.builderHandoff));
  localStorage.setItem("betapp.apiBase", apiBaseEl.value);
  setStatus(detailStatusEl, "Replay handoff saved. Open /builder to continue refinement.");
}

const savedToken = localStorage.getItem("betapp.authToken");
if (savedToken) {
  authTokenEl.value = savedToken;
}
const savedApiBase = localStorage.getItem("betapp.apiBase");
if (savedApiBase) {
  apiBaseEl.value = savedApiBase;
}

loadBetsBtn.addEventListener("click", loadPersistedBets);
loadReplayBtn.addEventListener("click", loadReplayHistory);
loadBetDetailBtn.addEventListener("click", loadPersistedBetDetail);
sendToBuilderBtn.addEventListener("click", sendToBuilder);
