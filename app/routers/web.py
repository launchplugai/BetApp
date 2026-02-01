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


class CanonicalLeg(BaseModel):
    """
    Ticket 27 Part A: Canonical leg representation.

    Each leg is represented exactly once with structured fields.
    This is the source of truth when present.
    """
    entity: str = Field(..., description="Team or player name")
    market: str = Field(..., description="Market type: moneyline, spread, total, player_prop")
    value: Optional[str] = Field(default=None, description="Line value (e.g., '-5.5', 'over 220')")
    raw: str = Field(..., description="Original text as entered")


class WebEvaluateRequest(BaseModel):
    """Request schema for web evaluation."""
    input: str = Field(..., description="Bet text input")
    tier: Optional[str] = Field(default=None, description="Plan tier: GOOD, BETTER, or BEST")
    # Ticket 27: Canonical legs array (optional for backwards compatibility)
    legs: Optional[List[CanonicalLeg]] = Field(
        default=None,
        description="Structured leg data from builder. When present, this is source of truth."
    )


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
        }}
        /* Ticket 32 Part B: Session Bar */
        .session-bar {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            margin-bottom: 16px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            font-size: 12px;
        }}
        .session-label {{
            color: var(--text-muted);
        }}
        .session-name-input {{
            flex: 1;
            padding: 4px 8px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--text);
            font-size: 12px;
            min-width: 0;
        }}
        .session-name-input:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        .session-name-input::placeholder {{
            color: var(--text-muted);
        }}
        .session-history {{
            color: var(--text-muted);
            white-space: nowrap;
            font-family: monospace;
        }}
        /* Ticket 32 Part D: Workbench Layout */
        .workbench {{
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .workbench-panel {{
            flex: 1;
        }}
        .workbench-panel-header {{
            padding: 8px 0;
            margin-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }}
        .workbench-panel-title {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--accent);
        }}
        .workbench-results .workbench-panel-title {{
            color: var(--green);
        }}
        /* Desktop: Side-by-side layout */
        @media (min-width: 768px) {{
            .workbench {{
                flex-direction: row;
                align-items: flex-start;
            }}
            .workbench-input {{
                flex: 0 0 45%;
                max-width: 45%;
                position: sticky;
                top: 16px;
            }}
            .workbench-results {{
                flex: 0 0 55%;
                max-width: 55%;
            }}
        }}
        /* Sticky action bar */
        .sticky-actions {{
            position: sticky;
            bottom: 0;
            background: var(--bg);
            padding: 12px 0;
            border-top: 1px solid var(--border);
            margin-top: 16px;
        }}
        @media (min-width: 768px) {{
            .sticky-actions {{
                position: static;
                border-top: none;
                margin-top: 16px;
            }}
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
        /* Ticket 32 Part C: Sherlock/DNA Analysis Badges */
        .analysis-badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 12px 0;
        }}
        .analysis-badge {{
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            font-size: 11px;
            cursor: help;
        }}
        .badge-icon {{
            font-size: 14px;
        }}
        .badge-text {{
            color: var(--text);
            font-weight: 500;
        }}
        .badge-qualifier {{
            color: var(--text-muted);
            font-size: 10px;
        }}
        .sherlock-badge {{
            border-left: 3px solid var(--accent);
        }}
        .dna-badge {{
            border-left: 3px solid var(--green);
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
        /* Ticket 25: Evaluated Parlay Receipt */
        .parlay-receipt {{
            background: var(--surface);
        }}
        .parlay-label {{
            font-size: 14px;
            font-weight: 500;
            color: var(--text);
            margin-bottom: 8px;
        }}
        .parlay-legs {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .parlay-legs li {{
            padding: 10px 8px;
            border-bottom: 1px solid var(--border);
            font-size: 13px;
            color: var(--text);
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }}
        .parlay-legs li:last-child {{
            border-bottom: none;
        }}
        .parlay-legs .leg-type {{
            font-size: 10px;
            color: var(--text-muted);
            margin-left: 8px;
            text-transform: uppercase;
        }}
        /* Ticket 35: Leg Controls in Results */
        .result-leg-num {{
            font-weight: 600;
            color: var(--text-muted);
            min-width: 20px;
            flex-shrink: 0;
        }}
        .result-leg-content {{
            flex: 1;
            min-width: 0;
        }}
        .result-leg-text {{
            word-break: break-word;
        }}
        .result-leg-controls {{
            display: flex;
            align-items: center;
            gap: 6px;
            flex-shrink: 0;
        }}
        .leg-lock-btn {{
            background: none;
            border: none;
            cursor: pointer;
            padding: 4px;
            font-size: 14px;
            color: var(--text-muted);
            border-radius: 4px;
            transition: all 0.15s ease;
        }}
        .leg-lock-btn:hover {{
            background: var(--surface);
            color: var(--text);
        }}
        .leg-lock-btn.locked {{
            color: var(--accent);
        }}
        .leg-lock-btn.locked:hover {{
            color: var(--accent);
            background: rgba(99, 102, 241, 0.1);
        }}
        .leg-remove-btn {{
            background: none;
            border: 1px solid var(--border);
            cursor: pointer;
            padding: 3px 8px;
            font-size: 11px;
            color: var(--text-muted);
            border-radius: 4px;
            transition: all 0.15s ease;
        }}
        .leg-remove-btn:hover {{
            background: rgba(239, 68, 68, 0.1);
            border-color: var(--red);
            color: var(--red);
        }}
        .leg-remove-btn:disabled {{
            opacity: 0.4;
            cursor: not-allowed;
        }}
        .leg-remove-btn:disabled:hover {{
            background: none;
            border-color: var(--border);
            color: var(--text-muted);
        }}
        .parlay-legs li.locked {{
            background: rgba(99, 102, 241, 0.05);
            border-left: 2px solid var(--accent);
            padding-left: 6px;
        }}
        /* Ticket 35: Re-evaluate Button */
        .reevaluate-btn {{
            background: var(--accent);
            border: none;
            color: white;
            padding: 12px 20px;
            border-radius: var(--radius);
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            flex: 1;
        }}
        .reevaluate-btn:hover {{
            opacity: 0.9;
        }}
        .reevaluate-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        .refine-actions-row {{
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .refine-hint {{
            font-size: 11px;
            color: var(--text-muted);
            text-align: center;
            margin-top: 4px;
        }}
        /* Ticket 26 Part A: Leg Interpretation */
        .leg-interpretation {{
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 4px;
            font-style: italic;
            padding-left: 0;
        }}
        /* Ticket 25: Notable Legs */
        .notable-legs-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .notable-leg {{
            padding: 10px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            margin-bottom: 8px;
        }}
        .notable-leg-text {{
            font-size: 13px;
            font-weight: 500;
            color: var(--text);
            margin-bottom: 4px;
        }}
        .notable-leg-reason {{
            font-size: 12px;
            color: var(--text-muted);
        }}
        /* Ticket 25: Final Verdict */
        .verdict-section {{
            background: var(--surface);
            border-left: 3px solid var(--accent);
        }}
        .verdict-text {{
            font-size: 14px;
            line-height: 1.6;
            color: var(--text);
            margin: 0;
        }}
        .verdict-section.tone-positive {{
            border-left-color: var(--green);
        }}
        .verdict-section.tone-mixed {{
            border-left-color: var(--yellow);
        }}
        .verdict-section.tone-cautious {{
            border-left-color: var(--red);
        }}
        /* Ticket 26 Part C: Gentle Guidance */
        .guidance-section {{
            margin-top: 12px;
            padding: 14px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
        }}
        .guidance-header {{
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 10px;
            font-weight: 500;
        }}
        .guidance-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .guidance-list li {{
            padding: 6px 0;
            font-size: 13px;
            color: var(--text);
            border-bottom: 1px dashed var(--border);
        }}
        .guidance-list li:last-child {{
            border-bottom: none;
        }}
        /* Ticket 27 Part D: Grounding Warnings */
        .grounding-warnings {{
            margin-top: 12px;
            padding: 10px 14px;
            background: var(--bg);
            border: 1px solid var(--yellow);
            border-left-width: 3px;
            border-radius: var(--radius);
        }}
        .grounding-warnings-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .grounding-warnings-list li {{
            font-size: 12px;
            color: var(--text-muted);
            padding: 3px 0;
            font-style: italic;
        }}
        /* Ticket 25: Action Buttons */
        .action-buttons {{
            display: none;
            gap: 8px;
            margin-top: 16px;
        }}
        .action-buttons.active {{
            display: flex;
        }}
        .refine-btn {{
            flex: 1;
            padding: 12px;
            background: var(--accent);
            border: none;
            border-radius: var(--radius);
            color: white;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s;
        }}
        .refine-btn:hover {{
            background: var(--accent-hover);
        }}
        .action-buttons .reset-btn {{
            flex: 1;
            display: block;
            margin-top: 0;
        }}
        /* Ticket 23: Parlay Builder Styles */
        .mode-toggle {{
            display: flex;
            gap: 4px;
            margin-bottom: 12px;
            background: var(--bg);
            border-radius: var(--radius);
            padding: 4px;
        }}
        .mode-btn {{
            flex: 1;
            padding: 8px;
            background: transparent;
            border: none;
            border-radius: 6px;
            color: var(--text-muted);
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .mode-btn.active {{
            background: var(--surface);
            color: var(--text);
        }}
        .builder-section {{
            display: none;
        }}
        .builder-section.active {{
            display: block;
        }}
        .paste-section {{
            display: none;
        }}
        .paste-section.active {{
            display: block;
        }}
        /* Ticket 32 Part A: Image Upload Styles */
        .image-upload-section {{
            margin: 16px 0;
            text-align: center;
        }}
        .image-upload-label {{
            cursor: pointer;
        }}
        .image-upload-btn {{
            display: inline-block;
            padding: 10px 16px;
            background: var(--surface);
            border: 1px dashed var(--border);
            border-radius: var(--radius);
            color: var(--text);
            font-size: 13px;
            transition: all 0.2s;
        }}
        .image-upload-btn:hover {{
            border-color: var(--accent);
            background: var(--surface-hover);
        }}
        .image-status {{
            margin-top: 8px;
            font-size: 12px;
            color: var(--text-muted);
        }}
        .image-status.loading {{
            color: var(--accent);
        }}
        .image-status.error {{
            color: var(--red);
        }}
        .ocr-result {{
            margin-top: 12px;
            text-align: left;
        }}
        .ocr-warning-banner {{
            display: flex;
            align-items: flex-start;
            gap: 8px;
            padding: 10px;
            margin-bottom: 10px;
            background: rgba(234, 179, 8, 0.1);
            border: 1px solid var(--yellow);
            border-radius: var(--radius);
        }}
        .ocr-warning-icon {{
            color: var(--yellow);
            font-size: 16px;
        }}
        .ocr-warning-text {{
            font-size: 12px;
            color: var(--text);
            line-height: 1.4;
        }}
        .ocr-result label {{
            display: block;
            font-size: 12px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}
        .ocr-result textarea {{
            width: 100%;
            min-height: 60px;
            padding: 8px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text);
            font-size: 12px;
            font-family: monospace;
            resize: vertical;
        }}
        .use-ocr-btn {{
            margin-top: 8px;
            padding: 8px 16px;
            background: var(--green);
            color: #000;
            border: none;
            border-radius: var(--radius);
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
        }}
        .use-ocr-btn:hover {{
            opacity: 0.9;
        }}
        .builder-row {{
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
        }}
        .builder-row > * {{
            flex: 1;
        }}
        .builder-select, .builder-input {{
            padding: 10px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text);
            font-size: 13px;
            font-family: inherit;
        }}
        .builder-select:focus, .builder-input:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        .builder-input::placeholder {{
            color: var(--text-muted);
        }}
        .builder-sign {{
            width: 60px;
            flex-shrink: 0;
            text-align: center;
            font-weight: 600;
        }}
        .builder-line-value {{
            flex: 1;
        }}
        #line-row {{
            display: none;
        }}
        #line-row.active {{
            display: flex;
        }}
        .add-leg-btn {{
            width: 100%;
            padding: 10px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            color: var(--text);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            margin-top: 8px;
            transition: all 0.15s;
        }}
        .add-leg-btn:hover {{
            background: var(--surface-hover);
            border-color: var(--accent);
        }}
        .legs-list {{
            margin-top: 12px;
        }}
        .leg-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            margin-bottom: 6px;
            font-size: 13px;
        }}
        .leg-item .leg-text {{
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .leg-item .leg-num {{
            color: var(--text-muted);
            font-size: 11px;
            min-width: 20px;
        }}
        .remove-leg-btn {{
            padding: 4px 8px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 4px;
            color: var(--red);
            font-size: 11px;
            cursor: pointer;
        }}
        .remove-leg-btn:hover {{
            background: rgba(239, 68, 68, 0.1);
        }}
        .builder-empty {{
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-size: 13px;
        }}
        .quick-chips {{
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
            margin-bottom: 12px;
        }}
        .quick-chip {{
            padding: 6px 10px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            color: var(--text-muted);
            font-size: 11px;
            cursor: pointer;
            transition: all 0.15s;
        }}
        .quick-chip:hover {{
            border-color: var(--accent);
            color: var(--text);
        }}
        .builder-warning {{
            font-size: 12px;
            color: var(--yellow);
            margin-top: 4px;
            display: none;
        }}
        .builder-warning.active {{
            display: block;
        }}
        /* Ticket 34: OCR Leg Clarity Indicators */
        .leg-clarity {{
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
            white-space: nowrap;
        }}
        .leg-clarity.clear {{
            background: rgba(34, 197, 94, 0.15);
            color: var(--green);
        }}
        .leg-clarity.review {{
            background: rgba(234, 179, 8, 0.15);
            color: var(--yellow);
        }}
        .leg-clarity.ambiguous {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--red);
        }}
        .leg-source-tag {{
            font-size: 10px;
            color: var(--text-muted);
            background: var(--surface);
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: auto;
        }}
        .leg-item.ocr-leg {{
            border-left: 2px solid var(--accent);
        }}
        .leg-item.ocr-leg.editable {{
            cursor: pointer;
        }}
        .leg-item.ocr-leg.editable:hover {{
            background: var(--surface);
        }}
        .leg-item.editing {{
            flex-direction: column;
            align-items: stretch;
            gap: 8px;
        }}
        .leg-edit-input {{
            flex: 1;
            padding: 8px;
            background: var(--bg);
            border: 1px solid var(--accent);
            border-radius: var(--radius);
            color: var(--text);
            font-size: 13px;
            font-family: inherit;
        }}
        .leg-edit-input:focus {{
            outline: none;
        }}
        .leg-edit-actions {{
            display: flex;
            gap: 6px;
        }}
        .leg-edit-btn {{
            padding: 4px 10px;
            font-size: 11px;
            border-radius: 4px;
            cursor: pointer;
        }}
        .leg-edit-save {{
            background: var(--accent);
            border: none;
            color: white;
        }}
        .leg-edit-cancel {{
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-muted);
        }}
        /* Ticket 34: OCR Info Box */
        .ocr-info-box {{
            display: none;
            margin: 12px 0;
            padding: 14px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-left: 3px solid var(--accent);
            border-radius: var(--radius);
        }}
        .ocr-info-box.active {{
            display: block;
        }}
        .ocr-info-title {{
            font-size: 13px;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 8px;
        }}
        .ocr-info-text {{
            font-size: 12px;
            color: var(--text-muted);
            line-height: 1.5;
        }}
        .ocr-info-text p {{
            margin: 4px 0;
        }}
        /* Ticket 34: OCR Review Soft Gate */
        .ocr-review-gate {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            padding: 16px;
        }}
        .ocr-review-gate.active {{
            display: flex;
        }}
        .ocr-review-gate-content {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 24px;
            max-width: 400px;
            width: 100%;
        }}
        .ocr-review-gate-title {{
            font-size: 15px;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 12px;
        }}
        .ocr-review-gate-message {{
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 20px;
            line-height: 1.5;
        }}
        .ocr-review-gate-actions {{
            display: flex;
            gap: 10px;
        }}
        .ocr-review-gate-btn {{
            flex: 1;
            padding: 10px;
            border-radius: var(--radius);
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
        }}
        .ocr-review-gate-btn.primary {{
            background: var(--accent);
            border: none;
            color: white;
        }}
        .ocr-review-gate-btn.secondary {{
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text);
        }}
        .leg-meta {{
            display: flex;
            align-items: center;
            gap: 6px;
            margin-left: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>DNA Bet Engine</h1>
            <span class="build-stamp">build: {git_sha}</span>
        </header>

        <!-- Ticket 32 Part B: Session Indicator -->
        <div class="session-bar" id="session-bar">
            <span class="session-label">Session:</span>
            <input type="text" id="session-name" class="session-name-input" placeholder="Name this session (optional)" maxlength="30">
            <span class="session-history" id="session-history">0 evaluations</span>
        </div>

        <!-- Ticket 32 Part D: Workbench Container -->
        <div class="workbench" id="workbench">
            <!-- Left Panel: Input/Builder -->
            <div class="workbench-panel workbench-input" id="workbench-input">
                <div class="workbench-panel-header">
                    <span class="workbench-panel-title">Build Your Parlay</span>
                </div>

        <div id="input-section" class="card">
            <!-- Ticket 23: Mode Toggle -->
            <div class="mode-toggle">
                <button class="mode-btn active" data-mode="builder">Builder</button>
                <button class="mode-btn" data-mode="paste">Paste Mode</button>
            </div>

            <!-- Ticket 23: Builder Section -->
            <div id="builder-section" class="builder-section active">
                <div class="quick-chips">
                    <button class="quick-chip" data-market="ML">+ Moneyline</button>
                    <button class="quick-chip" data-market="Spread">+ Spread</button>
                    <button class="quick-chip" data-market="Total">+ Over/Under</button>
                    <button class="quick-chip" data-market="Player Prop">+ Player Prop</button>
                </div>

                <div class="builder-row">
                    <select id="builder-sport" class="builder-select" aria-label="Sport">
                        <option value="">Sport</option>
                        <option value="NBA">NBA</option>
                        <option value="NFL">NFL</option>
                        <option value="MLB">MLB</option>
                        <option value="NCAA">NCAA</option>
                        <option value="Other">Other</option>
                    </select>
                    <select id="builder-market" class="builder-select" aria-label="Market Type">
                        <option value="">Market Type</option>
                        <option value="ML">Moneyline</option>
                        <option value="Spread">Spread</option>
                        <option value="Total">Over/Under</option>
                        <option value="Player Prop">Player Prop</option>
                    </select>
                </div>

                <div class="builder-row">
                    <input type="text" id="builder-team" class="builder-input" placeholder="Team or Player" aria-label="Team or Player">
                </div>

                <div class="builder-row" id="line-row">
                    <select id="builder-sign" class="builder-select builder-sign" aria-label="Line Sign">
                        <option value="-">-</option>
                        <option value="+">+</option>
                    </select>
                    <select id="builder-line" class="builder-select builder-line-value" aria-label="Line Value">
                        <option value="">Value</option>
                        <option value="0.5">0.5</option>
                        <option value="1">1</option>
                        <option value="1.5">1.5</option>
                        <option value="2">2</option>
                        <option value="2.5">2.5</option>
                        <option value="3">3</option>
                        <option value="3.5">3.5</option>
                        <option value="4">4</option>
                        <option value="4.5">4.5</option>
                        <option value="5">5</option>
                        <option value="5.5">5.5</option>
                        <option value="6">6</option>
                        <option value="6.5">6.5</option>
                        <option value="7">7</option>
                        <option value="7.5">7.5</option>
                        <option value="8">8</option>
                        <option value="8.5">8.5</option>
                        <option value="9">9</option>
                        <option value="9.5">9.5</option>
                        <option value="10">10</option>
                        <option value="10.5">10.5</option>
                        <option value="11">11</option>
                        <option value="11.5">11.5</option>
                        <option value="12">12</option>
                        <option value="12.5">12.5</option>
                        <option value="13">13</option>
                        <option value="13.5">13.5</option>
                        <option value="14">14</option>
                        <option value="14.5">14.5</option>
                        <option value="15">15</option>
                        <option value="16">16</option>
                        <option value="17">17</option>
                        <option value="17.5">17.5</option>
                        <option value="18">18</option>
                        <option value="19">19</option>
                        <option value="20">20</option>
                        <option value="20.5">20.5</option>
                        <option value="21">21</option>
                        <option value="22">22</option>
                        <option value="23">23</option>
                        <option value="24">24</option>
                        <option value="25">25</option>
                        <option value="25.5">25.5</option>
                        <option value="26">26</option>
                        <option value="27">27</option>
                        <option value="28">28</option>
                        <option value="29">29</option>
                        <option value="30">30</option>
                        <option value="35">35</option>
                        <option value="40">40</option>
                        <option value="45">45</option>
                        <option value="50">50</option>
                        <option value="50.5">50.5</option>
                    </select>
                </div>

                <div id="builder-warning" class="builder-warning"></div>

                <button id="add-leg-btn" class="add-leg-btn">Add Leg</button>

                <div id="legs-list" class="legs-list">
                    <div id="legs-empty" class="builder-empty">No legs added yet. Build your parlay above.</div>
                </div>
            </div>

            <!-- Ticket 23: Paste Section (Advanced Mode) -->
            <div id="paste-section" class="paste-section">
                <label for="bet-input">Paste or type your bet slip</label>
                <textarea
                    id="bet-input"
                    placeholder="Lakers -5.5&#10;Celtics ML&#10;LeBron over 25.5 points"
                ></textarea>
            </div>

            <!-- Ticket 32 Part A: Image Upload Section -->
            <div id="image-upload-section" class="image-upload-section">
                <label class="image-upload-label">
                    <input type="file" id="image-input" accept="image/png,image/jpeg,image/jpg,image/webp" style="display:none">
                    <span class="image-upload-btn">&#128247; Upload Bet Slip Image</span>
                </label>
                <div id="image-status" class="image-status" style="display:none"></div>
                <div id="ocr-result" class="ocr-result" style="display:none">
                    <div class="ocr-warning-banner">
                        <span class="ocr-warning-icon">&#9888;</span>
                        <span class="ocr-warning-text">Image text extracted. Please review for accuracy before evaluating.</span>
                    </div>
                    <label for="ocr-text">Extracted Text:</label>
                    <textarea id="ocr-text" readonly></textarea>
                    <button id="use-ocr-text" class="use-ocr-btn">Add to Builder</button>
                </div>
            </div>

            <!-- Ticket 34 Part D: OCR Info Box -->
            <div id="ocr-info-box" class="ocr-info-box">
                <div class="ocr-info-title">How DNA reads bet slips</div>
                <div class="ocr-info-text">
                    <p>DNA analyzes bet structure, not odds or payouts.</p>
                    <p>Sportsbook parlays (including 6-leg slips) are normal.</p>
                    <p>Image text may require review before analysis.</p>
                </div>
            </div>

            <div class="tier-selector">
                <button class="tier-btn active" data-tier="good">GOOD</button>
                <button class="tier-btn" data-tier="better">BETTER</button>
                <button class="tier-btn" data-tier="best">BEST</button>
            </div>

            <button id="submit-btn" class="submit-btn">Evaluate Bet</button>
        </div>

            </div> <!-- End workbench-input panel -->

            <!-- Right Panel: Results/Analysis -->
            <div class="workbench-panel workbench-results" id="workbench-results">
                <div class="workbench-panel-header">
                    <span class="workbench-panel-title">Analysis Results</span>
                </div>

        <div id="loading" class="loading">
            <div class="spinner"></div>
            <div>Analyzing your bet...</div>
        </div>

        <div id="error-panel" class="error-panel"></div>

        <div id="results" class="results">
            <!-- Ticket 25: Evaluated Parlay Receipt -->
            <div id="parlay-receipt" class="card parlay-receipt">
                <div class="section-title">Evaluated Parlay</div>
                <div id="parlay-label" class="parlay-label"></div>
                <ol id="parlay-legs" class="parlay-legs"></ol>
            </div>

            <div id="grade-panel" class="grade">
                <div id="grade-signal" class="grade-signal"></div>
                <div class="grade-info">
                    <h2 id="grade-title"></h2>
                    <p id="grade-subtitle"></p>
                </div>
            </div>

            <!-- Ticket 32 Part C: Sherlock/DNA Analysis Badges -->
            <div class="analysis-badges">
                <div class="analysis-badge sherlock-badge" title="Sherlock analyzes structural relationships between legs. It does NOT predict outcomes or calculate odds.">
                    <span class="badge-icon">&#128269;</span>
                    <span class="badge-text">Analyzed by Sherlock</span>
                    <span class="badge-qualifier">(Structural)</span>
                </div>
                <div class="analysis-badge dna-badge" title="DNA scores fragility and correlation risk based on bet structure. It does NOT factor in team strength, injuries, or live conditions.">
                    <span class="badge-icon">&#129516;</span>
                    <span class="badge-text">DNA Risk Model</span>
                    <span class="badge-qualifier">(Structural)</span>
                </div>
            </div>

            <div class="card">
                <div class="section-title">Key Risks</div>
                <ul id="risks-list" class="risks-list"></ul>
            </div>

            <!-- Ticket 25: Notable Legs -->
            <div id="notable-legs-section" class="card">
                <div class="section-title">Notable Legs</div>
                <ul id="notable-legs-list" class="notable-legs-list"></ul>
            </div>

            <div class="card">
                <div class="artifacts-header">
                    <div class="section-title">Artifacts</div>
                    <span id="artifact-count" class="artifact-count"></span>
                </div>
                <ul id="artifacts-list" class="artifacts-list"></ul>
            </div>

            <!-- Ticket 25: Final Verdict -->
            <div id="verdict-section" class="card verdict-section">
                <div class="section-title">Summary</div>
                <p id="verdict-text" class="verdict-text"></p>
            </div>

            <!-- Ticket 26 Part C: Gentle Guidance -->
            <div id="guidance-section" class="card guidance-section" style="display: none;">
                <div id="guidance-header" class="guidance-header"></div>
                <ul id="guidance-list" class="guidance-list"></ul>
            </div>

            <!-- Ticket 27 Part D: Grounding Warnings -->
            <div id="grounding-warnings" class="grounding-warnings" style="display: none;">
                <ul id="grounding-warnings-list" class="grounding-warnings-list"></ul>
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

        <!-- Ticket 25: Loop Signaling / Ticket 32 Part D: Sticky Action Bar -->
        <!-- Ticket 35: Added Re-evaluate for inline refinement -->
        <div id="action-buttons" class="action-buttons sticky-actions">
            <div class="refine-actions-row">
                <button id="reevaluate-btn" class="reevaluate-btn" onclick="reEvaluateParlay()">Re-evaluate</button>
                <button id="refine-btn" class="refine-btn" onclick="refineParlay()">Edit in Builder</button>
            </div>
            <button id="reset-btn" class="reset-btn" onclick="resetForm()">Evaluate Another</button>
            <div class="refine-hint">Remove or lock legs above, then re-evaluate</div>
        </div>

            </div> <!-- End workbench-results panel -->
        </div> <!-- End workbench container -->

        <!-- Ticket 34 Part C: OCR Review Soft Gate -->
        <div id="ocr-review-gate" class="ocr-review-gate">
            <div class="ocr-review-gate-content">
                <div class="ocr-review-gate-title">Review Detected Legs</div>
                <div class="ocr-review-gate-message">
                    Some detected legs may need review before analysis. You can edit them in the Builder or proceed anyway.
                </div>
                <div class="ocr-review-gate-actions">
                    <button id="gate-review-btn" class="ocr-review-gate-btn secondary">Review legs</button>
                    <button id="gate-proceed-btn" class="ocr-review-gate-btn primary">Evaluate anyway</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // State
        let selectedTier = 'good';
        let debugMode = new URLSearchParams(window.location.search).get('debug') === '1';
        let lastResponse = null;
        let currentMode = 'builder';
        let builderLegs = [];
        let hasOcrLegs = false; // Ticket 34: Track if legs came from OCR
        let pendingEvaluation = null; // Ticket 34: For soft gate flow
        let lockedLegIds = new Set(); // Ticket 37: Track locked legs by deterministic ID (was lockedLegIndices)
        let resultsLegs = []; // Ticket 35: Current legs in results view (for inline edits)
        let isReEvaluation = false; // Ticket 36: Track if current evaluation is a re-evaluation

        // ============================================================
        // Ticket 37: Deterministic Leg ID Generation
        // ============================================================

        /**
         * Ticket 37B: Get canonical string for leg hashing.
         */
        function getCanonicalLegString(leg) {{
            return [
                (leg.entity || '').toLowerCase().trim(),
                (leg.market || '').toLowerCase().trim(),
                (leg.value || '').toString().toLowerCase().trim(),
                (leg.sport || '').toLowerCase().trim()
            ].join('|');
        }}

        /**
         * Ticket 37B: djb2 hash algorithm (sync fallback).
         */
        function hashDjb2(str) {{
            let hash = 5381;
            for (let i = 0; i < str.length; i++) {{
                hash = ((hash << 5) + hash) + str.charCodeAt(i);
                hash = hash & hash;
            }}
            return 'leg_' + (hash >>> 0).toString(16).padStart(8, '0');
        }}

        /**
         * Ticket 37B: Generate leg_id using SHA-256 (WebCrypto) with djb2 fallback.
         * Uses first 16 hex chars of SHA-256 for 64 bits of entropy.
         */
        async function generateLegId(leg) {{
            const canonical = getCanonicalLegString(leg);

            // Try WebCrypto SHA-256 first
            if (typeof crypto !== 'undefined' && crypto.subtle) {{
                try {{
                    const encoder = new TextEncoder();
                    const data = encoder.encode(canonical);
                    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
                    const hashArray = Array.from(new Uint8Array(hashBuffer));
                    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
                    return 'leg_' + hashHex.substring(0, 16);
                }} catch (e) {{
                    // WebCrypto failed, fall through to djb2
                }}
            }}

            // Fallback to djb2 if WebCrypto unavailable
            return hashDjb2(canonical);
        }}

        /**
         * Ticket 37B: Synchronous leg_id generation (djb2 only).
         * Use async generateLegId() when possible for SHA-256.
         */
        function generateLegIdSync(leg) {{
            return hashDjb2(getCanonicalLegString(leg));
        }}

        // Elements
        const betInput = document.getElementById('bet-input');
        const submitBtn = document.getElementById('submit-btn');
        const loading = document.getElementById('loading');
        const errorPanel = document.getElementById('error-panel');
        const results = document.getElementById('results');
        const resetBtn = document.getElementById('reset-btn');
        const inputSection = document.getElementById('input-section');
        const builderSection = document.getElementById('builder-section');
        const pasteSection = document.getElementById('paste-section');
        const legsList = document.getElementById('legs-list');
        const legsEmpty = document.getElementById('legs-empty');
        const builderWarning = document.getElementById('builder-warning');

        // Ticket 32 Part A: Image Upload Elements
        const imageInput = document.getElementById('image-input');
        const imageStatus = document.getElementById('image-status');
        const ocrResult = document.getElementById('ocr-result');
        const ocrText = document.getElementById('ocr-text');
        const useOcrBtn = document.getElementById('use-ocr-text');

        // Ticket 34: OCR Info Box and Review Gate Elements
        const ocrInfoBox = document.getElementById('ocr-info-box');
        const ocrReviewGate = document.getElementById('ocr-review-gate');
        const gateReviewBtn = document.getElementById('gate-review-btn');
        const gateProceedBtn = document.getElementById('gate-proceed-btn');

        // ============================================================
        // Ticket 34 Part A: OCR → Canonical Leg Parsing
        // ============================================================

        /**
         * Parse OCR text into canonical leg objects.
         * Each line is treated as a potential leg.
         */
        function parseOcrToLegs(text) {{
            const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
            const legs = [];

            for (const line of lines) {{
                const leg = parseOcrLine(line);
                if (leg) {{
                    legs.push(leg);
                }}
            }}

            return legs;
        }}

        /**
         * Parse a single OCR line into a canonical leg object.
         */
        function parseOcrLine(line) {{
            const raw = line;
            let entity = '';
            let market = 'unknown';
            let value = null;
            let sport = null;

            // Normalize line for parsing
            const normalized = line.toLowerCase();

            // Detect sport (optional)
            if (/\\b(nba|basketball)\\b/i.test(line)) sport = 'NBA';
            else if (/\\b(nfl|football)\\b/i.test(line)) sport = 'NFL';
            else if (/\\b(mlb|baseball)\\b/i.test(line)) sport = 'MLB';
            else if (/\\b(ncaa|college)\\b/i.test(line)) sport = 'NCAA';

            // Detect market type and extract components
            // Moneyline patterns: "Lakers ML", "Lakers to win", "Lakers moneyline"
            if (/\\b(ml|moneyline|to win)\\b/i.test(line)) {{
                market = 'moneyline';
                entity = line.replace(/\\b(ml|moneyline|to win)\\b/gi, '').trim();
                entity = cleanEntityName(entity);
            }}
            // Spread patterns: "Lakers -5.5", "Lakers +3", "Lakers -5.5 spread"
            else if (/[+-]\\d+\\.?\\d*/i.test(line) && !/\\b(over|under|o\\/u|pts|points|rebounds|assists|3pt)\\b/i.test(line)) {{
                market = 'spread';
                const spreadMatch = line.match(/([+-]\\d+\\.?\\d*)/);
                if (spreadMatch) {{
                    value = spreadMatch[1];
                    entity = line.replace(/[+-]\\d+\\.?\\d*/g, '').replace(/\\bspread\\b/gi, '').trim();
                    entity = cleanEntityName(entity);
                }}
            }}
            // Total patterns: "over 220", "under 45.5", "Lakers o220", "Lakers u45"
            else if (/\\b(over|under|o\\/u)\\b/i.test(line) || /[ou]\\d+\\.?\\d*/i.test(line)) {{
                market = 'total';
                const overMatch = line.match(/\\b(over|o)\\s*(\\d+\\.?\\d*)/i);
                const underMatch = line.match(/\\b(under|u)\\s*(\\d+\\.?\\d*)/i);
                if (overMatch) {{
                    value = 'over ' + overMatch[2];
                    entity = line.replace(/\\b(over|o)\\s*\\d+\\.?\\d*/gi, '').trim();
                }} else if (underMatch) {{
                    value = 'under ' + underMatch[2];
                    entity = line.replace(/\\b(under|u)\\s*\\d+\\.?\\d*/gi, '').trim();
                }}
                entity = cleanEntityName(entity);
            }}
            // Player prop patterns: "LeBron over 25.5 pts", "Curry 5.5+ 3pt"
            else if (/\\b(pts|points|rebounds|assists|3pt|threes|steals|blocks)\\b/i.test(line)) {{
                market = 'player_prop';
                const propMatch = line.match(/(over|under)?\\s*(\\d+\\.?\\d*)\\s*(pts|points|rebounds|assists|3pt|threes|steals|blocks)/i);
                if (propMatch) {{
                    const direction = propMatch[1] ? propMatch[1].toLowerCase() : 'over';
                    value = direction + ' ' + propMatch[2] + ' ' + propMatch[3].toLowerCase();
                }}
                entity = line.replace(/(over|under)?\\s*\\d+\\.?\\d*\\s*(pts|points|rebounds|assists|3pt|threes|steals|blocks)/gi, '').trim();
                entity = cleanEntityName(entity);
            }}
            // If no pattern matched, use the whole line as entity with unknown market
            else {{
                entity = cleanEntityName(line);
            }}

            // Skip empty entities
            if (!entity || entity.length < 2) {{
                entity = line.split(/\\s+/)[0] || line;
            }}

            // Ticket 37: Generate deterministic leg_id
            const legData = {{ entity, market, value, sport }};
            const leg_id = generateLegIdSync(legData);

            return {{
                leg_id: leg_id,
                entity: entity,
                market: market,
                value: value,
                raw: raw,
                text: raw,
                sport: sport,
                source: 'ocr',
                clarity: getOcrLegClarity({{ entity, market, value, raw }})
            }};
        }}

        /**
         * Clean up entity name by removing common noise words.
         */
        function cleanEntityName(name) {{
            return name
                .replace(/\\b(nba|nfl|mlb|ncaa|college|basketball|football|baseball)\\b/gi, '')
                .replace(/\\b(game|match|vs|@|at)\\b/gi, '')
                .replace(/[,()]/g, '')
                .replace(/\\s+/g, ' ')
                .trim();
        }}

        // ============================================================
        // Ticket 34 Part B: Per-Leg Confidence Indicators
        // ============================================================

        /**
         * Determine clarity indicator for an OCR-derived leg.
         * Returns: 'clear', 'review', or 'ambiguous'
         */
        function getOcrLegClarity(leg) {{
            let score = 0;

            // Has recognized market type (+2)
            if (leg.market && leg.market !== 'unknown') {{
                score += 2;
            }}

            // Has clean entity name (+1)
            if (leg.entity && leg.entity.length >= 3 && /^[a-zA-Z\\s]+$/.test(leg.entity)) {{
                score += 1;
            }}

            // Has numeric value for spread/total/prop (+1)
            if (leg.value && /\\d/.test(leg.value)) {{
                score += 1;
            }}

            // Contains market keywords (+1)
            const marketKeywords = /(ml|moneyline|spread|over|under|pts|points|rebounds|assists)/i;
            if (marketKeywords.test(leg.raw)) {{
                score += 1;
            }}

            // Penalize if raw text is very short or has unusual characters
            if (leg.raw.length < 5) score -= 1;
            if (/[^a-zA-Z0-9\\s.+-]/g.test(leg.raw)) score -= 1;

            // Determine clarity level
            if (score >= 4) return 'clear';
            if (score >= 2) return 'review';
            return 'ambiguous';
        }}

        /**
         * Get clarity icon and label for display.
         */
        function getClarityDisplay(clarity) {{
            const displays = {{
                'clear': {{ icon: '&#10003;', label: 'Clear match', css: 'clear' }},
                'review': {{ icon: '&#9888;', label: 'Review recommended', css: 'review' }},
                'ambiguous': {{ icon: '?', label: 'Ambiguous', css: 'ambiguous' }}
            }};
            return displays[clarity] || displays['ambiguous'];
        }}

        /**
         * Check if any OCR legs need review (have review or ambiguous clarity).
         */
        function hasLegsNeedingReview() {{
            return builderLegs.some(leg =>
                leg.source === 'ocr' && (leg.clarity === 'review' || leg.clarity === 'ambiguous')
            );
        }}

        // Ticket 32 Part A: Image Upload Handler
        if (imageInput) {{
            imageInput.addEventListener('change', async (e) => {{
                const file = e.target.files[0];
                if (!file) return;

                // Validate file type
                if (!file.type.match(/^image\/(png|jpeg|jpg|webp)$/)) {{
                    imageStatus.textContent = 'Invalid file type. Use PNG, JPG, or WebP.';
                    imageStatus.className = 'image-status error';
                    imageStatus.style.display = 'block';
                    return;
                }}

                // Validate file size (max 5MB)
                if (file.size > 5 * 1024 * 1024) {{
                    imageStatus.textContent = 'File too large. Maximum 5MB.';
                    imageStatus.className = 'image-status error';
                    imageStatus.style.display = 'block';
                    return;
                }}

                // Show loading state
                imageStatus.textContent = 'Extracting text from image...';
                imageStatus.className = 'image-status loading';
                imageStatus.style.display = 'block';
                ocrResult.style.display = 'none';

                try {{
                    const formData = new FormData();
                    // Ticket 38A fix: Backend expects 'image' not 'file'
                    formData.append('image', file);

                    const response = await fetch('/leading-light/evaluate/image', {{
                        method: 'POST',
                        body: formData
                    }});

                    const data = await response.json();

                    if (!response.ok) {{
                        // Ticket 38A: Safely extract error message from response
                        throw new Error(safeResponseError(data, 'OCR extraction failed'));
                    }}

                    // Show extracted text with warning banner
                    const extractedText = data.extracted_text || data.image_parse?.extracted_text || '';
                    if (extractedText) {{
                        ocrText.value = extractedText;
                        ocrResult.style.display = 'block';
                        imageStatus.textContent = 'Text extracted successfully.';
                        imageStatus.className = 'image-status';
                    }} else {{
                        imageStatus.textContent = 'No text found in image.';
                        imageStatus.className = 'image-status error';
                    }}
                }} catch (err) {{
                    // Ticket 38A: Safe error string extraction
                    imageStatus.textContent = 'Error: ' + safeAnyToString(err, 'OCR extraction failed');
                    imageStatus.className = 'image-status error';
                }}
            }});
        }}

        // Ticket 34: Use OCR Text Button - Now populates Builder with parsed legs
        // Ticket 36: Reset refine loop state when importing OCR (fresh start)
        if (useOcrBtn) {{
            useOcrBtn.addEventListener('click', () => {{
                const extractedText = ocrText.value.trim();
                if (extractedText) {{
                    // Parse OCR text into canonical legs
                    const ocrLegs = parseOcrToLegs(extractedText);

                    if (ocrLegs.length > 0) {{
                        // Ticket 36/37: Clear refine loop state - this is a fresh start
                        lockedLegIds.clear();
                        resultsLegs = [];

                        // Replace builder legs with OCR-derived legs
                        builderLegs = ocrLegs;
                        hasOcrLegs = true;

                        // Switch to Builder mode (not Paste mode)
                        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                        document.querySelector('.mode-btn[data-mode="builder"]')?.classList.add('active');
                        builderSection.classList.add('active');
                        pasteSection.classList.remove('active');
                        currentMode = 'builder';

                        // Update UI
                        renderLegs();
                        syncTextarea();

                        // Show OCR info box (Part D)
                        if (ocrInfoBox) {{
                            ocrInfoBox.classList.add('active');
                        }}

                        // Hide the OCR result section since legs are now in builder
                        ocrResult.style.display = 'none';
                        imageStatus.textContent = ocrLegs.length + ' leg(s) added to Builder.';
                        imageStatus.className = 'image-status';
                    }} else {{
                        // Fallback: copy to textarea if parsing failed
                        betInput.value = extractedText;
                        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                        document.querySelector('.mode-btn[data-mode="paste"]')?.classList.add('active');
                        builderSection.classList.remove('active');
                        pasteSection.classList.add('active');
                        currentMode = 'paste';
                    }}
                }}
            }});
        }}

        // ============================================================
        // Ticket 32 Part B: Session Manager (localStorage)
        // ============================================================
        const SessionManager = {{
            STORAGE_KEY: 'dna_session',
            MAX_HISTORY: 5,

            // Get or create session
            getSession: function() {{
                try {{
                    const stored = localStorage.getItem(this.STORAGE_KEY);
                    if (stored) {{
                        return JSON.parse(stored);
                    }}
                }} catch (e) {{
                    console.warn('Session load failed:', e);
                }}

                // Create new session
                const session = {{
                    id: 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
                    name: '',
                    createdAt: new Date().toISOString(),
                    lastActivity: new Date().toISOString(),
                    evaluations: [],
                    refinementState: null
                }};
                this.saveSession(session);
                return session;
            }},

            // Save session
            saveSession: function(session) {{
                try {{
                    session.lastActivity = new Date().toISOString();
                    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(session));
                }} catch (e) {{
                    console.warn('Session save failed:', e);
                }}
            }},

            // Update session name
            setSessionName: function(name) {{
                const session = this.getSession();
                session.name = name || '';
                this.saveSession(session);
            }},

            // Add evaluation to history
            addEvaluation: function(evalData) {{
                const session = this.getSession();
                const entry = {{
                    id: 'eval_' + Date.now(),
                    timestamp: new Date().toISOString(),
                    input: evalData.input || '',
                    signal: evalData.signal || '',
                    grade: evalData.grade || '',
                    legCount: evalData.legCount || 0
                }};
                session.evaluations.unshift(entry);
                // Keep only last MAX_HISTORY
                session.evaluations = session.evaluations.slice(0, this.MAX_HISTORY);
                this.saveSession(session);
                return entry;
            }},

            // Get evaluation history
            getEvaluations: function() {{
                return this.getSession().evaluations || [];
            }},

            // Save refinement state
            saveRefinement: function(state) {{
                const session = this.getSession();
                session.refinementState = state;
                this.saveSession(session);
            }},

            // Get refinement state
            getRefinement: function() {{
                return this.getSession().refinementState;
            }},

            // Clear refinement state
            clearRefinement: function() {{
                const session = this.getSession();
                session.refinementState = null;
                this.saveSession(session);
            }},

            // Get session info for display
            getInfo: function() {{
                const session = this.getSession();
                return {{
                    id: session.id,
                    name: session.name,
                    evalCount: session.evaluations.length,
                    hasRefinement: !!session.refinementState
                }};
            }}
        }};

        // Export for testing
        window.SessionManager = SessionManager;

        // Initialize session UI
        const sessionNameInput = document.getElementById('session-name');
        const sessionHistorySpan = document.getElementById('session-history');

        function updateSessionUI() {{
            const info = SessionManager.getInfo();
            if (sessionNameInput) {{
                sessionNameInput.value = info.name || '';
            }}
            if (sessionHistorySpan) {{
                sessionHistorySpan.textContent = info.evalCount + ' evaluation' + (info.evalCount !== 1 ? 's' : '');
            }}
        }}

        // Initialize session display
        updateSessionUI();

        // Handle session name changes
        if (sessionNameInput) {{
            sessionNameInput.addEventListener('blur', () => {{
                SessionManager.setSessionName(sessionNameInput.value.trim());
            }});
            sessionNameInput.addEventListener('keydown', (e) => {{
                if (e.key === 'Enter') {{
                    sessionNameInput.blur();
                }}
            }});
        }}

        // Hook into results display to update session UI
        const originalShowResults = showResults;
        // Will be reassigned after showResults is defined

        // Ticket 23: Mode Toggle
        document.querySelectorAll('.mode-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentMode = btn.dataset.mode;
                if (currentMode === 'builder') {{
                    builderSection.classList.add('active');
                    pasteSection.classList.remove('active');
                }} else {{
                    builderSection.classList.remove('active');
                    pasteSection.classList.add('active');
                }}
            }});
        }});

        // Ticket 23: Quick Add Chips
        document.querySelectorAll('.quick-chip').forEach(chip => {{
            chip.addEventListener('click', () => {{
                const selectedMarket = chip.dataset.market;
                document.getElementById('builder-market').value = selectedMarket;
                updateLineRowVisibility(selectedMarket);
                document.getElementById('builder-team').focus();
            }});
        }});

        // Show/hide line row based on market type
        function updateLineRowVisibility(market) {{
            const lineRow = document.getElementById('line-row');
            if (market === 'Spread' || market === 'Total' || market === 'Player Prop') {{
                lineRow.classList.add('active');
            }} else {{
                lineRow.classList.remove('active');
            }}
        }}

        // Market dropdown change handler
        document.getElementById('builder-market').addEventListener('change', (e) => {{
            updateLineRowVisibility(e.target.value);
        }});

        // Ticket 23: Add Leg
        document.getElementById('add-leg-btn').addEventListener('click', addLeg);

        function addLeg() {{
            const market = document.getElementById('builder-market').value;
            const team = document.getElementById('builder-team').value.trim();
            const sign = document.getElementById('builder-sign').value;
            const lineValue = document.getElementById('builder-line').value;
            const sport = document.getElementById('builder-sport').value;

            // Build the full line (sign + value)
            let line = '';
            if (lineValue) {{
                line = sign + lineValue;
            }}

            // Validation
            if (!market) {{
                showBuilderWarning('Please select a market type');
                return;
            }}
            if (!team) {{
                showBuilderWarning('Please enter a team or player');
                return;
            }}
            // Line is encouraged for Spread/Total/Prop but not strictly required
            if ((market === 'Spread' || market === 'Total' || market === 'Player Prop') && !lineValue) {{
                showBuilderWarning('Line/value recommended for this market type');
                // Don't return - allow adding without line
            }}

            hideBuilderWarning();

            // Ticket 27: Map UI market to canonical market type
            const marketMap = {{
                'ML': 'moneyline',
                'Spread': 'spread',
                'Total': 'total',
                'Player Prop': 'player_prop'
            }};
            const canonicalMarket = marketMap[market] || 'unknown';

            // Build leg text (for display and textarea)
            let legText = team;
            let legValue = null;
            if (market === 'ML') {{
                legText += ' ML';
            }} else if (market === 'Spread') {{
                legText += ' ' + (line || '');
                legValue = line || null;
            }} else if (market === 'Total') {{
                // For totals, use "over" or "under" based on sign
                const overUnder = sign === '+' ? 'over' : 'under';
                const totalText = lineValue ? overUnder + ' ' + lineValue : '';
                legText += ' ' + totalText;
                legValue = totalText || null;
            }} else if (market === 'Player Prop') {{
                // For props, use "over" or "under" based on sign
                const overUnder = sign === '+' ? 'over' : 'under';
                const propText = lineValue ? overUnder + ' ' + lineValue : 'prop';
                legText += ' ' + propText;
                legValue = propText || null;
            }}
            legText = legText.trim();

            // Ticket 27 Part B: Add to legs array with canonical schema
            // Ticket 37: Include deterministic leg_id
            const legData = {{ entity: team, market: canonicalMarket, value: legValue, sport: sport }};
            const leg_id = generateLegIdSync(legData);

            builderLegs.push({{
                leg_id: leg_id,
                entity: team,
                market: canonicalMarket,
                value: legValue,
                raw: legText,
                // Keep display fields for UI
                text: legText,
                sport: sport,
            }});

            renderLegs();
            syncTextarea();
            clearBuilderInputs();
        }}

        function removeLeg(index) {{
            builderLegs.splice(index, 1);
            renderLegs();
            syncTextarea();
        }}

        function renderLegs() {{
            // Clear existing leg items (but keep empty message)
            legsList.querySelectorAll('.leg-item').forEach(el => el.remove());

            if (builderLegs.length === 0) {{
                legsEmpty.style.display = 'block';
            }} else {{
                legsEmpty.style.display = 'none';
                builderLegs.forEach((leg, i) => {{
                    const item = document.createElement('div');
                    const isOcr = leg.source === 'ocr';
                    item.className = 'leg-item' + (isOcr ? ' ocr-leg editable' : '');
                    item.dataset.index = i;

                    // Build leg HTML with OCR metadata if applicable
                    let legHtml = `<span class="leg-num">${{i + 1}}.</span>`;
                    legHtml += `<span class="leg-text">${{escapeHtml(leg.text)}}</span>`;

                    // Ticket 34: Add meta section for OCR legs
                    if (isOcr) {{
                        const clarityDisplay = getClarityDisplay(leg.clarity || 'review');
                        legHtml += `<div class="leg-meta">`;
                        legHtml += `<span class="leg-clarity ${{clarityDisplay.css}}">${{clarityDisplay.icon}} ${{clarityDisplay.label}}</span>`;
                        legHtml += `<span class="leg-source-tag">Detected from slip</span>`;
                        legHtml += `</div>`;
                    }}

                    legHtml += `<button class="remove-leg-btn" onclick="removeLeg(${{i}})">Remove</button>`;
                    item.innerHTML = legHtml;

                    // Ticket 34: Click to edit OCR legs
                    if (isOcr) {{
                        item.addEventListener('click', (e) => {{
                            // Don't trigger edit if clicking remove button
                            if (e.target.classList.contains('remove-leg-btn')) return;
                            startEditLeg(i);
                        }});
                    }}

                    legsList.appendChild(item);
                }});
            }}
        }}

        // Ticket 34: Edit leg functionality
        let editingLegIndex = null;

        function startEditLeg(index) {{
            // Don't start new edit if already editing
            if (editingLegIndex !== null) return;

            editingLegIndex = index;
            const leg = builderLegs[index];
            const item = legsList.querySelector(`.leg-item[data-index="${{index}}"]`);

            if (!item) return;

            // Replace content with edit form
            item.classList.add('editing');
            item.classList.remove('editable');
            item.innerHTML = `
                <div style="display:flex; align-items:center; gap:8px; width:100%;">
                    <span class="leg-num">${{index + 1}}.</span>
                    <input type="text" class="leg-edit-input" value="${{escapeHtml(leg.raw)}}" autofocus>
                </div>
                <div class="leg-edit-actions">
                    <button class="leg-edit-btn leg-edit-save">Save</button>
                    <button class="leg-edit-btn leg-edit-cancel">Cancel</button>
                </div>
            `;

            const input = item.querySelector('.leg-edit-input');
            const saveBtn = item.querySelector('.leg-edit-save');
            const cancelBtn = item.querySelector('.leg-edit-cancel');

            // Focus and select
            input.focus();
            input.select();

            // Prevent click from bubbling
            item.onclick = (e) => e.stopPropagation();

            // Save handler
            saveBtn.addEventListener('click', () => saveEditLeg(index, input.value));

            // Cancel handler
            cancelBtn.addEventListener('click', () => cancelEditLeg());

            // Enter to save, Escape to cancel
            input.addEventListener('keydown', (e) => {{
                if (e.key === 'Enter') {{
                    e.preventDefault();
                    saveEditLeg(index, input.value);
                }} else if (e.key === 'Escape') {{
                    cancelEditLeg();
                }}
            }});
        }}

        function saveEditLeg(index, newText) {{
            newText = newText.trim();
            if (newText) {{
                // Re-parse the edited text
                const newLeg = parseOcrLine(newText);
                // Mark as edited by user (upgrades clarity to clear since user reviewed it)
                newLeg.clarity = 'clear';
                builderLegs[index] = newLeg;
            }}
            editingLegIndex = null;
            renderLegs();
            syncTextarea();
        }}

        function cancelEditLeg() {{
            editingLegIndex = null;
            renderLegs();
        }}

        function syncTextarea() {{
            // Update textarea with current legs (single source of truth)
            betInput.value = builderLegs.map(l => l.text).join('\\n');
        }}

        function clearBuilderInputs() {{
            document.getElementById('builder-market').value = '';
            document.getElementById('builder-team').value = '';
            document.getElementById('builder-sign').value = '-';
            document.getElementById('builder-line').value = '';
            // Keep sport selected
            updateLineRowVisibility('');  // Hide line row when cleared
        }}

        function showBuilderWarning(msg) {{
            builderWarning.textContent = msg;
            builderWarning.classList.add('active');
        }}

        function hideBuilderWarning() {{
            builderWarning.classList.remove('active');
        }}

        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}

        /**
         * Ticket 38A: Safe error message extraction.
         * Handles Error objects, API error responses, and unknown objects.
         * Never returns "[object Object]".
         */
        function safeAnyToString(x, fallback) {{
            if (x === null || x === undefined) {{
                return fallback || 'Unknown error';
            }}
            if (typeof x === 'string') {{
                return x;
            }}
            // Error object
            if (x.message && typeof x.message === 'string') {{
                return x.message;
            }}
            // API error response shapes
            if (x.detail) {{
                // Pydantic validation errors have detail as array
                if (Array.isArray(x.detail)) {{
                    const msgs = x.detail.map(d => d.msg || d.message || JSON.stringify(d)).join('; ');
                    return msgs || fallback || 'Validation error';
                }}
                if (typeof x.detail === 'string') {{
                    return x.detail;
                }}
                // detail is object
                if (x.detail.msg) return x.detail.msg;
                if (x.detail.message) return x.detail.message;
            }}
            if (x.error && typeof x.error === 'string') {{
                return x.error;
            }}
            if (x.msg && typeof x.msg === 'string') {{
                return x.msg;
            }}
            // Custom toString (not Object.prototype.toString)
            if (typeof x.toString === 'function' && x.toString !== Object.prototype.toString) {{
                const str = x.toString();
                if (str !== '[object Object]') {{
                    return str;
                }}
            }}
            // Last resort: try JSON stringify (bounded length)
            try {{
                const json = JSON.stringify(x);
                if (json && json !== '{{}}' && json.length < 200) {{
                    return json;
                }}
            }} catch (e) {{
                // ignore stringify errors
            }}
            return fallback || 'Unknown error';
        }}

        /**
         * Ticket 38A: Extract error message from API response.
         * Use for response.json() results.
         */
        function safeResponseError(resJson, fallback) {{
            return safeAnyToString(resJson, fallback);
        }}

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
            // Always use textarea content as single source of truth
            const input = betInput.value.trim();
            if (!input) {{
                if (currentMode === 'builder' && builderLegs.length === 0) {{
                    showError('Please add at least one leg to your parlay');
                }} else {{
                    showError('Please enter a bet slip');
                }}
                return;
            }}

            // Ticket 34 Part C: Check if OCR legs need review
            if (hasOcrLegs && hasLegsNeedingReview()) {{
                // Store the evaluation intent and show soft gate
                pendingEvaluation = {{ input, tier: selectedTier }};
                showOcrReviewGate();
                return;
            }}

            // Ticket 36/37: This is a fresh evaluation, not a re-evaluation
            // Clear stale lock state to prevent state collision
            isReEvaluation = false;
            lockedLegIds.clear();

            // Proceed with evaluation
            await runEvaluation(input);
        }});

        // Ticket 34 Part C: Soft gate handlers
        if (gateReviewBtn) {{
            gateReviewBtn.addEventListener('click', () => {{
                hideOcrReviewGate();
                pendingEvaluation = null;
                // Focus the legs list for review
                const firstOcrLeg = legsList.querySelector('.leg-item.ocr-leg');
                if (firstOcrLeg) {{
                    firstOcrLeg.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }}
            }});
        }}

        if (gateProceedBtn) {{
            gateProceedBtn.addEventListener('click', async () => {{
                hideOcrReviewGate();
                if (pendingEvaluation) {{
                    // Ticket 36/37: This is a fresh evaluation from OCR, clear stale lock state
                    isReEvaluation = false;
                    lockedLegIds.clear();
                    await runEvaluation(pendingEvaluation.input);
                    pendingEvaluation = null;
                }}
            }});
        }}

        function showOcrReviewGate() {{
            if (ocrReviewGate) {{
                ocrReviewGate.classList.add('active');
            }}
        }}

        function hideOcrReviewGate() {{
            if (ocrReviewGate) {{
                ocrReviewGate.classList.remove('active');
            }}
        }}

        // Core evaluation function
        async function runEvaluation(input) {{
            showLoading();

            try {{
                // Ticket 27 Part B: Build request with canonical legs if from builder
                const requestBody = {{ input, tier: selectedTier }};

                // If we have builder legs, send canonical structure
                if (currentMode === 'builder' && builderLegs.length > 0) {{
                    requestBody.legs = builderLegs.map(leg => ({{
                        entity: leg.entity,
                        market: leg.market,
                        value: leg.value,
                        raw: leg.raw || leg.text
                    }}));
                }}

                const response = await fetch('/app/evaluate', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(requestBody)
                }});

                const data = await response.json();
                lastResponse = data;

                if (!response.ok) {{
                    // Ticket 38A: Safely extract error message
                    showError(safeResponseError(data, 'Evaluation failed'));
                    return;
                }}

                showResults(data);
            }} catch (err) {{
                showError('Network error. Please try again.');
            }}
        }}

        function showLoading() {{
            inputSection.style.display = 'none';
            loading.classList.add('active');
            errorPanel.classList.remove('active');
            results.classList.remove('active');
            document.getElementById('action-buttons').classList.remove('active');
        }}

        function showError(message) {{
            loading.classList.remove('active');
            inputSection.style.display = 'block';
            errorPanel.textContent = message;
            errorPanel.classList.add('active');
            results.classList.remove('active');
            document.getElementById('action-buttons').classList.remove('active');
        }}

        function showResults(data) {{
            loading.classList.remove('active');
            errorPanel.classList.remove('active');
            results.classList.add('active');
            document.getElementById('action-buttons').classList.add('active');

            // Ticket 32 Part B: Save evaluation to session history
            const parlay = data.evaluatedParlay;
            if (parlay) {{
                SessionManager.addEvaluation({{
                    input: parlay.display_label || betInput.value.trim(),
                    signal: data.signalInfo?.signal || '',
                    grade: data.signalInfo?.grade || '',
                    legCount: (parlay.legs || []).length
                }});
                updateSessionUI();
            }}

            // Ticket 25: Evaluated Parlay Receipt
            // Ticket 26 Part A: Leg interpretation display
            // Ticket 35: Add remove/lock controls for inline refinement
            // Ticket 37: Use leg_id for identity instead of index
            if (parlay) {{
                document.getElementById('parlay-label').textContent = parlay.display_label || 'Parlay';
                // Store legs for inline editing with deterministic leg_id
                resultsLegs = (parlay.legs || []).map((leg, i) => {{
                    // Generate leg_id from canonical fields
                    const leg_id = generateLegIdSync({{
                        entity: leg.entity || leg.text?.split(' ')[0] || '',
                        market: leg.bet_type || 'unknown',
                        value: leg.line_value || null,
                        sport: leg.sport || ''
                    }});
                    return {{
                        ...leg,
                        leg_id: leg_id,
                        originalIndex: i,
                        locked: lockedLegIds.has(leg_id)
                    }};
                }});
                renderResultsLegs();
            }}

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

            // Ticket 25: Notable Legs
            const notableSection = document.getElementById('notable-legs-section');
            const notableList = document.getElementById('notable-legs-list');
            notableList.innerHTML = '';
            const notable = data.notableLegs || [];
            if (notable.length === 0) {{
                notableSection.style.display = 'none';
            }} else {{
                notableSection.style.display = 'block';
                notable.forEach(item => {{
                    const li = document.createElement('li');
                    li.className = 'notable-leg';
                    li.innerHTML =
                        '<div class="notable-leg-text">' + escapeHtml(item.leg) + '</div>' +
                        '<div class="notable-leg-reason">' + escapeHtml(item.reason) + '</div>';
                    notableList.appendChild(li);
                }});
            }}

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

            // Ticket 25: Final Verdict
            const verdict = data.finalVerdict;
            const verdictSection = document.getElementById('verdict-section');
            if (verdict && verdict.verdict_text) {{
                verdictSection.style.display = 'block';
                document.getElementById('verdict-text').textContent = verdict.verdict_text;
                // Apply tone class
                verdictSection.className = 'card verdict-section';
                if (verdict.tone) {{
                    verdictSection.classList.add('tone-' + verdict.tone);
                }}
            }} else {{
                verdictSection.style.display = 'none';
            }}

            // Ticket 26 Part C: Gentle Guidance
            const guidance = data.gentleGuidance;
            const guidanceSection = document.getElementById('guidance-section');
            if (guidance && guidance.suggestions && guidance.suggestions.length > 0) {{
                guidanceSection.style.display = 'block';
                document.getElementById('guidance-header').textContent = guidance.header || 'If you wanted to adjust this:';
                const guidanceList = document.getElementById('guidance-list');
                guidanceList.innerHTML = '';
                guidance.suggestions.forEach(suggestion => {{
                    const li = document.createElement('li');
                    li.textContent = suggestion;
                    guidanceList.appendChild(li);
                }});
            }} else {{
                guidanceSection.style.display = 'none';
            }}

            // Ticket 27 Part D: Grounding Warnings
            const groundingWarnings = data.groundingWarnings;
            const groundingSection = document.getElementById('grounding-warnings');
            if (groundingWarnings && groundingWarnings.length > 0) {{
                groundingSection.style.display = 'block';
                const warningsList = document.getElementById('grounding-warnings-list');
                warningsList.innerHTML = '';
                groundingWarnings.forEach(warning => {{
                    const li = document.createElement('li');
                    li.textContent = warning;
                    warningsList.appendChild(li);
                }});
            }} else {{
                groundingSection.style.display = 'none';
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
            document.getElementById('action-buttons').classList.remove('active');
            betInput.value = '';
            // Ticket 23: Also reset builder state
            builderLegs = [];
            renderLegs();
            clearBuilderInputs();
            hideBuilderWarning();
            // Ticket 34: Reset OCR state
            hasOcrLegs = false;
            pendingEvaluation = null;
            if (ocrInfoBox) ocrInfoBox.classList.remove('active');
            if (ocrResult) ocrResult.style.display = 'none';
            if (imageStatus) imageStatus.style.display = 'none';
            if (imageInput) imageInput.value = '';
            // Ticket 35: Reset refine loop state
            // Ticket 36: Also reset re-evaluation flag
            // Ticket 37: Use leg_id based tracking
            lockedLegIds.clear();
            resultsLegs = [];
            isReEvaluation = false;
            // Focus appropriate element based on mode
            if (currentMode === 'builder') {{
                document.getElementById('builder-team').focus();
            }} else {{
                betInput.focus();
            }}
        }}

        // Ticket 25: Refine Parlay - returns to builder with legs preloaded
        // Ticket 35: Now uses resultsLegs (which may have been modified)
        function refineParlay() {{
            // Use resultsLegs if available (reflects inline edits), otherwise fall back
            const legsToUse = resultsLegs.length > 0 ? resultsLegs :
                              (lastResponse?.evaluatedParlay?.legs || []);

            if (legsToUse.length === 0) {{
                resetForm();
                return;
            }}

            // Preload legs from the current results state
            // Ticket 37: Include leg_id for deterministic tracking
            builderLegs = legsToUse.map(leg => {{
                const entity = leg.entity || leg.text?.split(' ')[0] || '';
                const market = leg.bet_type === 'player_prop' ? 'player_prop' :
                               leg.bet_type === 'total' ? 'total' :
                               leg.bet_type === 'spread' ? 'spread' : 'moneyline';
                const value = leg.line_value || null;
                const sport = leg.sport || '';
                // Use existing leg_id or generate new one
                const leg_id = leg.leg_id || generateLegIdSync({{ entity, market, value, sport }});
                return {{
                    leg_id: leg_id,
                    entity: entity,
                    text: leg.text,
                    raw: leg.text,
                    sport: sport,
                    market: market,
                    value: value,
                    locked: leg.locked || false
                }};
            }});

            // Switch to builder mode
            currentMode = 'builder';
            document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
            document.querySelector('[data-mode="builder"]').classList.add('active');
            builderSection.classList.add('active');
            pasteSection.classList.remove('active');

            // Update UI
            renderLegs();
            syncTextarea();

            // Hide results, show input
            inputSection.style.display = 'block';
            results.classList.remove('active');
            document.getElementById('action-buttons').classList.remove('active');

            // Focus on builder
            document.getElementById('builder-team').focus();
        }}

        // Enter key submits
        betInput.addEventListener('keydown', (e) => {{
            if (e.key === 'Enter' && e.metaKey) {{
                submitBtn.click();
            }}
        }});

        // ============================================================
        // Ticket 35: Inline Refine Loop
        // ============================================================

        /**
         * Render legs in results view with remove/lock controls.
         */
        function renderResultsLegs() {{
            const parlayLegs = document.getElementById('parlay-legs');
            parlayLegs.innerHTML = '';

            resultsLegs.forEach((leg, i) => {{
                const li = document.createElement('li');
                li.dataset.index = i;
                if (leg.locked) {{
                    li.classList.add('locked');
                }}

                // Leg number
                let html = '<span class="result-leg-num">' + (i + 1) + '.</span>';

                // Leg content
                html += '<div class="result-leg-content">';
                html += '<span class="result-leg-text">' + escapeHtml(leg.text) + '</span>';
                html += '<span class="leg-type">' + (leg.bet_type || '').replace('_', ' ') + '</span>';
                if (leg.interpretation) {{
                    html += '<div class="leg-interpretation">' + escapeHtml(leg.interpretation) + '</div>';
                }}
                html += '</div>';

                // Controls
                html += '<div class="result-leg-controls">';
                // Lock button
                const lockIcon = leg.locked ? '&#128274;' : '&#128275;'; // locked vs unlocked
                const lockClass = leg.locked ? 'leg-lock-btn locked' : 'leg-lock-btn';
                const lockTitle = leg.locked ? 'Unlock this leg' : 'Lock this leg (prevent removal)';
                html += '<button class="' + lockClass + '" onclick="toggleLegLock(' + i + ')" title="' + lockTitle + '">' + lockIcon + '</button>';
                // Remove button (disabled if locked)
                const removeDisabled = leg.locked ? 'disabled' : '';
                const removeTitle = leg.locked ? 'Unlock to remove' : 'Remove this leg';
                // Ticket 39: Use leg_id for robust removal (survives reordering)
                html += '<button class="leg-remove-btn" onclick="removeLegFromResults(\\'' + leg.leg_id + '\\')" ' + removeDisabled + ' title="' + removeTitle + '">Remove</button>';
                html += '</div>';

                li.innerHTML = html;
                parlayLegs.appendChild(li);
            }});

            // Update the parlay label to reflect current count
            updateParlayLabel();
            // Update re-evaluate button state
            updateReEvaluateButton();
        }}

        /**
         * Update parlay label to show current leg count.
         */
        function updateParlayLabel() {{
            const count = resultsLegs.length;
            let label = '';
            if (count === 0) {{
                label = 'No legs remaining';
            }} else if (count === 1) {{
                label = 'Single bet';
            }} else {{
                label = count + '-leg parlay';
            }}
            document.getElementById('parlay-label').textContent = label;
        }}

        /**
         * Update re-evaluate button enabled state.
         */
        function updateReEvaluateButton() {{
            const btn = document.getElementById('reevaluate-btn');
            if (btn) {{
                btn.disabled = resultsLegs.length === 0;
            }}
        }}

        /**
         * Toggle lock state for a leg.
         */
        function toggleLegLock(index) {{
            if (index < 0 || index >= resultsLegs.length) return;

            const leg = resultsLegs[index];
            leg.locked = !leg.locked;

            // Ticket 37: Update lock tracking using deterministic leg_id
            if (leg.locked) {{
                lockedLegIds.add(leg.leg_id);
            }} else {{
                lockedLegIds.delete(leg.leg_id);
            }}

            renderResultsLegs();
        }}

        /**
         * Remove a leg from results (inline refinement).
         * Ticket 39: Accepts leg_id (preferred) or index for robustness.
         * Does NOT remove locked legs.
         */
        function removeLegFromResults(identifier) {{
            let index;
            if (typeof identifier === 'string') {{
                // Ticket 39: leg_id-based removal (robust)
                index = resultsLegs.findIndex(leg => leg.leg_id === identifier);
            }} else {{
                // Legacy: index-based removal
                index = identifier;
            }}
            if (index < 0 || index >= resultsLegs.length) return;

            const leg = resultsLegs[index];
            // Cannot remove locked leg
            if (leg.locked) return;

            // Remove from results
            resultsLegs.splice(index, 1);

            // Sync state: update builderLegs and textarea
            syncStateFromResults();

            // Re-render
            renderResultsLegs();
        }}

        /**
         * Sync all state from resultsLegs.
         * Ensures builderLegs, textarea, and canonical state stay in sync.
         * Ticket 37: Includes leg_id for deterministic tracking.
         */
        function syncStateFromResults() {{
            // Update builderLegs to match resultsLegs
            builderLegs = resultsLegs.map(leg => ({{
                leg_id: leg.leg_id, // Ticket 37: Preserve deterministic leg_id
                entity: leg.entity || leg.text?.split(' ')[0] || '',
                market: leg.bet_type || 'unknown',
                value: leg.line_value || null,
                raw: leg.text,
                text: leg.text,
                sport: leg.sport || '',
                source: 'refined'
            }}));

            // Update textarea
            syncTextarea();
        }}

        /**
         * Re-evaluate parlay with current legs (after inline removals).
         * Ticket 36: This is a re-evaluation, so we preserve lock state.
         * Ticket 37: Uses deterministic leg_id for stable lock preservation.
         */
        async function reEvaluateParlay() {{
            if (resultsLegs.length === 0) {{
                showError('Add at least one leg to evaluate');
                return;
            }}

            // Ticket 36: Mark this as a re-evaluation (lock state should be preserved)
            isReEvaluation = true;

            // Build input from current results legs
            const input = resultsLegs.map(l => l.text).join('\\n');

            // Ensure state is synced
            syncStateFromResults();

            // Ticket 37: lockedLegIds persists across re-evaluation
            // No need to save/restore - showResults will use lockedLegIds.has(leg_id)

            // Run evaluation
            await runEvaluation(input);

            // Ticket 37: Lock state is automatically restored in showResults
            // via lockedLegIds.has(leg_id) check
            renderResultsLegs();
        }}
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
    # Ticket 27: Pass canonical legs if present
    try:
        canonical_legs = None
        if request.legs:
            canonical_legs = [leg.model_dump() for leg in request.legs]

        normalized = airlock_ingest(
            input_text=request.input,
            tier=request.tier,
            canonical_legs=canonical_legs,
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
            "evaluatedParlay": result.evaluated_parlay,
            "notableLegs": result.notable_legs,
            "finalVerdict": result.final_verdict,
            "gentleGuidance": result.gentle_guidance,
            "groundingWarnings": result.grounding_warnings,
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
