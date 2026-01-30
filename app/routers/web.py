# app/routers/web.py
"""
Web UI Router - Ticket 22: Scorched Earth UI Reset

Single canonical UI at /app with redirects from / and /ui2.
Minimal, clean, mobile-friendly interface.

Design principles:
- ONE UI, no confusion
- Simple textarea + tier selector + submit
- Clear loading/error states
- Artifacts displayed using Ticket 21 UI contract
- Debug mode for raw JSON inspection
"""
from __future__ import annotations

import json
import logging
import math
import time
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.airlock import airlock_ingest, AirlockError
from app.config import load_config
from app.correlation import get_request_id
from app.rate_limiter import get_client_ip, get_rate_limiter

_logger = logging.getLogger(__name__)

router = APIRouter(tags=["Web UI"])


# =============================================================================
# Request Schema
# =============================================================================


class WebEvaluateRequest(BaseModel):
    """Request schema for web evaluation."""
    input: str = Field(..., description="Bet text input")
    tier: Optional[str] = Field(default=None, description="Plan tier: GOOD, BETTER, or BEST")


# =============================================================================
# Structured Logging
# =============================================================================


def _log_request(
    request_id: str,
    client_ip: str,
    tier: str,
    input_length: int,
    status_code: int,
    latency_ms: float,
    rate_limited: bool = False,
    error_type: Optional[str] = None,
) -> None:
    """Log structured request entry."""
    log_data = {
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "route": "/app/evaluate",
        "method": "POST",
        "client_ip": client_ip,
        "tier": tier,
        "input_length": input_length,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
        "rate_limited": rate_limited,
    }
    if error_type:
        log_data["error_type"] = error_type

    _logger.info(
        "request_id=%(request_id)s tier=%(tier)s status=%(status_code)d latency=%(latency_ms).2fms",
        log_data,
    )


# =============================================================================
# HTML Template - Minimal Canonical UI
# =============================================================================


def _get_canonical_ui_html() -> str:
    """Generate the single canonical UI HTML."""
    config = load_config()
    git_sha = config.git_sha[:8] if config.git_sha else "dev"

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>DNA Bet Engine</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        :root {{
            --bg: #0a0a0a;
            --surface: #141414;
            --surface-hover: #1a1a1a;
            --border: #2a2a2a;
            --text: #e0e0e0;
            --text-muted: #808080;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --green: #22c55e;
            --yellow: #eab308;
            --red: #ef4444;
            --radius: 8px;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            padding: 16px;
            line-height: 1.5;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }}
        h1 {{
            font-size: 20px;
            font-weight: 600;
        }}
        .build-stamp {{
            font-size: 11px;
            color: var(--text-muted);
            font-family: monospace;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
            margin-bottom: 16px;
        }}
        label {{
            display: block;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 8px;
            color: var(--text-muted);
        }}
        textarea {{
            width: 100%;
            min-height: 120px;
            padding: 12px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text);
            font-size: 14px;
            font-family: inherit;
            resize: vertical;
        }}
        textarea:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        textarea::placeholder {{
            color: var(--text-muted);
        }}
        .tier-selector {{
            display: flex;
            gap: 8px;
            margin: 16px 0;
        }}
        .tier-btn {{
            flex: 1;
            padding: 10px 8px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text-muted);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .tier-btn:hover {{
            background: var(--surface-hover);
        }}
        .tier-btn.active {{
            background: var(--accent);
            border-color: var(--accent);
            color: white;
        }}
        .submit-btn {{
            width: 100%;
            padding: 14px;
            background: var(--accent);
            border: none;
            border-radius: var(--radius);
            color: white;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.15s;
        }}
        .submit-btn:hover {{
            background: var(--accent-hover);
        }}
        .submit-btn:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
        }}
        .loading {{
            display: none;
            text-align: center;
            padding: 32px;
            color: var(--text-muted);
        }}
        .loading.active {{
            display: block;
        }}
        .spinner {{
            width: 24px;
            height: 24px;
            border: 2px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 12px;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        .error-panel {{
            display: none;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--red);
            border-radius: var(--radius);
            padding: 12px;
            margin-bottom: 16px;
            color: var(--red);
            font-size: 14px;
        }}
        .error-panel.active {{
            display: block;
        }}
        .results {{
            display: none;
        }}
        .results.active {{
            display: block;
        }}
        .grade {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 16px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            margin-bottom: 16px;
        }}
        .grade-signal {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: 700;
        }}
        .grade-signal.blue {{ background: rgba(59, 130, 246, 0.2); color: #3b82f6; }}
        .grade-signal.green {{ background: rgba(34, 197, 94, 0.2); color: #22c55e; }}
        .grade-signal.yellow {{ background: rgba(234, 179, 8, 0.2); color: #eab308; }}
        .grade-signal.red {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; }}
        .grade-info h2 {{
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .grade-info p {{
            font-size: 13px;
            color: var(--text-muted);
        }}
        .section-title {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        .risks-list {{
            list-style: none;
        }}
        .risks-list li {{
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        .risks-list li:last-child {{
            border-bottom: none;
        }}
        .artifacts-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .artifact-count {{
            font-size: 12px;
            color: var(--text-muted);
            font-family: monospace;
        }}
        .artifacts-list {{
            list-style: none;
        }}
        .artifact-item {{
            padding: 10px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            margin-bottom: 8px;
            font-size: 13px;
        }}
        .artifact-label {{
            font-weight: 500;
            color: var(--text);
            margin-bottom: 4px;
        }}
        .artifact-text {{
            color: var(--text-muted);
            font-size: 12px;
        }}
        .artifact-type-weight {{ border-left: 3px solid var(--accent); }}
        .artifact-type-constraint {{ border-left: 3px solid var(--yellow); }}
        .artifact-type-audit_note {{ border-left: 3px solid var(--green); }}
        .artifact-type-unknown {{ border-left: 3px solid var(--text-muted); }}
        .debug-section {{
            display: none;
            margin-top: 16px;
        }}
        .debug-section.active {{
            display: block;
        }}
        .debug-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            padding: 8px 0;
        }}
        .debug-content {{
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 12px;
            font-family: monospace;
            font-size: 11px;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 400px;
            overflow: auto;
        }}
        .contract-status {{
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: monospace;
        }}
        .contract-status.pass {{
            background: rgba(34, 197, 94, 0.2);
            color: var(--green);
        }}
        .contract-status.fail {{
            background: rgba(239, 68, 68, 0.2);
            color: var(--red);
        }}
        .reset-btn {{
            display: none;
            width: 100%;
            padding: 12px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text-muted);
            font-size: 14px;
            cursor: pointer;
            margin-top: 16px;
        }}
        .reset-btn:hover {{
            background: var(--surface);
        }}
        .reset-btn.active {{
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>DNA Bet Engine</h1>
            <span class="build-stamp">build: {git_sha}</span>
        </header>

        <div id="input-section" class="card">
            <label for="bet-input">Enter your bet slip</label>
            <textarea
                id="bet-input"
                placeholder="Lakers -5.5&#10;Celtics ML&#10;LeBron over 25.5 points"
            ></textarea>

            <div class="tier-selector">
                <button class="tier-btn active" data-tier="good">GOOD</button>
                <button class="tier-btn" data-tier="better">BETTER</button>
                <button class="tier-btn" data-tier="best">BEST</button>
            </div>

            <button id="submit-btn" class="submit-btn">Evaluate Bet</button>
        </div>

        <div id="loading" class="loading">
            <div class="spinner"></div>
            <div>Analyzing your bet...</div>
        </div>

        <div id="error-panel" class="error-panel"></div>

        <div id="results" class="results">
            <div id="grade-panel" class="grade">
                <div id="grade-signal" class="grade-signal"></div>
                <div class="grade-info">
                    <h2 id="grade-title"></h2>
                    <p id="grade-subtitle"></p>
                </div>
            </div>

            <div class="card">
                <div class="section-title">Key Risks</div>
                <ul id="risks-list" class="risks-list"></ul>
            </div>

            <div class="card">
                <div class="artifacts-header">
                    <div class="section-title">Artifacts</div>
                    <span id="artifact-count" class="artifact-count"></span>
                </div>
                <ul id="artifacts-list" class="artifacts-list"></ul>
            </div>

            <div id="debug-section" class="debug-section">
                <div class="card">
                    <div class="debug-header" onclick="toggleDebug()">
                        <div class="section-title">Debug Info</div>
                        <span id="ui-contract-status" class="contract-status"></span>
                    </div>
                    <div id="debug-content" class="debug-content"></div>
                </div>
            </div>
        </div>

        <button id="reset-btn" class="reset-btn" onclick="resetForm()">Evaluate Another</button>
    </div>

    <script>
        // State
        let selectedTier = 'good';
        let debugMode = new URLSearchParams(window.location.search).get('debug') === '1';
        let lastResponse = null;

        // Elements
        const betInput = document.getElementById('bet-input');
        const submitBtn = document.getElementById('submit-btn');
        const loading = document.getElementById('loading');
        const errorPanel = document.getElementById('error-panel');
        const results = document.getElementById('results');
        const resetBtn = document.getElementById('reset-btn');
        const inputSection = document.getElementById('input-section');

        // Tier selector
        document.querySelectorAll('.tier-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.tier-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                selectedTier = btn.dataset.tier;
            }});
        }});

        // Submit handler
        submitBtn.addEventListener('click', async () => {{
            const input = betInput.value.trim();
            if (!input) {{
                showError('Please enter a bet slip');
                return;
            }}

            showLoading();

            try {{
                const response = await fetch('/app/evaluate', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ input, tier: selectedTier }})
                }});

                const data = await response.json();
                lastResponse = data;

                if (!response.ok) {{
                    showError(data.detail || data.error || 'Evaluation failed');
                    return;
                }}

                showResults(data);
            }} catch (err) {{
                showError('Network error. Please try again.');
            }}
        }});

        function showLoading() {{
            inputSection.style.display = 'none';
            loading.classList.add('active');
            errorPanel.classList.remove('active');
            results.classList.remove('active');
            resetBtn.classList.remove('active');
        }}

        function showError(message) {{
            loading.classList.remove('active');
            inputSection.style.display = 'block';
            errorPanel.textContent = message;
            errorPanel.classList.add('active');
            results.classList.remove('active');
            resetBtn.classList.remove('active');
        }}

        function showResults(data) {{
            loading.classList.remove('active');
            errorPanel.classList.remove('active');
            results.classList.add('active');
            resetBtn.classList.add('active');

            // Grade/Signal
            const signal = data.signalInfo?.signal || 'yellow';
            const signalLabels = {{ blue: 'Strong', green: 'Solid', yellow: 'Fixable', red: 'Fragile' }};
            const gradeSignal = document.getElementById('grade-signal');
            gradeSignal.className = 'grade-signal ' + signal;
            gradeSignal.textContent = signal[0].toUpperCase();

            document.getElementById('grade-title').textContent = signalLabels[signal] || 'Unknown';
            document.getElementById('grade-subtitle').textContent =
                data.evaluation?.recommendation?.reason ||
                data.humanSummary?.verdict ||
                'Evaluation complete';

            // Risks
            const risksList = document.getElementById('risks-list');
            risksList.innerHTML = '';
            const risks = [];
            if (data.primaryFailure?.type) {{
                risks.push(data.primaryFailure.type.replace(/_/g, ' '));
            }}
            if (data.evaluation?.inductor?.explanation) {{
                risks.push(data.evaluation.inductor.explanation);
            }}
            if (data.secondaryFactors) {{
                data.secondaryFactors.slice(0, 2).forEach(f => risks.push(f));
            }}
            if (risks.length === 0) {{
                risks.push('No significant risks detected');
            }}
            risks.slice(0, 4).forEach(risk => {{
                const li = document.createElement('li');
                li.textContent = risk;
                risksList.appendChild(li);
            }});

            // Artifacts
            const artifacts = data.proofSummary?.sample_artifacts || [];
            const counts = data.proofSummary?.dna_artifact_counts || {{}};
            const countStr = Object.entries(counts).map(([k,v]) => k + ':' + v).join(', ') || 'none';
            document.getElementById('artifact-count').textContent = countStr;

            const artifactsList = document.getElementById('artifacts-list');
            artifactsList.innerHTML = '';
            if (artifacts.length === 0) {{
                const li = document.createElement('li');
                li.className = 'artifact-item';
                li.innerHTML = '<div class="artifact-label">(No artifacts)</div>';
                artifactsList.appendChild(li);
            }} else {{
                artifacts.slice(0, 5).forEach(a => {{
                    const li = document.createElement('li');
                    const type = a.artifact_type || a.type || 'unknown';
                    li.className = 'artifact-item artifact-type-' + type;
                    li.innerHTML =
                        '<div class="artifact-label">' + (a.display_label || type) + '</div>' +
                        '<div class="artifact-text">' + (a.display_text || '') + '</div>';
                    artifactsList.appendChild(li);
                }});
            }}

            // Debug section
            if (debugMode) {{
                document.getElementById('debug-section').classList.add('active');
                const uiStatus = data.proofSummary?.ui_contract_status || 'unknown';
                const uiVersion = data.proofSummary?.ui_contract_version || 'unknown';
                const statusEl = document.getElementById('ui-contract-status');
                statusEl.textContent = 'UI: ' + uiStatus + ' (' + uiVersion + ')';
                statusEl.className = 'contract-status ' + (uiStatus === 'PASS' ? 'pass' : 'fail');
                document.getElementById('debug-content').textContent = JSON.stringify(data, null, 2);
            }}
        }}

        function toggleDebug() {{
            const content = document.getElementById('debug-content');
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
        }}

        function resetForm() {{
            inputSection.style.display = 'block';
            results.classList.remove('active');
            resetBtn.classList.remove('active');
            betInput.value = '';
            betInput.focus();
        }}

        // Enter key submits
        betInput.addEventListener('keydown', (e) => {{
            if (e.key === 'Enter' && e.metaKey) {{
                submitBtn.click();
            }}
        }});
    </script>
</body>
</html>'''


# =============================================================================
# Routes
# =============================================================================


@router.get("/", response_class=RedirectResponse)
async def root_redirect():
    """Redirect / to /app (canonical UI)."""
    return RedirectResponse(url="/app", status_code=302)


@router.get("/ui2", response_class=RedirectResponse)
async def ui2_redirect():
    """Redirect /ui2 to /app (canonical UI)."""
    return RedirectResponse(url="/app", status_code=302)


@router.get("/app", response_class=HTMLResponse)
async def canonical_app():
    """
    Canonical UI - Single source of truth for all UI interactions.

    Ticket 22: Scorched earth reset. One UI to rule them all.
    """
    return HTMLResponse(content=_get_canonical_ui_html())


@router.post("/app/evaluate")
async def evaluate_proxy(request: WebEvaluateRequest, raw_request: Request):
    """
    Server-side proxy for evaluation requests.

    Rate limited: 10 requests/minute per IP.
    All input passes through Airlock for validation.
    """
    from app.routers.leading_light import is_leading_light_enabled
    from app.pipeline import run_evaluation

    start_time = time.perf_counter()
    request_id = get_request_id(raw_request) or "unknown"
    client_ip = get_client_ip(raw_request)

    # Airlock validation
    try:
        normalized = airlock_ingest(
            input_text=request.input,
            tier=request.tier,
        )
    except AirlockError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        _log_request(
            request_id=request_id,
            client_ip=client_ip,
            tier=request.tier or "unknown",
            input_length=len(request.input) if request.input else 0,
            status_code=400,
            latency_ms=latency_ms,
            error_type=e.code,
        )
        return JSONResponse(
            status_code=400,
            content={
                "request_id": request_id,
                "error": e.code,
                "detail": e.message,
                "code": e.code,
            },
        )

    tier = normalized.tier.value
    input_length = normalized.input_length

    # Rate limiting
    limiter = get_rate_limiter()
    allowed, retry_after = limiter.check(client_ip)

    if not allowed:
        latency_ms = (time.perf_counter() - start_time) * 1000
        _log_request(
            request_id=request_id,
            client_ip=client_ip,
            tier=tier,
            input_length=input_length,
            status_code=429,
            latency_ms=latency_ms,
            rate_limited=True,
        )
        return JSONResponse(
            status_code=429,
            content={
                "request_id": request_id,
                "error": "rate_limited",
                "detail": "Too many requests. Please slow down.",
                "retry_after_seconds": math.ceil(retry_after),
            },
            headers={"Retry-After": str(math.ceil(retry_after))},
        )

    # Feature flag check
    if not is_leading_light_enabled():
        latency_ms = (time.perf_counter() - start_time) * 1000
        _log_request(
            request_id=request_id,
            client_ip=client_ip,
            tier=tier,
            input_length=input_length,
            status_code=503,
            latency_ms=latency_ms,
            error_type="SERVICE_DISABLED",
        )
        return JSONResponse(
            status_code=503,
            content={
                "request_id": request_id,
                "error": "SERVICE_DISABLED",
                "detail": "Evaluation service is currently disabled.",
            },
        )

    try:
        result = run_evaluation(normalized)

        latency_ms = (time.perf_counter() - start_time) * 1000
        _log_request(
            request_id=request_id,
            client_ip=client_ip,
            tier=result.tier,
            input_length=input_length,
            status_code=200,
            latency_ms=latency_ms,
        )

        eval_response = result.evaluation
        response_data = {
            "request_id": request_id,
            "input": {
                "bet_text": normalized.input_text,
                "tier": result.tier,
            },
            "evaluation": {
                "parlay_id": str(eval_response.parlay_id),
                "inductor": {
                    "level": eval_response.inductor.level.value,
                    "explanation": eval_response.inductor.explanation,
                },
                "metrics": {
                    "raw_fragility": eval_response.metrics.raw_fragility,
                    "final_fragility": eval_response.metrics.final_fragility,
                    "leg_penalty": eval_response.metrics.leg_penalty,
                    "correlation_penalty": eval_response.metrics.correlation_penalty,
                    "correlation_multiplier": eval_response.metrics.correlation_multiplier,
                },
                "correlations": [
                    {
                        "block_a": str(c.block_a),
                        "block_b": str(c.block_b),
                        "type": c.type,
                        "penalty": c.penalty,
                    }
                    for c in eval_response.correlations
                ],
                "recommendation": {
                    "action": eval_response.recommendation.action.value,
                    "reason": eval_response.recommendation.reason,
                },
            },
            "interpretation": result.interpretation,
            "explain": result.explain,
            "context": result.context,
            "primaryFailure": result.primary_failure,
            "deltaPreview": result.delta_preview,
            "signalInfo": result.signal_info,
            "entities": result.entities,
            "secondaryFactors": result.secondary_factors,
            "humanSummary": result.human_summary,
            "proofSummary": result.proof_summary,
        }

        return JSONResponse(content=response_data)

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        _log_request(
            request_id=request_id,
            client_ip=client_ip,
            tier=tier,
            input_length=input_length,
            status_code=500,
            latency_ms=latency_ms,
            error_type="INTERNAL_ERROR",
        )
        _logger.exception("Evaluation failed: %s", e)
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": "INTERNAL_ERROR",
                "detail": "An internal error occurred.",
            },
        )
