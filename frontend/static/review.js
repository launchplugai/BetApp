const apiBaseEl = document.getElementById("api-base");
const fileInputEl = document.getElementById("ocr-file");
const uploadLabelEl = document.getElementById("upload-label");
const statusEl = document.getElementById("status");
const requestIdEl = document.getElementById("request-id");
const confidenceEl = document.getElementById("confidence");
const requiresReviewEl = document.getElementById("requires-review");
const legCountEl = document.getElementById("leg-count");
const legsEmptyEl = document.getElementById("legs-empty");
const legListEl = document.getElementById("leg-list");
const rawTextEl = document.getElementById("raw-text");
const responseJsonEl = document.getElementById("response-json");

function pretty(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.className = isError ? "status error" : "status";
}

function renderLegs(legs) {
  legListEl.innerHTML = "";
  if (!Array.isArray(legs) || legs.length === 0) {
    legsEmptyEl.textContent = "No OCR legs detected.";
    legsEmptyEl.style.display = "block";
    return;
  }

  legsEmptyEl.style.display = "none";
  legs.forEach((leg) => {
    const item = document.createElement("li");
    const value = leg.value ? ` ${leg.value}` : "";
    item.innerHTML = `<strong>${leg.entity}</strong> ${leg.market}${value} <em>(${leg.clarity})</em>`;
    legListEl.appendChild(item);
  });
}

function renderResult(data) {
  requestIdEl.textContent = data.requestId || "missing";
  confidenceEl.textContent = `${Math.round((data.confidence || 0) * 100)}%`;
  requiresReviewEl.textContent = data.requiresReview ? "yes" : "no";
  legCountEl.textContent = String(Array.isArray(data.detectedLegs) ? data.detectedLegs.length : 0);
  renderLegs(data.detectedLegs || []);
  rawTextEl.textContent = data.rawText || "";
  responseJsonEl.textContent = pretty(data);
}

async function handleFileChange() {
  const file = fileInputEl.files?.[0];
  if (!file) {
    uploadLabelEl.textContent = "Choose a slip screenshot";
    return;
  }

  uploadLabelEl.textContent = file.name;
  setStatus("Extracting OCR review payload...");

  try {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${apiBaseEl.value}/api/ocr/review`, {
      method: "POST",
      body: formData,
    });

    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.detail || payload?.error || "OCR review request failed");
    }

    renderResult(payload);
    setStatus("OCR review payload ready.");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Unexpected error", true);
  }
}

fileInputEl.addEventListener("change", handleFileChange);
