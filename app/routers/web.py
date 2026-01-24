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
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status, Response, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, EmailStr

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


def _get_app_page_html(user=None, active_tab: str = "evaluate") -> str:
    """Generate app page HTML with tabbed interface.

    Args:
        user: Authenticated user object or None
        active_tab: Active tab (discover, evaluate, builder, history)
    """
    # User info for header
    user_email = user.email if user else None
    user_tier = user.tier if user else "GOOD"
    is_logged_in = user is not None

    # Tab active states
    discover_active = "active" if active_tab == "discover" else ""
    evaluate_active = "active" if active_tab == "evaluate" else ""
    builder_active = "active" if active_tab == "builder" else ""
    history_active = "active" if active_tab == "history" else ""

    # User section in header (tier badge + email, both clickable to account)
    user_section = ""
    if is_logged_in:
        tier_class = user_tier.lower()
        user_section = f'''
            <a href="/app/account" class="user-info-header">
                <span class="tier-badge {tier_class}">{user_tier}</span>
                <span class="account-email">{user_email}</span>
            </a>
        '''
    else:
        user_section = '<a href="/login" class="login-link">Login</a>'

    # Orientation banner (first-run guidance)
    login_hint = '' if is_logged_in else '<span class="orientation-login">Log in to save history and manage your plan.</span>'
    orientation_banner = f'''
        <div class="orientation-banner">
            <span class="orientation-main">Build a parlay or paste a bet. We analyze risk, correlation, and fragility.</span>
            {login_hint}
        </div>
    '''

    # Upgrade CTA link (depends on login state)
    upgrade_link = "/app/account" if is_logged_in else "/login"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DNA Bet Engine</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 1.5rem;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0;
            padding-bottom: 1rem;
            border-bottom: 1px solid #333;
        }}
        .header-left {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        h1 {{ font-size: 1.5rem; color: #fff; }}
        header a {{
            color: #4a9eff;
            text-decoration: none;
            font-size: 0.875rem;
        }}
        .user-info-header {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            text-decoration: none;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            transition: background 0.2s;
        }}
        .user-info-header:hover {{
            background: #1a1a1a;
        }}
        .account-email {{
            color: #888;
            font-size: 0.875rem;
        }}
        .tier-badge {{
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .tier-badge.good {{ background: #1a2a3a; color: #4a9eff; }}
        .tier-badge.better {{ background: #2a2a1a; color: #f39c12; }}
        .tier-badge.best {{ background: #1a2a1a; color: #2ecc71; }}
        .login-link {{
            padding: 0.5rem 1rem;
            border: 1px solid #4a9eff;
            border-radius: 4px;
        }}

        /* Orientation Banner */
        .orientation-banner {{
            background: linear-gradient(135deg, #1a1a2a 0%, #1a2a2a 100%);
            border: 1px solid #2a3a4a;
            border-radius: 6px;
            padding: 0.75rem 1rem;
            margin: 1rem 0 0.5rem;
            font-size: 0.9rem;
        }}
        .orientation-main {{
            color: #ccc;
        }}
        .orientation-login {{
            display: block;
            margin-top: 0.25rem;
            font-size: 0.8rem;
            color: #888;
        }}
        .orientation-login a {{
            color: #4a9eff;
        }}

        /* Upgrade CTA */
        .upgrade-cta {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: linear-gradient(135deg, #2a1a3a 0%, #1a2a3a 100%);
            border: 1px solid #f39c12;
            border-radius: 4px;
            color: #f39c12;
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s;
        }}
        .upgrade-cta:hover {{
            background: #f39c12;
            color: #111;
        }}
        .upgrade-cta-inline {{
            margin-top: 0.75rem;
            text-align: center;
        }}

        /* Navigation Tabs */
        .nav-tabs {{
            display: flex;
            gap: 0;
            margin: 1rem 0;
            border-bottom: 1px solid #333;
        }}
        .nav-tab {{
            padding: 0.75rem 1.5rem;
            color: #888;
            text-decoration: none;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
            cursor: pointer;
        }}
        .nav-tab:hover {{
            color: #e0e0e0;
        }}
        .nav-tab.active {{
            color: #f39c12;
            border-bottom-color: #f39c12;
        }}

        /* Tab Content */
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}

        .main-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }}
        @media (max-width: 768px) {{
            .main-grid {{ grid-template-columns: 1fr; }}
        }}

        /* Builder Section */
        .builder-section {{
            background: #111;
            padding: 1.25rem;
            border-radius: 8px;
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }}
        .section-title {{
            font-size: 1.1rem;
            font-weight: 600;
            color: #fff;
        }}
        .leg-count {{
            font-size: 0.875rem;
            color: #888;
        }}

        /* Sport Selector */
        .sport-selector {{
            margin-bottom: 1rem;
        }}
        .sport-selector select {{
            width: 100%;
            padding: 0.75rem;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 4px;
            color: #e0e0e0;
            font-size: 0.9rem;
        }}
        .sport-selector select:focus {{
            outline: none;
            border-color: #4a9eff;
        }}

        /* Legs Container */
        .legs-container {{
            max-height: 400px;
            overflow-y: auto;
            margin-bottom: 1rem;
        }}
        .leg-card {{
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 0.75rem;
            position: relative;
        }}
        .leg-card:last-child {{ margin-bottom: 0; }}
        .leg-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
        }}
        .leg-number {{
            font-weight: 600;
            font-size: 0.875rem;
            color: #4a9eff;
        }}
        .remove-leg {{
            background: transparent;
            border: none;
            color: #ff4a4a;
            cursor: pointer;
            font-size: 1.25rem;
            padding: 0;
            width: auto;
            line-height: 1;
        }}
        .remove-leg:hover {{ color: #ff6b6b; }}
        .remove-leg:disabled {{ color: #444; cursor: not-allowed; }}

        .leg-fields {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
        }}
        .leg-field {{
            display: flex;
            flex-direction: column;
        }}
        .leg-field.full-width {{
            grid-column: 1 / -1;
        }}
        .leg-field label {{
            font-size: 0.7rem;
            color: #888;
            margin-bottom: 0.25rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .leg-field input, .leg-field select {{
            padding: 0.5rem;
            background: #0a0a0a;
            border: 1px solid #333;
            border-radius: 4px;
            color: #e0e0e0;
            font-size: 0.875rem;
        }}
        .leg-field input:focus, .leg-field select:focus {{
            outline: none;
            border-color: #4a9eff;
        }}
        .leg-field input::placeholder {{
            color: #555;
        }}

        /* Add Leg Button */
        .add-leg-btn {{
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
        }}
        .add-leg-btn:hover {{
            border-color: #4a9eff;
            color: #4a9eff;
        }}
        .add-leg-btn:disabled {{
            border-color: #222;
            color: #444;
            cursor: not-allowed;
        }}

        /* Tier Selector */
        .tier-selector-wrapper {{
            margin-bottom: 1rem;
        }}
        .tier-selector-label {{
            font-size: 0.7rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        .tier-selector {{
            display: flex;
            gap: 0.5rem;
        }}
        .tier-option {{
            flex: 1;
            position: relative;
        }}
        .tier-option input {{
            position: absolute;
            opacity: 0;
        }}
        .tier-option label {{
            display: block;
            padding: 0.625rem 0.5rem;
            background: #1a1a1a;
            border: 2px solid #333;
            border-radius: 4px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tier-option input:checked + label {{
            border-color: #4a9eff;
            background: #1a2a3a;
        }}
        .tier-option label:hover {{
            border-color: #555;
        }}
        .tier-name {{
            font-weight: 600;
            font-size: 0.8rem;
        }}
        .tier-desc {{
            font-size: 0.65rem;
            color: #888;
        }}

        /* Submit Button */
        .submit-btn {{
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
        }}
        .submit-btn:hover {{ background: #3a8eef; }}
        .submit-btn:disabled {{
            background: #333;
            color: #666;
            cursor: not-allowed;
        }}

        /* Results Section */
        .results-section {{
            background: #111;
            padding: 1.25rem;
            border-radius: 8px;
        }}
        .results-placeholder {{
            text-align: center;
            color: #555;
            padding: 3rem 1rem;
        }}
        .results-placeholder p {{
            margin-bottom: 0.5rem;
        }}

        /* Grade Display */
        .grade-display {{
            text-align: center;
            padding: 1.5rem;
            background: #1a1a1a;
            border-radius: 8px;
            margin-bottom: 1rem;
        }}
        .grade-label {{
            font-size: 0.75rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }}
        .grade-value {{
            font-size: 3rem;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 0.5rem;
        }}
        .grade-value.low {{ color: #4ade80; }}
        .grade-value.medium {{ color: #fbbf24; }}
        .grade-value.high {{ color: #f97316; }}
        .grade-value.critical {{ color: #ef4444; }}
        .grade-bucket {{
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
        }}

        /* Verdict */
        .verdict-panel {{
            background: #1a1a1a;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .verdict-panel h3 {{
            font-size: 0.75rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        .verdict-text {{
            font-size: 1rem;
            line-height: 1.5;
        }}
        .action-accept {{ color: #4ade80; }}
        .action-reduce {{ color: #fbbf24; }}
        .action-avoid {{ color: #ef4444; }}

        /* Insights Panel */
        .insights-panel {{
            background: #1a1a1a;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .insights-panel h3 {{
            font-size: 0.75rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.75rem;
        }}
        .insight-item {{
            padding: 0.5rem 0;
            border-bottom: 1px solid #333;
            font-size: 0.875rem;
        }}
        .insight-item:last-child {{ border-bottom: none; }}

        /* Locked Content */
        .locked-panel {{
            position: relative;
            overflow: hidden;
        }}
        .locked-panel .locked-overlay {{
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
        }}
        .locked-icon {{
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }}
        .locked-text {{
            font-size: 0.75rem;
            color: #888;
        }}

        /* Decision Summary (Always shown) */
        .decision-summary {{
            background: linear-gradient(135deg, #1a2a3a 0%, #1a1a2a 100%);
            border: 1px solid #2a3a4a;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .decision-summary h3 {{
            font-size: 0.7rem;
            color: #4a9eff;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.75rem;
        }}
        .decision-verdict {{
            font-size: 1rem;
            line-height: 1.4;
            margin-bottom: 0.75rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid #2a3a4a;
        }}
        .decision-bullets {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .decision-bullets li {{
            font-size: 0.8rem;
            padding: 0.35rem 0;
            padding-left: 1.25rem;
            position: relative;
            color: #bbb;
        }}
        .decision-bullets li::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0.65rem;
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }}
        .bullet-risk::before {{ background: #ef4444; }}
        .bullet-improve::before {{ background: #4ade80; }}
        .bullet-unknown::before {{ background: #888; }}

        /* Why Section */
        .why-section {{
            margin-bottom: 1rem;
        }}
        .why-section-title {{
            font-size: 0.7rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        }}
        .why-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
        }}
        @media (max-width: 500px) {{
            .why-grid {{ grid-template-columns: 1fr; }}
        }}
        .why-panel {{
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 0.75rem;
            min-height: 80px;
        }}
        .why-panel h4 {{
            font-size: 0.7rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .why-panel h4 .icon {{
            font-size: 0.9rem;
        }}
        .why-panel-content {{
            font-size: 0.8rem;
            line-height: 1.4;
            color: #ccc;
        }}
        .why-panel-content .metric {{
            font-weight: 600;
            color: #fff;
        }}
        .why-panel-content .detail {{
            color: #888;
            font-size: 0.75rem;
        }}

        /* Alerts (BEST only) */
        .alerts-panel {{
            background: #2a1a1a;
            border: 1px solid #4a2a2a;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .alerts-panel h3 {{
            font-size: 0.75rem;
            color: #ef4444;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.75rem;
        }}
        .alert-item {{
            font-size: 0.875rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid #4a2a2a;
        }}
        .alert-item:last-child {{ border-bottom: none; }}

        /* Error Panel */
        .error-panel {{
            background: #2a1a1a;
            border: 1px solid #ff4a4a;
            border-radius: 6px;
            padding: 1rem;
        }}
        .error-panel h3 {{
            color: #ff4a4a;
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }}
        .error-text {{
            font-size: 0.875rem;
            color: #e0e0e0;
        }}

        /* Hidden utility */
        .hidden {{ display: none !important; }}

        /* Context Panel Styles (Sprint 3) */
        .context-panel {{
            border: 1px solid #2a5a2a;
            background: #0a1a0a;
        }}
        .context-panel h3 {{
            color: #4a9e4a;
        }}
        .context-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.75rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #333;
        }}
        .context-source {{
            font-size: 0.75rem;
            color: #888;
        }}
        .context-summary {{
            background: #1a2a1a;
            padding: 0.75rem;
            border-radius: 4px;
            margin-bottom: 0.75rem;
            font-size: 0.9rem;
        }}
        .context-modifiers {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .context-modifier {{
            padding: 0.5rem;
            margin-bottom: 0.5rem;
            background: #1a1a1a;
            border-radius: 4px;
            border-left: 3px solid #666;
        }}
        .context-modifier.negative {{
            border-left-color: #e74c3c;
        }}
        .context-modifier.positive {{
            border-left-color: #2ecc71;
        }}
        .context-modifier-reason {{
            font-size: 0.85rem;
        }}
        .context-modifier-adjustment {{
            font-size: 0.75rem;
            color: #888;
            margin-top: 0.25rem;
        }}
        .context-missing {{
            font-size: 0.8rem;
            color: #f39c12;
            margin-top: 0.5rem;
            padding: 0.5rem;
            background: #2a2a1a;
            border-radius: 4px;
        }}
        .context-entities {{
            font-size: 0.75rem;
            color: #888;
            margin-top: 0.5rem;
        }}

        /* Alerts Feed Styles (Sprint 4) */
        .alerts-feed {{
            border: 1px solid #e74c3c;
            background: #1a0a0a;
            margin-bottom: 1rem;
        }}
        .alerts-feed h3 {{
            color: #e74c3c;
        }}
        .alerts-feed.locked {{
            border-color: #444;
            background: #1a1a1a;
        }}
        .alerts-feed.locked h3 {{
            color: #666;
        }}
        .alert-item {{
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            background: #1a1a1a;
            border-radius: 4px;
            border-left: 3px solid #e74c3c;
        }}
        .alert-item.warning {{
            border-left-color: #f39c12;
        }}
        .alert-item.info {{
            border-left-color: #3498db;
        }}
        .alert-title {{
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}
        .alert-message {{
            font-size: 0.85rem;
            color: #aaa;
        }}
        .alert-meta {{
            font-size: 0.75rem;
            color: #666;
            margin-top: 0.5rem;
        }}
        .alerts-empty {{
            color: #666;
            font-style: italic;
            padding: 0.5rem;
        }}
        .alerts-locked-message {{
            color: #888;
            font-size: 0.9rem;
            padding: 0.5rem;
        }}

        /* Share Button Styles (Sprint 5) */
        .share-section {{
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #333;
            text-align: center;
        }}
        .share-btn {{
            background: #3498db;
            color: white;
            border: none;
            padding: 0.5rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
        }}
        .share-btn:hover {{
            background: #2980b9;
        }}
        .share-btn:disabled {{
            background: #555;
            cursor: not-allowed;
        }}
        .share-link {{
            margin-top: 0.75rem;
            padding: 0.5rem;
            background: #1a1a1a;
            border-radius: 4px;
            display: none;
        }}
        .share-link.visible {{
            display: block;
        }}
        .share-link input {{
            width: 100%;
            padding: 0.5rem;
            background: #0a0a0a;
            border: 1px solid #333;
            color: #eee;
            border-radius: 4px;
            font-family: monospace;
        }}
        .share-link .copy-btn {{
            margin-top: 0.5rem;
            padding: 0.25rem 1rem;
            font-size: 0.8rem;
        }}

        /* Upgrade Nudge Styles (Sprint 5) */
        .upgrade-nudge {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid #f39c12;
            border-radius: 6px;
            padding: 1rem;
            margin-top: 1rem;
            text-align: center;
        }}
        .upgrade-nudge h4 {{
            color: #f39c12;
            margin: 0 0 0.5rem;
            font-size: 0.95rem;
        }}
        .upgrade-nudge p {{
            color: #aaa;
            font-size: 0.85rem;
            margin: 0 0 0.75rem;
        }}
        .upgrade-nudge .upgrade-btn {{
            background: #f39c12;
            color: #111;
            border: none;
            padding: 0.5rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 600;
        }}
        .upgrade-nudge .upgrade-btn:hover {{
            background: #e67e22;
        }}
        /* Evaluate Tab Styles */
        .evaluate-section {{
            background: #111;
            padding: 1.25rem;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }}
        .eval-explainer {{
            font-size: 0.9rem;
            color: #888;
            margin-bottom: 1rem;
        }}
        .bundle-prompt {{
            border: 2px dashed #333;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            background: #1a1a1a;
        }}
        .bundle-prompt p {{
            color: #888;
            margin-bottom: 1rem;
        }}
        .secondary-btn {{
            padding: 0.75rem 1.5rem;
            background: transparent;
            border: 1px solid #4a9eff;
            border-radius: 4px;
            color: #4a9eff;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .secondary-btn:hover {{
            background: #4a9eff;
            color: #000;
        }}
        .secondary-btn.disabled {{
            border-color: #444;
            color: #444;
            cursor: not-allowed;
        }}
        .secondary-btn.disabled:hover {{
            background: transparent;
            color: #444;
        }}
        .builder-cta {{
            width: 100%;
            margin-top: 0.75rem;
        }}

        /* Signal System */
        .signal-display {{
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1.25rem;
            background: #1a1a1a;
            border-radius: 8px;
            margin-bottom: 1rem;
        }}
        .signal-badge {{
            width: 64px;
            height: 64px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1.5rem;
            flex-shrink: 0;
        }}
        .signal-badge.signal-blue {{ background: #1a2a4a; color: #4a9eff; border: 2px solid #4a9eff; }}
        .signal-badge.signal-green {{ background: #1a3a2a; color: #4ade80; border: 2px solid #4ade80; }}
        .signal-badge.signal-yellow {{ background: #3a3a1a; color: #fbbf24; border: 2px solid #fbbf24; }}
        .signal-badge.signal-red {{ background: #3a1a1a; color: #ef4444; border: 2px solid #ef4444; }}
        .signal-score {{
            display: flex;
            flex-direction: column;
        }}
        .signal-score-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #fff;
        }}
        .signal-score-label {{
            font-size: 0.75rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* Verdict Bar */
        .verdict-bar {{
            padding: 0.75rem 1rem;
            background: #1a1a1a;
            border-radius: 6px;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }}
        .verdict-action {{
            font-weight: 700;
            margin-right: 0.5rem;
        }}
        .verdict-action.action-accept {{ color: #4ade80; }}
        .verdict-action.action-reduce {{ color: #fbbf24; }}
        .verdict-action.action-avoid {{ color: #ef4444; }}
        .verdict-reason {{
            color: #ccc;
        }}

        /* Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }}
        .metric-item {{
            background: #1a1a1a;
            padding: 0.75rem;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
        }}
        .metric-label {{
            font-size: 0.7rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.25rem;
        }}
        .metric-value {{
            font-size: 1.1rem;
            font-weight: 600;
            color: #fff;
        }}

        /* Tips Panel */
        .tips-panel {{
            background: #1a2a1a;
            border: 1px solid #2a4a2a;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .tips-panel h3 {{
            font-size: 0.7rem;
            color: #4ade80;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        .tips-content {{
            font-size: 0.875rem;
            color: #ccc;
            line-height: 1.5;
        }}
        .tip-item {{
            padding: 0.4rem 0;
            padding-left: 1rem;
            position: relative;
        }}
        .tip-item::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0.7rem;
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: #4ade80;
        }}

        /* Correlations Panel (BETTER+) */
        .correlations-panel {{
            background: #2a2a1a;
            border: 1px solid #4a4a2a;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .correlations-panel h3 {{
            font-size: 0.7rem;
            color: #fbbf24;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        .correlation-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.5rem 0;
            border-bottom: 1px solid #333;
            font-size: 0.85rem;
        }}
        .correlation-item:last-child {{ border-bottom: none; }}
        .correlation-type {{
            color: #fbbf24;
            font-weight: 600;
            font-size: 0.75rem;
        }}
        .correlation-penalty {{
            color: #ef4444;
            font-weight: 600;
        }}

        /* Summary Panel (BETTER+) */
        .summary-panel {{
            background: #1a1a2a;
            border: 1px solid #2a2a4a;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .summary-panel h3 {{
            font-size: 0.7rem;
            color: #4a9eff;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        .summary-item {{
            padding: 0.4rem 0;
            font-size: 0.85rem;
            color: #ccc;
            border-bottom: 1px solid #2a2a4a;
        }}
        .summary-item:last-child {{ border-bottom: none; }}

        /* Alerts Panel (BEST) */
        .alerts-detail-panel {{
            background: #2a1a1a;
            border: 1px solid #4a2a2a;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .alerts-detail-panel h3 {{
            font-size: 0.7rem;
            color: #ef4444;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }}
        .alert-detail-item {{
            padding: 0.5rem;
            margin-bottom: 0.5rem;
            background: #1a1a1a;
            border-left: 3px solid #ef4444;
            border-radius: 4px;
            font-size: 0.85rem;
            color: #ccc;
        }}

        /* Post-Result Actions */
        .post-actions {{
            display: flex;
            gap: 0.5rem;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #333;
        }}
        .action-btn {{
            flex: 1;
            padding: 0.6rem 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid;
            transition: all 0.2s;
        }}
        .action-improve {{
            background: transparent;
            border-color: #4a9eff;
            color: #4a9eff;
        }}
        .action-improve:hover {{ background: #4a9eff; color: #000; }}
        .action-reeval {{
            background: transparent;
            border-color: #fbbf24;
            color: #fbbf24;
        }}
        .action-reeval:hover {{ background: #fbbf24; color: #000; }}
        .action-save {{
            background: transparent;
            border-color: #4ade80;
            color: #4ade80;
        }}
        .action-save:hover {{ background: #4ade80; color: #000; }}

        .input-tabs {{
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }}
        .input-tab {{
            padding: 0.5rem 1rem;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 4px;
            color: #888;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .input-tab.active {{
            background: #2a2a2a;
            border-color: #4a9eff;
            color: #4a9eff;
        }}
        .input-panel {{
            display: none;
        }}
        .input-panel.active {{
            display: block;
        }}
        .text-input {{
            width: 100%;
            min-height: 150px;
            padding: 1rem;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 4px;
            color: #e0e0e0;
            font-size: 0.95rem;
            resize: vertical;
        }}
        .text-input:focus {{
            outline: none;
            border-color: #4a9eff;
        }}
        /* Image Not Available (OCR not implemented) */
        .image-not-available {{
            border: 2px dashed #444;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            background: #1a1a1a;
        }}
        .image-not-available-icon {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
            opacity: 0.5;
        }}
        .image-not-available-title {{
            font-weight: 600;
            color: #f39c12;
            margin-bottom: 0.5rem;
        }}
        .image-not-available-text {{
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 1rem;
        }}
        .switch-to-text-btn {{
            display: inline-block;
            padding: 0.5rem 1rem;
            background: #4a9eff;
            color: #111;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 500;
            font-size: 0.85rem;
        }}
        .switch-to-text-btn:hover {{
            background: #3a8eef;
        }}

        .file-upload-area {{
            border: 2px dashed #333;
            border-radius: 8px;
            padding: 2rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .file-upload-area:hover {{
            border-color: #4a9eff;
            background: #1a1a2a;
        }}
        .file-upload-area.has-file {{
            border-color: #2ecc71;
            background: #1a2a1a;
        }}
        .file-upload-area.dragover {{
            border-color: #4a9eff;
            background: #1a1a2a;
        }}
        .file-upload-area.uploading {{
            pointer-events: none;
            opacity: 0.7;
        }}
        .file-upload-area input {{
            display: none;
        }}
        .file-upload-icon {{
            font-size: 2.5rem;
            margin-bottom: 0.75rem;
        }}
        .file-upload-text {{
            color: #888;
            line-height: 1.5;
        }}
        .file-types {{
            font-size: 0.75rem;
            color: #666;
        }}
        .file-selected {{
            color: #2ecc71;
        }}
        .file-selected-icon {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        .file-selected-name {{
            font-weight: 600;
            margin-bottom: 0.75rem;
            word-break: break-all;
        }}
        .clear-file-btn {{
            padding: 0.375rem 1rem;
            background: transparent;
            border: 1px solid #e74c3c;
            color: #e74c3c;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85rem;
            transition: all 0.2s;
        }}
        .clear-file-btn:hover {{
            background: #e74c3c;
            color: #fff;
        }}
        .image-error {{
            margin-top: 0.75rem;
            padding: 0.75rem;
            background: #2a1a1a;
            border: 1px solid #e74c3c;
            border-radius: 4px;
            color: #e74c3c;
            font-size: 0.85rem;
        }}
        .image-parse-info {{
            background: #1a2a1a;
            border: 1px solid #2ecc71;
            border-radius: 6px;
            padding: 0.75rem;
            margin-bottom: 1rem;
            font-size: 0.85rem;
        }}
        .image-parse-confidence {{
            color: #2ecc71;
            font-weight: 600;
        }}
        .image-parse-notes {{
            color: #888;
            margin-top: 0.25rem;
            font-size: 0.8rem;
        }}
        .clear-file {{
            margin-top: 0.5rem;
            padding: 0.25rem 0.75rem;
            background: transparent;
            border: 1px solid #e74c3c;
            color: #e74c3c;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
        }}
        .eval-submit {{
            width: 100%;
            margin-top: 1rem;
        }}

        /* Discover Tab Styles */
        .discover-section {{
            max-width: 600px;
            margin: 0 auto;
            padding: 2rem 1rem;
        }}
        .discover-hero {{
            text-align: center;
            margin-bottom: 2rem;
        }}
        .discover-hero h2 {{
            font-size: 1.5rem;
            color: #fff;
            margin-bottom: 0.75rem;
        }}
        .discover-tagline {{
            color: #888;
            font-size: 1rem;
        }}
        .discover-steps {{
            margin-bottom: 2rem;
        }}
        .discover-step {{
            display: flex;
            gap: 1rem;
            padding: 1rem;
            background: #1a1a1a;
            border-radius: 8px;
            margin-bottom: 0.75rem;
        }}
        .step-number {{
            width: 32px;
            height: 32px;
            background: #4a9eff;
            color: #000;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            flex-shrink: 0;
        }}
        .step-content h3 {{
            font-size: 1rem;
            color: #fff;
            margin-bottom: 0.25rem;
        }}
        .step-content p {{
            font-size: 0.875rem;
            color: #888;
            margin: 0;
        }}
        .discover-cta {{
            text-align: center;
        }}
        .discover-start-btn {{
            max-width: 300px;
        }}

        /* History Tab Styles */
        .history-section {{
            background: #111;
            padding: 1.25rem;
            border-radius: 8px;
        }}
        .history-empty {{
            text-align: center;
            padding: 2rem;
            color: #666;
        }}
        .history-item {{
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 6px;
            padding: 1rem;
            margin-bottom: 0.75rem;
        }}
        .history-date {{
            font-size: 0.75rem;
            color: #666;
            margin-bottom: 0.5rem;
        }}
        .history-text {{
            font-family: monospace;
            font-size: 0.9rem;
            color: #ccc;
            margin-bottom: 0.5rem;
        }}
        .history-grade {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.8rem;
        }}
        .history-grade.low {{ background: #1a3a2a; color: #4ade80; }}
        .history-grade.medium {{ background: #3a3a1a; color: #fbbf24; }}
        .history-grade.high {{ background: #3a2a1a; color: #f97316; }}
        .history-grade.critical {{ background: #3a1a1a; color: #ef4444; }}
        .login-prompt {{
            text-align: center;
            padding: 2rem;
            background: #1a1a1a;
            border-radius: 8px;
        }}
        .login-prompt a {{
            display: inline-block;
            margin-top: 1rem;
            padding: 0.75rem 1.5rem;
            background: #f39c12;
            color: #111;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-left">
                <h1>DNA Bet Engine</h1>
            </div>
            {user_section}
        </header>

        <!-- Orientation Banner -->
        {orientation_banner}

        <!-- Navigation Tabs -->
        <nav class="nav-tabs">
            <a class="nav-tab {discover_active}" data-tab="discover">Discover</a>
            <a class="nav-tab {evaluate_active}" data-tab="evaluate">Evaluate</a>
            <a class="nav-tab {builder_active}" data-tab="builder">Builder</a>
            <a class="nav-tab {history_active}" data-tab="history">History</a>
        </nav>

        <!-- Discover Tab Content -->
        <div class="tab-content {discover_active}" id="tab-discover">
            <div class="discover-section">
                <div class="discover-hero">
                    <h2>Know Your Bet Before You Place It</h2>
                    <p class="discover-tagline">We analyze risk, correlation, and fragility so you can make informed decisions.</p>
                </div>

                <div class="discover-steps">
                    <div class="discover-step">
                        <div class="step-number">1</div>
                        <div class="step-content">
                            <h3>Submit Your Bet</h3>
                            <p>Paste text, upload an image, or build a parlay from scratch.</p>
                        </div>
                    </div>
                    <div class="discover-step">
                        <div class="step-number">2</div>
                        <div class="step-content">
                            <h3>Get Your Analysis</h3>
                            <p>See fragility score, correlation risks, and actionable recommendations.</p>
                        </div>
                    </div>
                    <div class="discover-step">
                        <div class="step-number">3</div>
                        <div class="step-content">
                            <h3>Decide With Confidence</h3>
                            <p>Understand exactly why a bet is strong or weak before you commit.</p>
                        </div>
                    </div>
                </div>

                <div class="discover-cta">
                    <button type="button" class="submit-btn discover-start-btn" onclick="switchToTab('evaluate')">
                        Start Evaluating
                    </button>
                </div>
            </div>
        </div> <!-- End tab-discover -->

        <!-- Builder Tab Content -->
        <div class="tab-content {builder_active}" id="tab-builder">
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

                <div class="tier-selector-wrapper">
                    <div class="tier-selector-label">Analysis detail level</div>
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

                    <!-- Share Section (Sprint 5) -->
                    <div class="share-section hidden" id="share-section">
                        <button type="button" class="share-btn" id="share-btn">Share Result</button>
                        <div class="share-link" id="share-link">
                            <input type="text" id="share-url" readonly>
                            <button type="button" class="share-btn copy-btn" id="copy-btn">Copy Link</button>
                        </div>
                    </div>

                    <!-- Upgrade Nudge (Sprint 5) -->
                    <div class="upgrade-nudge hidden" id="upgrade-nudge">
                        <h4>Get Full Analysis</h4>
                        <p id="upgrade-message">See detailed breakdowns, correlations, and live alerts</p>
                        <a href="{upgrade_link}" class="upgrade-cta">Upgrade to BEST</a>
                    </div>
                </div>

                <div id="error-panel" class="error-panel hidden">
                    <h3>Error</h3>
                    <div class="error-text" id="error-text"></div>
                </div>
            </div>
        </div>
        </div> <!-- End tab-builder -->

        <!-- Evaluate Tab Content -->
        <div class="tab-content {evaluate_active}" id="tab-evaluate">
            <div class="main-grid">
                <div class="evaluate-section">
                    <div class="section-header">
                        <span class="section-title">Evaluate Bet</span>
                    </div>

                    <!-- Short Explainer -->
                    <p class="eval-explainer">Submit your bet for analysis. We check risk, correlation, and fragility.</p>

                    <!-- Input Type Tabs -->
                    <div class="input-tabs">
                        <div class="input-tab active" data-input="text">Text</div>
                        <div class="input-tab" data-input="image">Image</div>
                        <div class="input-tab" data-input="bundle">Bundle</div>
                    </div>

                    <!-- Text Input Panel -->
                    <div class="input-panel active" id="text-input-panel">
                        <textarea class="text-input" id="eval-text-input" placeholder="Paste your bet slip text here...&#10;&#10;Example:&#10;Lakers -5.5 + Celtics ML + LeBron O27.5 pts parlay"></textarea>
                    </div>

                    <!-- Image Input Panel -->
                    <div class="input-panel" id="image-input-panel">
                        <div class="file-upload-area" id="file-upload-area">
                            <input type="file" id="file-input" accept="image/png,image/jpeg,image/jpg,image/webp">
                            <div class="file-upload-icon" id="file-upload-icon">&#128247;</div>
                            <div class="file-upload-text" id="file-upload-text">
                                Click or drag to upload bet slip image<br>
                                <span class="file-types">PNG, JPG, or WebP (max 5MB)</span>
                            </div>
                            <div class="file-selected hidden" id="file-selected">
                                <div class="file-selected-icon">&#9989;</div>
                                <div class="file-selected-name" id="file-name"></div>
                                <button type="button" class="clear-file-btn" id="clear-file">Remove</button>
                            </div>
                        </div>
                        <div class="image-error hidden" id="image-error"></div>
                    </div>

                    <!-- Bundle Input Panel -->
                    <div class="input-panel" id="bundle-input-panel">
                        <div class="bundle-prompt">
                            <p>Build a custom parlay using the Builder.</p>
                            <button type="button" class="secondary-btn" onclick="switchToTab('builder')">Go to Builder</button>
                        </div>
                    </div>

                    <!-- Tier Selector -->
                    <div class="tier-selector-wrapper" style="margin-top: 1rem;">
                        <div class="tier-selector-label">Analysis detail level</div>
                        <div class="tier-selector">
                            <div class="tier-option">
                                <input type="radio" name="eval-tier" id="eval-tier-good" value="good" checked>
                                <label for="eval-tier-good">
                                    <div class="tier-name">GOOD</div>
                                    <div class="tier-desc">Grade + Verdict</div>
                                </label>
                            </div>
                            <div class="tier-option">
                                <input type="radio" name="eval-tier" id="eval-tier-better" value="better">
                                <label for="eval-tier-better">
                                    <div class="tier-name">BETTER</div>
                                    <div class="tier-desc">+ Insights</div>
                                </label>
                            </div>
                            <div class="tier-option">
                                <input type="radio" name="eval-tier" id="eval-tier-best" value="best">
                                <label for="eval-tier-best">
                                    <div class="tier-name">BEST</div>
                                    <div class="tier-desc">+ Full Analysis</div>
                                </label>
                            </div>
                        </div>
                    </div>

                    <button type="button" class="submit-btn eval-submit" id="eval-submit-btn" disabled>
                        Evaluate
                    </button>

                    <!-- Disabled Builder CTA (shown until evaluation exists) -->
                    <button type="button" class="secondary-btn builder-cta disabled" id="builder-cta-btn" disabled title="Evaluate a bet first">
                        Build Custom Parlay
                    </button>
                </div>

                <!-- Results Section (same structure as builder) -->
                <div class="results-section">
                    <div class="section-header">
                        <span class="section-title">Results</span>
                    </div>

                    <div id="eval-results-placeholder" class="results-placeholder">
                        <p>Enter or upload your bet and click Evaluate</p>
                    </div>

                    <div id="eval-results-content" class="hidden">
                        <!-- Signal Badge + Fragility Score -->
                        <div class="signal-display" id="eval-signal-display">
                            <div class="signal-badge" id="eval-signal-badge">--</div>
                            <div class="signal-score">
                                <span class="signal-score-value" id="eval-signal-score">--</span>
                                <span class="signal-score-label">Fragility</span>
                            </div>
                        </div>

                        <!-- Verdict (GOOD+) -->
                        <div class="verdict-bar" id="eval-verdict-bar">
                            <span class="verdict-action" id="eval-verdict-action"></span>
                            <span class="verdict-reason" id="eval-verdict-reason"></span>
                        </div>

                        <!-- Metrics (GOOD+) -->
                        <div class="metrics-grid" id="eval-metrics-grid">
                            <div class="metric-item">
                                <span class="metric-label">Leg Penalty</span>
                                <span class="metric-value" id="eval-metric-leg">--</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Correlation</span>
                                <span class="metric-value" id="eval-metric-corr">--</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Raw Fragility</span>
                                <span class="metric-value" id="eval-metric-raw">--</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Final Score</span>
                                <span class="metric-value" id="eval-metric-final">--</span>
                            </div>
                        </div>

                        <!-- Improvement Tips (GOOD+) -->
                        <div class="tips-panel" id="eval-tips-panel">
                            <h3>How to Improve</h3>
                            <div class="tips-content" id="eval-tips-content"></div>
                        </div>

                        <!-- Correlations Panel (BETTER+) -->
                        <div class="correlations-panel hidden" id="eval-correlations-panel">
                            <h3>Correlations Found</h3>
                            <div class="correlations-list" id="eval-correlations-list"></div>
                        </div>

                        <!-- Summary Insights (BETTER+) -->
                        <div class="summary-panel hidden" id="eval-summary-panel">
                            <h3>Deeper Insights</h3>
                            <div class="summary-list" id="eval-summary-list"></div>
                        </div>

                        <!-- Alerts (BEST only) -->
                        <div class="alerts-detail-panel hidden" id="eval-alerts-panel">
                            <h3>Alerts</h3>
                            <div class="alerts-list" id="eval-alerts-list"></div>
                        </div>

                        <!-- Post-Result Actions -->
                        <div class="post-actions" id="eval-post-actions">
                            <button type="button" class="action-btn action-improve" id="eval-action-improve" onclick="switchToTab('builder')">Improve in Builder</button>
                            <button type="button" class="action-btn action-reeval" id="eval-action-reeval">Re-Evaluate</button>
                            <button type="button" class="action-btn action-save" id="eval-action-save">Save</button>
                        </div>
                    </div>

                    <div id="eval-error-panel" class="error-panel hidden">
                        <h3>Error</h3>
                        <div class="error-text" id="eval-error-text"></div>
                    </div>
                </div>
            </div>
        </div> <!-- End tab-evaluate -->

        <!-- History Tab Content -->
        <div class="tab-content {history_active}" id="tab-history">
            <div class="history-section">
                <div class="section-header">
                    <span class="section-title">Evaluation History</span>
                </div>

                <div id="history-content">
                    {"<div class='login-prompt'><p>Sign in to view your evaluation history</p><a href='/login'>Login</a></div>" if not is_logged_in else "<div class='loading'>Loading history...</div>"}
                </div>
            </div>
        </div> <!-- End tab-history -->

    </div>

    <script>
        (function() {{
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
                {{ value: 'spread', label: 'Spread' }},
                {{ value: 'ml', label: 'Moneyline' }},
                {{ value: 'total', label: 'Total (O/U)' }},
                {{ value: 'player_prop', label: 'Player Prop' }}
            ];

            // Initialize with 2 legs
            function init() {{
                addLeg();
                addLeg();
                updateUI();
            }}

            function createLegHTML(index) {{
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
            }}

            function addLeg() {{
                if (legs.length >= MAX_LEGS) return;
                legs.push({{ selection: '', market: 'spread', line: '', odds: '' }});
                renderLegs();
                updateUI();
            }}

            function removeLeg(index) {{
                if (legs.length <= MIN_LEGS) return;
                legs.splice(index, 1);
                renderLegs();
                updateUI();
            }}

            function renderLegs() {{
                legsContainer.innerHTML = legs.map((_, i) => createLegHTML(i)).join('');
                attachLegListeners();
                // Restore values
                legs.forEach((leg, i) => {{
                    const card = legsContainer.querySelector('[data-index="' + i + '"]');
                    if (card) {{
                        const selInput = card.querySelector('.leg-selection');
                        const mktSelect = card.querySelector('.leg-market');
                        const lineInput = card.querySelector('.leg-line');
                        const oddsInput = card.querySelector('.leg-odds');
                        if (selInput) selInput.value = leg.selection;
                        if (mktSelect) mktSelect.value = leg.market;
                        if (lineInput) lineInput.value = leg.line;
                        if (oddsInput) oddsInput.value = leg.odds;
                    }}
                }});
            }}

            function attachLegListeners() {{
                // Remove buttons
                legsContainer.querySelectorAll('.remove-leg').forEach(btn => {{
                    btn.addEventListener('click', function() {{
                        removeLeg(parseInt(this.dataset.index));
                    }});
                }});
                // Input changes
                legsContainer.querySelectorAll('.leg-selection').forEach(input => {{
                    input.addEventListener('input', function() {{
                        legs[parseInt(this.dataset.index)].selection = this.value;
                        updateUI();
                    }});
                }});
                legsContainer.querySelectorAll('.leg-market').forEach(select => {{
                    select.addEventListener('change', function() {{
                        legs[parseInt(this.dataset.index)].market = this.value;
                    }});
                }});
                legsContainer.querySelectorAll('.leg-line').forEach(input => {{
                    input.addEventListener('input', function() {{
                        legs[parseInt(this.dataset.index)].line = this.value;
                    }});
                }});
                legsContainer.querySelectorAll('.leg-odds').forEach(input => {{
                    input.addEventListener('input', function() {{
                        legs[parseInt(this.dataset.index)].odds = this.value;
                    }});
                }});
            }}

            function updateUI() {{
                // Leg count
                legCountDisplay.textContent = legs.length + ' leg' + (legs.length !== 1 ? 's' : '');

                // Add button state
                addLegBtn.disabled = legs.length >= MAX_LEGS;

                // Remove button state
                legsContainer.querySelectorAll('.remove-leg').forEach(btn => {{
                    btn.disabled = legs.length <= MIN_LEGS;
                }});

                // Submit button - require at least selection for each leg
                const validLegs = legs.filter(leg => leg.selection.trim().length > 0);
                submitBtn.disabled = validLegs.length < MIN_LEGS;
            }}

            function getSelectedTier() {{
                const selected = document.querySelector('input[name="tier"]:checked');
                return selected ? selected.value : 'good';
            }}

            function buildBetText() {{
                // Convert structured legs to text format for existing endpoint
                const parts = legs.map(leg => {{
                    let text = leg.selection.trim();
                    if (leg.line.trim()) {{
                        text += ' ' + leg.line.trim();
                    }}
                    if (leg.market === 'ml') {{
                        text += ' ML';
                    }} else if (leg.market === 'player_prop') {{
                        text += ' prop';
                    }}
                    return text;
                }}).filter(t => t.length > 0);

                return parts.join(' + ') + ' parlay';
            }}

            function showError(message) {{
                resultsPlaceholder.classList.add('hidden');
                resultsContent.classList.add('hidden');
                errorPanel.classList.remove('hidden');
                document.getElementById('error-text').textContent = message;
            }}

            function showResults(data) {{
                resultsPlaceholder.classList.add('hidden');
                errorPanel.classList.add('hidden');
                resultsContent.classList.remove('hidden');

                const tier = getSelectedTier();
                const evaluation = data.evaluation;
                const interpretation = data.interpretation;
                const explain = data.explain || {{}};
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
                const riskMap = {{
                    'stable': 'Low structural risk',
                    'loaded': 'Moderate complexity - multiple dependencies',
                    'tense': 'High correlation or fragility detected',
                    'critical': 'Extreme fragility - many failure points'
                }};
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

                if (isLocked) {{
                    whyStructure.classList.add('locked-panel');
                    structureLocked.classList.remove('hidden');
                    structureContent.innerHTML = '<span style="color:#555">Locked</span>';
                }} else {{
                    whyStructure.classList.remove('locked-panel');
                    structureLocked.classList.add('hidden');
                    const legCount = legs.length;
                    const legPenalty = metrics.leg_penalty || 0;
                    let structureHtml = '<span class="metric">' + legCount + ' legs</span>';
                    if (showDetail) {{
                        structureHtml += '<br><span class="detail">Leg penalty: +' + legPenalty.toFixed(1) + '</span>';
                        if (legCount >= 4) {{
                            structureHtml += '<br><span class="detail">High concentration risk</span>';
                        }}
                    }} else {{
                        structureHtml += '<br><span class="detail">Each leg adds risk</span>';
                    }}
                    structureContent.innerHTML = structureHtml;
                }}

                // Correlation Panel
                const correlationContent = document.getElementById('correlation-content');
                const correlationLocked = document.getElementById('correlation-locked');
                const whyCorrelation = document.getElementById('why-correlation');

                if (isLocked) {{
                    whyCorrelation.classList.add('locked-panel');
                    correlationLocked.classList.remove('hidden');
                    correlationContent.innerHTML = '<span style="color:#555">Locked</span>';
                }} else {{
                    whyCorrelation.classList.remove('locked-panel');
                    correlationLocked.classList.add('hidden');
                    const corrCount = evaluation.correlations ? evaluation.correlations.length : 0;
                    const corrPenalty = metrics.correlation_penalty || 0;
                    const corrMult = metrics.correlation_multiplier || 1.0;
                    let corrHtml = '<span class="metric">' + corrCount + ' correlation' + (corrCount !== 1 ? 's' : '') + '</span>';
                    if (showDetail) {{
                        corrHtml += '<br><span class="detail">Penalty: +' + corrPenalty.toFixed(1) + '</span>';
                        corrHtml += '<br><span class="detail">Multiplier: ' + corrMult.toFixed(2) + 'x</span>';
                    }} else {{
                        corrHtml += '<br><span class="detail">' + (corrCount > 0 ? 'Linked outcomes' : 'Independent legs') + '</span>';
                    }}
                    correlationContent.innerHTML = corrHtml;
                }}

                // Fragility Panel
                const fragilityContent = document.getElementById('fragility-content');
                const fragilityLocked = document.getElementById('fragility-locked');
                const whyFragility = document.getElementById('why-fragility');

                if (isLocked) {{
                    whyFragility.classList.add('locked-panel');
                    fragilityLocked.classList.remove('hidden');
                    fragilityContent.innerHTML = '<span style="color:#555">Locked</span>';
                }} else {{
                    whyFragility.classList.remove('locked-panel');
                    fragilityLocked.classList.add('hidden');
                    const rawFrag = metrics.raw_fragility || 0;
                    const finalFrag = metrics.final_fragility || 0;
                    let fragHtml = '<span class="metric">' + fragility.bucket.toUpperCase() + '</span>';
                    if (showDetail) {{
                        fragHtml += '<br><span class="detail">Base: ' + rawFrag.toFixed(1) + '</span>';
                        fragHtml += '<br><span class="detail">Final: ' + finalFrag.toFixed(1) + '</span>';
                    }} else {{
                        fragHtml += '<br><span class="detail">' + escapeHtml(fragility.meaning) + '</span>';
                    }}
                    fragilityContent.innerHTML = fragHtml;
                }}

                // Confidence Panel
                const confidenceContent = document.getElementById('confidence-content');
                const confidenceLocked = document.getElementById('confidence-locked');
                const whyConfidence = document.getElementById('why-confidence');

                if (isLocked) {{
                    whyConfidence.classList.add('locked-panel');
                    confidenceLocked.classList.remove('hidden');
                    confidenceContent.innerHTML = '<span style="color:#555">Locked</span>';
                }} else {{
                    whyConfidence.classList.remove('locked-panel');
                    confidenceLocked.classList.add('hidden');
                    let confHtml = '<span class="metric">Structural Only</span>';
                    if (showDetail) {{
                        confHtml += '<br><span class="detail">+ No live injury data</span>';
                        confHtml += '<br><span class="detail">+ No weather data</span>';
                        confHtml += '<br><span class="detail">+ No odds movement</span>';
                    }} else {{
                        confHtml += '<br><span class="detail">Context data not included</span>';
                    }}
                    confidenceContent.innerHTML = confHtml;
                }}

                // ============================================================
                // ALERTS (BEST only)
                // ============================================================
                const alertsPanel = document.getElementById('alerts-panel');
                const alertsContentEl = document.getElementById('alerts-content');
                if (tier === 'best' && explain.alerts && explain.alerts.length > 0) {{
                    alertsPanel.classList.remove('hidden');
                    alertsContentEl.innerHTML = explain.alerts.map(a =>
                        '<div class="alert-item">' + escapeHtml(a) + '</div>'
                    ).join('');
                }} else {{
                    alertsPanel.classList.add('hidden');
                }}

                // ============================================================
                // RECOMMENDATION (BEST only)
                // ============================================================
                const recommendationPanel = document.getElementById('recommendation-panel');
                const recommendationContent = document.getElementById('recommendation-content');
                if (tier === 'best' && explain.recommended_next_step) {{
                    recommendationPanel.classList.remove('hidden');
                    recommendationContent.textContent = explain.recommended_next_step;
                }} else {{
                    recommendationPanel.classList.add('hidden');
                }}

                // ============================================================
                // CONTEXT PANEL (Sprint 3)
                // ============================================================
                const contextPanel = document.getElementById('context-panel');
                const contextContent = document.getElementById('context-content');
                const context = data.context;

                if (context && context.impact) {{
                    contextPanel.classList.remove('hidden');
                    let html = '';

                    // Header with source and timestamp
                    html += '<div class="context-header">';
                    html += '<span>NBA Player Availability</span>';
                    html += '<span class="context-source">Source: ' + escapeHtml(context.source) + '</span>';
                    html += '</div>';

                    // Summary
                    if (context.impact.summary) {{
                        html += '<div class="context-summary">' + escapeHtml(context.impact.summary) + '</div>';
                    }}

                    // Modifiers
                    if (context.impact.modifiers && context.impact.modifiers.length > 0) {{
                        html += '<ul class="context-modifiers">';
                        context.impact.modifiers.forEach(function(mod) {{
                            const modClass = mod.adjustment > 0 ? 'negative' : (mod.adjustment < 0 ? 'positive' : '');
                            html += '<li class="context-modifier ' + modClass + '">';
                            html += '<div class="context-modifier-reason">' + escapeHtml(mod.reason) + '</div>';
                            if (mod.adjustment !== 0) {{
                                const sign = mod.adjustment > 0 ? '+' : '';
                                html += '<div class="context-modifier-adjustment">Fragility adjustment: ' + sign + mod.adjustment.toFixed(1) + '</div>';
                            }}
                            if (mod.affected_players && mod.affected_players.length > 0) {{
                                html += '<div class="context-modifier-adjustment">Players: ' + mod.affected_players.join(', ') + '</div>';
                            }}
                            html += '</li>';
                        }});
                        html += '</ul>';
                    }}

                    // Missing data warnings
                    if (context.missing_data && context.missing_data.length > 0) {{
                        html += '<div class="context-missing">';
                        html += '<strong>Missing data:</strong> ' + context.missing_data.join(', ');
                        html += '</div>';
                    }}

                    // Entities found
                    if (context.entities_found) {{
                        const players = context.entities_found.players || [];
                        const teams = context.entities_found.teams || [];
                        if (players.length > 0 || teams.length > 0) {{
                            html += '<div class="context-entities">';
                            if (players.length > 0) {{
                                html += 'Players detected: ' + players.join(', ');
                            }}
                            if (teams.length > 0) {{
                                html += (players.length > 0 ? ' | ' : '') + 'Teams: ' + teams.join(', ');
                            }}
                            html += '</div>';
                        }}
                    }}

                    contextContent.innerHTML = html;
                }} else {{
                    contextPanel.classList.add('hidden');
                }}

                // ============================================================
                // ALERTS FEED (Sprint 4 - BEST only)
                // ============================================================
                const alertsFeed = document.getElementById('alerts-feed');
                const alertsContent = document.getElementById('alerts-content');

                if (tier === 'best') {{
                    // Fetch alerts for BEST tier
                    fetchAlerts(alertsFeed, alertsContent);
                }} else {{
                    alertsFeed.classList.add('hidden');
                }}

                // ============================================================
                // SHARE & UPGRADE (Sprint 5)
                // ============================================================
                showShareSection(data.evaluation_id);
                showUpgradeNudge(tier);
            }}

            async function fetchAlerts(alertsFeed, alertsContent) {{
                const tier = getSelectedTier();

                try {{
                    const response = await fetch('/app/alerts', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ tier: tier, limit: 10 }})
                    }});

                    const data = await response.json();

                    if (data.tier_locked) {{
                        alertsFeed.classList.add('locked');
                        alertsContent.innerHTML = '<div class="alerts-locked-message">Upgrade to BEST tier for live alerts</div>';
                        alertsFeed.classList.remove('hidden');
                        return;
                    }}

                    alertsFeed.classList.remove('locked');

                    if (data.alerts && data.alerts.length > 0) {{
                        let html = '';
                        data.alerts.forEach(function(alert) {{
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
                        }});
                        alertsContent.innerHTML = html;
                        alertsFeed.classList.remove('hidden');
                    }} else {{
                        alertsContent.innerHTML = '<div class="alerts-empty">No active alerts</div>';
                        alertsFeed.classList.remove('hidden');
                    }}

                }} catch (err) {{
                    console.error('Failed to fetch alerts:', err);
                    alertsFeed.classList.add('hidden');
                }}
            }}

            function escapeHtml(text) {{
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }}

            async function submitEvaluation() {{
                const input = buildBetText();
                const tier = getSelectedTier();

                submitBtn.disabled = true;
                submitBtn.textContent = 'Evaluating...';

                try {{
                    const response = await fetch('/app/evaluate', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ input, tier }})
                    }});

                    const data = await response.json();

                    if (!response.ok) {{
                        showError(data.detail || 'Evaluation failed');
                        return;
                    }}

                    showResults(data);
                }} catch (err) {{
                    showError('Network error: ' + err.message);
                }} finally {{
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Evaluate Parlay';
                    updateUI();
                }}
            }}

            submitBtn.addEventListener('click', submitEvaluation);
            addLegBtn.addEventListener('click', addLeg);

            // ============================================================
            // SHARE FUNCTIONALITY (Sprint 5)
            // ============================================================
            let currentEvaluationId = null;

            const shareSection = document.getElementById('share-section');
            const shareBtn = document.getElementById('share-btn');
            const shareLink = document.getElementById('share-link');
            const shareUrl = document.getElementById('share-url');
            const copyBtn = document.getElementById('copy-btn');
            const upgradeNudge = document.getElementById('upgrade-nudge');
            const upgradeMessage = document.getElementById('upgrade-message');

            shareBtn.addEventListener('click', async function() {{
                if (!currentEvaluationId) return;

                shareBtn.disabled = true;
                shareBtn.textContent = 'Creating link...';

                try {{
                    const response = await fetch('/app/share', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ evaluation_id: currentEvaluationId }})
                    }});

                    const data = await response.json();

                    if (data.token) {{
                        const fullUrl = window.location.origin + data.share_url;
                        shareUrl.value = fullUrl;
                        shareLink.classList.add('visible');
                    }} else {{
                        alert('Failed to create share link');
                    }}
                }} catch (err) {{
                    console.error('Share error:', err);
                    alert('Failed to create share link');
                }} finally {{
                    shareBtn.disabled = false;
                    shareBtn.textContent = 'Share Result';
                }}
            }});

            copyBtn.addEventListener('click', function() {{
                shareUrl.select();
                document.execCommand('copy');
                copyBtn.textContent = 'Copied!';
                setTimeout(function() {{
                    copyBtn.textContent = 'Copy Link';
                }}, 2000);
            }});

            // Show share section when results are displayed
            function showShareSection(evaluationId) {{
                currentEvaluationId = evaluationId;
                if (evaluationId) {{
                    shareSection.classList.remove('hidden');
                    shareLink.classList.remove('visible');
                }} else {{
                    shareSection.classList.add('hidden');
                }}
            }}

            // Show upgrade nudge for non-BEST tiers
            function showUpgradeNudge(tier) {{
                if (tier === 'best') {{
                    upgradeNudge.classList.add('hidden');
                    return;
                }}

                upgradeNudge.classList.remove('hidden');

                if (tier === 'good') {{
                    upgradeMessage.textContent = 'Upgrade to BETTER for structural analysis, or BEST for live alerts and full insights';
                }} else {{
                    upgradeMessage.textContent = 'Upgrade to BEST for live alerts, player availability, and recommended actions';
                }}
            }}

            // Upgrade tier function (called from button)
            window.upgradeTier = function() {{
                const currentTier = getSelectedTier();
                if (currentTier === 'good') {{
                    document.getElementById('tier-better').checked = true;
                }} else if (currentTier === 'better') {{
                    document.getElementById('tier-best').checked = true;
                }}
                // Optionally re-evaluate
                if (currentEvaluationId) {{
                    submitEvaluation();
                }}
            }};

            // Initialize
            init();
        }})();

        // ============================================================
        // TAB SWITCHING
        // ============================================================
        // Global function for programmatic tab switching
        function switchToTab(tabName) {{
            const navTabs = document.querySelectorAll('.nav-tab');
            const tabContents = document.querySelectorAll('.tab-content');

            // Update URL
            const url = new URL(window.location);
            url.searchParams.set('tab', tabName);
            window.history.pushState({{}}, '', url);

            // Switch tabs
            navTabs.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            const activeTab = document.querySelector('.nav-tab[data-tab="' + tabName + '"]');
            if (activeTab) activeTab.classList.add('active');
            const activeContent = document.getElementById('tab-' + tabName);
            if (activeContent) activeContent.classList.add('active');

            // Load history if switching to history tab
            if (tabName === 'history') {{
                loadHistory();
            }}
        }}

        (function() {{
            const navTabs = document.querySelectorAll('.nav-tab');

            navTabs.forEach(tab => {{
                tab.addEventListener('click', function() {{
                    switchToTab(this.dataset.tab);
                }});
            }});
        }})();

        // ============================================================
        // EVALUATE TAB FUNCTIONALITY
        // ============================================================
        (function() {{
            const inputTabs = document.querySelectorAll('.input-tab');
            const inputPanels = document.querySelectorAll('.input-panel');
            const textInput = document.getElementById('eval-text-input');
            const evalSubmitBtn = document.getElementById('eval-submit-btn');
            const evalResultsPlaceholder = document.getElementById('eval-results-placeholder');
            const evalResultsContent = document.getElementById('eval-results-content');
            const evalErrorPanel = document.getElementById('eval-error-panel');

            // Image upload elements
            const fileInput = document.getElementById('file-input');
            const fileUploadArea = document.getElementById('file-upload-area');
            const fileUploadIcon = document.getElementById('file-upload-icon');
            const fileUploadText = document.getElementById('file-upload-text');
            const fileSelected = document.getElementById('file-selected');
            const fileNameSpan = document.getElementById('file-name');
            const clearFileBtn = document.getElementById('clear-file');
            const imageError = document.getElementById('image-error');

            let currentInputMode = 'text';
            let selectedFile = null;
            const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
            const ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];

            // Input type tabs (text/image)
            inputTabs.forEach(tab => {{
                tab.addEventListener('click', function() {{
                    const inputType = this.dataset.input;
                    currentInputMode = inputType;

                    inputTabs.forEach(t => t.classList.remove('active'));
                    inputPanels.forEach(p => p.classList.remove('active'));

                    this.classList.add('active');
                    document.getElementById(inputType + '-input-panel').classList.add('active');

                    updateEvalSubmitState();
                }});
            }});

            // Text input change
            textInput.addEventListener('input', updateEvalSubmitState);

            // ========== FILE UPLOAD HANDLING ==========

            // Click to upload
            fileUploadArea.addEventListener('click', function(e) {{
                if (e.target === clearFileBtn || clearFileBtn.contains(e.target)) return;
                fileInput.click();
            }});

            // Drag and drop
            fileUploadArea.addEventListener('dragover', function(e) {{
                e.preventDefault();
                e.stopPropagation();
                this.classList.add('dragover');
            }});

            fileUploadArea.addEventListener('dragleave', function(e) {{
                e.preventDefault();
                e.stopPropagation();
                this.classList.remove('dragover');
            }});

            fileUploadArea.addEventListener('drop', function(e) {{
                e.preventDefault();
                e.stopPropagation();
                this.classList.remove('dragover');
                if (e.dataTransfer.files.length > 0) {{
                    handleFileSelect(e.dataTransfer.files[0]);
                }}
            }});

            // File input change
            fileInput.addEventListener('change', function() {{
                if (this.files.length > 0) {{
                    handleFileSelect(this.files[0]);
                }}
            }});

            // Clear file
            clearFileBtn.addEventListener('click', function(e) {{
                e.preventDefault();
                e.stopPropagation();
                clearFile();
            }});

            function handleFileSelect(file) {{
                hideImageError();

                // Validate type
                if (!ALLOWED_TYPES.includes(file.type)) {{
                    showImageError('Invalid file type. Please use PNG, JPG, or WebP.');
                    return;
                }}

                // Validate size
                if (file.size > MAX_FILE_SIZE) {{
                    showImageError('File too large. Maximum size is 5MB.');
                    return;
                }}

                selectedFile = file;
                fileUploadArea.classList.add('has-file');
                fileUploadIcon.classList.add('hidden');
                fileUploadText.classList.add('hidden');
                fileSelected.classList.remove('hidden');
                fileNameSpan.textContent = file.name;
                updateEvalSubmitState();
            }}

            function clearFile() {{
                selectedFile = null;
                fileInput.value = '';
                fileUploadArea.classList.remove('has-file');
                fileUploadIcon.classList.remove('hidden');
                fileUploadText.classList.remove('hidden');
                fileSelected.classList.add('hidden');
                hideImageError();
                updateEvalSubmitState();
            }}

            function showImageError(message) {{
                imageError.textContent = message;
                imageError.classList.remove('hidden');
            }}

            function hideImageError() {{
                imageError.classList.add('hidden');
            }}

            // ========== EVALUATION FUNCTIONS ==========

            function updateEvalSubmitState() {{
                if (currentInputMode === 'text') {{
                    evalSubmitBtn.disabled = textInput.value.trim().length < 5;
                }} else if (currentInputMode === 'image') {{
                    evalSubmitBtn.disabled = !selectedFile;
                }} else {{
                    // Bundle mode - submit button not used (redirects to builder)
                    evalSubmitBtn.disabled = true;
                }}
            }}

            function getEvalTier() {{
                const selected = document.querySelector('input[name="eval-tier"]:checked');
                return selected ? selected.value : 'good';
            }}

            function showEvalError(message) {{
                evalResultsPlaceholder.classList.add('hidden');
                evalResultsContent.classList.add('hidden');
                evalErrorPanel.classList.remove('hidden');
                document.getElementById('eval-error-text').textContent = message;
            }}

            function showEvalResults(data, imageParse) {{
                evalResultsPlaceholder.classList.add('hidden');
                evalErrorPanel.classList.add('hidden');
                evalResultsContent.classList.remove('hidden');

                const evaluation = data.evaluation;
                const interpretation = data.interpretation;
                const fragility = interpretation.fragility;
                const explain = data.explain || {{}};
                const tier = (data.input && data.input.tier) || 'good';
                const metrics = evaluation.metrics;
                const correlations = evaluation.correlations || [];

                // === SIGNAL SYSTEM ===
                // Map bucket → signal: low=Blue, medium=Green, high=Yellow, critical=Red
                const signalMap = {{
                    'low': {{ cls: 'signal-blue', label: 'Strong' }},
                    'medium': {{ cls: 'signal-green', label: 'Solid' }},
                    'high': {{ cls: 'signal-yellow', label: 'Fixable' }},
                    'critical': {{ cls: 'signal-red', label: 'Fragile' }}
                }};
                const signal = signalMap[fragility.bucket] || signalMap['medium'];

                const signalBadge = document.getElementById('eval-signal-badge');
                signalBadge.textContent = signal.label;
                signalBadge.className = 'signal-badge ' + signal.cls;

                document.getElementById('eval-signal-score').textContent = Math.round(fragility.display_value);

                // === VERDICT BAR (GOOD+) ===
                const action = evaluation.recommendation.action;
                const verdictAction = document.getElementById('eval-verdict-action');
                const verdictReason = document.getElementById('eval-verdict-reason');
                verdictAction.textContent = action.toUpperCase();
                verdictAction.className = 'verdict-action action-' + action;
                verdictReason.textContent = evaluation.recommendation.reason;

                // === METRICS GRID (GOOD+) ===
                document.getElementById('eval-metric-leg').textContent = '+' + (metrics.leg_penalty || 0).toFixed(1);
                document.getElementById('eval-metric-corr').textContent = '+' + (metrics.correlation_penalty || 0).toFixed(1);
                document.getElementById('eval-metric-raw').textContent = (metrics.raw_fragility || 0).toFixed(1);
                document.getElementById('eval-metric-final').textContent = Math.round(metrics.final_fragility || 0);

                // === IMPROVEMENT TIPS (GOOD+) ===
                const tipsContent = document.getElementById('eval-tips-content');
                const tipsPanel = document.getElementById('eval-tips-panel');
                const whatToDo = fragility.what_to_do || '';
                const meaning = fragility.meaning || '';
                if (whatToDo || meaning) {{
                    let tipsHtml = '';
                    if (meaning) {{
                        tipsHtml += '<div class="tip-item">' + meaning + '</div>';
                    }}
                    if (whatToDo) {{
                        tipsHtml += '<div class="tip-item">' + whatToDo + '</div>';
                    }}
                    tipsContent.innerHTML = tipsHtml;
                    tipsPanel.classList.remove('hidden');
                }} else {{
                    tipsPanel.classList.add('hidden');
                }}

                // === CORRELATIONS PANEL (BETTER+) ===
                const corrPanel = document.getElementById('eval-correlations-panel');
                const corrList = document.getElementById('eval-correlations-list');
                if ((tier === 'better' || tier === 'best') && correlations.length > 0) {{
                    let corrHtml = '';
                    correlations.forEach(function(c) {{
                        corrHtml += '<div class="correlation-item">';
                        corrHtml += '<span>' + c.block_a + ' / ' + c.block_b + '</span>';
                        corrHtml += '<span class="correlation-type">' + c.type + '</span>';
                        corrHtml += '<span class="correlation-penalty">+' + (c.penalty || 0).toFixed(1) + '</span>';
                        corrHtml += '</div>';
                    }});
                    corrList.innerHTML = corrHtml;
                    corrPanel.classList.remove('hidden');
                }} else {{
                    corrPanel.classList.add('hidden');
                }}

                // === SUMMARY INSIGHTS (BETTER+) ===
                const summaryPanel = document.getElementById('eval-summary-panel');
                const summaryList = document.getElementById('eval-summary-list');
                const summaryItems = explain.summary || [];
                if ((tier === 'better' || tier === 'best') && summaryItems.length > 0) {{
                    let summaryHtml = '';
                    summaryItems.forEach(function(s) {{
                        summaryHtml += '<div class="summary-item">' + s + '</div>';
                    }});
                    summaryList.innerHTML = summaryHtml;
                    summaryPanel.classList.remove('hidden');
                }} else {{
                    summaryPanel.classList.add('hidden');
                }}

                // === ALERTS (BEST only) ===
                const alertsPanel = document.getElementById('eval-alerts-panel');
                const alertsList = document.getElementById('eval-alerts-list');
                const alertItems = explain.alerts || [];
                if (tier === 'best' && alertItems.length > 0) {{
                    let alertsHtml = '';
                    alertItems.forEach(function(a) {{
                        alertsHtml += '<div class="alert-detail-item">' + a + '</div>';
                    }});
                    alertsList.innerHTML = alertsHtml;
                    alertsPanel.classList.remove('hidden');
                }} else {{
                    alertsPanel.classList.add('hidden');
                }}

                // === IMAGE PARSE INFO ===
                const existingParseInfo = evalResultsContent.querySelector('.image-parse-info');
                if (existingParseInfo) existingParseInfo.remove();
                if (imageParse) {{
                    const confidencePct = Math.round((imageParse.confidence || 0) * 100);
                    let parseHtml = '<div class="image-parse-info">';
                    parseHtml += '<span class="image-parse-confidence">Parsed from image (' + confidencePct + '% confidence)</span>';
                    if (imageParse.notes && imageParse.notes.length > 0) {{
                        parseHtml += '<div class="image-parse-notes">' + imageParse.notes.join(' | ') + '</div>';
                    }}
                    parseHtml += '</div>';
                    evalResultsContent.insertAdjacentHTML('afterbegin', parseHtml);
                }}

                // === ENABLE BUILDER CTA ===
                const builderCtaBtn = document.getElementById('builder-cta-btn');
                if (builderCtaBtn) {{
                    builderCtaBtn.disabled = false;
                    builderCtaBtn.classList.remove('disabled');
                    builderCtaBtn.title = 'Build a custom parlay';
                    builderCtaBtn.onclick = function() {{ switchToTab('builder'); }};
                }}

                // Store last eval data for re-evaluate
                window._lastEvalData = data;
            }}

            // Submit evaluation
            evalSubmitBtn.addEventListener('click', async function() {{
                const tier = getEvalTier();

                evalSubmitBtn.disabled = true;
                evalSubmitBtn.textContent = 'Evaluating...';

                try {{
                    let response, data;

                    if (currentInputMode === 'text') {{
                        // Text evaluation
                        const input = textInput.value.trim();
                        if (input.length < 5) {{
                            showEvalError('Please enter more text to evaluate');
                            return;
                        }}

                        response = await fetch('/app/evaluate', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ input, tier }})
                        }});

                        data = await response.json();

                        if (!response.ok) {{
                            showEvalError(data.detail || 'Evaluation failed');
                            return;
                        }}

                        showEvalResults(data, null);

                    }} else {{
                        // Image evaluation
                        if (!selectedFile) {{
                            showEvalError('Please select an image');
                            return;
                        }}

                        fileUploadArea.classList.add('uploading');

                        const formData = new FormData();
                        formData.append('file', selectedFile);
                        formData.append('tier', tier);

                        response = await fetch('/app/evaluate/image', {{
                            method: 'POST',
                            body: formData
                        }});

                        data = await response.json();

                        fileUploadArea.classList.remove('uploading');

                        if (!response.ok) {{
                            showEvalError(data.detail || 'Image evaluation failed');
                            return;
                        }}

                        showEvalResults(data, data.image_parse);
                    }}
                }} catch (err) {{
                    showEvalError('Network error: ' + err.message);
                    if (fileUploadArea) fileUploadArea.classList.remove('uploading');
                }} finally {{
                    evalSubmitBtn.disabled = false;
                    evalSubmitBtn.textContent = 'Evaluate';
                    updateEvalSubmitState();
                }}
            }});

            // Re-Evaluate button: reset results and focus input
            const reEvalBtn = document.getElementById('eval-action-reeval');
            if (reEvalBtn) {{
                reEvalBtn.addEventListener('click', function() {{
                    evalResultsContent.classList.add('hidden');
                    evalResultsPlaceholder.classList.remove('hidden');
                    evalErrorPanel.classList.add('hidden');
                    if (currentInputMode === 'text') {{
                        textInput.focus();
                        textInput.select();
                    }}
                    updateEvalSubmitState();
                }});
            }}

            // Save button: persist evaluation
            const saveBtn = document.getElementById('eval-action-save');
            if (saveBtn) {{
                saveBtn.addEventListener('click', function() {{
                    if (window._lastEvalData && window._lastEvalData.evaluation_id) {{
                        saveBtn.textContent = 'Saved';
                        saveBtn.disabled = true;
                        saveBtn.style.background = '#4ade80';
                        saveBtn.style.color = '#000';
                    }} else {{
                        saveBtn.textContent = 'Login to Save';
                        saveBtn.disabled = true;
                    }}
                }});
            }}
        }})();

        // ============================================================
        // HISTORY TAB FUNCTIONALITY
        // ============================================================
        (function() {{
            let historyLoaded = false;

            window.loadHistory = async function() {{
                if (historyLoaded) return;

                const historyContent = document.getElementById('history-content');

                // Check if logged in (if login prompt is shown, don't try to load)
                if (historyContent.querySelector('.login-prompt')) {{
                    return;
                }}

                try {{
                    const response = await fetch('/app/account/history');
                    const data = await response.json();

                    if (!data.logged_in) {{
                        historyContent.innerHTML = "<div class='login-prompt'><p>Sign in to view your evaluation history</p><a href='/login'>Login</a></div>";
                        return;
                    }}

                    const evaluations = data.evaluations || [];

                    if (evaluations.length === 0) {{
                        historyContent.innerHTML = "<div class='history-empty'>No evaluations yet. Build a parlay and evaluate it!</div>";
                        return;
                    }}

                    let html = '';
                    evaluations.forEach(function(e) {{
                        const result = e.result || {{}};
                        const interpretation = result.interpretation || {{}};
                        const fragility = interpretation.fragility || {{}};
                        const bucket = fragility.bucket || 'medium';
                        const score = Math.round(fragility.display_value || 0);
                        const date = new Date(e.created_at).toLocaleString();

                        html += '<div class="history-item">';
                        html += '<div class="history-date">' + date + '</div>';
                        html += '<div class="history-text">' + (e.input_text || 'N/A') + '</div>';
                        html += '<span class="history-grade ' + bucket + '">' + score + ' - ' + bucket.toUpperCase() + '</span>';
                        html += '</div>';
                    }});

                    historyContent.innerHTML = html;
                    historyLoaded = true;

                }} catch (err) {{
                    console.error('Failed to load history:', err);
                    historyContent.innerHTML = "<div class='history-empty'>Failed to load history</div>";
                }}
            }};

            // Load history if starting on history tab
            const activeTab = new URLSearchParams(window.location.search).get('tab');
            if (activeTab === 'history') {{
                loadHistory();
            }}
        }})();
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


@router.get("/login", response_class=HTMLResponse)
async def login_page(raw_request: Request):
    """
    Login/signup page.

    Redirects to /app if already authenticated.
    """
    from auth.middleware import get_session_id
    from auth.service import get_current_user

    session_id = get_session_id(raw_request)
    user = get_current_user(session_id)

    if user:
        # Already logged in, redirect to app
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/app", status_code=302)

    return HTMLResponse(content=_get_login_page_html(redirect_to="/app"))


@router.get("/app", response_class=HTMLResponse)
async def app_page(raw_request: Request, tab: str = "evaluate"):
    """
    Main application page with tabbed interface.

    Tabs:
    - discover: Product intro (default landing)
    - evaluate: Text/image evaluation (default)
    - builder: Parlay builder
    - history: Saved history (requires login)

    Returns HTML with unified app shell.
    """
    from auth.middleware import get_session_id
    from auth.service import get_current_user

    session_id = get_session_id(raw_request)
    user = get_current_user(session_id)

    return _get_app_page_html(user=user, active_tab=tab)


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
        }

        # Sprint 5: Persist evaluation for sharing
        # Sprint 6A: Associate with user if logged in
        try:
            from persistence.evaluations import save_evaluation
            from persistence.metrics import record_evaluation_latency
            from auth.middleware import get_session_id
            from auth.service import get_current_user as get_user_from_session

            # Get user_id if logged in
            session_id = get_session_id(raw_request)
            current_user = get_user_from_session(session_id)
            user_id = current_user.id if current_user else None

            eval_id = save_evaluation(
                parlay_id=str(eval_response.parlay_id),
                tier=result.tier,
                input_text=normalized.input_text,
                result=response_data,
                correlation_id=request_id,
                user_id=user_id,
            )
            response_data["evaluation_id"] = eval_id

            # Record latency metric
            record_evaluation_latency(latency_ms, result.tier)

        except Exception as persist_err:
            _logger.warning(f"Failed to persist evaluation: {persist_err}")
            # Don't fail the request if persistence fails

        return response_data

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
# Image Evaluation API (Sprint 7.2)
# =============================================================================


@router.post("/app/evaluate/image")
async def evaluate_image(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Evaluate a bet slip image using OpenAI Vision API.

    Accepts image upload, extracts bet text, and runs through evaluation pipeline.
    Returns same response shape as text evaluation plus image_parse metadata.

    Rate limited: shares limit with /app/evaluate.
    """
    from app.image_eval import (
        is_image_eval_enabled,
        extract_bet_text_from_image,
        ImageParseResult,
    )
    from app.image_eval.config import (
        is_openai_configured,
        MAX_IMAGE_SIZE,
        ALLOWED_IMAGE_TYPES,
        ALLOWED_EXTENSIONS,
    )

    request_id = get_request_id(request) or str(uuid.uuid4())[:8]
    client_ip = get_client_ip(request)
    start_time = time.perf_counter()

    # Check if image evaluation is enabled
    if not is_image_eval_enabled():
        return JSONResponse(
            status_code=503,
            content={
                "request_id": request_id,
                "error": "Image evaluation is disabled",
                "code": "FEATURE_DISABLED",
            },
        )

    # Check if OpenAI is configured
    if not is_openai_configured():
        return JSONResponse(
            status_code=503,
            content={
                "request_id": request_id,
                "error": "Image evaluation is not configured",
                "code": "NOT_CONFIGURED",
            },
        )

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

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        return JSONResponse(
            status_code=400,
            content={
                "request_id": request_id,
                "error": "Invalid file type",
                "detail": f"Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}",
                "code": "INVALID_FILE_TYPE",
            },
        )

    # Validate file extension
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return JSONResponse(
            status_code=400,
            content={
                "request_id": request_id,
                "error": "Invalid file extension",
                "detail": f"Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}",
                "code": "INVALID_EXTENSION",
            },
        )

    try:
        # Read file content
        image_bytes = await file.read()

        # Validate file size
        if len(image_bytes) > MAX_IMAGE_SIZE:
            return JSONResponse(
                status_code=400,
                content={
                    "request_id": request_id,
                    "error": "File too large",
                    "detail": f"Maximum size: {MAX_IMAGE_SIZE // (1024 * 1024)}MB",
                    "code": "FILE_TOO_LARGE",
                },
            )

        # Extract bet text from image using OpenAI Vision
        _logger.info(f"[{request_id}] Extracting bet text from image: {filename}")
        parse_result = await extract_bet_text_from_image(image_bytes)

        # Check extraction confidence
        if parse_result.confidence < 0.3:
            return JSONResponse(
                status_code=422,
                content={
                    "request_id": request_id,
                    "error": "Could not extract bet information",
                    "detail": "The image does not appear to contain clear bet information",
                    "code": "LOW_CONFIDENCE",
                    "image_parse": parse_result.to_dict(),
                },
            )

        if not parse_result.bet_text.strip():
            return JSONResponse(
                status_code=422,
                content={
                    "request_id": request_id,
                    "error": "No bet text extracted",
                    "detail": "Could not identify any bet information in the image",
                    "code": "NO_BET_TEXT",
                    "image_parse": parse_result.to_dict(),
                },
            )

        _logger.info(
            f"[{request_id}] Extracted bet text (confidence={parse_result.confidence:.2f}): "
            f"{parse_result.bet_text[:100]}..."
        )

        # Get tier from session (default to "good")
        tier = "good"
        session_id = request.cookies.get("session_id")
        if session_id:
            from auth.middleware import get_session_id
            from auth.service import get_current_user as get_user_from_session
            current_user = get_user_from_session(session_id)
            if current_user and hasattr(current_user, 'tier') and current_user.tier:
                tier = current_user.tier

        # Normalize via Airlock (same as text endpoint)
        normalized = airlock_ingest(
            input_text=parse_result.bet_text,
            tier=tier,
        )

        # Run through evaluation pipeline (same as text endpoint)
        from app.pipeline import run_evaluation
        eval_start = time.perf_counter()
        result = run_evaluation(normalized)
        eval_latency = (time.perf_counter() - eval_start) * 1000

        total_latency = (time.perf_counter() - start_time) * 1000

        # Log successful evaluation
        _log_request(
            request_id=request_id,
            client_ip=client_ip,
            tier=result.tier,
            input_length=len(parse_result.bet_text),
            status_code=200,
            latency_ms=total_latency,
        )

        # Build response matching text endpoint shape + image_parse
        eval_response = result.evaluation
        response = {
            "request_id": request_id,
            "success": True,
            "input": {
                "bet_text": normalized.input_text,
                "tier": result.tier,
                "source": "image",
                "filename": filename,
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
            "image_parse": {
                "confidence": parse_result.confidence,
                "notes": parse_result.notes,
                "missing": parse_result.missing,
            },
            "latency_ms": {
                "total": round(total_latency, 2),
                "evaluation": round(eval_latency, 2),
            },
        }

        return response

    except Exception as e:
        _logger.error(
            f"[{request_id}] Image evaluation error: {e}",
            exc_info=True,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000
        _log_request(
            request_id=request_id,
            client_ip=client_ip,
            tier="unknown",
            input_length=0,
            status_code=500,
            latency_ms=latency_ms,
            error_type="INTERNAL_ERROR",
        )
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": "Image evaluation failed",
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


# =============================================================================
# Share API (Sprint 5)
# =============================================================================


class ShareRequest(BaseModel):
    """Request to create a shareable link."""

    evaluation_id: str = Field(..., description="Evaluation ID to share")


@router.post("/app/share")
async def create_share_link(request: ShareRequest, raw_request: Request):
    """
    Create a shareable link for an evaluation result.

    Returns a short token that can be used to view the result.
    Share pages are read-only and safe (no PII).
    """
    from persistence.shares import create_share
    from persistence.metrics import record_counter, METRIC_SHARE_CREATED
    from auth.middleware import get_session_id
    from auth.service import get_current_user as get_user_from_session

    request_id = get_request_id(raw_request) or "unknown"

    # Get user_id if logged in
    session_id = get_session_id(raw_request)
    current_user = get_user_from_session(session_id)
    user_id = current_user.id if current_user else None

    try:
        token = create_share(request.evaluation_id, user_id=user_id)

        if token is None:
            return JSONResponse(
                status_code=404,
                content={
                    "request_id": request_id,
                    "error": "Evaluation not found",
                    "detail": "Cannot create share link for unknown evaluation",
                },
            )

        # Record metric
        try:
            record_counter(METRIC_SHARE_CREATED)
        except Exception:
            pass  # Don't fail on metrics

        # Build share URL
        share_url = f"/app/share/{token}"

        return {
            "request_id": request_id,
            "token": token,
            "share_url": share_url,
            "expires_in_days": 30,
        }

    except Exception as e:
        _logger.error(f"Share creation error: {e}", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": "Internal error",
                "detail": str(e),
            },
        )


@router.get("/app/share/{token}", response_class=HTMLResponse)
async def view_shared_result(token: str, raw_request: Request):
    """
    View a shared evaluation result.

    Read-only page showing the evaluation without tier restrictions.
    Increments view count on each access.
    """
    from persistence.evaluations import get_evaluation_by_token
    from persistence.metrics import record_counter, METRIC_SHARE_VIEWED

    request_id = get_request_id(raw_request) or "unknown"

    try:
        evaluation = get_evaluation_by_token(token)

        if evaluation is None:
            return HTMLResponse(
                content=_get_share_not_found_html(),
                status_code=404,
            )

        # Record view metric
        try:
            record_counter(METRIC_SHARE_VIEWED)
        except Exception:
            pass

        return HTMLResponse(
            content=_get_share_page_html(evaluation, token),
        )

    except Exception as e:
        _logger.error(f"Share view error: {e}", extra={"request_id": request_id})
        return HTMLResponse(
            content=_get_share_error_html(),
            status_code=500,
        )


def _get_share_not_found_html() -> str:
    """HTML for share not found."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Link Expired - DNA Bet Engine</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: system-ui; background: #111; color: #eee; padding: 2rem; text-align: center; }
        .container { max-width: 500px; margin: 4rem auto; }
        h1 { color: #e74c3c; }
        a { color: #3498db; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Link Expired or Not Found</h1>
        <p>This shared result is no longer available.</p>
        <p>Share links expire after 30 days.</p>
        <p><a href="/app">Create a new evaluation</a></p>
    </div>
</body>
</html>"""


def _get_share_error_html() -> str:
    """HTML for share error."""
    return """<!DOCTYPE html>
<html>
<head>
    <title>Error - DNA Bet Engine</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: system-ui; background: #111; color: #eee; padding: 2rem; text-align: center; }
        .container { max-width: 500px; margin: 4rem auto; }
        h1 { color: #e74c3c; }
        a { color: #3498db; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Something went wrong</h1>
        <p>Unable to load this shared result.</p>
        <p><a href="/app">Go to DNA Bet Engine</a></p>
    </div>
</body>
</html>"""


def _get_share_page_html(evaluation: dict, token: str) -> str:
    """Generate HTML for shared result page."""
    result = evaluation.get("result", {})
    eval_data = result.get("evaluation", {})
    explain = result.get("explain", {})
    context = result.get("context", {})

    # Extract key metrics
    metrics = eval_data.get("metrics", {})
    fragility = metrics.get("final_fragility", 0)
    recommendation = eval_data.get("recommendation", {})
    action = recommendation.get("action", "unknown")
    reason = recommendation.get("reason", "")

    # Fragility bucket
    if fragility <= 30:
        bucket = "Low Risk"
        bucket_color = "#27ae60"
    elif fragility <= 50:
        bucket = "Moderate"
        bucket_color = "#f39c12"
    elif fragility <= 70:
        bucket = "High Risk"
        bucket_color = "#e67e22"
    else:
        bucket = "Extreme Risk"
        bucket_color = "#e74c3c"

    # Format correlations
    correlations = eval_data.get("correlations", [])
    corr_html = ""
    if correlations:
        corr_html = "<ul>"
        for c in correlations[:5]:
            corr_html += f"<li>{c.get('type', 'unknown')}: +{c.get('penalty', 0):.1f}</li>"
        corr_html += "</ul>"

    # Format context
    context_html = ""
    if context and context.get("impact"):
        impact = context["impact"]
        if impact.get("summary"):
            context_html = f"<p>{impact['summary']}</p>"

    # View count
    view_count = evaluation.get("view_count", 1)

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Shared Result - DNA Bet Engine</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            background: #111;
            color: #eee;
            margin: 0;
            padding: 1rem;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #333;
        }}
        header h1 {{
            color: #f39c12;
            margin: 0;
            font-size: 1.5rem;
        }}
        header p {{
            color: #666;
            font-size: 0.85rem;
            margin: 0.5rem 0 0;
        }}
        .grade-display {{
            text-align: center;
            padding: 2rem;
            background: #1a1a1a;
            border-radius: 8px;
            margin-bottom: 1.5rem;
        }}
        .grade-value {{
            font-size: 3rem;
            font-weight: bold;
            color: {bucket_color};
        }}
        .grade-bucket {{
            font-size: 1.25rem;
            color: {bucket_color};
            margin-top: 0.5rem;
        }}
        .section {{
            background: #1a1a1a;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .section h3 {{
            margin: 0 0 0.75rem;
            color: #f39c12;
            font-size: 1rem;
        }}
        .section p, .section ul {{
            margin: 0;
            color: #ccc;
        }}
        .section ul {{
            padding-left: 1.25rem;
        }}
        .recommendation {{
            border-left: 3px solid {bucket_color};
            padding-left: 1rem;
        }}
        .bet-text {{
            font-family: monospace;
            background: #0a0a0a;
            padding: 0.75rem;
            border-radius: 4px;
            font-size: 0.9rem;
            word-break: break-word;
        }}
        .footer {{
            text-align: center;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #333;
            color: #666;
            font-size: 0.85rem;
        }}
        .footer a {{
            color: #3498db;
        }}
        .meta {{
            font-size: 0.75rem;
            color: #666;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>DNA Bet Engine</h1>
            <p>Shared Parlay Analysis</p>
        </header>

        <div class="grade-display">
            <div class="grade-value">{fragility:.0f}</div>
            <div class="grade-bucket">{bucket}</div>
        </div>

        <div class="section">
            <h3>Bet Analyzed</h3>
            <div class="bet-text">{evaluation.get('input_text', 'N/A')}</div>
        </div>

        <div class="section recommendation">
            <h3>Recommendation</h3>
            <p><strong>{action.upper()}</strong></p>
            <p>{reason}</p>
        </div>

        {f'<div class="section"><h3>Correlations Detected</h3>{corr_html}</div>' if corr_html else ''}

        {f'<div class="section"><h3>Context</h3>{context_html}</div>' if context_html else ''}

        <div class="meta">
            Viewed {view_count} time{'s' if view_count != 1 else ''}
        </div>

        <div class="footer">
            <p>Want to analyze your own parlays?</p>
            <p><a href="/app">Try DNA Bet Engine</a></p>
        </div>
    </div>
</body>
</html>"""


# =============================================================================
# Auth API (Sprint 6A)
# =============================================================================


class SignupRequest(BaseModel):
    """Request schema for user signup."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")


class LoginRequest(BaseModel):
    """Request schema for user login."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="Password")


@router.post("/app/auth/signup")
async def signup(request: SignupRequest, raw_request: Request, response: Response):
    """
    Create a new user account.

    Returns user info and sets session cookie on success.
    """
    from auth.service import create_user, create_session, UserExistsError, WeakPasswordError
    from auth.middleware import set_session_cookie

    request_id = get_request_id(raw_request) or "unknown"

    try:
        # Create user
        user = create_user(
            email=request.email,
            password=request.password,
            tier="GOOD",  # Default tier for new users
        )

        # Create session
        client_ip = get_client_ip(raw_request)
        user_agent = raw_request.headers.get("user-agent")
        session = create_session(
            user_id=user.id,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Set session cookie
        set_session_cookie(response, session.id)

        return {
            "request_id": request_id,
            "success": True,
            "user": user.to_dict(),
        }

    except UserExistsError as e:
        return JSONResponse(
            status_code=409,
            content={
                "request_id": request_id,
                "error": "user_exists",
                "detail": str(e),
            },
        )

    except WeakPasswordError as e:
        return JSONResponse(
            status_code=400,
            content={
                "request_id": request_id,
                "error": "weak_password",
                "detail": str(e),
            },
        )

    except Exception as e:
        _logger.error(f"Signup error: {e}", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": "internal_error",
                "detail": "Failed to create account",
            },
        )


@router.post("/app/auth/login")
async def login(request: LoginRequest, raw_request: Request, response: Response):
    """
    Authenticate user and create session.

    Returns user info and sets session cookie on success.
    """
    from auth.service import authenticate_user, create_session, InvalidCredentialsError
    from auth.middleware import set_session_cookie

    request_id = get_request_id(raw_request) or "unknown"

    try:
        # Authenticate
        user = authenticate_user(request.email, request.password)

        # Create session
        client_ip = get_client_ip(raw_request)
        user_agent = raw_request.headers.get("user-agent")
        session = create_session(
            user_id=user.id,
            ip_address=client_ip,
            user_agent=user_agent,
        )

        # Set session cookie
        set_session_cookie(response, session.id)

        return {
            "request_id": request_id,
            "success": True,
            "user": user.to_dict(),
        }

    except InvalidCredentialsError:
        return JSONResponse(
            status_code=401,
            content={
                "request_id": request_id,
                "error": "invalid_credentials",
                "detail": "Invalid email or password",
            },
        )

    except Exception as e:
        _logger.error(f"Login error: {e}", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": "internal_error",
                "detail": "Login failed",
            },
        )


@router.post("/app/auth/logout")
async def logout(raw_request: Request, response: Response):
    """
    Log out the current user.

    Invalidates the session and clears the session cookie.
    """
    from auth.middleware import get_session_id, clear_session_cookie
    from auth.service import invalidate_session

    request_id = get_request_id(raw_request) or "unknown"

    try:
        session_id = get_session_id(raw_request)
        if session_id:
            invalidate_session(session_id)

        clear_session_cookie(response)

        return {
            "request_id": request_id,
            "success": True,
            "message": "Logged out successfully",
        }

    except Exception as e:
        _logger.error(f"Logout error: {e}", extra={"request_id": request_id})
        # Still clear the cookie even if invalidation fails
        from auth.middleware import clear_session_cookie
        clear_session_cookie(response)
        return {
            "request_id": request_id,
            "success": True,
            "message": "Logged out",
        }


@router.get("/app/auth/me")
async def get_current_user_info(raw_request: Request):
    """
    Get current user info from session.

    Returns null user if not logged in (anonymous).
    """
    from auth.middleware import get_session_id
    from auth.service import get_current_user

    request_id = get_request_id(raw_request) or "unknown"
    session_id = get_session_id(raw_request)
    user = get_current_user(session_id)

    return {
        "request_id": request_id,
        "logged_in": user is not None,
        "user": user.to_dict() if user else None,
    }


# =============================================================================
# Account Page (Sprint 6A)
# =============================================================================


@router.get("/app/account", response_class=HTMLResponse)
async def account_page(raw_request: Request):
    """
    Account page showing user info and saved history.

    Redirects to login if not authenticated.
    """
    from auth.middleware import get_session_id
    from auth.service import get_current_user
    from fastapi.responses import RedirectResponse

    session_id = get_session_id(raw_request)
    user = get_current_user(session_id)

    if not user:
        # Redirect to login page
        return RedirectResponse(url="/login", status_code=302)

    return HTMLResponse(
        content=_get_account_page_html(user),
    )


@router.get("/app/account/history")
async def get_user_history(raw_request: Request):
    """
    Get evaluation history for the current user.

    Returns empty list for anonymous users.
    """
    from auth.middleware import get_session_id
    from auth.service import get_current_user
    from persistence.evaluations import get_evaluations_by_user
    from persistence.shares import get_shares_by_user

    request_id = get_request_id(raw_request) or "unknown"
    session_id = get_session_id(raw_request)
    user = get_current_user(session_id)

    if not user:
        return {
            "request_id": request_id,
            "logged_in": False,
            "evaluations": [],
            "shares": [],
        }

    try:
        evaluations = get_evaluations_by_user(user.id, limit=50)
        shares = get_shares_by_user(user.id, limit=50)

        return {
            "request_id": request_id,
            "logged_in": True,
            "user_id": user.id,
            "evaluations": evaluations,
            "shares": shares,
        }

    except Exception as e:
        _logger.error(f"History fetch error: {e}", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": "internal_error",
                "detail": "Failed to fetch history",
            },
        )


# =============================================================================
# Billing API (Sprint 6B)
# =============================================================================


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    tier: str = Field(default="BEST", description="Tier to subscribe to")


@router.post("/app/billing/checkout")
async def create_checkout(request: CheckoutRequest, raw_request: Request):
    """
    Create a Stripe Checkout session for subscription.

    Requires authenticated user.
    """
    from auth.middleware import get_session_id
    from auth.service import get_current_user
    from billing.service import create_checkout_session, BillingDisabledError, CheckoutError
    from billing.stripe_client import is_billing_enabled

    request_id = get_request_id(raw_request) or "unknown"

    # Require authentication
    session_id = get_session_id(raw_request)
    user = get_current_user(session_id)

    if not user:
        return JSONResponse(
            status_code=401,
            content={
                "request_id": request_id,
                "error": "authentication_required",
                "detail": "Please log in to upgrade",
            },
        )

    # Check if billing is enabled
    if not is_billing_enabled():
        return JSONResponse(
            status_code=503,
            content={
                "request_id": request_id,
                "error": "billing_disabled",
                "detail": "Billing is not configured",
            },
        )

    # Check if user already has BEST tier
    if user.tier == "BEST":
        return JSONResponse(
            status_code=400,
            content={
                "request_id": request_id,
                "error": "already_subscribed",
                "detail": "You already have BEST tier",
            },
        )

    try:
        # Build URLs
        base_url = str(raw_request.base_url).rstrip("/")
        success_url = f"{base_url}/app/account?upgraded=true"
        cancel_url = f"{base_url}/app/account?cancelled=true"

        result = create_checkout_session(
            user_id=user.id,
            user_email=user.email,
            success_url=success_url,
            cancel_url=cancel_url,
            tier=request.tier,
        )

        return {
            "request_id": request_id,
            "session_id": result["session_id"],
            "checkout_url": result["checkout_url"],
        }

    except BillingDisabledError as e:
        return JSONResponse(
            status_code=503,
            content={
                "request_id": request_id,
                "error": "billing_disabled",
                "detail": str(e),
            },
        )

    except CheckoutError as e:
        _logger.error(f"Checkout error: {e}", extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": "checkout_failed",
                "detail": str(e),
            },
        )


@router.post("/app/billing/webhook")
async def handle_stripe_webhook(raw_request: Request):
    """
    Handle Stripe webhook events.

    Verifies signature and processes subscription events.
    """
    from billing.webhooks import verify_webhook_signature, process_webhook_event, SignatureVerificationError, WebhookError

    request_id = get_request_id(raw_request) or "unknown"

    # Get raw body and signature
    try:
        payload = await raw_request.body()
        signature = raw_request.headers.get("stripe-signature", "")

        if not signature:
            _logger.warning("Webhook received without signature")
            return JSONResponse(
                status_code=400,
                content={"error": "Missing signature"},
            )

        # Verify and parse event
        event = verify_webhook_signature(payload, signature)

        # Process the event
        success, message = process_webhook_event(event)

        if success:
            return {"received": True, "message": message}
        else:
            _logger.warning(f"Webhook processing failed: {message}")
            return JSONResponse(
                status_code=500,
                content={"error": message},
            )

    except SignatureVerificationError as e:
        _logger.warning(f"Webhook signature verification failed: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid signature"},
        )

    except WebhookError as e:
        _logger.error(f"Webhook error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )

    except Exception as e:
        _logger.error(f"Unexpected webhook error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal error"},
        )


@router.get("/app/billing/portal")
async def get_billing_portal(raw_request: Request):
    """
    Get Stripe Customer Portal URL for subscription management.

    Requires authenticated user with active subscription.
    """
    from auth.middleware import get_session_id
    from auth.service import get_current_user
    from billing.service import get_customer_portal_url

    request_id = get_request_id(raw_request) or "unknown"

    # Require authentication
    session_id = get_session_id(raw_request)
    user = get_current_user(session_id)

    if not user:
        return JSONResponse(
            status_code=401,
            content={
                "request_id": request_id,
                "error": "authentication_required",
                "detail": "Please log in",
            },
        )

    if not user.stripe_customer_id:
        return JSONResponse(
            status_code=400,
            content={
                "request_id": request_id,
                "error": "no_subscription",
                "detail": "No subscription found",
            },
        )

    # Build return URL
    base_url = str(raw_request.base_url).rstrip("/")
    return_url = f"{base_url}/app/account"

    portal_url = get_customer_portal_url(user.id, return_url)

    if not portal_url:
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": "portal_failed",
                "detail": "Could not create portal session",
            },
        )

    return {
        "request_id": request_id,
        "portal_url": portal_url,
    }


def _get_login_page_html(redirect_to: str = "/app") -> str:
    """HTML for login/signup page."""
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Login - DNA Bet Engine</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
        }}
        .container {{
            width: 100%;
            max-width: 400px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 2rem;
        }}
        .header h1 {{
            color: #f39c12;
            font-size: 1.75rem;
            margin-bottom: 0.5rem;
        }}
        .header p {{
            color: #888;
        }}
        .tabs {{
            display: flex;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid #333;
        }}
        .tab {{
            flex: 1;
            padding: 0.75rem;
            text-align: center;
            cursor: pointer;
            color: #888;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}
        .tab.active {{
            color: #f39c12;
            border-bottom-color: #f39c12;
        }}
        .tab:hover {{
            color: #f39c12;
        }}
        .form-panel {{
            display: none;
        }}
        .form-panel.active {{
            display: block;
        }}
        .form-group {{
            margin-bottom: 1rem;
        }}
        label {{
            display: block;
            margin-bottom: 0.5rem;
            color: #aaa;
            font-size: 0.9rem;
        }}
        input {{
            width: 100%;
            padding: 0.75rem;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 4px;
            color: #e0e0e0;
            font-size: 1rem;
        }}
        input:focus {{
            outline: none;
            border-color: #f39c12;
        }}
        .submit-btn {{
            width: 100%;
            padding: 0.875rem;
            background: #f39c12;
            color: #111;
            border: none;
            border-radius: 4px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .submit-btn:hover {{
            background: #e67e22;
        }}
        .submit-btn:disabled {{
            background: #555;
            cursor: not-allowed;
        }}
        .error-msg {{
            color: #e74c3c;
            font-size: 0.9rem;
            margin-top: 0.5rem;
            display: none;
        }}
        .error-msg.visible {{
            display: block;
        }}
        .footer {{
            text-align: center;
            margin-top: 2rem;
            color: #666;
            font-size: 0.85rem;
        }}
        .footer a {{
            color: #4a9eff;
            text-decoration: none;
        }}
        .password-requirements {{
            font-size: 0.75rem;
            color: #666;
            margin-top: 0.25rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>DNA Bet Engine</h1>
            <p>Sign in to save your history</p>
        </div>

        <div class="tabs">
            <div class="tab active" data-tab="login">Login</div>
            <div class="tab" data-tab="signup">Sign Up</div>
        </div>

        <div class="form-panel active" id="login-panel">
            <form id="login-form">
                <div class="form-group">
                    <label for="login-email">Email</label>
                    <input type="email" id="login-email" required autocomplete="email">
                </div>
                <div class="form-group">
                    <label for="login-password">Password</label>
                    <input type="password" id="login-password" required autocomplete="current-password">
                </div>
                <div class="error-msg" id="login-error"></div>
                <button type="submit" class="submit-btn">Login</button>
            </form>
        </div>

        <div class="form-panel" id="signup-panel">
            <form id="signup-form">
                <div class="form-group">
                    <label for="signup-email">Email</label>
                    <input type="email" id="signup-email" required autocomplete="email">
                </div>
                <div class="form-group">
                    <label for="signup-password">Password</label>
                    <input type="password" id="signup-password" required minlength="8" autocomplete="new-password">
                    <div class="password-requirements">At least 8 characters with a letter and number</div>
                </div>
                <div class="error-msg" id="signup-error"></div>
                <button type="submit" class="submit-btn">Create Account</button>
            </form>
        </div>

        <div class="footer">
            <a href="/app">Continue without account</a>
        </div>
    </div>

    <script>
        const REDIRECT_TO = '{redirect_to}';

        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {{
            tab.addEventListener('click', () => {{
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.form-panel').forEach(p => p.classList.remove('active'));
                tab.classList.add('active');
                document.getElementById(tab.dataset.tab + '-panel').classList.add('active');
            }});
        }});

        // Login form
        document.getElementById('login-form').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const errorEl = document.getElementById('login-error');
            errorEl.classList.remove('visible');

            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;

            try {{
                const response = await fetch('/app/auth/login', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ email, password }})
                }});

                const data = await response.json();

                if (data.success) {{
                    window.location.href = REDIRECT_TO;
                }} else {{
                    errorEl.textContent = data.detail || 'Login failed';
                    errorEl.classList.add('visible');
                }}
            }} catch (err) {{
                errorEl.textContent = 'Network error';
                errorEl.classList.add('visible');
            }}
        }});

        // Signup form
        document.getElementById('signup-form').addEventListener('submit', async (e) => {{
            e.preventDefault();
            const errorEl = document.getElementById('signup-error');
            errorEl.classList.remove('visible');

            const email = document.getElementById('signup-email').value;
            const password = document.getElementById('signup-password').value;

            try {{
                const response = await fetch('/app/auth/signup', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ email, password }})
                }});

                const data = await response.json();

                if (data.success) {{
                    window.location.href = REDIRECT_TO;
                }} else {{
                    errorEl.textContent = data.detail || 'Signup failed';
                    errorEl.classList.add('visible');
                }}
            }} catch (err) {{
                errorEl.textContent = 'Network error';
                errorEl.classList.add('visible');
            }}
        }});
    </script>
</body>
</html>"""


def _get_account_page_html(user) -> str:
    """Generate HTML for account page."""
    # Determine what to show based on tier and subscription status
    show_upgrade = user.tier != "BEST"
    has_subscription = user.has_active_subscription

    upgrade_section = ""
    if show_upgrade:
        upgrade_section = """
        <div class="upgrade-section">
            <h3>Upgrade to BEST</h3>
            <div class="upgrade-benefits">
                <ul>
                    <li>Live player availability alerts</li>
                    <li>Full analysis with all insights</li>
                    <li>Recommended actions</li>
                    <li>Context-aware evaluation</li>
                </ul>
            </div>
            <div class="upgrade-price">$19.99/month</div>
            <button class="upgrade-btn" id="upgrade-btn">Upgrade Now</button>
            <div class="upgrade-note">Cancel anytime. Secure payment via Stripe.</div>
        </div>
        """

    manage_section = ""
    if has_subscription:
        manage_section = """
        <div class="manage-section">
            <h3>Subscription</h3>
            <p>You have an active BEST subscription.</p>
            <button class="manage-btn" id="manage-btn">Manage Subscription</button>
        </div>
        """

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Account - DNA Bet Engine</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: system-ui, -apple-system, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 1rem;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 1rem;
            margin-bottom: 2rem;
            border-bottom: 1px solid #333;
        }}
        header h1 {{
            color: #f39c12;
            font-size: 1.5rem;
        }}
        header nav {{
            display: flex;
            gap: 1rem;
        }}
        header nav a {{
            color: #4a9eff;
            text-decoration: none;
        }}
        .logout-btn {{
            background: transparent;
            border: 1px solid #e74c3c;
            color: #e74c3c;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
        }}
        .logout-btn:hover {{
            background: #e74c3c;
            color: #fff;
        }}
        .user-info {{
            background: #1a1a1a;
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }}
        .user-info h2 {{
            margin-bottom: 1rem;
            font-size: 1.1rem;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid #333;
        }}
        .info-row:last-child {{
            border-bottom: none;
        }}
        .info-label {{
            color: #888;
        }}
        .tier-badge {{
            padding: 0.25rem 0.75rem;
            background: #2a3a4a;
            border-radius: 4px;
            font-weight: 600;
        }}
        .tier-badge.good {{ color: #4a9eff; }}
        .tier-badge.better {{ color: #f39c12; }}
        .tier-badge.best {{ color: #2ecc71; }}
        .section {{
            margin-bottom: 2rem;
        }}
        .section h3 {{
            color: #f39c12;
            margin-bottom: 1rem;
            font-size: 1rem;
        }}
        .history-list {{
            background: #1a1a1a;
            border-radius: 8px;
            overflow: hidden;
        }}
        .history-item {{
            padding: 1rem;
            border-bottom: 1px solid #333;
        }}
        .history-item:last-child {{
            border-bottom: none;
        }}
        .history-bet {{
            font-family: monospace;
            color: #ccc;
            margin-bottom: 0.5rem;
        }}
        .history-meta {{
            font-size: 0.8rem;
            color: #666;
        }}
        .history-meta span {{
            margin-right: 1rem;
        }}
        .empty-state {{
            color: #666;
            text-align: center;
            padding: 2rem;
            font-style: italic;
        }}
        .loading {{
            text-align: center;
            padding: 2rem;
            color: #888;
        }}
        /* Upgrade Section Styles */
        .upgrade-section {{
            background: linear-gradient(135deg, #1a2a1a 0%, #1a1a2a 100%);
            border: 1px solid #2ecc71;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
            text-align: center;
        }}
        .upgrade-section h3 {{
            color: #2ecc71;
            margin-bottom: 1rem;
        }}
        .upgrade-benefits ul {{
            list-style: none;
            text-align: left;
            max-width: 300px;
            margin: 0 auto 1rem;
        }}
        .upgrade-benefits li {{
            padding: 0.4rem 0;
            padding-left: 1.5rem;
            position: relative;
        }}
        .upgrade-benefits li::before {{
            content: '✓';
            position: absolute;
            left: 0;
            color: #2ecc71;
        }}
        .upgrade-price {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #2ecc71;
            margin-bottom: 1rem;
        }}
        .upgrade-btn {{
            background: #2ecc71;
            color: #111;
            border: none;
            padding: 0.875rem 2rem;
            border-radius: 4px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
        }}
        .upgrade-btn:hover {{
            background: #27ae60;
        }}
        .upgrade-btn:disabled {{
            background: #555;
            cursor: wait;
        }}
        .upgrade-note {{
            font-size: 0.75rem;
            color: #888;
            margin-top: 0.75rem;
        }}
        /* Manage Subscription Styles */
        .manage-section {{
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }}
        .manage-section h3 {{
            color: #2ecc71;
            margin-bottom: 0.5rem;
        }}
        .manage-section p {{
            color: #888;
            margin-bottom: 1rem;
        }}
        .manage-btn {{
            background: transparent;
            border: 1px solid #4a9eff;
            color: #4a9eff;
            padding: 0.5rem 1.5rem;
            border-radius: 4px;
            cursor: pointer;
        }}
        .manage-btn:hover {{
            background: #4a9eff;
            color: #111;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>DNA Bet Engine</h1>
            <nav>
                <a href="/app">Parlay Builder</a>
                <button class="logout-btn" id="logout-btn">Logout</button>
            </nav>
        </header>

        <div class="user-info">
            <h2>Account</h2>
            <div class="info-row">
                <span class="info-label">Email</span>
                <span>{user.email}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Tier</span>
                <span class="tier-badge {user.tier.lower()}">{user.tier}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Member Since</span>
                <span>{user.created_at.strftime('%b %d, %Y')}</span>
            </div>
        </div>

        {upgrade_section}
        {manage_section}

        <div class="section">
            <h3>Evaluation History</h3>
            <div class="history-list" id="evaluations-list">
                <div class="loading">Loading...</div>
            </div>
        </div>

        <div class="section">
            <h3>Shared Links</h3>
            <div class="history-list" id="shares-list">
                <div class="loading">Loading...</div>
            </div>
        </div>
    </div>

    <script>
        // Logout
        document.getElementById('logout-btn').addEventListener('click', async () => {{
            await fetch('/app/auth/logout', {{ method: 'POST' }});
            window.location.href = '/app';
        }});

        // Upgrade button
        const upgradeBtn = document.getElementById('upgrade-btn');
        if (upgradeBtn) {{
            upgradeBtn.addEventListener('click', async () => {{
                upgradeBtn.disabled = true;
                upgradeBtn.textContent = 'Redirecting...';
                try {{
                    const response = await fetch('/app/billing/checkout', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ tier: 'BEST' }})
                    }});
                    const data = await response.json();
                    if (data.checkout_url) {{
                        window.location.href = data.checkout_url;
                    }} else {{
                        alert(data.detail || 'Could not start checkout');
                        upgradeBtn.disabled = false;
                        upgradeBtn.textContent = 'Upgrade Now';
                    }}
                }} catch (err) {{
                    alert('Error starting checkout');
                    upgradeBtn.disabled = false;
                    upgradeBtn.textContent = 'Upgrade Now';
                }}
            }});
        }}

        // Manage subscription button
        const manageBtn = document.getElementById('manage-btn');
        if (manageBtn) {{
            manageBtn.addEventListener('click', async () => {{
                try {{
                    const response = await fetch('/app/billing/portal');
                    const data = await response.json();
                    if (data.portal_url) {{
                        window.location.href = data.portal_url;
                    }} else {{
                        alert(data.detail || 'Could not open subscription portal');
                    }}
                }} catch (err) {{
                    alert('Error opening portal');
                }}
            }});
        }}

        // Load history
        async function loadHistory() {{
            try {{
                const response = await fetch('/app/account/history');
                const data = await response.json();

                // Render evaluations
                const evalList = document.getElementById('evaluations-list');
                if (data.evaluations && data.evaluations.length > 0) {{
                    evalList.innerHTML = data.evaluations.map(e => `
                        <div class="history-item">
                            <div class="history-bet">${{e.input_text}}</div>
                            <div class="history-meta">
                                <span>Tier: ${{e.tier.toUpperCase()}}</span>
                                <span>Date: ${{new Date(e.created_at).toLocaleDateString()}}</span>
                            </div>
                        </div>
                    `).join('');
                }} else {{
                    evalList.innerHTML = '<div class="empty-state">No evaluations yet</div>';
                }}

                // Render shares
                const shareList = document.getElementById('shares-list');
                if (data.shares && data.shares.length > 0) {{
                    shareList.innerHTML = data.shares.map(s => `
                        <div class="history-item">
                            <div class="history-bet">${{s.input_text}}</div>
                            <div class="history-meta">
                                <span>Views: ${{s.view_count}}</span>
                                <span>Link: /app/share/${{s.token}}</span>
                            </div>
                        </div>
                    `).join('');
                }} else {{
                    shareList.innerHTML = '<div class="empty-state">No shared links yet</div>';
                }}
            }} catch (err) {{
                console.error('Failed to load history:', err);
            }}
        }}

        loadHistory();
    </script>
</body>
</html>"""
