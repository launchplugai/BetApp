# app/routers/web.py
"""
Web UI Router - Minimal browser interface for evaluation.

This is a strict system boundary:
- Browser never calls internal APIs directly
- All evaluation proxied through /app/evaluate
- Server remains source of truth for tier enforcement
- Rate limiting applied to prevent abuse
- Structured logging for traceability (no sensitive data)
- ALL input passes through Airlock before evaluation
"""
from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.airlock import (
    airlock_ingest,
    AirlockError,
    EmptyInputError,
    InputTooLongError,
    InvalidTierError,
    get_max_input_length,
)
from app.config import load_config
from app.correlation import get_request_id
from app.rate_limiter import get_client_ip, get_rate_limiter


# Logger for structured request logging
_logger = logging.getLogger(__name__)


router = APIRouter(tags=["Web UI"])


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
    """
    Log a structured request entry for /app/evaluate.

    NEVER logs raw user input or full payloads.
    Only logs metadata for debugging and abuse monitoring.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    log_data = {
        "request_id": request_id,
        "timestamp": timestamp,
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

    # Single-line structured log entry
    _logger.info(
        "request_id=%(request_id)s timestamp=%(timestamp)s route=%(route)s "
        "method=%(method)s client_ip=%(client_ip)s tier=%(tier)s "
        "input_length=%(input_length)d status_code=%(status_code)d "
        "latency_ms=%(latency_ms).2f rate_limited=%(rate_limited)s"
        + (" error_type=%(error_type)s" if error_type else ""),
        log_data,
    )


# =============================================================================
# Request/Response Schemas
# =============================================================================


class WebEvaluateRequest(BaseModel):
    """
    Request schema for web evaluation proxy.

    IMPORTANT: This schema does minimal validation.
    Full validation/normalization happens in Airlock.
    """
    input: str = Field(..., description="Bet text input")
    tier: Optional[str] = Field(default=None, description="Plan tier: GOOD, BETTER, or BEST")


# =============================================================================
# HTML Templates
# =============================================================================


def _get_landing_page_html() -> str:
    """Generate landing page HTML."""
    config = load_config()
    git_sha_display = config.git_sha or "not set"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DNA Matrix - Leading Light</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        }}
        .container {{
            max-width: 600px;
            text-align: center;
        }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            color: #fff;
        }}
        .subtitle {{
            color: #888;
            margin-bottom: 2rem;
        }}
        .links {{
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin-bottom: 2rem;
        }}
        a {{
            color: #4a9eff;
            text-decoration: none;
            padding: 0.75rem 1.5rem;
            border: 1px solid #4a9eff;
            border-radius: 4px;
            transition: all 0.2s;
        }}
        a:hover {{
            background: #4a9eff;
            color: #000;
        }}
        .info {{
            font-size: 0.875rem;
            color: #666;
            margin-top: 2rem;
        }}
        .sha {{
            font-family: monospace;
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>DNA Matrix</h1>
        <p class="subtitle">Leading Light Evaluation Engine</p>
        <div class="links">
            <a href="/app">Launch App</a>
            <a href="/health">Health Check</a>
        </div>
        <p class="info">
            Version: {config.service_version} |
            Git SHA: <span class="sha">{git_sha_display[:8] if len(git_sha_display) > 8 else git_sha_display}</span>
        </p>
    </div>
</body>
</html>"""


def _get_app_page_html() -> str:
    """Generate app page HTML with parlay builder and evaluation form."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Leading Light - Parlay Builder</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 1.5rem;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #333;
        }
        h1 { font-size: 1.5rem; color: #fff; }
        header a {
            color: #4a9eff;
            text-decoration: none;
            font-size: 0.875rem;
        }
        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }
        @media (max-width: 768px) {
            .main-grid { grid-template-columns: 1fr; }
        }

        /* Builder Section */
        .builder-section {
            background: #111;
            padding: 1.25rem;
            border-radius: 8px;
        }
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        .section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: #fff;
        }
        .leg-count {
            font-size: 0.875rem;
            color: #888;
        }

        /* Sport Selector */
        .sport-selector {
            margin-bottom: 1rem;
        }
        .sport-selector select {
            width: 100%;
            padding: 0.75rem;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 4px;
            color: #e0e0e0;
            font-size: 0.9rem;
        }
        .sport-selector select:focus {
            outline: none;
            border-color: #4a9eff;
        }

        /* Legs Container */
        .legs-container {
            max-height: 400px;
            overflow-y: auto;
            margin-bottom: 1rem;
        }
        .leg-card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            position: relative;
        }
        .leg-card:last-child { margin-bottom: 0; }
        .leg-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }
        .leg-number {
            font-weight: 600;
            font-size: 0.875rem;
            color: #4a9eff;
        }
        .remove-leg {
            background: transparent;
            border: none;
            color: #ff4a4a;
            cursor: pointer;
            font-size: 1.25rem;
            padding: 0;
            width: auto;
            line-height: 1;
        }
        .remove-leg:hover { color: #ff6b6b; }
        .remove-leg:disabled { color: #444; cursor: not-allowed; }

        .leg-fields {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
        }
        .leg-field {
            display: flex;
            flex-direction: column;
        }
        .leg-field.full-width {
            grid-column: 1 / -1;
        }
        .leg-field label {
            font-size: 0.7rem;
            color: #888;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .leg-field input, .leg-field select {
            padding: 0.5rem;
            background: #0a0a0a;
            border: 1px solid #333;
            border-radius: 4px;
            color: #e0e0e0;
            font-size: 0.875rem;
        }
        .leg-field input:focus, .leg-field select:focus {
            outline: none;
            border-color: #4a9eff;
        }
        .leg-field input::placeholder {
            color: #555;
        }

        /* Add Leg Button */
        .add-leg-btn {
            width: 100%;
            padding: 0.75rem;
            background: transparent;
            border: 2px dashed #333;
            border-radius: 6px;
            color: #888;
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 1rem;
        }
        .add-leg-btn:hover {
            border-color: #4a9eff;
            color: #4a9eff;
        }
        .add-leg-btn:disabled {
            border-color: #222;
            color: #444;
            cursor: not-allowed;
        }

        /* Tier Selector */
        .tier-selector {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        .tier-option {
            flex: 1;
            position: relative;
        }
        .tier-option input {
            position: absolute;
            opacity: 0;
        }
        .tier-option label {
            display: block;
            padding: 0.625rem 0.5rem;
            background: #1a1a1a;
            border: 2px solid #333;
            border-radius: 4px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        .tier-option input:checked + label {
            border-color: #4a9eff;
            background: #1a2a3a;
        }
        .tier-option label:hover {
            border-color: #555;
        }
        .tier-name {
            font-weight: 600;
            font-size: 0.8rem;
        }
        .tier-desc {
            font-size: 0.65rem;
            color: #888;
        }

        /* Submit Button */
        .submit-btn {
            width: 100%;
            padding: 1rem;
            background: #4a9eff;
            border: none;
            border-radius: 4px;
            color: #000;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }
        .submit-btn:hover { background: #3a8eef; }
        .submit-btn:disabled {
            background: #333;
            color: #666;
            cursor: not-allowed;
        }

        /* Results Section */
        .results-section {
            background: #111;
            padding: 1.25rem;
            border-radius: 8px;
        }
        .results-placeholder {
            text-align: center;
            color: #555;
            padding: 3rem 1rem;
        }
        .results-placeholder p {
            margin-bottom: 0.5rem;
        }

        /* Grade Display */
        .grade-display {
            text-align: center;
            padding: 1.5rem;
            background: #1a1a1a;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        .grade-label {
            font-size: 0.75rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }
        .grade-value {
            font-size: 3rem;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 0.5rem;
        }
        .grade-value.low { color: #4ade80; }
        .grade-value.medium { color: #fbbf24; }
        .grade-value.high { color: #f97316; }
        .grade-value.critical { color: #ef4444; }
        .grade-bucket {
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        /* Verdict */
        .verdict-panel {
            background: #1a1a1a;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .verdict-panel h3 {
            font-size: 0.75rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }
        .verdict-text {
            font-size: 1rem;
            line-height: 1.5;
        }
        .action-accept { color: #4ade80; }
        .action-reduce { color: #fbbf24; }
        .action-avoid { color: #ef4444; }

        /* Insights Panel */
        .insights-panel {
            background: #1a1a1a;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .insights-panel h3 {
            font-size: 0.75rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.75rem;
        }
        .insight-item {
            padding: 0.5rem 0;
            border-bottom: 1px solid #333;
            font-size: 0.875rem;
        }
        .insight-item:last-child { border-bottom: none; }

        /* Locked Content */
        .locked-panel {
            position: relative;
            overflow: hidden;
        }
        .locked-panel .locked-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(10, 10, 10, 0.8);
            backdrop-filter: blur(4px);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 10;
        }
        .locked-icon {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }
        .locked-text {
            font-size: 0.75rem;
            color: #888;
        }

        /* Decision Summary (Always shown) */
        .decision-summary {
            background: linear-gradient(135deg, #1a2a3a 0%, #1a1a2a 100%);
            border: 1px solid #2a3a4a;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .decision-summary h3 {
            font-size: 0.7rem;
            color: #4a9eff;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.75rem;
        }
        .decision-verdict {
            font-size: 1rem;
            line-height: 1.4;
            margin-bottom: 0.75rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid #2a3a4a;
        }
        .decision-bullets {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .decision-bullets li {
            font-size: 0.8rem;
            padding: 0.35rem 0;
            padding-left: 1.25rem;
            position: relative;
            color: #bbb;
        }
        .decision-bullets li::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0.65rem;
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }
        .bullet-risk::before { background: #ef4444; }
        .bullet-improve::before { background: #4ade80; }
        .bullet-unknown::before { background: #888; }

        /* Why Section */
        .why-section {
            margin-bottom: 1rem;
        }
        .why-section-title {
            font-size: 0.7rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }
        .why-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
        }
        @media (max-width: 500px) {
            .why-grid { grid-template-columns: 1fr; }
        }
        .why-panel {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 0.75rem;
            min-height: 80px;
        }
        .why-panel h4 {
            font-size: 0.7rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .why-panel h4 .icon {
            font-size: 0.9rem;
        }
        .why-panel-content {
            font-size: 0.8rem;
            line-height: 1.4;
            color: #ccc;
        }
        .why-panel-content .metric {
            font-weight: 600;
            color: #fff;
        }
        .why-panel-content .detail {
            color: #888;
            font-size: 0.75rem;
        }

        /* Alerts (BEST only) */
        .alerts-panel {
            background: #2a1a1a;
            border: 1px solid #4a2a2a;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .alerts-panel h3 {
            font-size: 0.75rem;
            color: #ef4444;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.75rem;
        }
        .alert-item {
            font-size: 0.875rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid #4a2a2a;
        }
        .alert-item:last-child { border-bottom: none; }

        /* Error Panel */
        .error-panel {
            background: #2a1a1a;
            border: 1px solid #ff4a4a;
            border-radius: 6px;
            padding: 1rem;
        }
        .error-panel h3 {
            color: #ff4a4a;
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }
        .error-text {
            font-size: 0.875rem;
            color: #e0e0e0;
        }

        /* Hidden utility */
        .hidden { display: none !important; }

        /* Context Panel Styles (Sprint 3) */
        .context-panel {
            border: 1px solid #2a5a2a;
            background: #0a1a0a;
        }
        .context-panel h3 {
            color: #4a9e4a;
        }
        .context-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #333;
        }
        .context-source {
            font-size: 0.75rem;
            color: #888;
        }
        .context-summary {
            background: #1a2a1a;
            padding: 0.75rem;
            border-radius: 4px;
            margin-bottom: 0.75rem;
            font-size: 0.9rem;
        }
        .context-modifiers {
            list-style: none;
            padding: 0;
            margin: 0;
        }
        .context-modifier {
            padding: 0.5rem;
            margin-bottom: 0.5rem;
            background: #1a1a1a;
            border-radius: 4px;
            border-left: 3px solid #666;
        }
        .context-modifier.negative {
            border-left-color: #e74c3c;
        }
        .context-modifier.positive {
            border-left-color: #2ecc71;
        }
        .context-modifier-reason {
            font-size: 0.85rem;
        }
        .context-modifier-adjustment {
            font-size: 0.75rem;
            color: #888;
            margin-top: 0.25rem;
        }
        .context-missing {
            font-size: 0.8rem;
            color: #f39c12;
            margin-top: 0.5rem;
            padding: 0.5rem;
            background: #2a2a1a;
            border-radius: 4px;
        }
        .context-entities {
            font-size: 0.75rem;
            color: #888;
            margin-top: 0.5rem;
        }

        /* Alerts Feed Styles (Sprint 4) */
        .alerts-feed {
            border: 1px solid #e74c3c;
            background: #1a0a0a;
            margin-bottom: 1rem;
        }
        .alerts-feed h3 {
            color: #e74c3c;
        }
        .alerts-feed.locked {
            border-color: #444;
            background: #1a1a1a;
        }
        .alerts-feed.locked h3 {
            color: #666;
        }
        .alert-item {
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            background: #1a1a1a;
            border-radius: 4px;
            border-left: 3px solid #e74c3c;
        }
        .alert-item.warning {
            border-left-color: #f39c12;
        }
        .alert-item.info {
            border-left-color: #3498db;
        }
        .alert-title {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
        .alert-message {
            font-size: 0.85rem;
            color: #aaa;
        }
        .alert-meta {
            font-size: 0.75rem;
            color: #666;
            margin-top: 0.5rem;
        }
        .alerts-empty {
            color: #666;
            font-style: italic;
            padding: 0.5rem;
        }
        .alerts-locked-message {
            color: #888;
            font-size: 0.9rem;
            padding: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Leading Light</h1>
            <a href="/">Back to Home</a>
        </header>

        <div class="main-grid">
            <!-- Builder Section -->
            <div class="builder-section">
                <div class="section-header">
                    <span class="section-title">Parlay Builder</span>
                    <span class="leg-count" id="leg-count">2 legs</span>
                </div>

                <div class="sport-selector">
                    <select id="sport-select">
                        <option value="basketball" selected>Basketball (NBA)</option>
                    </select>
                </div>

                <div class="legs-container" id="legs-container">
                    <!-- Legs will be dynamically added here -->
                </div>

                <button type="button" class="add-leg-btn" id="add-leg-btn">+ Add Leg</button>

                <div class="tier-selector">
                    <div class="tier-option">
                        <input type="radio" name="tier" id="tier-good" value="good" checked>
                        <label for="tier-good">
                            <div class="tier-name">GOOD</div>
                            <div class="tier-desc">Grade + Verdict</div>
                        </label>
                    </div>
                    <div class="tier-option">
                        <input type="radio" name="tier" id="tier-better" value="better">
                        <label for="tier-better">
                            <div class="tier-name">BETTER</div>
                            <div class="tier-desc">+ Insights</div>
                        </label>
                    </div>
                    <div class="tier-option">
                        <input type="radio" name="tier" id="tier-best" value="best">
                        <label for="tier-best">
                            <div class="tier-name">BEST</div>
                            <div class="tier-desc">+ Full Analysis</div>
                        </label>
                    </div>
                </div>

                <button type="button" class="submit-btn" id="submit-btn" disabled>
                    Evaluate Parlay
                </button>
            </div>

            <!-- Results Section -->
            <div class="results-section">
                <div class="section-header">
                    <span class="section-title">Results</span>
                </div>

                <!-- Alerts Feed (Sprint 4 - BEST only) -->
                <div class="why-panel alerts-feed hidden" id="alerts-feed">
                    <h3><span class="icon">&#128276;</span> Live Alerts</h3>
                    <div id="alerts-content"></div>
                </div>

                <div id="results-placeholder" class="results-placeholder">
                    <p>Build your parlay and click Evaluate</p>
                    <p style="font-size: 0.75rem;">Minimum 2 legs required</p>
                </div>

                <div id="results-content" class="hidden">
                    <!-- Grade Display -->
                    <div class="grade-display" id="grade-display">
                        <div class="grade-label">Fragility Score</div>
                        <div class="grade-value" id="grade-value">--</div>
                        <div class="grade-bucket" id="grade-bucket">--</div>
                    </div>

                    <!-- Decision Summary (Always shown) -->
                    <div class="decision-summary" id="decision-summary">
                        <h3>Decision Summary</h3>
                        <div class="decision-verdict" id="decision-verdict"></div>
                        <ul class="decision-bullets">
                            <li class="bullet-risk" id="bullet-risk"></li>
                            <li class="bullet-improve" id="bullet-improve"></li>
                            <li class="bullet-unknown" id="bullet-unknown"></li>
                        </ul>
                    </div>

                    <!-- Why Section (Tier-gated) -->
                    <div class="why-section" id="why-section">
                        <div class="why-section-title">Why This Score?</div>
                        <div class="why-grid">
                            <!-- Structure Panel -->
                            <div class="why-panel" id="why-structure">
                                <h4><span class="icon">&#9881;</span> Structure</h4>
                                <div class="why-panel-content" id="structure-content"></div>
                                <div class="locked-overlay hidden" id="structure-locked">
                                    <span class="locked-icon">&#128274;</span>
                                </div>
                            </div>
                            <!-- Correlation Panel -->
                            <div class="why-panel" id="why-correlation">
                                <h4><span class="icon">&#128279;</span> Correlation</h4>
                                <div class="why-panel-content" id="correlation-content"></div>
                                <div class="locked-overlay hidden" id="correlation-locked">
                                    <span class="locked-icon">&#128274;</span>
                                </div>
                            </div>
                            <!-- Fragility Panel -->
                            <div class="why-panel" id="why-fragility">
                                <h4><span class="icon">&#9888;</span> Fragility</h4>
                                <div class="why-panel-content" id="fragility-content"></div>
                                <div class="locked-overlay hidden" id="fragility-locked">
                                    <span class="locked-icon">&#128274;</span>
                                </div>
                            </div>
                            <!-- Confidence Panel -->
                            <div class="why-panel" id="why-confidence">
                                <h4><span class="icon">&#128269;</span> Confidence</h4>
                                <div class="why-panel-content" id="confidence-content"></div>
                                <div class="locked-overlay hidden" id="confidence-locked">
                                    <span class="locked-icon">&#128274;</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Alerts (BEST only) -->
                    <div class="alerts-panel hidden" id="alerts-panel">
                        <h3>Alerts</h3>
                        <div id="alerts-content"></div>
                    </div>

                    <!-- Recommendation (BEST only) -->
                    <div class="insights-panel hidden" id="recommendation-panel">
                        <h3>Recommended Action</h3>
                        <div id="recommendation-content"></div>
                    </div>

                    <!-- Context Panel (Sprint 3) -->
                    <div class="why-panel context-panel hidden" id="context-panel">
                        <h3><span class="icon">&#128200;</span> Player Availability</h3>
                        <div id="context-content"></div>
                    </div>
                </div>

                <div id="error-panel" class="error-panel hidden">
                    <h3>Error</h3>
                    <div class="error-text" id="error-text"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        (function() {
            // State
            let legs = [];
            const MIN_LEGS = 2;
            const MAX_LEGS = 6;

            // Elements
            const legsContainer = document.getElementById('legs-container');
            const addLegBtn = document.getElementById('add-leg-btn');
            const submitBtn = document.getElementById('submit-btn');
            const legCountDisplay = document.getElementById('leg-count');
            const resultsPlaceholder = document.getElementById('results-placeholder');
            const resultsContent = document.getElementById('results-content');
            const errorPanel = document.getElementById('error-panel');

            // Market types
            const MARKETS = [
                { value: 'spread', label: 'Spread' },
                { value: 'ml', label: 'Moneyline' },
                { value: 'total', label: 'Total (O/U)' },
                { value: 'player_prop', label: 'Player Prop' }
            ];

            // Initialize with 2 legs
            function init() {
                addLeg();
                addLeg();
                updateUI();
            }

            function createLegHTML(index) {
                const marketOptions = MARKETS.map(m =>
                    '<option value="' + m.value + '">' + m.label + '</option>'
                ).join('');

                return '<div class="leg-card" data-index="' + index + '">' +
                    '<div class="leg-header">' +
                        '<span class="leg-number">Leg ' + (index + 1) + '</span>' +
                        '<button type="button" class="remove-leg" data-index="' + index + '">&times;</button>' +
                    '</div>' +
                    '<div class="leg-fields">' +
                        '<div class="leg-field full-width">' +
                            '<label>Team / Player</label>' +
                            '<input type="text" class="leg-selection" data-index="' + index + '" placeholder="e.g., Lakers or LeBron James">' +
                        '</div>' +
                        '<div class="leg-field">' +
                            '<label>Market</label>' +
                            '<select class="leg-market" data-index="' + index + '">' + marketOptions + '</select>' +
                        '</div>' +
                        '<div class="leg-field">' +
                            '<label>Line / Condition</label>' +
                            '<input type="text" class="leg-line" data-index="' + index + '" placeholder="e.g., -5.5 or O 220.5">' +
                        '</div>' +
                        '<div class="leg-field">' +
                            '<label>Odds</label>' +
                            '<input type="text" class="leg-odds" data-index="' + index + '" placeholder="e.g., -110">' +
                        '</div>' +
                    '</div>' +
                '</div>';
            }

            function addLeg() {
                if (legs.length >= MAX_LEGS) return;
                legs.push({ selection: '', market: 'spread', line: '', odds: '' });
                renderLegs();
                updateUI();
            }

            function removeLeg(index) {
                if (legs.length <= MIN_LEGS) return;
                legs.splice(index, 1);
                renderLegs();
                updateUI();
            }

            function renderLegs() {
                legsContainer.innerHTML = legs.map((_, i) => createLegHTML(i)).join('');
                attachLegListeners();
                // Restore values
                legs.forEach((leg, i) => {
                    const card = legsContainer.querySelector('[data-index="' + i + '"]');
                    if (card) {
                        const selInput = card.querySelector('.leg-selection');
                        const mktSelect = card.querySelector('.leg-market');
                        const lineInput = card.querySelector('.leg-line');
                        const oddsInput = card.querySelector('.leg-odds');
                        if (selInput) selInput.value = leg.selection;
                        if (mktSelect) mktSelect.value = leg.market;
                        if (lineInput) lineInput.value = leg.line;
                        if (oddsInput) oddsInput.value = leg.odds;
                    }
                });
            }

            function attachLegListeners() {
                // Remove buttons
                legsContainer.querySelectorAll('.remove-leg').forEach(btn => {
                    btn.addEventListener('click', function() {
                        removeLeg(parseInt(this.dataset.index));
                    });
                });
                // Input changes
                legsContainer.querySelectorAll('.leg-selection').forEach(input => {
                    input.addEventListener('input', function() {
                        legs[parseInt(this.dataset.index)].selection = this.value;
                        updateUI();
                    });
                });
                legsContainer.querySelectorAll('.leg-market').forEach(select => {
                    select.addEventListener('change', function() {
                        legs[parseInt(this.dataset.index)].market = this.value;
                    });
                });
                legsContainer.querySelectorAll('.leg-line').forEach(input => {
                    input.addEventListener('input', function() {
                        legs[parseInt(this.dataset.index)].line = this.value;
                    });
                });
                legsContainer.querySelectorAll('.leg-odds').forEach(input => {
                    input.addEventListener('input', function() {
                        legs[parseInt(this.dataset.index)].odds = this.value;
                    });
                });
            }

            function updateUI() {
                // Leg count
                legCountDisplay.textContent = legs.length + ' leg' + (legs.length !== 1 ? 's' : '');

                // Add button state
                addLegBtn.disabled = legs.length >= MAX_LEGS;

                // Remove button state
                legsContainer.querySelectorAll('.remove-leg').forEach(btn => {
                    btn.disabled = legs.length <= MIN_LEGS;
                });

                // Submit button - require at least selection for each leg
                const validLegs = legs.filter(leg => leg.selection.trim().length > 0);
                submitBtn.disabled = validLegs.length < MIN_LEGS;
            }

            function getSelectedTier() {
                const selected = document.querySelector('input[name="tier"]:checked');
                return selected ? selected.value : 'good';
            }

            function buildBetText() {
                // Convert structured legs to text format for existing endpoint
                const parts = legs.map(leg => {
                    let text = leg.selection.trim();
                    if (leg.line.trim()) {
                        text += ' ' + leg.line.trim();
                    }
                    if (leg.market === 'ml') {
                        text += ' ML';
                    } else if (leg.market === 'player_prop') {
                        text += ' prop';
                    }
                    return text;
                }).filter(t => t.length > 0);

                return parts.join(' + ') + ' parlay';
            }

            function showError(message) {
                resultsPlaceholder.classList.add('hidden');
                resultsContent.classList.add('hidden');
                errorPanel.classList.remove('hidden');
                document.getElementById('error-text').textContent = message;
            }

            function showResults(data) {
                resultsPlaceholder.classList.add('hidden');
                errorPanel.classList.add('hidden');
                resultsContent.classList.remove('hidden');

                const tier = getSelectedTier();
                const evaluation = data.evaluation;
                const interpretation = data.interpretation;
                const explain = data.explain || {};
                const metrics = evaluation.metrics;

                // Grade display
                const fragility = interpretation.fragility;
                const gradeValue = document.getElementById('grade-value');
                const gradeBucket = document.getElementById('grade-bucket');
                gradeValue.textContent = Math.round(fragility.display_value);
                gradeBucket.textContent = fragility.bucket;
                gradeValue.className = 'grade-value ' + fragility.bucket;

                // ============================================================
                // DECISION SUMMARY (Always shown)
                // ============================================================
                const decisionVerdict = document.getElementById('decision-verdict');
                const action = evaluation.recommendation.action;
                const actionClass = 'action-' + action;
                decisionVerdict.innerHTML = '<span class="' + actionClass + '">' +
                    action.toUpperCase() + '</span>: ' +
                    escapeHtml(evaluation.recommendation.reason);

                // 3 Bullets: Risk, Improvement, Unknown
                const bulletRisk = document.getElementById('bullet-risk');
                const bulletImprove = document.getElementById('bullet-improve');
                const bulletUnknown = document.getElementById('bullet-unknown');

                // Biggest risk - derived from inductor level
                const riskMap = {
                    'stable': 'Low structural risk',
                    'loaded': 'Moderate complexity - multiple dependencies',
                    'tense': 'High correlation or fragility detected',
                    'critical': 'Extreme fragility - many failure points'
                };
                bulletRisk.textContent = 'Risk: ' + (riskMap[evaluation.inductor.level] || 'Structural analysis');

                // Best improvement
                bulletImprove.textContent = 'Improve: ' + escapeHtml(fragility.what_to_do);

                // Biggest unknown
                bulletUnknown.textContent = 'Unknown: No live injury/lineup data in this evaluation';

                // ============================================================
                // WHY PANELS (Tier-gated)
                // ============================================================
                const isLocked = (tier === 'good');
                const showDetail = (tier === 'best');

                // Structure Panel
                const structureContent = document.getElementById('structure-content');
                const structureLocked = document.getElementById('structure-locked');
                const whyStructure = document.getElementById('why-structure');

                if (isLocked) {
                    whyStructure.classList.add('locked-panel');
                    structureLocked.classList.remove('hidden');
                    structureContent.innerHTML = '<span style="color:#555">Locked</span>';
                } else {
                    whyStructure.classList.remove('locked-panel');
                    structureLocked.classList.add('hidden');
                    const legCount = legs.length;
                    const legPenalty = metrics.leg_penalty || 0;
                    let structureHtml = '<span class="metric">' + legCount + ' legs</span>';
                    if (showDetail) {
                        structureHtml += '<br><span class="detail">Leg penalty: +' + legPenalty.toFixed(1) + '</span>';
                        if (legCount >= 4) {
                            structureHtml += '<br><span class="detail">High concentration risk</span>';
                        }
                    } else {
                        structureHtml += '<br><span class="detail">Each leg adds risk</span>';
                    }
                    structureContent.innerHTML = structureHtml;
                }

                // Correlation Panel
                const correlationContent = document.getElementById('correlation-content');
                const correlationLocked = document.getElementById('correlation-locked');
                const whyCorrelation = document.getElementById('why-correlation');

                if (isLocked) {
                    whyCorrelation.classList.add('locked-panel');
                    correlationLocked.classList.remove('hidden');
                    correlationContent.innerHTML = '<span style="color:#555">Locked</span>';
                } else {
                    whyCorrelation.classList.remove('locked-panel');
                    correlationLocked.classList.add('hidden');
                    const corrCount = evaluation.correlations ? evaluation.correlations.length : 0;
                    const corrPenalty = metrics.correlation_penalty || 0;
                    const corrMult = metrics.correlation_multiplier || 1.0;
                    let corrHtml = '<span class="metric">' + corrCount + ' correlation' + (corrCount !== 1 ? 's' : '') + '</span>';
                    if (showDetail) {
                        corrHtml += '<br><span class="detail">Penalty: +' + corrPenalty.toFixed(1) + '</span>';
                        corrHtml += '<br><span class="detail">Multiplier: ' + corrMult.toFixed(2) + 'x</span>';
                    } else {
                        corrHtml += '<br><span class="detail">' + (corrCount > 0 ? 'Linked outcomes' : 'Independent legs') + '</span>';
                    }
                    correlationContent.innerHTML = corrHtml;
                }

                // Fragility Panel
                const fragilityContent = document.getElementById('fragility-content');
                const fragilityLocked = document.getElementById('fragility-locked');
                const whyFragility = document.getElementById('why-fragility');

                if (isLocked) {
                    whyFragility.classList.add('locked-panel');
                    fragilityLocked.classList.remove('hidden');
                    fragilityContent.innerHTML = '<span style="color:#555">Locked</span>';
                } else {
                    whyFragility.classList.remove('locked-panel');
                    fragilityLocked.classList.add('hidden');
                    const rawFrag = metrics.raw_fragility || 0;
                    const finalFrag = metrics.final_fragility || 0;
                    let fragHtml = '<span class="metric">' + fragility.bucket.toUpperCase() + '</span>';
                    if (showDetail) {
                        fragHtml += '<br><span class="detail">Base: ' + rawFrag.toFixed(1) + '</span>';
                        fragHtml += '<br><span class="detail">Final: ' + finalFrag.toFixed(1) + '</span>';
                    } else {
                        fragHtml += '<br><span class="detail">' + escapeHtml(fragility.meaning) + '</span>';
                    }
                    fragilityContent.innerHTML = fragHtml;
                }

                // Confidence Panel
                const confidenceContent = document.getElementById('confidence-content');
                const confidenceLocked = document.getElementById('confidence-locked');
                const whyConfidence = document.getElementById('why-confidence');

                if (isLocked) {
                    whyConfidence.classList.add('locked-panel');
                    confidenceLocked.classList.remove('hidden');
                    confidenceContent.innerHTML = '<span style="color:#555">Locked</span>';
                } else {
                    whyConfidence.classList.remove('locked-panel');
                    confidenceLocked.classList.add('hidden');
                    let confHtml = '<span class="metric">Structural Only</span>';
                    if (showDetail) {
                        confHtml += '<br><span class="detail">+ No live injury data</span>';
                        confHtml += '<br><span class="detail">+ No weather data</span>';
                        confHtml += '<br><span class="detail">+ No odds movement</span>';
                    } else {
                        confHtml += '<br><span class="detail">Context data not included</span>';
                    }
                    confidenceContent.innerHTML = confHtml;
                }

                // ============================================================
                // ALERTS (BEST only)
                // ============================================================
                const alertsPanel = document.getElementById('alerts-panel');
                const alertsContentEl = document.getElementById('alerts-content');
                if (tier === 'best' && explain.alerts && explain.alerts.length > 0) {
                    alertsPanel.classList.remove('hidden');
                    alertsContentEl.innerHTML = explain.alerts.map(a =>
                        '<div class="alert-item">' + escapeHtml(a) + '</div>'
                    ).join('');
                } else {
                    alertsPanel.classList.add('hidden');
                }

                // ============================================================
                // RECOMMENDATION (BEST only)
                // ============================================================
                const recommendationPanel = document.getElementById('recommendation-panel');
                const recommendationContent = document.getElementById('recommendation-content');
                if (tier === 'best' && explain.recommended_next_step) {
                    recommendationPanel.classList.remove('hidden');
                    recommendationContent.textContent = explain.recommended_next_step;
                } else {
                    recommendationPanel.classList.add('hidden');
                }

                // ============================================================
                // CONTEXT PANEL (Sprint 3)
                // ============================================================
                const contextPanel = document.getElementById('context-panel');
                const contextContent = document.getElementById('context-content');
                const context = data.context;

                if (context && context.impact) {
                    contextPanel.classList.remove('hidden');
                    let html = '';

                    // Header with source and timestamp
                    html += '<div class="context-header">';
                    html += '<span>NBA Player Availability</span>';
                    html += '<span class="context-source">Source: ' + escapeHtml(context.source) + '</span>';
                    html += '</div>';

                    // Summary
                    if (context.impact.summary) {
                        html += '<div class="context-summary">' + escapeHtml(context.impact.summary) + '</div>';
                    }

                    // Modifiers
                    if (context.impact.modifiers && context.impact.modifiers.length > 0) {
                        html += '<ul class="context-modifiers">';
                        context.impact.modifiers.forEach(function(mod) {
                            const modClass = mod.adjustment > 0 ? 'negative' : (mod.adjustment < 0 ? 'positive' : '');
                            html += '<li class="context-modifier ' + modClass + '">';
                            html += '<div class="context-modifier-reason">' + escapeHtml(mod.reason) + '</div>';
                            if (mod.adjustment !== 0) {
                                const sign = mod.adjustment > 0 ? '+' : '';
                                html += '<div class="context-modifier-adjustment">Fragility adjustment: ' + sign + mod.adjustment.toFixed(1) + '</div>';
                            }
                            if (mod.affected_players && mod.affected_players.length > 0) {
                                html += '<div class="context-modifier-adjustment">Players: ' + mod.affected_players.join(', ') + '</div>';
                            }
                            html += '</li>';
                        });
                        html += '</ul>';
                    }

                    // Missing data warnings
                    if (context.missing_data && context.missing_data.length > 0) {
                        html += '<div class="context-missing">';
                        html += '<strong>Missing data:</strong> ' + context.missing_data.join(', ');
                        html += '</div>';
                    }

                    // Entities found
                    if (context.entities_found) {
                        const players = context.entities_found.players || [];
                        const teams = context.entities_found.teams || [];
                        if (players.length > 0 || teams.length > 0) {
                            html += '<div class="context-entities">';
                            if (players.length > 0) {
                                html += 'Players detected: ' + players.join(', ');
                            }
                            if (teams.length > 0) {
                                html += (players.length > 0 ? ' | ' : '') + 'Teams: ' + teams.join(', ');
                            }
                            html += '</div>';
                        }
                    }

                    contextContent.innerHTML = html;
                } else {
                    contextPanel.classList.add('hidden');
                }

                // ============================================================
                // ALERTS FEED (Sprint 4 - BEST only)
                // ============================================================
                const alertsFeed = document.getElementById('alerts-feed');
                const alertsContent = document.getElementById('alerts-content');

                if (tier === 'best') {
                    // Fetch alerts for BEST tier
                    fetchAlerts(alertsFeed, alertsContent);
                } else {
                    alertsFeed.classList.add('hidden');
                }
            }

            async function fetchAlerts(alertsFeed, alertsContent) {
                const tier = getSelectedTier();

                try {
                    const response = await fetch('/app/alerts', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tier: tier, limit: 10 })
                    });

                    const data = await response.json();

                    if (data.tier_locked) {
                        alertsFeed.classList.add('locked');
                        alertsContent.innerHTML = '<div class="alerts-locked-message">Upgrade to BEST tier for live alerts</div>';
                        alertsFeed.classList.remove('hidden');
                        return;
                    }

                    alertsFeed.classList.remove('locked');

                    if (data.alerts && data.alerts.length > 0) {
                        let html = '';
                        data.alerts.forEach(function(alert) {
                            const severityClass = alert.severity === 'critical' ? '' :
                                                  alert.severity === 'warning' ? 'warning' : 'info';
                            html += '<div class="alert-item ' + severityClass + '">';
                            html += '<div class="alert-title">' + escapeHtml(alert.title) + '</div>';
                            html += '<div class="alert-message">' + escapeHtml(alert.message) + '</div>';

                            let meta = [];
                            if (alert.player_name) meta.push(alert.player_name);
                            if (alert.team) meta.push(alert.team);
                            const timestamp = new Date(alert.created_at).toLocaleTimeString();
                            meta.push(timestamp);

                            html += '<div class="alert-meta">' + meta.join(' | ') + '</div>';
                            html += '</div>';
                        });
                        alertsContent.innerHTML = html;
                        alertsFeed.classList.remove('hidden');
                    } else {
                        alertsContent.innerHTML = '<div class="alerts-empty">No active alerts</div>';
                        alertsFeed.classList.remove('hidden');
                    }

                } catch (err) {
                    console.error('Failed to fetch alerts:', err);
                    alertsFeed.classList.add('hidden');
                }
            }

            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }

            async function submitEvaluation() {
                const input = buildBetText();
                const tier = getSelectedTier();

                submitBtn.disabled = true;
                submitBtn.textContent = 'Evaluating...';

                try {
                    const response = await fetch('/app/evaluate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ input, tier })
                    });

                    const data = await response.json();

                    if (!response.ok) {
                        showError(data.detail || 'Evaluation failed');
                        return;
                    }

                    showResults(data);
                } catch (err) {
                    showError('Network error: ' + err.message);
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Evaluate Parlay';
                    updateUI();
                }
            }

            submitBtn.addEventListener('click', submitEvaluation);
            addLegBtn.addEventListener('click', addLeg);

            // Initialize
            init();
        })();
    </script>
</body>
</html>"""


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/", response_class=HTMLResponse)
async def landing_page():
    """
    Landing page with service info and navigation.

    Returns HTML with:
    - Service name
    - Link to /app
    - Link to /health
    - Current git_sha
    """
    return _get_landing_page_html()


@router.get("/app", response_class=HTMLResponse)
async def app_page():
    """
    Main application page with evaluation form.

    Returns HTML with:
    - Bet text textarea
    - Tier selector (GOOD, BETTER, BEST)
    - Submit button
    - Output panels for evaluation, explain, and errors
    """
    return _get_app_page_html()


@router.post("/app/evaluate")
async def evaluate_proxy(request: WebEvaluateRequest, raw_request: Request):
    """
    Server-side proxy for evaluation requests.

    This endpoint exists to:
    1. ALL input passes through Airlock for validation/normalization
    2. Ensure browser cannot bypass tier enforcement
    3. Provide a single boundary for auth/rate limiting
    4. Structured logging for traceability

    Rate limited: 10 requests/minute per IP, burst of 3.
    Includes request_id in all responses for debugging.
    """
    from app.routers.leading_light import is_leading_light_enabled
    from app.pipeline import run_evaluation

    # Start timing for latency measurement
    start_time = time.perf_counter()

    # Get correlation ID and client IP (before Airlock - needed for logging)
    request_id = get_request_id(raw_request) or "unknown"
    client_ip = get_client_ip(raw_request)

    # =========================================================================
    # AIRLOCK: Single source of truth for validation/normalization
    # All evaluation requests MUST pass through Airlock first
    # =========================================================================
    try:
        normalized = airlock_ingest(
            input_text=request.input,
            tier=request.tier,
        )
    except AirlockError as e:
        # Log validation failure (use raw input length for logging)
        raw_input_length = len(request.input) if request.input else 0
        latency_ms = (time.perf_counter() - start_time) * 1000
        _log_request(
            request_id=request_id,
            client_ip=client_ip,
            tier=request.tier or "unknown",
            input_length=raw_input_length,
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

    # Use normalized values from Airlock for pre-pipeline checks
    tier = normalized.tier.value  # For logging before pipeline runs
    input_length = normalized.input_length

    # Rate limiting check
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

    # Check feature flag
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
                "error": "Leading Light disabled",
                "detail": "The Leading Light feature is currently disabled.",
                "code": "SERVICE_DISABLED",
            },
        )

    try:
        # =====================================================================
        # PIPELINE: Single entry point for all evaluation
        # Route does NOT call core.evaluation directly
        # =====================================================================
        result = run_evaluation(normalized)

        # Log successful request
        latency_ms = (time.perf_counter() - start_time) * 1000
        _log_request(
            request_id=request_id,
            client_ip=client_ip,
            tier=result.tier,
            input_length=input_length,
            status_code=200,
            latency_ms=latency_ms,
        )

        # Build response with request_id for traceability
        eval_response = result.evaluation
        return {
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
        }

    except ValueError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        _log_request(
            request_id=request_id,
            client_ip=client_ip,
            tier=tier,
            input_length=input_length,
            status_code=400,
            latency_ms=latency_ms,
            error_type="VALIDATION_ERROR",
        )
        return JSONResponse(
            status_code=400,
            content={
                "request_id": request_id,
                "error": "Invalid input",
                "detail": str(e),
                "code": "VALIDATION_ERROR",
            },
        )
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
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": "Internal error",
                "detail": str(e),
                "code": "INTERNAL_ERROR",
            },
        )


# =============================================================================
# Alerts API (Sprint 4)
# =============================================================================


class AlertsRequest(BaseModel):
    """Request for alerts endpoint."""

    tier: str = Field(default="best", description="User tier (alerts are BEST only)")
    limit: int = Field(default=20, ge=1, le=100, description="Max alerts to return")
    correlation_id: Optional[str] = Field(default=None, description="Filter by session ID")


@router.post("/app/alerts")
async def get_alerts(request: AlertsRequest, raw_request: Request):
    """
    Get recent alerts for the user.

    BEST tier only - returns empty list for other tiers.
    Alerts are driven by NBA availability changes.

    Rate limited: shares limit with /app/evaluate.
    """
    from alerts.service import get_alert_service

    request_id = get_request_id(raw_request) or "unknown"
    client_ip = get_client_ip(raw_request)

    # Tier check - alerts are BEST only
    if request.tier.lower() != "best":
        return {
            "request_id": request_id,
            "alerts": [],
            "count": 0,
            "tier_locked": True,
            "message": "Alerts are available for BEST tier only",
        }

    # Rate limiting
    limiter = get_rate_limiter()
    allowed, retry_after = limiter.check(client_ip)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "request_id": request_id,
                "error": "rate_limited",
                "detail": f"Too many requests. Try again in {retry_after} seconds.",
                "retry_after": retry_after,
            },
        )

    try:
        service = get_alert_service()

        if request.correlation_id:
            alerts = service.get_alerts(
                correlation_id=request.correlation_id,
                limit=request.limit,
            )
        else:
            alerts = service.get_recent_alerts(limit=request.limit)

        return {
            "request_id": request_id,
            "alerts": [a.to_dict() for a in alerts],
            "count": len(alerts),
            "total_active": service.get_alert_count(),
            "tier_locked": False,
        }

    except Exception as e:
        _logger.error(f"Alerts endpoint error: {e}", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": "Internal error",
                "detail": str(e),
            },
        )
