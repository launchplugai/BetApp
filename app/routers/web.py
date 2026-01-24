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
        /* ============================================
           DESIGN SYSTEM: Precision & Density (Dark)
           Based on interface-design/system-precision
           Base unit: 4px | Depth: borders-only
           ============================================ */
        :root {{
            /* Spacing (4px base) */
            --sp-1: 4px;
            --sp-2: 8px;
            --sp-3: 12px;
            --sp-4: 16px;
            --sp-5: 20px;
            --sp-6: 24px;
            --sp-8: 32px;
            --sp-12: 48px;

            /* Surfaces (darkest to lightest) */
            --surface-base: #0a0a0a;
            --surface-raised: #111111;
            --surface-overlay: #1a1a1a;
            --surface-hover: #222222;

            /* Foreground */
            --fg-primary: #e8e8e8;
            --fg-secondary: #999999;
            --fg-muted: #666666;
            --fg-faint: #444444;

            /* Border */
            --border-default: rgba(255, 255, 255, 0.08);
            --border-subtle: rgba(255, 255, 255, 0.05);
            --border-strong: rgba(255, 255, 255, 0.15);

            /* Accent */
            --accent: #4a9eff;
            --accent-hover: #3a8eef;
            --accent-surface: #1a2a3a;

            /* Signals */
            --signal-blue: #4a9eff;
            --signal-green: #4ade80;
            --signal-yellow: #fbbf24;
            --signal-red: #ef4444;

            /* Semantic */
            --success: #4ade80;
            --warning: #fbbf24;
            --danger: #ef4444;
            --info: #4a9eff;

            /* Radius (sharp, technical) */
            --radius-sm: 4px;
            --radius-md: 6px;
            --radius-lg: 8px;

            /* Typography */
            --font-sans: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            --font-mono: 'SF Mono', 'Consolas', 'Monaco', monospace;
            --text-xs: 11px;
            --text-sm: 12px;
            --text-base: 14px;
            --text-md: 16px;
            --text-lg: 18px;
            --text-xl: 24px;

            /* Transitions */
            --transition-fast: 150ms ease;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--font-sans);
            background: var(--surface-base);
            color: var(--fg-primary);
            min-height: 100vh;
            padding: var(--sp-6);
            font-size: var(--text-base);
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0;
            padding-bottom: var(--sp-4);
            border-bottom: 1px solid var(--border-default);
        }}
        .header-left {{
            display: flex;
            align-items: center;
            gap: var(--sp-3);
        }}
        h1 {{ font-size: var(--text-lg); color: var(--fg-primary); font-weight: 600; }}
        header a {{
            color: var(--accent);
            text-decoration: none;
            font-size: var(--text-sm);
        }}
        .user-info-header {{
            display: flex;
            align-items: center;
            gap: var(--sp-3);
            text-decoration: none;
            padding: var(--sp-1) var(--sp-2);
            border-radius: var(--radius-sm);
            transition: background var(--transition-fast);
        }}
        .user-info-header:hover {{
            background: var(--surface-overlay);
        }}
        .account-email {{
            color: var(--fg-secondary);
            font-size: var(--text-sm);
        }}
        .tier-badge {{
            padding: var(--sp-1) var(--sp-2);
            border-radius: var(--radius-sm);
            font-size: var(--text-xs);
            font-weight: 600;
            text-transform: uppercase;
        }}
        .tier-badge.good {{ background: var(--accent-surface); color: var(--accent); }}
        .tier-badge.better {{ background: rgba(251, 191, 36, 0.1); color: var(--signal-yellow); }}
        .tier-badge.best {{ background: rgba(74, 222, 128, 0.1); color: var(--signal-green); }}
        .login-link {{
            padding: var(--sp-2) var(--sp-4);
            border: 1px solid var(--accent);
            border-radius: var(--radius-sm);
        }}

        /* Orientation Banner */
        .orientation-banner {{
            background: var(--surface-raised);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            padding: var(--sp-3) var(--sp-4);
            margin: var(--sp-4) 0 var(--sp-2);
            font-size: var(--text-base);
        }}
        .orientation-main {{
            color: var(--fg-secondary);
        }}
        .orientation-login {{
            display: block;
            margin-top: var(--sp-1);
            font-size: var(--text-sm);
            color: var(--fg-muted);
        }}
        .orientation-login a {{
            color: var(--accent);
        }}

        /* Upgrade CTA */
        .upgrade-cta {{
            display: inline-flex;
            align-items: center;
            gap: var(--sp-2);
            padding: var(--sp-2) var(--sp-4);
            background: transparent;
            border: 1px solid var(--signal-yellow);
            border-radius: var(--radius-sm);
            color: var(--signal-yellow);
            text-decoration: none;
            font-size: var(--text-sm);
            font-weight: 500;
            transition: all var(--transition-fast);
        }}
        .upgrade-cta:hover {{
            background: var(--signal-yellow);
            color: var(--surface-base);
        }}

        /* Navigation Tabs */
        .nav-tabs {{
            display: flex;
            gap: 0;
            margin: var(--sp-4) 0;
            border-bottom: 1px solid var(--border-default);
        }}
        .nav-tab {{
            padding: var(--sp-3) var(--sp-5);
            color: var(--fg-muted);
            text-decoration: none;
            font-size: var(--text-base);
            font-weight: 500;
            border-bottom: 2px solid transparent;
            transition: all var(--transition-fast);
            cursor: pointer;
        }}
        .nav-tab:hover {{
            color: var(--fg-primary);
        }}
        .nav-tab.active {{
            color: var(--accent);
            border-bottom-color: var(--accent);
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
            gap: var(--sp-6);
        }}
        @media (max-width: 768px) {{
            .main-grid {{ grid-template-columns: 1fr; }}
        }}

        /* Builder Section */
        .builder-section {{
            background: var(--surface-raised);
            border: 1px solid var(--border-default);
            padding: var(--sp-4);
            border-radius: var(--radius-lg);
        }}
        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--sp-4);
        }}
        .section-title {{
            font-size: var(--text-md);
            font-weight: 600;
            color: var(--fg-primary);
        }}
        .leg-count {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
        }}

        /* Sport Selector */
        .sport-selector {{
            margin-bottom: var(--sp-4);
        }}
        .sport-selector select {{
            width: 100%;
            padding: var(--sp-2) var(--sp-3);
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-sm);
            color: var(--fg-primary);
            font-size: var(--text-base);
        }}
        .sport-selector select:focus {{
            outline: none;
            border-color: var(--accent);
        }}

        /* Legs Container */
        .legs-container {{
            max-height: 400px;
            overflow-y: auto;
            margin-bottom: var(--sp-4);
        }}
        .leg-card {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            padding: var(--sp-3);
            margin-bottom: var(--sp-3);
            position: relative;
        }}
        .leg-card:last-child {{ margin-bottom: 0; }}
        .leg-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--sp-3);
        }}
        .leg-number {{
            font-weight: 600;
            font-size: var(--text-sm);
            color: var(--accent);
        }}
        .remove-leg {{
            background: transparent;
            border: none;
            color: var(--danger);
            cursor: pointer;
            font-size: var(--text-md);
            padding: 0;
            width: auto;
            line-height: 1;
        }}
        .remove-leg:hover {{ color: var(--signal-red); }}
        .remove-leg:disabled {{ color: var(--fg-faint); cursor: not-allowed; }}

        .leg-fields {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: var(--sp-2);
        }}
        .leg-field {{
            display: flex;
            flex-direction: column;
        }}
        .leg-field.full-width {{
            grid-column: 1 / -1;
        }}
        .leg-field label {{
            font-size: var(--text-xs);
            color: var(--fg-secondary);
            margin-bottom: var(--sp-1);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .leg-field input, .leg-field select {{
            padding: var(--sp-2);
            background: var(--surface-base);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-sm);
            color: var(--fg-primary);
            font-size: var(--text-base);
        }}
        .leg-field input:focus, .leg-field select:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        .leg-field input::placeholder {{
            color: var(--fg-faint);
        }}

        /* Add Leg Button */
        .add-leg-btn {{
            width: 100%;
            padding: var(--sp-3);
            background: transparent;
            border: 1px dashed var(--border-strong);
            border-radius: var(--radius-md);
            color: var(--fg-muted);
            font-size: var(--text-base);
            cursor: pointer;
            transition: all var(--transition-fast);
            margin-bottom: var(--sp-4);
        }}
        .add-leg-btn:hover {{
            border-color: var(--accent);
            color: var(--accent);
        }}
        .add-leg-btn:disabled {{
            border-color: var(--border-subtle);
            color: var(--fg-faint);
            cursor: not-allowed;
        }}

        /* Tier Selector */
        .tier-selector-wrapper {{
            margin-bottom: var(--sp-4);
        }}
        .tier-selector-label {{
            font-size: var(--text-xs);
            color: var(--fg-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-2);
        }}
        .tier-selector {{
            display: flex;
            gap: var(--sp-2);
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
            padding: var(--sp-2) var(--sp-2);
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-sm);
            text-align: center;
            cursor: pointer;
            transition: all var(--transition-fast);
        }}
        .tier-option input:checked + label {{
            border-color: var(--accent);
            background: var(--accent-surface);
        }}
        .tier-option label:hover {{
            border-color: var(--border-strong);
        }}
        .tier-name {{
            font-weight: 600;
            font-size: var(--text-sm);
        }}
        .tier-desc {{
            font-size: var(--text-xs);
            color: var(--fg-secondary);
        }}

        /* Submit Button */
        .submit-btn {{
            width: 100%;
            padding: var(--sp-3) var(--sp-4);
            background: var(--accent);
            border: none;
            border-radius: var(--radius-sm);
            color: var(--surface-base);
            font-size: var(--text-base);
            font-weight: 600;
            cursor: pointer;
            transition: background var(--transition-fast);
        }}
        .submit-btn:hover {{ background: var(--accent-hover); }}
        .submit-btn:disabled {{
            background: var(--surface-overlay);
            color: var(--fg-muted);
            cursor: not-allowed;
        }}

        /* Results Section */
        .results-section {{
            background: var(--surface-raised);
            border: 1px solid var(--border-default);
            padding: var(--sp-4);
            border-radius: var(--radius-lg);
        }}
        .results-placeholder {{
            text-align: center;
            color: var(--fg-faint);
            padding: var(--sp-12) var(--sp-4);
        }}
        .results-placeholder p {{
            margin-bottom: var(--sp-2);
        }}

        /* Grade Display */
        .grade-display {{
            text-align: center;
            padding: var(--sp-6);
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-lg);
            margin-bottom: var(--sp-4);
        }}
        .grade-label {{
            font-size: var(--text-xs);
            color: var(--fg-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: var(--sp-2);
        }}
        .grade-value {{
            font-size: var(--text-xl);
            font-weight: 700;
            line-height: 1;
            margin-bottom: var(--sp-2);
            font-family: var(--font-mono);
        }}
        .grade-value.low {{ color: var(--signal-green); }}
        .grade-value.medium {{ color: var(--signal-yellow); }}
        .grade-value.high {{ color: var(--signal-yellow); }}
        .grade-value.critical {{ color: var(--signal-red); }}
        .grade-bucket {{
            font-size: var(--text-sm);
            font-weight: 600;
            text-transform: uppercase;
        }}

        /* Verdict */
        .verdict-panel {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .verdict-panel h3 {{
            font-size: var(--text-xs);
            color: var(--fg-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-2);
        }}
        .verdict-text {{
            font-size: var(--text-base);
            line-height: 1.5;
        }}
        .action-accept {{ color: var(--signal-green); }}
        .action-reduce {{ color: var(--signal-yellow); }}
        .action-avoid {{ color: var(--signal-red); }}

        /* Insights Panel */
        .insights-panel {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .insights-panel h3 {{
            font-size: var(--text-xs);
            color: var(--fg-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-3);
        }}
        .insight-item {{
            padding: var(--sp-2) 0;
            border-bottom: 1px solid var(--border-default);
            font-size: var(--text-sm);
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
            background: rgba(10, 10, 10, 0.85);
            backdrop-filter: blur(4px);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 10;
        }}
        .locked-icon {{
            font-size: var(--text-lg);
            margin-bottom: var(--sp-2);
        }}
        .locked-text {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
        }}

        /* Decision Summary (Always shown) */
        .decision-summary {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-lg);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .decision-summary h3 {{
            font-size: var(--text-xs);
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: var(--sp-3);
        }}
        .decision-verdict {{
            font-size: var(--text-base);
            line-height: 1.4;
            margin-bottom: var(--sp-3);
            padding-bottom: var(--sp-3);
            border-bottom: 1px solid var(--border-default);
        }}
        .decision-bullets {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .decision-bullets li {{
            font-size: var(--text-sm);
            padding: var(--sp-1) 0;
            padding-left: var(--sp-5);
            position: relative;
            color: var(--fg-secondary);
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
        .bullet-risk::before {{ background: var(--danger); }}
        .bullet-improve::before {{ background: var(--success); }}
        .bullet-unknown::before {{ background: var(--fg-secondary); }}

        /* Why Section */
        .why-section {{
            margin-bottom: var(--sp-4);
        }}
        .why-section-title {{
            font-size: var(--text-xs);
            color: var(--fg-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: var(--sp-2);
        }}
        .why-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: var(--sp-2);
        }}
        @media (max-width: 500px) {{
            .why-grid {{ grid-template-columns: 1fr; }}
        }}
        .why-panel {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            padding: var(--sp-3);
            min-height: 80px;
        }}
        .why-panel h4 {{
            font-size: var(--text-xs);
            color: var(--fg-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-2);
            display: flex;
            align-items: center;
            gap: var(--sp-1);
        }}
        .why-panel h4 .icon {{
            font-size: var(--text-base);
        }}
        .why-panel-content {{
            font-size: var(--text-sm);
            line-height: 1.4;
            color: var(--fg-primary);
        }}
        .why-panel-content .metric {{
            font-weight: 600;
            color: #fff;
        }}
        .why-panel-content .detail {{
            color: var(--fg-secondary);
            font-size: var(--text-sm);
        }}

        /* Alerts (BEST only) */
        .alerts-panel {{
            background: rgba(239, 68, 68, 0.05);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .alerts-panel h3 {{
            font-size: var(--text-xs);
            color: var(--signal-red);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-3);
        }}
        .alert-item {{
            font-size: var(--text-sm);
            padding: var(--sp-2) 0;
            border-bottom: 1px solid rgba(239, 68, 68, 0.15);
        }}
        .alert-item:last-child {{ border-bottom: none; }}

        /* Error Panel */
        .error-panel {{
            background: var(--surface-overlay);
            border: 1px solid var(--danger);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
        }}
        .error-panel h3 {{
            color: var(--danger);
            font-size: var(--text-base);
            font-weight: 600;
            margin-bottom: var(--sp-2);
        }}
        .error-text {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
        }}

        /* Hidden utility */
        .hidden {{ display: none !important; }}

        /* Context Panel Styles (Sprint 3) */
        .context-panel {{
            border: 1px solid rgba(74, 222, 128, 0.2);
            background: rgba(74, 222, 128, 0.03);
        }}
        .context-panel h3 {{
            color: var(--signal-green);
        }}
        .context-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--sp-3);
            padding-bottom: var(--sp-2);
            border-bottom: 1px solid var(--border-default);
        }}
        .context-source {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
        }}
        .context-summary {{
            background: rgba(74, 222, 128, 0.05);
            padding: var(--sp-3);
            border-radius: var(--radius-sm);
            margin-bottom: var(--sp-3);
            font-size: var(--text-base);
        }}
        .context-modifiers {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .context-modifier {{
            padding: var(--sp-2);
            margin-bottom: var(--sp-2);
            background: var(--surface-overlay);
            border-radius: var(--radius-sm);
            border-left: 3px solid var(--fg-muted);
        }}
        .context-modifier.negative {{
            border-left-color: var(--signal-red);
        }}
        .context-modifier.positive {{
            border-left-color: var(--signal-green);
        }}
        .context-modifier-reason {{
            font-size: var(--text-sm);
        }}
        .context-modifier-adjustment {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            margin-top: var(--sp-1);
        }}
        .context-missing {{
            font-size: var(--text-sm);
            color: var(--signal-yellow);
            margin-top: var(--sp-2);
            padding: var(--sp-2);
            background: rgba(251, 191, 36, 0.05);
            border-radius: var(--radius-sm);
        }}
        .context-entities {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            margin-top: var(--sp-2);
        }}

        /* Alerts Feed Styles (Sprint 4) */
        .alerts-feed {{
            border: 1px solid var(--signal-red);
            background: rgba(239, 68, 68, 0.03);
            margin-bottom: var(--sp-4);
        }}
        .alerts-feed h3 {{
            color: var(--signal-red);
        }}
        .alerts-feed.locked {{
            border-color: var(--fg-faint);
            background: var(--surface-overlay);
        }}
        .alerts-feed.locked h3 {{
            color: var(--fg-muted);
        }}
        .alert-item {{
            padding: var(--sp-3);
            margin-bottom: var(--sp-2);
            background: var(--surface-overlay);
            border-radius: var(--radius-sm);
            border-left: 3px solid var(--signal-red);
        }}
        .alert-item.warning {{
            border-left-color: var(--signal-yellow);
        }}
        .alert-item.info {{
            border-left-color: var(--accent);
        }}
        .alert-title {{
            font-weight: 600;
            margin-bottom: var(--sp-1);
        }}
        .alert-message {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
        }}
        .alert-meta {{
            font-size: var(--text-sm);
            color: var(--fg-muted);
            margin-top: var(--sp-2);
        }}
        .alerts-empty {{
            color: var(--fg-muted);
            font-style: italic;
            padding: var(--sp-2);
        }}
        .alerts-locked-message {{
            color: var(--fg-secondary);
            font-size: var(--text-base);
            padding: var(--sp-2);
        }}

        /* Share Button Styles (Sprint 5) */
        .share-section {{
            margin-top: var(--sp-4);
            padding-top: var(--sp-4);
            border-top: 1px solid var(--border-default);
            text-align: center;
        }}
        .share-btn {{
            background: var(--accent);
            color: var(--surface-base);
            border: none;
            padding: var(--sp-2) var(--sp-6);
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: var(--text-base);
        }}
        .share-btn:hover {{
            background: var(--accent-hover);
        }}
        .share-btn:disabled {{
            background: var(--fg-faint);
            cursor: not-allowed;
        }}
        .share-link {{
            margin-top: var(--sp-3);
            padding: var(--sp-2);
            background: var(--surface-overlay);
            border-radius: var(--radius-sm);
            display: none;
        }}
        .share-link.visible {{
            display: block;
        }}
        .share-link input {{
            width: 100%;
            padding: var(--sp-2);
            background: var(--surface-base);
            border: 1px solid var(--border-default);
            color: var(--fg-primary);
            border-radius: var(--radius-sm);
            font-family: var(--font-mono);
        }}
        .share-link .copy-btn {{
            margin-top: var(--sp-2);
            padding: var(--sp-1) var(--sp-4);
            font-size: var(--text-sm);
        }}

        /* Upgrade Nudge Styles (Sprint 5) */
        .upgrade-nudge {{
            background: var(--surface-overlay);
            border: 1px solid var(--signal-yellow);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-top: var(--sp-4);
            text-align: center;
        }}
        .upgrade-nudge h4 {{
            color: var(--signal-yellow);
            margin: 0 0 var(--sp-2);
            font-size: var(--text-base);
        }}
        .upgrade-nudge p {{
            color: var(--fg-secondary);
            font-size: var(--text-sm);
            margin: 0 0 var(--sp-3);
        }}
        .upgrade-nudge .upgrade-btn {{
            background: var(--signal-yellow);
            color: var(--surface-base);
            border: none;
            padding: var(--sp-2) var(--sp-6);
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-weight: 600;
        }}
        .upgrade-nudge .upgrade-btn:hover {{
            opacity: 0.9;
        }}
        /* Evaluate Tab Styles */
        .evaluate-section {{
            background: var(--surface-raised);
            border: 1px solid var(--border-default);
            padding: var(--sp-4);
            border-radius: var(--radius-lg);
            margin-bottom: var(--sp-6);
        }}
        .eval-step {{
            margin-bottom: var(--sp-4);
            padding-bottom: var(--sp-4);
            border-bottom: 1px solid var(--border-subtle);
        }}
        .eval-step:last-of-type {{
            border-bottom: none;
            margin-bottom: var(--sp-3);
            padding-bottom: 0;
        }}
        .eval-step-indicator {{
            display: flex;
            align-items: center;
            gap: var(--sp-2);
            margin-bottom: var(--sp-3);
        }}
        .eval-step-number {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--accent-surface);
            border: 1px solid var(--accent);
            color: var(--accent);
            font-size: var(--text-xs);
            font-weight: 600;
            font-family: var(--font-mono);
        }}
        .eval-step-label {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 500;
        }}
        .bundle-prompt {{
            border: 1px dashed var(--border-strong);
            border-radius: var(--radius-lg);
            padding: var(--sp-8);
            text-align: center;
            background: var(--surface-overlay);
        }}
        .bundle-prompt p {{
            color: var(--fg-secondary);
            margin-bottom: var(--sp-4);
        }}
        .secondary-btn {{
            padding: var(--sp-3) var(--sp-6);
            background: transparent;
            border: 1px solid var(--accent);
            border-radius: var(--radius-sm);
            color: var(--accent);
            font-size: var(--text-base);
            font-weight: 500;
            cursor: pointer;
            transition: all var(--transition-fast);
        }}
        .secondary-btn:hover {{
            background: var(--accent);
            color: var(--surface-base);
        }}
        .secondary-btn.disabled {{
            border-color: var(--fg-faint);
            color: var(--fg-faint);
            cursor: not-allowed;
        }}
        .secondary-btn.disabled:hover {{
            background: transparent;
            color: var(--fg-faint);
        }}
        .builder-cta {{
            width: 100%;
            margin-top: var(--sp-3);
        }}

        /* Signal System */
        .signal-display {{
            display: flex;
            align-items: center;
            gap: var(--sp-4);
            padding: var(--sp-5) var(--sp-4);
            background: var(--surface-overlay);
            border: 1px solid var(--border-strong);
            border-radius: var(--radius-lg);
            margin-bottom: var(--sp-3);
        }}
        .signal-badge {{
            width: 56px;
            height: 56px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: var(--text-xs);
            flex-shrink: 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .signal-badge.signal-blue {{ background: transparent; color: var(--signal-blue); border: 2px solid var(--signal-blue); }}
        .signal-badge.signal-green {{ background: transparent; color: var(--signal-green); border: 2px solid var(--signal-green); }}
        .signal-badge.signal-yellow {{ background: transparent; color: var(--signal-yellow); border: 2px solid var(--signal-yellow); }}
        .signal-badge.signal-red {{ background: transparent; color: var(--signal-red); border: 2px solid var(--signal-red); }}
        .signal-score {{
            display: flex;
            flex-direction: column;
        }}
        .signal-score-value {{
            font-size: var(--text-xl);
            font-weight: 700;
            color: var(--fg-primary);
            font-family: var(--font-mono);
        }}
        .signal-score-label {{
            font-size: var(--text-xs);
            color: var(--fg-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* Verdict Bar */
        .verdict-bar {{
            padding: var(--sp-3) var(--sp-4);
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            margin-bottom: var(--sp-4);
            font-size: var(--text-base);
        }}
        .verdict-action {{
            font-weight: 700;
            margin-right: var(--sp-2);
        }}
        .verdict-action.action-accept {{ color: var(--signal-green); }}
        .verdict-action.action-reduce {{ color: var(--signal-yellow); }}
        .verdict-action.action-avoid {{ color: var(--signal-red); }}
        .verdict-reason {{
            color: var(--fg-secondary);
        }}

        /* Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: var(--sp-2);
            margin-bottom: var(--sp-4);
        }}
        .metric-item {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-subtle);
            padding: var(--sp-3);
            border-radius: var(--radius-md);
            display: flex;
            flex-direction: column;
        }}
        .metric-label {{
            font-size: var(--text-xs);
            color: var(--fg-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-1);
        }}
        .metric-value {{
            font-size: var(--text-md);
            font-weight: 600;
            color: var(--fg-primary);
            font-family: var(--font-mono);
        }}

        /* Tips Panel */
        .tips-panel {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-left: 3px solid var(--signal-green);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .tips-panel h3 {{
            font-size: var(--text-xs);
            color: var(--signal-green);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-2);
        }}
        .tips-content {{
            font-size: var(--text-base);
            color: var(--fg-secondary);
            line-height: 1.5;
        }}
        .tip-item {{
            padding: var(--sp-1) 0;
            padding-left: var(--sp-4);
            position: relative;
        }}
        .tip-item::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 0.7rem;
            width: 4px;
            height: 4px;
            border-radius: 50%;
            background: var(--signal-green);
        }}

        /* Correlations Panel (BETTER+) */
        .correlations-panel {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-left: 3px solid var(--signal-yellow);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .correlations-panel h3 {{
            font-size: var(--text-xs);
            color: var(--signal-yellow);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-2);
        }}
        .correlation-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: var(--sp-2) 0;
            border-bottom: 1px solid var(--border-subtle);
            font-size: var(--text-sm);
        }}
        .correlation-item:last-child {{ border-bottom: none; }}
        .correlation-type {{
            color: var(--signal-yellow);
            font-weight: 600;
            font-size: var(--text-xs);
        }}
        .correlation-penalty {{
            color: var(--signal-red);
            font-weight: 600;
            font-family: var(--font-mono);
        }}

        /* Summary Panel (BETTER+) */
        .summary-panel {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-left: 3px solid var(--accent);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .summary-panel h3 {{
            font-size: var(--text-xs);
            color: var(--accent);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-2);
        }}
        .summary-item {{
            padding: var(--sp-1) 0;
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            border-bottom: 1px solid var(--border-subtle);
        }}
        .summary-item:last-child {{ border-bottom: none; }}

        /* Alerts Panel (BEST) */
        .alerts-detail-panel {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-left: 3px solid var(--signal-red);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .alerts-detail-panel h3 {{
            font-size: var(--text-xs);
            color: var(--signal-red);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-2);
        }}
        .alert-detail-item {{
            padding: var(--sp-2) var(--sp-3);
            margin-bottom: var(--sp-2);
            background: var(--surface-base);
            border-left: 2px solid var(--signal-red);
            border-radius: var(--radius-sm);
            font-size: var(--text-sm);
            color: var(--fg-secondary);
        }}

        /* GOOD Tier Structured Output */
        .good-output {{
            display: flex;
            flex-direction: column;
            gap: var(--sp-4);
        }}
        .good-signal-grade {{
            display: flex;
            align-items: center;
            gap: var(--sp-4);
            padding: var(--sp-5) var(--sp-4);
            background: var(--surface-overlay);
            border: 1px solid var(--border-strong);
            border-radius: var(--radius-md);
            margin-bottom: var(--sp-3);
        }}
        .good-signal {{
            padding: var(--sp-2) var(--sp-4);
            border-radius: var(--radius-sm);
            font-size: var(--text-base);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .good-signal.blue {{ background: rgba(74, 158, 255, 0.12); color: var(--signal-blue); border: 1px solid var(--signal-blue); }}
        .good-signal.green {{ background: rgba(74, 222, 128, 0.12); color: var(--signal-green); border: 1px solid var(--signal-green); }}
        .good-signal.yellow {{ background: rgba(251, 191, 36, 0.12); color: var(--signal-yellow); border: 1px solid var(--signal-yellow); }}
        .good-signal.red {{ background: rgba(239, 68, 68, 0.12); color: var(--signal-red); border: 1px solid var(--signal-red); }}
        .good-grade {{
            font-family: var(--font-mono);
            font-size: var(--text-xl);
            font-weight: 700;
            color: var(--fg-primary);
        }}
        .good-fragility {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--sp-3) var(--sp-4);
            background: var(--surface-raised);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
        }}
        .good-fragility-value {{
            font-family: var(--font-mono);
            font-size: var(--text-lg);
            font-weight: 600;
            color: var(--fg-primary);
        }}
        .good-section {{
            padding: var(--sp-3) var(--sp-4);
            background: var(--surface-raised);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
        }}
        .good-section-label {{
            font-size: var(--text-xs);
            color: var(--fg-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
            margin: 0 0 var(--sp-2);
        }}
        .good-contributor {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: var(--sp-2) 0;
            border-bottom: 1px solid var(--border-subtle);
            font-size: var(--text-sm);
        }}
        .good-contributor:last-child {{ border-bottom: none; }}
        .good-contributor-type {{
            color: var(--fg-primary);
            font-weight: 500;
        }}
        .good-contributor-impact {{
            font-family: var(--font-mono);
            font-size: var(--text-xs);
            padding: var(--sp-1) var(--sp-2);
            border-radius: var(--radius-sm);
        }}
        .good-contributor-impact.low {{ color: var(--signal-blue); background: rgba(74, 158, 255, 0.08); }}
        .good-contributor-impact.medium {{ color: var(--signal-yellow); background: rgba(251, 191, 36, 0.08); }}
        .good-contributor-impact.high {{ color: var(--signal-red); background: rgba(239, 68, 68, 0.08); }}
        .good-warnings-list, .good-tips-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .good-warnings-list li {{
            padding: var(--sp-2) 0;
            border-bottom: 1px solid var(--border-subtle);
            font-size: var(--text-sm);
            color: var(--signal-yellow);
        }}
        .good-warnings-list li:last-child {{ border-bottom: none; }}
        .good-tips-list li {{
            padding: var(--sp-2) 0;
            border-bottom: 1px solid var(--border-subtle);
            font-size: var(--text-sm);
            color: var(--fg-primary);
        }}
        .good-tips-list li:last-child {{ border-bottom: none; }}
        .good-removal-item {{
            display: inline-block;
            padding: var(--sp-1) var(--sp-2);
            margin: var(--sp-1);
            background: rgba(239, 68, 68, 0.08);
            border: 1px solid var(--signal-red);
            border-radius: var(--radius-sm);
            font-size: var(--text-xs);
            font-family: var(--font-mono);
            color: var(--signal-red);
        }}
        .good-section.empty {{
            display: none;
        }}

        /* Post-Result Actions */
        .post-actions {{
            display: flex;
            gap: var(--sp-2);
            margin-top: var(--sp-4);
            padding-top: var(--sp-4);
            border-top: 1px solid var(--border-default);
        }}
        .action-btn {{
            flex: 1;
            padding: var(--sp-2) var(--sp-2);
            border-radius: var(--radius-sm);
            font-size: var(--text-sm);
            font-weight: 500;
            cursor: pointer;
            border: 1px solid;
            background: transparent;
            transition: all var(--transition-fast);
        }}
        .action-improve {{
            border-color: var(--accent);
            color: var(--accent);
        }}
        .action-improve:hover {{ background: var(--accent); color: var(--surface-base); }}
        .action-reeval {{
            border-color: var(--signal-yellow);
            color: var(--signal-yellow);
        }}
        .action-reeval:hover {{ background: var(--signal-yellow); color: var(--surface-base); }}
        .action-save {{
            border-color: var(--signal-green);
            color: var(--signal-green);
        }}
        .action-save:hover {{ background: var(--signal-green); color: var(--surface-base); }}

        .input-tabs {{
            display: flex;
            gap: var(--sp-2);
            margin-bottom: var(--sp-4);
        }}
        .input-tab {{
            padding: var(--sp-2) var(--sp-4);
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-sm);
            color: var(--fg-muted);
            font-size: var(--text-sm);
            font-weight: 500;
            cursor: pointer;
            transition: all var(--transition-fast);
        }}
        .input-tab.active {{
            background: var(--surface-hover);
            border-color: var(--accent);
            color: var(--accent);
        }}
        .input-panel {{
            display: none;
        }}
        .input-panel.active {{
            display: block;
        }}
        .text-input {{
            width: 100%;
            min-height: 140px;
            padding: var(--sp-3);
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            color: var(--fg-primary);
            font-size: var(--text-base);
            font-family: var(--font-sans);
            resize: vertical;
            line-height: 1.5;
        }}
        .text-input:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        /* Image Not Available (OCR not implemented) */
        .image-not-available {{
            border: 2px dashed var(--fg-faint);
            border-radius: var(--radius-lg);
            padding: var(--sp-8);
            text-align: center;
            background: var(--surface-overlay);
        }}
        .image-not-available-icon {{
            font-size: var(--text-xl);
            margin-bottom: var(--sp-2);
            opacity: 0.5;
        }}
        .image-not-available-title {{
            font-weight: 600;
            color: var(--signal-yellow);
            margin-bottom: var(--sp-2);
        }}
        .image-not-available-text {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            margin-bottom: var(--sp-4);
        }}
        .switch-to-text-btn {{
            display: inline-block;
            padding: var(--sp-2) var(--sp-4);
            background: var(--accent);
            color: var(--surface-base);
            text-decoration: none;
            border-radius: var(--radius-sm);
            font-weight: 500;
            font-size: var(--text-sm);
        }}
        .switch-to-text-btn:hover {{
            background: var(--accent-hover);
        }}

        .file-upload-area {{
            border: 2px dashed var(--border-strong);
            border-radius: var(--radius-lg);
            padding: var(--sp-8);
            text-align: center;
            cursor: pointer;
            transition: all var(--transition-fast);
        }}
        .file-upload-area:hover {{
            border-color: var(--accent);
            background: var(--accent-surface);
        }}
        .file-upload-area.has-file {{
            border-color: var(--signal-green);
            background: rgba(74, 222, 128, 0.05);
        }}
        .file-upload-area.dragover {{
            border-color: var(--accent);
            background: var(--accent-surface);
        }}
        .file-upload-area.uploading {{
            pointer-events: none;
            opacity: 0.7;
        }}
        .file-upload-area input {{
            display: none;
        }}
        .file-upload-icon {{
            font-size: var(--text-xl);
            margin-bottom: var(--sp-3);
        }}
        .file-upload-text {{
            color: var(--fg-secondary);
            line-height: 1.5;
        }}
        .file-types {{
            font-size: var(--text-sm);
            color: var(--fg-muted);
        }}
        .file-selected {{
            color: var(--signal-green);
        }}
        .file-selected-icon {{
            font-size: var(--text-xl);
            margin-bottom: var(--sp-2);
        }}
        .file-selected-name {{
            font-weight: 600;
            margin-bottom: var(--sp-3);
            word-break: break-all;
        }}
        .clear-file-btn {{
            padding: var(--sp-1) var(--sp-4);
            background: transparent;
            border: 1px solid var(--signal-red);
            color: var(--signal-red);
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: var(--text-sm);
            transition: all var(--transition-fast);
        }}
        .clear-file-btn:hover {{
            background: var(--signal-red);
            color: #fff;
        }}
        .image-error {{
            margin-top: var(--sp-3);
            padding: var(--sp-3);
            background: rgba(239, 68, 68, 0.05);
            border: 1px solid var(--signal-red);
            border-radius: var(--radius-sm);
            color: var(--signal-red);
            font-size: var(--text-sm);
        }}
        .image-parse-info {{
            background: rgba(74, 222, 128, 0.05);
            border: 1px solid var(--signal-green);
            border-radius: var(--radius-md);
            padding: var(--sp-3);
            margin-bottom: var(--sp-4);
            font-size: var(--text-sm);
        }}
        .image-parse-confidence {{
            color: var(--signal-green);
            font-weight: 600;
        }}
        .image-parse-notes {{
            color: var(--fg-secondary);
            margin-top: var(--sp-1);
            font-size: var(--text-sm);
        }}
        .clear-file {{
            margin-top: var(--sp-2);
            padding: var(--sp-1) var(--sp-3);
            background: transparent;
            border: 1px solid var(--signal-red);
            color: var(--signal-red);
            border-radius: var(--radius-sm);
            cursor: pointer;
            font-size: var(--text-sm);
        }}
        .eval-submit {{
            width: 100%;
            margin-top: var(--sp-4);
        }}

        /* Discover Tab Styles */
        .discover-section {{
            max-width: 560px;
            margin: 0 auto;
            padding: var(--sp-8) var(--sp-4);
        }}
        .discover-hero {{
            text-align: center;
            margin-bottom: var(--sp-8);
        }}
        .discover-hero h2 {{
            font-size: var(--text-xl);
            color: var(--fg-primary);
            margin-bottom: var(--sp-3);
            font-weight: 600;
        }}
        .discover-tagline {{
            color: var(--fg-secondary);
            font-size: var(--text-base);
        }}
        .discover-steps {{
            margin-bottom: var(--sp-8);
        }}
        .discover-step {{
            display: flex;
            gap: var(--sp-4);
            padding: var(--sp-4);
            background: var(--surface-raised);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-lg);
            margin-bottom: var(--sp-3);
        }}
        .step-number {{
            width: 28px;
            height: 28px;
            background: var(--accent);
            color: var(--surface-base);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: var(--text-sm);
            flex-shrink: 0;
        }}
        .step-content h3 {{
            font-size: var(--text-base);
            color: var(--fg-primary);
            font-weight: 600;
            margin-bottom: var(--sp-1);
        }}
        .step-content p {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            margin: 0;
        }}
        .discover-cta {{
            text-align: center;
        }}
        .discover-start-btn {{
            max-width: 280px;
        }}

        /* History Tab Styles */
        .history-section {{
            background: var(--surface-raised);
            border: 1px solid var(--border-default);
            padding: var(--sp-4);
            border-radius: var(--radius-lg);
        }}
        .history-empty {{
            text-align: center;
            padding: var(--sp-8);
            color: var(--fg-muted);
        }}
        .history-item {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-3);
        }}
        .history-date {{
            font-size: var(--text-xs);
            color: var(--fg-muted);
            margin-bottom: var(--sp-2);
        }}
        .history-text {{
            font-family: var(--font-mono);
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            margin-bottom: var(--sp-2);
        }}
        .history-grade {{
            display: inline-block;
            padding: var(--sp-1) var(--sp-2);
            border-radius: var(--radius-sm);
            font-weight: 600;
            font-size: var(--text-sm);
            font-family: var(--font-mono);
        }}
        .history-grade.low {{ background: transparent; color: var(--signal-green); border: 1px solid var(--signal-green); }}
        .history-grade.medium {{ background: transparent; color: var(--signal-yellow); border: 1px solid var(--signal-yellow); }}
        .history-grade.high {{ background: transparent; color: var(--signal-yellow); border: 1px solid var(--signal-yellow); }}
        .history-grade.critical {{ background: transparent; color: var(--signal-red); border: 1px solid var(--signal-red); }}
        .login-prompt {{
            text-align: center;
            padding: var(--sp-8);
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-lg);
        }}
        .login-prompt a {{
            display: inline-block;
            margin-top: var(--sp-4);
            padding: var(--sp-3) var(--sp-6);
            background: var(--accent);
            color: var(--surface-base);
            text-decoration: none;
            border-radius: var(--radius-sm);
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
                            <h3>See What's Weak</h3>
                            <p>Know which legs add risk and what to change before you commit.</p>
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

                    <!-- Step 1: Provide Bet -->
                    <div class="eval-step">
                        <div class="eval-step-indicator">
                            <span class="eval-step-number">1</span>
                            <span class="eval-step-label">Provide bet</span>
                        </div>

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
                    </div>

                    <!-- Step 2: Choose Depth -->
                    <div class="eval-step">
                        <div class="eval-step-indicator">
                            <span class="eval-step-number">2</span>
                            <span class="eval-step-label">Choose depth</span>
                        </div>

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
                                    <div class="tier-desc">Full Analysis</div>
                                </label>
                            </div>
                        </div>
                    </div>

                    <!-- Step 3: Analyze -->
                    <div class="eval-step">
                        <div class="eval-step-indicator">
                            <span class="eval-step-number">3</span>
                            <span class="eval-step-label">Analyze</span>
                        </div>

                        <button type="button" class="submit-btn eval-submit" id="eval-submit-btn" disabled>
                            Evaluate
                        </button>
                    </div>

                    <!-- Builder CTA: response to evaluation, not destination -->
                    <button type="button" class="secondary-btn builder-cta disabled" id="builder-cta-btn" disabled title="Evaluate a bet first">
                        Improve This Bet
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
                        <!-- GOOD Tier Structured Output (exclusive to GOOD) -->
                        <div id="eval-good-output" class="good-output hidden">
                            <div class="good-signal-grade" id="good-signal-grade">
                                <div class="good-signal" id="good-signal-indicator"></div>
                                <div class="good-grade" id="good-grade-value"></div>
                            </div>
                            <div class="good-fragility" id="good-fragility">
                                <span class="good-section-label">Fragility Score</span>
                                <span class="good-fragility-value" id="good-fragility-value">--</span>
                            </div>
                            <div class="good-section" id="good-contributors-section">
                                <h4 class="good-section-label">Contributors</h4>
                                <div class="good-contributors-list" id="good-contributors-list"></div>
                            </div>
                            <div class="good-section" id="good-warnings-section">
                                <h4 class="good-section-label">Warnings</h4>
                                <ul class="good-warnings-list" id="good-warnings-list"></ul>
                            </div>
                            <div class="good-section" id="good-tips-section">
                                <h4 class="good-section-label">Tips</h4>
                                <ul class="good-tips-list" id="good-tips-list"></ul>
                            </div>
                            <div class="good-section" id="good-removals-section">
                                <h4 class="good-section-label">Suggested Removals</h4>
                                <div class="good-removals-list" id="good-removals-list"></div>
                            </div>
                        </div>

                        <!-- Shared tier panels (BETTER/BEST) -->
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
                            <button type="button" class="action-btn action-improve" id="eval-action-improve" onclick="switchToTab('builder')">Improve This Bet</button>
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
                    <span class="section-title">Past Decisions</span>
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

                // === GOOD TIER: Structured Output ===
                const goodOutput = document.getElementById('eval-good-output');
                const sharedSignal = document.getElementById('eval-signal-display');
                const sharedVerdict = document.getElementById('eval-verdict-bar');
                const sharedMetrics = document.getElementById('eval-metrics-grid');
                const sharedTips = document.getElementById('eval-tips-panel');

                if (tier === 'good' && explain.overallSignal) {{
                    // Show GOOD output, hide shared panels
                    goodOutput.classList.remove('hidden');
                    sharedSignal.classList.add('hidden');
                    sharedVerdict.classList.add('hidden');
                    sharedMetrics.classList.add('hidden');
                    sharedTips.classList.add('hidden');

                    // Signal + Grade
                    const signalEl = document.getElementById('good-signal-indicator');
                    signalEl.textContent = explain.overallSignal.toUpperCase();
                    signalEl.className = 'good-signal ' + explain.overallSignal;
                    document.getElementById('good-grade-value').textContent = 'Grade: ' + explain.grade;

                    // Fragility Score
                    document.getElementById('good-fragility-value').textContent = Math.round(explain.fragilityScore);

                    // Contributors
                    const contribList = document.getElementById('good-contributors-list');
                    const contribSection = document.getElementById('good-contributors-section');
                    if (explain.contributors && explain.contributors.length > 0) {{
                        let contribHtml = '';
                        explain.contributors.forEach(function(c) {{
                            contribHtml += '<div class="good-contributor">';
                            contribHtml += '<span class="good-contributor-type">' + c.type + '</span>';
                            contribHtml += '<span class="good-contributor-impact ' + c.impact + '">' + c.impact + '</span>';
                            contribHtml += '</div>';
                        }});
                        contribList.innerHTML = contribHtml;
                        contribSection.classList.remove('empty');
                    }} else {{
                        contribSection.classList.add('empty');
                    }}

                    // Warnings
                    const warningsList = document.getElementById('good-warnings-list');
                    const warningsSection = document.getElementById('good-warnings-section');
                    if (explain.warnings && explain.warnings.length > 0) {{
                        warningsList.innerHTML = explain.warnings.map(function(w) {{
                            return '<li>' + w + '</li>';
                        }}).join('');
                        warningsSection.classList.remove('empty');
                    }} else {{
                        warningsSection.classList.add('empty');
                    }}

                    // Tips
                    const tipsList = document.getElementById('good-tips-list');
                    const tipsSection = document.getElementById('good-tips-section');
                    if (explain.tips && explain.tips.length > 0) {{
                        tipsList.innerHTML = explain.tips.map(function(t) {{
                            return '<li>' + t + '</li>';
                        }}).join('');
                        tipsSection.classList.remove('empty');
                    }} else {{
                        tipsSection.classList.add('empty');
                    }}

                    // Removal Suggestions
                    const removalsList = document.getElementById('good-removals-list');
                    const removalsSection = document.getElementById('good-removals-section');
                    if (explain.removalSuggestions && explain.removalSuggestions.length > 0) {{
                        removalsList.innerHTML = explain.removalSuggestions.map(function(r) {{
                            return '<span class="good-removal-item">' + r.substring(0, 8) + '</span>';
                        }}).join('');
                        removalsSection.classList.remove('empty');
                    }} else {{
                        removalsSection.classList.add('empty');
                    }}

                    // Hide BETTER/BEST panels
                    document.getElementById('eval-correlations-panel').classList.add('hidden');
                    document.getElementById('eval-summary-panel').classList.add('hidden');
                    document.getElementById('eval-alerts-panel').classList.add('hidden');

                }} else {{
                    // === BETTER/BEST: Shared panels ===
                    goodOutput.classList.add('hidden');
                    sharedSignal.classList.remove('hidden');
                    sharedVerdict.classList.remove('hidden');
                    sharedMetrics.classList.remove('hidden');

                    // Signal badge
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

                    // Verdict
                    const action = evaluation.recommendation.action;
                    const verdictAction = document.getElementById('eval-verdict-action');
                    const verdictReason = document.getElementById('eval-verdict-reason');
                    verdictAction.textContent = action.toUpperCase();
                    verdictAction.className = 'verdict-action action-' + action;
                    verdictReason.textContent = evaluation.recommendation.reason;

                    // Metrics grid
                    document.getElementById('eval-metric-leg').textContent = '+' + (metrics.leg_penalty || 0).toFixed(1);
                    document.getElementById('eval-metric-corr').textContent = '+' + (metrics.correlation_penalty || 0).toFixed(1);
                    document.getElementById('eval-metric-raw').textContent = (metrics.raw_fragility || 0).toFixed(1);
                    document.getElementById('eval-metric-final').textContent = Math.round(metrics.final_fragility || 0);

                    // Tips
                    const tipsContent = document.getElementById('eval-tips-content');
                    const tipsPanel = document.getElementById('eval-tips-panel');
                    const whatToDo = fragility.what_to_do || '';
                    const meaning = fragility.meaning || '';
                    if (whatToDo || meaning) {{
                        let tipsHtml = '';
                        if (meaning) tipsHtml += '<div class="tip-item">' + meaning + '</div>';
                        if (whatToDo) tipsHtml += '<div class="tip-item">' + whatToDo + '</div>';
                        tipsContent.innerHTML = tipsHtml;
                        tipsPanel.classList.remove('hidden');
                    }} else {{
                        tipsPanel.classList.add('hidden');
                    }}

                    // Correlations (BETTER+)
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

                    // Summary (BETTER+)
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

                    // Alerts (BEST only)
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
