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
from typing import Optional, List

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


class ApplyFixRequest(BaseModel):
    """
    VC-2: Request schema for applying a fix from the Builder.

    The fix is pre-determined by primaryFailure.fastestFix.
    This endpoint executes the fix and re-evaluates.
    """
    evaluation_id: Optional[str] = Field(default=None, description="Original evaluation ID")
    fix_action: str = Field(..., description="Fix action: remove_leg, split_parlay, reduce_props, swap_leg")
    affected_leg_ids: List[str] = Field(default=[], description="IDs of affected legs")


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

        /* Parlay Builder (Sprint 2) */
        .parlay-builder {{
            padding: var(--sp-4);
        }}
        .builder-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--sp-4);
        }}
        .builder-title {{
            font-size: var(--text-lg);
            font-weight: 600;
            color: var(--fg-primary);
        }}
        .builder-leg-count {{
            font-size: var(--text-sm);
            color: var(--fg-muted);
        }}
        .builder-sport-selector {{
            margin-bottom: var(--sp-4);
        }}
        .builder-select {{
            width: 100%;
            padding: var(--sp-3);
            background: var(--bg-secondary);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--fg-primary);
            font-size: var(--text-base);
        }}
        .builder-legs {{
            display: flex;
            flex-direction: column;
            gap: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .builder-leg {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: var(--sp-3);
        }}
        .leg-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--sp-3);
        }}
        .leg-label {{
            font-size: var(--text-sm);
            font-weight: 600;
            color: var(--accent);
        }}
        .leg-remove-btn {{
            background: transparent;
            border: none;
            color: var(--fg-muted);
            font-size: var(--text-lg);
            cursor: pointer;
            padding: var(--sp-1);
            line-height: 1;
        }}
        .leg-remove-btn:hover {{
            color: var(--signal-red);
        }}
        .leg-field {{
            margin-bottom: var(--sp-3);
        }}
        .leg-field-label {{
            display: block;
            font-size: var(--text-xs);
            color: var(--fg-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-1);
        }}
        .leg-input, .leg-select {{
            width: 100%;
            padding: var(--sp-2) var(--sp-3);
            background: var(--bg-tertiary);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-sm);
            color: var(--fg-primary);
            font-size: var(--text-base);
        }}
        .leg-input:focus, .leg-select:focus {{
            outline: none;
            border-color: var(--accent);
        }}
        .leg-row {{
            display: flex;
            gap: var(--sp-3);
        }}
        .leg-field-half {{
            flex: 1;
        }}

        /* Auto-suggest Dropdown (Sprint 2) */
        .autosuggest-wrapper {{
            position: relative;
        }}
        .autosuggest-dropdown {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: var(--bg-primary);
            border: 1px solid var(--border-strong);
            border-radius: var(--radius-sm);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            max-height: 200px;
            overflow-y: auto;
            z-index: 100;
        }}
        .autosuggest-item {{
            padding: var(--sp-2) var(--sp-3);
            cursor: pointer;
            font-size: var(--text-base);
            color: var(--fg-primary);
            border-bottom: 1px solid var(--border-subtle);
        }}
        .autosuggest-item:last-child {{
            border-bottom: none;
        }}
        .autosuggest-item:hover, .autosuggest-item.selected {{
            background: var(--accent);
            color: white;
        }}
        .autosuggest-item .item-type {{
            font-size: var(--text-xs);
            color: var(--fg-muted);
            margin-left: var(--sp-2);
        }}
        .autosuggest-item:hover .item-type, .autosuggest-item.selected .item-type {{
            color: rgba(255, 255, 255, 0.7);
        }}

        /* Leg Explanation (Sprint 2) */
        .leg-explanation {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            padding: var(--sp-2);
            background: rgba(99, 102, 241, 0.08);
            border-radius: var(--radius-sm);
            margin-top: var(--sp-2);
        }}

        /* Builder Tier Selector */
        .builder-tier-section {{
            margin-bottom: var(--sp-4);
        }}
        .builder-tier-label {{
            font-size: var(--text-xs);
            color: var(--fg-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-2);
        }}
        .builder-tier-selector {{
            display: flex;
            gap: var(--sp-2);
        }}
        .builder-tier-option {{
            flex: 1;
            padding: var(--sp-2) var(--sp-3);
            background: var(--bg-secondary);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-sm);
            text-align: center;
            cursor: pointer;
            transition: all var(--transition-fast);
        }}
        .builder-tier-option:hover {{
            border-color: var(--accent);
        }}
        .builder-tier-option.selected {{
            background: var(--accent);
            border-color: var(--accent);
        }}
        .builder-tier-option .tier-name {{
            display: block;
            font-size: var(--text-sm);
            font-weight: 600;
            color: var(--fg-primary);
        }}
        .builder-tier-option.selected .tier-name {{
            color: white;
        }}
        .builder-tier-option .tier-desc {{
            display: block;
            font-size: var(--text-xs);
            color: var(--fg-muted);
        }}
        .builder-tier-option.selected .tier-desc {{
            color: rgba(255, 255, 255, 0.7);
        }}

        /* Builder Evaluate Button */
        .builder-evaluate-btn {{
            width: 100%;
            padding: var(--sp-3);
            background: var(--bg-tertiary);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            color: var(--fg-secondary);
            font-size: var(--text-base);
            cursor: pointer;
            transition: all var(--transition-fast);
            margin-bottom: var(--sp-4);
        }}
        .builder-evaluate-btn:hover {{
            background: var(--accent);
            border-color: var(--accent);
            color: white;
        }}
        .builder-evaluate-btn:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        /* Builder Results */
        .builder-results {{
            background: var(--bg-secondary);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: var(--sp-3);
        }}
        .builder-results-placeholder {{
            text-align: center;
            padding: var(--sp-4);
            color: var(--fg-muted);
        }}
        .builder-results-hint {{
            font-size: var(--text-sm);
            color: var(--fg-faint);
            margin-top: var(--sp-2);
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

        /* VC-2: Fix Mode Styles */
        .fix-blocked {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 300px;
            text-align: center;
            padding: var(--sp-8);
        }}
        .fix-blocked-icon {{
            font-size: 48px;
            margin-bottom: var(--sp-4);
            opacity: 0.5;
        }}
        .fix-blocked-message {{
            font-size: var(--text-lg);
            font-weight: 600;
            color: var(--fg-primary);
            margin-bottom: var(--sp-2);
        }}
        .fix-blocked-hint {{
            font-size: var(--text-sm);
            color: var(--fg-muted);
            margin-bottom: var(--sp-6);
        }}
        .fix-blocked-cta {{
            padding: var(--sp-3) var(--sp-6);
            background: var(--accent);
            border: none;
            border-radius: var(--radius-sm);
            color: var(--surface-base);
            font-size: var(--text-base);
            font-weight: 600;
            cursor: pointer;
        }}
        .fix-blocked-cta:hover {{
            background: var(--accent-hover);
        }}
        .fix-mode {{
            max-width: 600px;
            margin: 0 auto;
            padding: var(--sp-6);
        }}
        .fix-problem {{
            background: var(--surface-raised);
            border: 1px solid var(--signal-yellow);
            border-left: 4px solid var(--signal-yellow);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .fix-problem.severity-critical {{
            border-color: var(--signal-red);
        }}
        .fix-problem.severity-high {{
            border-color: var(--signal-red);
        }}
        .fix-problem.severity-medium {{
            border-color: var(--signal-yellow);
        }}
        .fix-problem.severity-low {{
            border-color: var(--signal-green);
        }}
        .fix-problem-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--sp-3);
        }}
        .fix-problem-label {{
            font-size: var(--text-xs);
            font-weight: 600;
            color: var(--fg-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .fix-problem-severity {{
            font-size: var(--text-xs);
            font-weight: 700;
            text-transform: uppercase;
            padding: var(--sp-1) var(--sp-2);
            border-radius: var(--radius-sm);
            background: var(--signal-yellow);
            color: var(--surface-base);
        }}
        .fix-problem-severity.severity-critical,
        .fix-problem-severity.severity-high {{
            background: var(--signal-red);
        }}
        .fix-problem-severity.severity-low {{
            background: var(--signal-green);
        }}
        .fix-problem-type {{
            font-size: var(--text-md);
            font-weight: 600;
            color: var(--fg-primary);
            margin-bottom: var(--sp-2);
            text-transform: capitalize;
        }}
        .fix-problem-description {{
            font-size: var(--text-base);
            color: var(--fg-secondary);
            line-height: 1.5;
            margin-bottom: var(--sp-2);
        }}
        .fix-affected-legs {{
            font-size: var(--text-sm);
            color: var(--fg-muted);
        }}
        .fix-delta {{
            display: flex;
            align-items: stretch;
            gap: var(--sp-3);
            background: var(--surface-raised);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .fix-delta-before, .fix-delta-after {{
            flex: 1;
            text-align: center;
            padding: var(--sp-3);
            border-radius: var(--radius-sm);
        }}
        .fix-delta-before {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
        }}
        .fix-delta-after {{
            background: rgba(74, 222, 128, 0.1);
            border: 1px solid rgba(74, 222, 128, 0.2);
        }}
        .fix-delta-arrow {{
            display: flex;
            align-items: center;
            font-size: var(--text-xl);
            color: var(--fg-muted);
        }}
        .fix-delta-label {{
            font-size: var(--text-xs);
            font-weight: 600;
            color: var(--fg-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: var(--sp-2);
        }}
        .fix-delta-signal {{
            font-size: var(--text-base);
            font-weight: 700;
            text-transform: uppercase;
            margin-bottom: var(--sp-1);
        }}
        .fix-delta-signal.signal-blue {{ color: var(--signal-blue); }}
        .fix-delta-signal.signal-green {{ color: var(--signal-green); }}
        .fix-delta-signal.signal-yellow {{ color: var(--signal-yellow); }}
        .fix-delta-signal.signal-red {{ color: var(--signal-red); }}
        .fix-delta-grade {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            margin-bottom: var(--sp-1);
        }}
        .fix-delta-score {{
            font-size: var(--text-lg);
            font-weight: 700;
            font-family: var(--font-mono);
            color: var(--fg-primary);
        }}
        .fix-action-panel {{
            display: flex;
            gap: var(--sp-3);
        }}
        .fix-apply-btn {{
            flex: 1;
            padding: var(--sp-4);
            background: var(--signal-green);
            border: none;
            border-radius: var(--radius-md);
            color: var(--surface-base);
            font-size: var(--text-base);
            font-weight: 700;
            cursor: pointer;
            transition: all var(--transition-fast);
        }}
        .fix-apply-btn:hover {{
            background: #3dcc70;
        }}
        .fix-apply-btn:disabled {{
            background: var(--fg-faint);
            cursor: not-allowed;
        }}
        .fix-cancel-btn {{
            padding: var(--sp-4) var(--sp-6);
            background: transparent;
            border: 1px solid var(--border-strong);
            border-radius: var(--radius-md);
            color: var(--fg-secondary);
            font-size: var(--text-base);
            cursor: pointer;
            transition: all var(--transition-fast);
        }}
        .fix-cancel-btn:hover {{
            border-color: var(--fg-muted);
            color: var(--fg-primary);
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

        /* Context Echo (Ticket 14) */
        .context-echo {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            padding: var(--sp-2) var(--sp-3);
            background: rgba(99, 102, 241, 0.06);
            border-left: 2px solid rgba(99, 102, 241, 0.3);
            border-radius: var(--radius-sm);
            margin-bottom: var(--sp-3);
        }}

        /* Human Summary (Sprint 2) */
        .human-summary {{
            font-size: var(--text-base);
            color: var(--fg-primary);
            padding: var(--sp-3);
            background: rgba(34, 197, 94, 0.06);
            border-left: 3px solid rgba(34, 197, 94, 0.4);
            border-radius: var(--radius-sm);
            margin-bottom: var(--sp-3);
            line-height: 1.5;
        }}

        /* Secondary Factors (Sprint 2) */
        .detail-secondary-factor {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: var(--sp-2);
            padding: var(--sp-2);
            background: var(--bg-tertiary);
            border-radius: var(--radius-sm);
            margin-bottom: var(--sp-2);
        }}
        .sf-type {{
            font-weight: 500;
            color: var(--fg-secondary);
            text-transform: capitalize;
        }}
        .sf-impact {{
            font-size: var(--text-xs);
            padding: 2px 6px;
            border-radius: var(--radius-sm);
            text-transform: uppercase;
        }}
        .sf-impact.impact-low {{
            background: rgba(34, 197, 94, 0.15);
            color: var(--signal-green);
        }}
        .sf-impact.impact-medium {{
            background: rgba(234, 179, 8, 0.15);
            color: var(--signal-yellow);
        }}
        .sf-impact.impact-high {{
            background: rgba(239, 68, 68, 0.15);
            color: var(--signal-red);
        }}
        .sf-explanation {{
            width: 100%;
            font-size: var(--text-sm);
            color: var(--fg-muted);
            margin-top: var(--sp-1);
        }}

        /* Staged Analysis Progress (Ticket 14) */
        .analysis-progress {{
            padding: var(--sp-3);
            margin-bottom: var(--sp-3);
        }}
        .ap-step {{
            font-size: var(--text-sm);
            color: var(--fg-muted);
            padding: var(--sp-1) 0;
            opacity: 0.4;
            transition: opacity 0.2s, color 0.2s;
        }}
        .ap-step.active {{
            color: var(--fg-secondary);
            opacity: 1.0;
        }}
        .ap-step.done {{
            color: var(--signal-green);
            opacity: 0.7;
        }}
        .ap-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--fg-muted);
            margin-right: var(--sp-2);
            vertical-align: middle;
        }}
        .ap-step.active .ap-dot {{
            background: var(--signal-blue);
        }}
        .ap-step.done .ap-dot {{
            background: var(--signal-green);
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
        .signal-line {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            padding: var(--sp-1) var(--sp-4);
            margin-bottom: var(--sp-3);
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

        /* Primary Failure Card */
        .primary-failure-card {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-strong);
            border-left: 4px solid var(--signal-yellow);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .primary-failure-card.severity-high {{
            border-left-color: var(--signal-red);
        }}
        .primary-failure-card.severity-low {{
            border-left-color: var(--signal-green);
        }}
        .pf-header {{
            display: flex;
            align-items: center;
            gap: var(--sp-2);
            margin-bottom: var(--sp-2);
        }}
        .pf-title {{
            font-size: var(--text-xs);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--fg-primary);
        }}
        .pf-badge {{
            font-size: var(--text-xs);
            padding: 2px var(--sp-2);
            border-radius: var(--radius-sm);
            background: var(--surface-base);
            border: 1px solid var(--border-default);
            color: var(--fg-secondary);
        }}
        .pf-description {{
            font-size: var(--text-sm);
            color: var(--fg-primary);
            margin-bottom: var(--sp-2);
            line-height: 1.4;
        }}
        .pf-affected {{
            font-size: var(--text-xs);
            color: var(--fg-muted);
            margin-bottom: var(--sp-3);
        }}
        .pf-fix {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
            padding: var(--sp-2) var(--sp-3);
            background: var(--surface-base);
            border-radius: var(--radius-sm);
            margin-bottom: var(--sp-2);
        }}
        .pf-fix-label {{
            font-weight: 600;
            color: var(--signal-green);
            margin-right: var(--sp-1);
        }}
        .pf-delta {{
            display: flex;
            align-items: center;
            gap: var(--sp-2);
            font-size: var(--text-sm);
            padding: var(--sp-2) var(--sp-3);
            background: var(--surface-base);
            border-radius: var(--radius-sm);
        }}
        .pf-delta-label {{
            color: var(--fg-muted);
            font-size: var(--text-xs);
        }}
        .pf-delta-before {{
            color: var(--fg-secondary);
        }}
        .pf-delta-arrow {{
            color: var(--signal-green);
            font-weight: 700;
        }}
        .pf-delta-after {{
            color: var(--fg-primary);
            font-weight: 600;
        }}

        /* VC-1: Compressed Evaluation Layout */
        .compressed-primary-failure {{
            background: var(--surface-overlay);
            border: 2px solid var(--border-strong);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-3);
        }}
        .compressed-primary-failure.severity-high {{
            border-color: var(--signal-red);
        }}
        .compressed-primary-failure.severity-medium {{
            border-color: var(--signal-yellow);
        }}
        .compressed-primary-failure.severity-low {{
            border-color: var(--signal-green);
        }}
        .cpf-header {{
            margin-bottom: var(--sp-2);
        }}
        .cpf-badge {{
            display: inline-block;
            font-size: var(--text-xs);
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 2px var(--sp-2);
            border-radius: var(--radius-sm);
            background: var(--surface-base);
            border: 1px solid var(--border-default);
            color: var(--fg-secondary);
        }}
        .cpf-description {{
            font-size: var(--text-base);
            font-weight: 500;
            color: var(--fg-primary);
            line-height: 1.4;
        }}
        .compressed-fix-cta {{
            display: block;
            width: 100%;
            padding: var(--sp-3) var(--sp-4);
            margin-bottom: var(--sp-3);
            font-size: var(--text-sm);
            font-weight: 600;
            color: var(--fg-primary);
            background: var(--surface-raised);
            border: 1px solid var(--border-strong);
            border-radius: var(--radius-md);
            cursor: pointer;
            text-align: center;
        }}
        .compressed-fix-cta:hover {{
            background: var(--surface-overlay);
            border-color: var(--accent);
        }}
        .compressed-delta {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--sp-4);
            padding: var(--sp-3);
            margin-bottom: var(--sp-3);
            background: var(--surface-base);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
        }}
        .cdelta-before, .cdelta-after {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: var(--sp-1);
        }}
        .cdelta-signal {{
            font-size: var(--text-xs);
            font-weight: 600;
            text-transform: uppercase;
            padding: 2px var(--sp-2);
            border-radius: var(--radius-sm);
            border: 1px solid currentColor;
        }}
        .cdelta-signal.signal-blue {{ color: var(--signal-blue); }}
        .cdelta-signal.signal-green {{ color: var(--signal-green); }}
        .cdelta-signal.signal-yellow {{ color: var(--signal-yellow); }}
        .cdelta-signal.signal-red {{ color: var(--signal-red); }}
        .cdelta-score {{
            font-size: var(--text-lg);
            font-weight: 700;
            font-family: var(--font-mono);
            color: var(--fg-primary);
        }}
        .cdelta-arrow {{
            font-size: var(--text-xl);
            color: var(--signal-green);
            font-weight: 700;
        }}
        .eval-details-accordion {{
            margin-bottom: var(--sp-3);
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
        }}
        .eval-details-accordion summary {{
            padding: var(--sp-3) var(--sp-4);
            cursor: pointer;
            font-size: var(--text-sm);
            font-weight: 600;
            color: var(--fg-secondary);
            list-style: none;
        }}
        .eval-details-accordion summary::-webkit-details-marker {{
            display: none;
        }}
        .eval-details-accordion summary::before {{
            content: '\u25B6 ';
            font-size: var(--text-xs);
        }}
        .eval-details-accordion[open] summary::before {{
            content: '\u25BC ';
        }}
        .details-content {{
            padding: 0 var(--sp-4) var(--sp-4);
        }}
        .detail-row {{
            display: flex;
            justify-content: space-between;
            padding: var(--sp-2) 0;
            border-bottom: 1px solid var(--border-subtle);
        }}
        .detail-row:last-child {{ border-bottom: none; }}
        .detail-label {{
            font-size: var(--text-sm);
            color: var(--fg-muted);
        }}
        .detail-value {{
            font-size: var(--text-sm);
            font-weight: 600;
            color: var(--fg-primary);
            font-family: var(--font-mono);
        }}
        .detail-section {{
            margin-top: var(--sp-3);
            padding-top: var(--sp-3);
            border-top: 1px solid var(--border-subtle);
        }}
        .detail-section-label {{
            display: block;
            font-size: var(--text-xs);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--fg-muted);
            margin-bottom: var(--sp-2);
        }}
        .detail-section-content {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
        }}
        .detail-section-content ul {{
            margin: 0;
            padding-left: var(--sp-4);
        }}
        .detail-section-content li {{
            margin-bottom: var(--sp-1);
        }}
        .detail-contributor {{
            display: flex;
            justify-content: space-between;
            padding: var(--sp-1) 0;
            font-size: var(--text-sm);
        }}
        .contrib-type {{ color: var(--fg-secondary); }}
        .contrib-impact {{ font-weight: 600; text-transform: uppercase; font-size: var(--text-xs); }}
        .impact-high {{ color: var(--signal-red); }}
        .impact-medium {{ color: var(--signal-yellow); }}
        .impact-low {{ color: var(--signal-green); }}
        .detail-corr-item {{
            display: flex;
            justify-content: space-between;
            padding: var(--sp-1) 0;
            font-size: var(--text-sm);
            gap: var(--sp-2);
        }}
        .corr-type {{ color: var(--fg-muted); font-size: var(--text-xs); }}
        .corr-penalty {{ font-weight: 600; color: var(--signal-yellow); font-family: var(--font-mono); }}
        .detail-insight, .detail-alert {{
            padding: var(--sp-1) 0;
            font-size: var(--text-sm);
        }}
        .detail-alert {{ color: var(--signal-yellow); }}
        .post-actions-minimal {{
            display: flex;
            gap: var(--sp-2);
            justify-content: flex-end;
        }}
        .post-actions-minimal .action-btn {{
            flex: 0 0 auto;
            padding: var(--sp-2) var(--sp-3);
            font-size: var(--text-xs);
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

        /* Collapsible panels */
        .summary-panel details,
        .alerts-detail-panel details {{
            border: none;
        }}
        .summary-panel summary,
        .alerts-detail-panel summary {{
            cursor: pointer;
            list-style: none;
        }}
        .summary-panel summary::-webkit-details-marker,
        .alerts-detail-panel summary::-webkit-details-marker {{
            display: none;
        }}
        .summary-panel summary h3::after,
        .alerts-detail-panel summary h3::after {{
            content: ' \u25B6';
            font-size: var(--text-xs);
        }}
        .summary-panel details[open] summary h3::after,
        .alerts-detail-panel details[open] summary h3::after {{
            content: ' \u25BC';
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
        .discover-signals {{
            margin-top: var(--sp-4);
            padding: var(--sp-4);
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
        }}
        .discover-signals h3 {{
            font-size: var(--text-xs);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--fg-muted);
            margin-bottom: var(--sp-2);
        }}
        .discover-signal-row {{
            display: flex;
            align-items: center;
            gap: var(--sp-3);
            padding: var(--sp-1) 0;
        }}
        .discover-signal-badge {{
            display: inline-block;
            width: 64px;
            text-align: center;
            font-size: var(--text-xs);
            font-weight: 600;
            padding: 2px var(--sp-2);
            border-radius: var(--radius-sm);
            border: 1px solid currentColor;
        }}
        .discover-signal-badge.signal-blue {{ color: var(--signal-blue); }}
        .discover-signal-badge.signal-green {{ color: var(--signal-green); }}
        .discover-signal-badge.signal-yellow {{ color: var(--signal-yellow); }}
        .discover-signal-badge.signal-red {{ color: var(--signal-red); }}
        .discover-signal-desc {{
            font-size: var(--text-sm);
            color: var(--fg-secondary);
        }}
        .discover-cta {{
            text-align: center;
            margin-top: var(--sp-4);
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
        .history-grade.blue {{ background: transparent; color: var(--signal-blue); border: 1px solid var(--signal-blue); }}
        .history-grade.green {{ background: transparent; color: var(--signal-green); border: 1px solid var(--signal-green); }}
        .history-grade.yellow {{ background: transparent; color: var(--signal-yellow); border: 1px solid var(--signal-yellow); }}
        .history-grade.red {{ background: transparent; color: var(--signal-red); border: 1px solid var(--signal-red); }}
        .history-signal-line {{
            font-size: var(--text-xs);
            color: var(--fg-muted);
            margin-top: var(--sp-1);
        }}
        /* Ticket 6: History item actions */
        .history-item-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: var(--sp-2);
        }}
        .history-item-meta {{
            display: flex;
            flex-direction: column;
            gap: var(--sp-1);
        }}
        .history-item-actions {{
            display: flex;
            gap: var(--sp-2);
        }}
        .history-action-btn {{
            padding: var(--sp-1) var(--sp-2);
            font-size: var(--text-xs);
            border-radius: var(--radius-sm);
            cursor: pointer;
            border: 1px solid var(--border-default);
            background: var(--surface-overlay);
            color: var(--fg-secondary);
            transition: all 0.15s ease;
        }}
        .history-action-btn:hover {{
            background: var(--surface-hover);
            color: var(--fg-primary);
        }}
        .history-action-btn.primary {{
            background: var(--accent);
            border-color: var(--accent);
            color: var(--surface-base);
        }}
        .history-action-btn.primary:hover {{
            background: var(--accent-hover);
        }}
        .history-sport {{
            font-size: var(--text-xs);
            color: var(--fg-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .history-empty-state {{
            text-align: center;
            padding: var(--sp-8);
            color: var(--fg-muted);
        }}
        .history-empty-state p {{
            margin-bottom: var(--sp-4);
        }}
        .history-start-btn {{
            padding: var(--sp-3) var(--sp-6);
            background: var(--accent);
            border: none;
            border-radius: var(--radius-sm);
            color: var(--surface-base);
            font-size: var(--text-base);
            font-weight: 600;
            cursor: pointer;
        }}
        .history-start-btn:hover {{
            background: var(--accent-hover);
        }}
        .history-loading {{
            text-align: center;
            padding: var(--sp-8);
            color: var(--fg-muted);
        }}
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

        /* VC-3: PAYOFF BANNER */
        .payoff-banner {{
            background: linear-gradient(135deg, var(--signal-green-bg, rgba(34,197,94,0.1)) 0%, var(--surface-overlay) 100%);
            border: 1px solid var(--signal-green, #22c55e);
            border-radius: var(--radius-md);
            padding: var(--sp-4);
            margin-bottom: var(--sp-4);
        }}
        .payoff-banner.no-improvement {{
            background: linear-gradient(135deg, var(--signal-yellow-bg, rgba(234,179,8,0.1)) 0%, var(--surface-overlay) 100%);
            border-color: var(--signal-yellow, #eab308);
        }}
        .payoff-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: var(--sp-2);
        }}
        .payoff-title {{
            font-size: var(--text-lg);
            font-weight: 700;
            color: var(--signal-green, #22c55e);
        }}
        .payoff-banner.no-improvement .payoff-title {{
            color: var(--signal-yellow, #eab308);
        }}
        .payoff-dismiss {{
            background: transparent;
            border: none;
            font-size: var(--text-xl);
            color: var(--fg-muted);
            cursor: pointer;
            padding: 0;
            line-height: 1;
        }}
        .payoff-dismiss:hover {{
            color: var(--fg-primary);
        }}
        .payoff-line {{
            font-size: var(--text-sm);
            color: var(--fg-primary);
            margin-bottom: var(--sp-2);
        }}
        .payoff-line .delta-num {{
            font-weight: 700;
            color: var(--signal-green, #22c55e);
        }}
        .payoff-banner.no-improvement .payoff-line .delta-num {{
            color: var(--signal-yellow, #eab308);
        }}
        .payoff-status {{
            font-size: var(--text-sm);
            font-weight: 600;
        }}
        .payoff-status.improved {{
            color: var(--signal-green, #22c55e);
        }}
        .payoff-status.no-change {{
            color: var(--signal-yellow, #eab308);
        }}

        /* VC-3: MINI DIFF */
        .mini-diff {{
            background: var(--surface-overlay);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-md);
            margin-bottom: var(--sp-4);
        }}
        .mini-diff > summary {{
            padding: var(--sp-3) var(--sp-4);
            font-size: var(--text-sm);
            font-weight: 600;
            color: var(--fg-secondary);
            cursor: pointer;
        }}
        .mini-diff > summary:hover {{
            color: var(--fg-primary);
        }}
        .mini-diff-content {{
            padding: 0 var(--sp-4) var(--sp-4);
        }}
        .mini-diff-row {{
            display: flex;
            align-items: center;
            gap: var(--sp-2);
            padding: var(--sp-2) 0;
            border-top: 1px solid var(--border-subtle);
        }}
        .mini-diff-label {{
            flex: 0 0 100px;
            font-size: var(--text-xs);
            color: var(--fg-muted);
            text-transform: uppercase;
        }}
        .mini-diff-before {{
            flex: 1;
            font-size: var(--text-sm);
            color: var(--fg-secondary);
        }}
        .mini-diff-arrow {{
            flex: 0 0 auto;
            color: var(--fg-muted);
        }}
        .mini-diff-after {{
            flex: 1;
            font-size: var(--text-sm);
            font-weight: 600;
            color: var(--fg-primary);
        }}

        /* VC-3: LOOP SHORTCUTS */
        .loop-shortcuts {{
            display: flex;
            gap: var(--sp-2);
            margin-top: var(--sp-4);
            padding-top: var(--sp-4);
            border-top: 1px solid var(--border-default);
        }}
        .loop-btn {{
            flex: 1;
            padding: var(--sp-2) var(--sp-3);
            border-radius: var(--radius-sm);
            font-size: var(--text-sm);
            font-weight: 500;
            cursor: pointer;
            border: 1px solid var(--border-default);
            background: var(--surface-overlay);
            color: var(--fg-secondary);
            transition: all 0.15s ease;
        }}
        .loop-btn:hover {{
            background: var(--surface-highlight);
            color: var(--fg-primary);
        }}
        .loop-reeval {{
            background: var(--accent);
            color: var(--surface-base);
            border-color: var(--accent);
        }}
        .loop-reeval:hover {{
            background: var(--accent-hover);
        }}
        .loop-try-fix {{
            background: var(--signal-green-bg, rgba(34,197,94,0.1));
            border-color: var(--signal-green, #22c55e);
            color: var(--signal-green, #22c55e);
        }}
        .loop-try-fix:hover {{
            background: var(--signal-green, #22c55e);
            color: var(--surface-base);
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
            <a class="nav-tab {discover_active}" href="#discover" data-tab="discover">Discover</a>
            <a class="nav-tab {evaluate_active}" href="#evaluate" data-tab="evaluate">Evaluate</a>
            <a class="nav-tab {builder_active}" href="#builder" data-tab="builder">Builder</a>
            <a class="nav-tab {history_active}" href="#history" data-tab="history">History</a>
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

                <div class="discover-signals">
                    <h3>Signal Guide</h3>
                    <div class="discover-signal-row">
                        <span class="discover-signal-badge signal-blue">Strong</span>
                        <span class="discover-signal-desc">Top risk: minimal</span>
                    </div>
                    <div class="discover-signal-row">
                        <span class="discover-signal-badge signal-green">Solid</span>
                        <span class="discover-signal-desc">Top risk: moderate</span>
                    </div>
                    <div class="discover-signal-row">
                        <span class="discover-signal-badge signal-yellow">Fixable</span>
                        <span class="discover-signal-desc">Top risk: addressable</span>
                    </div>
                    <div class="discover-signal-row">
                        <span class="discover-signal-badge signal-red">Fragile</span>
                        <span class="discover-signal-desc">Top risk: critical</span>
                    </div>
                </div>

                <div class="discover-cta">
                    <button type="button" class="submit-btn discover-start-btn" onclick="switchToTab('evaluate')">
                        Start Evaluating
                    </button>
                </div>
            </div>
        </div> <!-- End tab-discover -->

        <!-- Builder Tab Content (Sprint 2: Freeform Builder + Fix Mode) -->
        <div class="tab-content {builder_active}" id="tab-builder">
            <!-- PARLAY BUILDER (Sprint 2) -->
            <div class="parlay-builder" id="parlay-builder">
                <div class="builder-header">
                    <span class="builder-title">Parlay Builder</span>
                    <span class="builder-leg-count" id="builder-leg-count">2 legs</span>
                </div>

                <!-- Sport Selector -->
                <div class="builder-sport-selector">
                    <select id="builder-sport" class="builder-select">
                        <option value="nba">Basketball (NBA)</option>
                        <option value="nfl">Football (NFL)</option>
                        <option value="mlb">Baseball (MLB)</option>
                        <option value="nhl">Hockey (NHL)</option>
                    </select>
                </div>

                <!-- Legs Container -->
                <div class="builder-legs" id="builder-legs">
                    <!-- Leg 1 -->
                    <div class="builder-leg" data-leg-index="0">
                        <div class="leg-header">
                            <span class="leg-label">Leg 1</span>
                            <button type="button" class="leg-remove-btn" onclick="removeBuilderLeg(0)" title="Remove leg">&times;</button>
                        </div>
                        <div class="leg-field">
                            <label class="leg-field-label">TEAM / PLAYER</label>
                            <div class="autosuggest-wrapper">
                                <input type="text" class="leg-input team-player-input" data-leg="0" placeholder="e.g., Lakers or LeBron James" autocomplete="off">
                                <div class="autosuggest-dropdown hidden" data-leg="0"></div>
                            </div>
                            <div class="leg-explanation hidden" data-leg="0"></div>
                        </div>
                        <div class="leg-row">
                            <div class="leg-field leg-field-half">
                                <label class="leg-field-label">MARKET</label>
                                <select class="leg-select market-select" data-leg="0">
                                    <option value="spread">Spread</option>
                                    <option value="ml">Moneyline</option>
                                    <option value="total">Total (O/U)</option>
                                    <option value="prop">Player Prop</option>
                                </select>
                            </div>
                            <div class="leg-field leg-field-half">
                                <label class="leg-field-label">LINE / CONDITION</label>
                                <input type="text" class="leg-input line-input" data-leg="0" placeholder="e.g., -5.5 or O 220.5">
                            </div>
                        </div>
                        <div class="leg-field">
                            <label class="leg-field-label">ODDS</label>
                            <input type="text" class="leg-input odds-input" data-leg="0" placeholder="e.g., -110">
                        </div>
                    </div>

                    <!-- Leg 2 -->
                    <div class="builder-leg" data-leg-index="1">
                        <div class="leg-header">
                            <span class="leg-label">Leg 2</span>
                            <button type="button" class="leg-remove-btn" onclick="removeBuilderLeg(1)" title="Remove leg">&times;</button>
                        </div>
                        <div class="leg-field">
                            <label class="leg-field-label">TEAM / PLAYER</label>
                            <div class="autosuggest-wrapper">
                                <input type="text" class="leg-input team-player-input" data-leg="1" placeholder="e.g., Lakers or LeBron James" autocomplete="off">
                                <div class="autosuggest-dropdown hidden" data-leg="1"></div>
                            </div>
                            <div class="leg-explanation hidden" data-leg="1"></div>
                        </div>
                        <div class="leg-row">
                            <div class="leg-field leg-field-half">
                                <label class="leg-field-label">MARKET</label>
                                <select class="leg-select market-select" data-leg="1">
                                    <option value="spread">Spread</option>
                                    <option value="ml">Moneyline</option>
                                    <option value="total">Total (O/U)</option>
                                    <option value="prop">Player Prop</option>
                                </select>
                            </div>
                            <div class="leg-field leg-field-half">
                                <label class="leg-field-label">LINE / CONDITION</label>
                                <input type="text" class="leg-input line-input" data-leg="1" placeholder="e.g., -5.5 or O 220.5">
                            </div>
                        </div>
                        <div class="leg-field">
                            <label class="leg-field-label">ODDS</label>
                            <input type="text" class="leg-input odds-input" data-leg="1" placeholder="e.g., -110">
                        </div>
                    </div>
                </div>

                <!-- Add Leg Button -->
                <button type="button" class="add-leg-btn" id="add-leg-btn" onclick="addBuilderLeg()">+ Add Leg</button>

                <!-- Tier Selector -->
                <div class="builder-tier-section">
                    <label class="builder-tier-label">ANALYSIS DETAIL LEVEL</label>
                    <div class="builder-tier-selector">
                        <div class="builder-tier-option selected" data-tier="good">
                            <span class="tier-name">GOOD</span>
                            <span class="tier-desc">Grade + Verdict</span>
                        </div>
                        <div class="builder-tier-option" data-tier="better">
                            <span class="tier-name">BETTER</span>
                            <span class="tier-desc">+ Insights</span>
                        </div>
                        <div class="builder-tier-option" data-tier="best">
                            <span class="tier-name">BEST</span>
                            <span class="tier-desc">+ Full Analysis</span>
                        </div>
                    </div>
                </div>

                <!-- Evaluate Button -->
                <button type="button" class="builder-evaluate-btn" id="builder-evaluate-btn" onclick="evaluateBuilderParlay()">Evaluate Parlay</button>

                <!-- Builder Results -->
                <div class="builder-results" id="builder-results">
                    <div class="section-header">
                        <span class="section-title">Results</span>
                    </div>
                    <div class="builder-results-placeholder" id="builder-results-placeholder">
                        <p>Build your parlay and click Evaluate</p>
                        <p class="builder-results-hint">Minimum 2 legs required</p>
                    </div>
                    <div class="builder-results-content hidden" id="builder-results-content"></div>
                </div>
            </div>

            <!-- FIX MODE: Active when fix context exists (shown as overlay) -->
            <div class="fix-mode hidden" id="fix-mode">
                <!-- A. PROBLEM DISPLAY -->
                <div class="fix-problem" id="fix-problem">
                    <div class="fix-problem-header">
                        <span class="fix-problem-label">ISSUE DETECTED</span>
                        <span class="fix-problem-severity" id="fix-severity"></span>
                    </div>
                    <div class="fix-problem-type" id="fix-type"></div>
                    <div class="fix-problem-description" id="fix-description"></div>
                    <div class="fix-affected-legs" id="fix-affected"></div>
                </div>

                <!-- B. DELTA COMPARISON (always visible) -->
                <div class="fix-delta" id="fix-delta">
                    <div class="fix-delta-before">
                        <div class="fix-delta-label">CURRENT</div>
                        <div class="fix-delta-signal" id="fix-delta-signal-before"></div>
                        <div class="fix-delta-grade" id="fix-delta-grade-before"></div>
                        <div class="fix-delta-score" id="fix-delta-score-before"></div>
                    </div>
                    <div class="fix-delta-arrow">&rarr;</div>
                    <div class="fix-delta-after">
                        <div class="fix-delta-label">AFTER FIX</div>
                        <div class="fix-delta-signal" id="fix-delta-signal-after"></div>
                        <div class="fix-delta-grade" id="fix-delta-grade-after"></div>
                        <div class="fix-delta-score" id="fix-delta-score-after"></div>
                    </div>
                </div>

                <!-- C. SINGLE ACTION -->
                <div class="fix-action-panel" id="fix-action-panel">
                    <button type="button" class="fix-apply-btn" id="fix-apply-btn">
                        Apply Fix
                    </button>
                    <button type="button" class="fix-cancel-btn" id="fix-cancel-btn">
                        Cancel
                    </button>
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

                    <!-- STAGED ANALYSIS PROGRESS (Ticket 14) -->
                    <div id="analysis-progress" class="analysis-progress hidden">
                        <div class="ap-step" id="ap-step-1"><span class="ap-dot"></span> Parsing slip</div>
                        <div class="ap-step" id="ap-step-2"><span class="ap-dot"></span> Identifying markets</div>
                        <div class="ap-step" id="ap-step-3"><span class="ap-dot"></span> Checking constraints</div>
                        <div class="ap-step" id="ap-step-4"><span class="ap-dot"></span> Computing fragility</div>
                        <div class="ap-step" id="ap-step-5"><span class="ap-dot"></span> Recommending action</div>
                    </div>

                    <div id="eval-results-content" class="hidden">
                        <!-- VC-3: PAYOFF BANNER (shows after apply-fix) -->
                        <div class="payoff-banner hidden" id="payoff-banner">
                            <div class="payoff-header">
                                <span class="payoff-title">Fix Applied</span>
                                <button type="button" class="payoff-dismiss" id="payoff-dismiss">&times;</button>
                            </div>
                            <div class="payoff-line" id="payoff-line"></div>
                            <div class="payoff-status" id="payoff-status"></div>
                        </div>

                        <!-- VC-3: MINI DIFF (collapsed, shows after apply-fix) -->
                        <details class="mini-diff hidden" id="mini-diff">
                            <summary>See what changed</summary>
                            <div class="mini-diff-content">
                                <div class="mini-diff-row">
                                    <span class="mini-diff-label">Primary Failure</span>
                                    <span class="mini-diff-before" id="mini-diff-pf-before"></span>
                                    <span class="mini-diff-arrow">&rarr;</span>
                                    <span class="mini-diff-after" id="mini-diff-pf-after"></span>
                                </div>
                                <div class="mini-diff-row">
                                    <span class="mini-diff-label">Recommendation</span>
                                    <span class="mini-diff-before" id="mini-diff-rec-before"></span>
                                    <span class="mini-diff-arrow">&rarr;</span>
                                    <span class="mini-diff-after" id="mini-diff-rec-after"></span>
                                </div>
                            </div>
                        </details>

                        <!-- CONTEXT ECHO (Ticket 14) -->
                        <div class="context-echo hidden" id="context-echo"></div>

                        <!-- HUMAN SUMMARY (Sprint 2) -->
                        <div class="human-summary hidden" id="human-summary"></div>

                        <!-- A. PRIMARY FAILURE (full width, dominant) -->
                        <div class="compressed-primary-failure" id="compressed-pf">
                            <div class="cpf-header">
                                <span class="cpf-badge" id="cpf-badge"></span>
                            </div>
                            <div class="cpf-description" id="cpf-description"></div>
                        </div>

                        <!-- B. FASTEST FIX (single CTA) -->
                        <button type="button" class="compressed-fix-cta" id="compressed-fix-cta"></button>

                        <!-- C. DELTA PREVIEW (before → after) -->
                        <div class="compressed-delta hidden" id="compressed-delta">
                            <div class="cdelta-before" id="cdelta-before">
                                <span class="cdelta-signal" id="cdelta-signal-before"></span>
                                <span class="cdelta-score" id="cdelta-score-before"></span>
                            </div>
                            <div class="cdelta-arrow">&rarr;</div>
                            <div class="cdelta-after" id="cdelta-after">
                                <span class="cdelta-signal" id="cdelta-signal-after"></span>
                                <span class="cdelta-score" id="cdelta-score-after"></span>
                            </div>
                        </div>

                        <!-- D. DETAILS ACCORDION (collapsed by default) -->
                        <details class="eval-details-accordion" id="eval-details-accordion">
                            <summary>Details</summary>
                            <div class="details-content">
                                <!-- Signal + Grade -->
                                <div class="detail-row" id="detail-signal-row">
                                    <span class="detail-label">Signal</span>
                                    <span class="detail-value" id="detail-signal"></span>
                                </div>
                                <div class="detail-row" id="detail-fragility-row">
                                    <span class="detail-label">Fragility</span>
                                    <span class="detail-value" id="detail-fragility"></span>
                                </div>
                                <!-- Metrics -->
                                <div class="detail-row" id="detail-leg-penalty-row">
                                    <span class="detail-label">Leg Penalty</span>
                                    <span class="detail-value" id="detail-leg-penalty"></span>
                                </div>
                                <div class="detail-row" id="detail-correlation-row">
                                    <span class="detail-label">Correlation</span>
                                    <span class="detail-value" id="detail-correlation"></span>
                                </div>
                                <!-- Contributors -->
                                <div class="detail-section hidden" id="detail-contributors">
                                    <span class="detail-section-label">Contributors</span>
                                    <div class="detail-section-content" id="detail-contributors-list"></div>
                                </div>
                                <!-- Secondary Factors (Sprint 2) -->
                                <div class="detail-section hidden" id="detail-secondary-factors">
                                    <span class="detail-section-label">Secondary Factors</span>
                                    <div class="detail-section-content" id="detail-secondary-factors-list"></div>
                                </div>
                                <!-- Warnings -->
                                <div class="detail-section hidden" id="detail-warnings">
                                    <span class="detail-section-label">Warnings</span>
                                    <ul class="detail-section-content" id="detail-warnings-list"></ul>
                                </div>
                                <!-- Tips -->
                                <div class="detail-section hidden" id="detail-tips">
                                    <span class="detail-section-label">Tips</span>
                                    <ul class="detail-section-content" id="detail-tips-list"></ul>
                                </div>
                                <!-- Correlations (BETTER+) -->
                                <div class="detail-section hidden" id="detail-correlations">
                                    <span class="detail-section-label">Correlations</span>
                                    <div class="detail-section-content" id="detail-correlations-list"></div>
                                </div>
                                <!-- Summary (BETTER+) -->
                                <div class="detail-section hidden" id="detail-summary">
                                    <span class="detail-section-label">Insights</span>
                                    <div class="detail-section-content" id="detail-summary-list"></div>
                                </div>
                                <!-- Alerts (BEST) -->
                                <div class="detail-section hidden" id="detail-alerts">
                                    <span class="detail-section-label">Alerts</span>
                                    <div class="detail-section-content" id="detail-alerts-list"></div>
                                </div>
                            </div>
                        </details>

                        <!-- VC-3: LOOP SHORTCUTS -->
                        <div class="loop-shortcuts" id="loop-shortcuts">
                            <button type="button" class="loop-btn loop-reeval" id="loop-reeval">Re-Evaluate</button>
                            <button type="button" class="loop-btn loop-try-fix hidden" id="loop-try-fix">Try Another Fix</button>
                            <button type="button" class="loop-btn loop-save" id="loop-save">Save</button>
                        </div>
                    </div>

                    <div id="eval-error-panel" class="error-panel hidden">
                        <h3>Error</h3>
                        <div class="error-text" id="eval-error-text"></div>
                    </div>
                </div>
            </div>
        </div> <!-- End tab-evaluate -->

        <!-- History Tab Content (Ticket 6) -->
        <div class="tab-content {history_active}" id="tab-history">
            <div class="history-section">
                <div class="section-header">
                    <span class="section-title">Evaluation History</span>
                </div>

                <div id="history-content">
                    <div class="history-loading">Loading history...</div>
                </div>

                <!-- Empty state (shown when no items) -->
                <div id="history-empty" class="history-empty-state hidden">
                    <p>No evaluations yet.</p>
                    <button type="button" class="history-start-btn" onclick="switchToTab('evaluate')">Start Evaluating</button>
                </div>
            </div>
        </div> <!-- End tab-history -->

    </div>

    <script>
        // ============================================================
        // VC-2: FIX MODE ONLY (No freeform building)
        // ============================================================
        (function() {{
            // Elements
            const fixBlocked = document.getElementById('fix-blocked');
            const fixMode = document.getElementById('fix-mode');
            const fixProblem = document.getElementById('fix-problem');
            const fixSeverity = document.getElementById('fix-severity');
            const fixType = document.getElementById('fix-type');
            const fixDescription = document.getElementById('fix-description');
            const fixAffected = document.getElementById('fix-affected');
            const fixApplyBtn = document.getElementById('fix-apply-btn');
            const fixCancelBtn = document.getElementById('fix-cancel-btn');

            // Delta elements
            const fixDeltaSignalBefore = document.getElementById('fix-delta-signal-before');
            const fixDeltaGradeBefore = document.getElementById('fix-delta-grade-before');
            const fixDeltaScoreBefore = document.getElementById('fix-delta-score-before');
            const fixDeltaSignalAfter = document.getElementById('fix-delta-signal-after');
            const fixDeltaGradeAfter = document.getElementById('fix-delta-grade-after');
            const fixDeltaScoreAfter = document.getElementById('fix-delta-score-after');

            // Check for fix context and render appropriate state
            function checkFixContext() {{
                const ctx = window._fixContext;

                if (!ctx || !ctx.primaryFailure || !ctx.fastestFix) {{
                    // No fix context → show blocked state
                    fixBlocked.classList.remove('hidden');
                    fixMode.classList.add('hidden');
                    return;
                }}

                // Valid fix context → show fix mode
                fixBlocked.classList.add('hidden');
                fixMode.classList.remove('hidden');

                const pf = ctx.primaryFailure;
                const ff = ctx.fastestFix;
                const dp = ctx.deltaPreview;

                // A. Populate problem display
                fixSeverity.textContent = pf.severity.toUpperCase();
                fixSeverity.className = 'fix-problem-severity severity-' + pf.severity;
                fixProblem.className = 'fix-problem severity-' + pf.severity;

                fixType.textContent = pf.type.replace(/_/g, ' ');
                fixDescription.textContent = pf.description;

                if (pf.affectedLegIds && pf.affectedLegIds.length > 0) {{
                    fixAffected.textContent = pf.affectedLegIds.length + ' leg' + (pf.affectedLegIds.length > 1 ? 's' : '') + ' affected';
                    fixAffected.classList.remove('hidden');
                }} else {{
                    fixAffected.classList.add('hidden');
                }}

                // B. Populate delta comparison
                if (dp && dp.before) {{
                    fixDeltaSignalBefore.textContent = dp.before.signal.toUpperCase();
                    fixDeltaSignalBefore.className = 'fix-delta-signal signal-' + dp.before.signal;
                    fixDeltaGradeBefore.textContent = dp.before.grade;
                    fixDeltaScoreBefore.textContent = Math.round(dp.before.fragilityScore);
                }}

                if (dp && dp.after) {{
                    fixDeltaSignalAfter.textContent = dp.after.signal.toUpperCase();
                    fixDeltaSignalAfter.className = 'fix-delta-signal signal-' + dp.after.signal;
                    fixDeltaGradeAfter.textContent = dp.after.grade;
                    fixDeltaScoreAfter.textContent = Math.round(dp.after.fragilityScore);
                }} else {{
                    // No after state (e.g., single leg parlay)
                    fixDeltaSignalAfter.textContent = '--';
                    fixDeltaSignalAfter.className = 'fix-delta-signal';
                    fixDeltaGradeAfter.textContent = '--';
                    fixDeltaScoreAfter.textContent = '--';
                }}

                // C. Set button text based on action
                const actionLabels = {{
                    'remove_leg': 'Remove Problem Leg',
                    'split_parlay': 'Split Parlay',
                    'reduce_props': 'Reduce Props',
                    'swap_leg': 'Swap Leg'
                }};
                fixApplyBtn.textContent = actionLabels[ff.action] || 'Apply Fix';
            }}

            // Apply fix handler
            fixApplyBtn.addEventListener('click', async function() {{
                const ctx = window._fixContext;
                if (!ctx) return;

                fixApplyBtn.disabled = true;
                fixApplyBtn.textContent = 'Applying...';

                try {{
                    // Execute fix via API
                    const response = await fetch('/app/apply-fix', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            evaluation_id: ctx.evaluationId,
                            fix_action: ctx.fastestFix.action,
                            affected_leg_ids: ctx.primaryFailure.affectedLegIds || []
                        }})
                    }});

                    const data = await response.json();

                    if (response.ok && data.success) {{
                        // VC-3: Store before/after for payoff banner
                        window._fixApplied = {{
                            before: ctx.deltaPreview ? ctx.deltaPreview.before : null,
                            after: ctx.deltaPreview ? ctx.deltaPreview.after : null,
                            primaryFailureBefore: ctx.primaryFailure,
                            recommendationBefore: ctx.fastestFix
                        }};
                        // Clear fix context
                        window._fixContext = null;
                        // Store new evaluation result
                        window._lastEvalData = data.evaluation;
                        // Return to evaluate tab with new results
                        switchToTab('evaluate');
                        // Trigger result display with payoff flag
                        if (typeof showEvalResults === 'function') {{
                            showEvalResults(data.evaluation, null, true);
                        }}
                    }} else {{
                        alert(data.detail || 'Fix failed');
                        fixApplyBtn.disabled = false;
                        fixApplyBtn.textContent = 'Apply Fix';
                    }}
                }} catch (err) {{
                    console.error('Fix error:', err);
                    alert('Network error');
                    fixApplyBtn.disabled = false;
                    fixApplyBtn.textContent = 'Apply Fix';
                }}
            }});

            // Cancel handler
            fixCancelBtn.addEventListener('click', function() {{
                window._fixContext = null;
                switchToTab('evaluate');
            }});

            // Export check function for tab switching
            window._checkFixContext = checkFixContext;

            // Initial check
            checkFixContext();
        }})();

        // ============================================================
        // TAB SWITCHING
        // ============================================================
        // Global function for programmatic tab switching (exposed on window for inline handlers)
        window.switchToTab = function switchToTab(tabName) {{
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

            // VC-2: Check fix context when switching to builder
            if (tabName === 'builder' && typeof window._checkFixContext === 'function') {{
                window._checkFixContext();
            }}
        }};

        (function() {{
            const navTabs = document.querySelectorAll('.nav-tab');

            navTabs.forEach(tab => {{
                tab.addEventListener('click', function(e) {{
                    e.preventDefault();
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

            function showEvalResults(data, imageParse, showPayoff) {{
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
                const si = data.signalInfo || {{}};

                // ========================================
                // VC-3: PAYOFF BANNER + MINI DIFF
                // ========================================
                const payoffBanner = document.getElementById('payoff-banner');
                const miniDiff = document.getElementById('mini-diff');

                if (showPayoff && window._fixApplied) {{
                    const fa = window._fixApplied;
                    const before = fa.before;
                    const after = fa.after || (data.deltaPreview && data.deltaPreview.after);
                    const newPf = data.primaryFailure;
                    const newFf = newPf && newPf.fastestFix;

                    // Calculate improvement
                    const beforeScore = before ? Math.round(before.fragilityScore) : null;
                    const afterScore = after ? Math.round(after.fragilityScore) : (si.fragilityScore ? Math.round(si.fragilityScore) : null);
                    const improved = (beforeScore !== null && afterScore !== null && afterScore < beforeScore);
                    const delta = (beforeScore !== null && afterScore !== null) ? (beforeScore - afterScore) : 0;

                    // Populate banner
                    const payoffLine = document.getElementById('payoff-line');
                    const payoffStatus = document.getElementById('payoff-status');

                    if (before && afterScore !== null) {{
                        payoffLine.innerHTML = 'Signal: <strong>' + (before.signal || '').toUpperCase() + '</strong> &rarr; <strong>' + (si.signal || after.signal || '').toUpperCase() + '</strong> | Fragility: <strong>' + beforeScore + '</strong> &rarr; <strong>' + afterScore + '</strong> (<span class="delta-num">&Delta; ' + delta + '</span>)';
                    }} else {{
                        payoffLine.textContent = 'Fix applied successfully';
                    }}

                    if (improved) {{
                        payoffBanner.classList.remove('no-improvement');
                        payoffStatus.textContent = 'Improved';
                        payoffStatus.className = 'payoff-status improved';
                    }} else {{
                        payoffBanner.classList.add('no-improvement');
                        payoffStatus.textContent = 'No improvement';
                        payoffStatus.className = 'payoff-status no-change';
                    }}

                    payoffBanner.classList.remove('hidden');

                    // Populate mini diff
                    const pfBefore = fa.primaryFailureBefore;
                    const recBefore = fa.recommendationBefore;
                    document.getElementById('mini-diff-pf-before').textContent = pfBefore ? (pfBefore.type.replace(/_/g, ' ') + ' (' + pfBefore.severity + ')') : '--';
                    document.getElementById('mini-diff-pf-after').textContent = newPf ? (newPf.type.replace(/_/g, ' ') + ' (' + newPf.severity + ')') : 'None';
                    document.getElementById('mini-diff-rec-before').textContent = recBefore ? recBefore.action.replace(/_/g, ' ') : '--';
                    document.getElementById('mini-diff-rec-after').textContent = newFf ? newFf.action.replace(/_/g, ' ') : 'None';

                    miniDiff.classList.remove('hidden');
                }} else {{
                    payoffBanner.classList.add('hidden');
                    miniDiff.classList.add('hidden');
                    // Clear fix applied context on new eval
                    window._fixApplied = null;
                }}

                // ========================================
                // CONTEXT ECHO (Ticket 14 + Sprint 2)
                // ========================================
                const contextEcho = document.getElementById('context-echo');
                const ent = data.entities || {{}};
                const echoParts = [];
                if (ent.sport_guess && ent.sport_guess !== 'unknown') {{
                    echoParts.push(ent.sport_guess.toUpperCase());
                }}
                if (ent.teams_mentioned && ent.teams_mentioned.length > 0) {{
                    echoParts.push(ent.teams_mentioned.join(', '));
                }}
                if (ent.players_mentioned && ent.players_mentioned.length > 0) {{
                    echoParts.push(ent.players_mentioned.join(', '));
                }}
                if (ent.markets_detected && ent.markets_detected.length > 0) {{
                    const marketLabels = ent.markets_detected.filter(function(m) {{ return m !== 'spread' || !ent.markets_detected.includes('ml'); }});
                    if (marketLabels.length > 0) {{
                        echoParts.push(marketLabels.join(', ') + (marketLabels.length > 1 ? ' markets' : ' market'));
                    }}
                }}
                // Sprint 2: Add volatility flag
                if (ent.volatility_flag) {{
                    echoParts.push('Volatility: ' + ent.volatility_flag);
                }}
                // Sprint 2: Add same-game indicator
                const sgi = ent.same_game_indicator || {{}};
                if (sgi.has_same_game) {{
                    echoParts.push('Same-game: ' + sgi.same_game_count + ' legs');
                }}
                if (echoParts.length > 0) {{
                    contextEcho.textContent = 'Recognized: ' + echoParts.join(' | ');
                    contextEcho.classList.remove('hidden');
                }} else {{
                    contextEcho.classList.add('hidden');
                }}

                // ========================================
                // HUMAN SUMMARY (Sprint 2 — always shown)
                // ========================================
                const humanSummaryEl = document.getElementById('human-summary');
                if (humanSummaryEl && data.humanSummary) {{
                    humanSummaryEl.textContent = data.humanSummary;
                    humanSummaryEl.classList.remove('hidden');
                }} else if (humanSummaryEl) {{
                    humanSummaryEl.classList.add('hidden');
                }}

                // ========================================
                // COMPRESSED LAYOUT: VC-1 Visual Hierarchy
                // A. PRIMARY FAILURE (top, dominant)
                // B. FASTEST FIX (single CTA)
                // C. DELTA PREVIEW (before → after)
                // D. DETAILS ACCORDION (collapsed)
                // ========================================

                // === A. PRIMARY FAILURE ===
                const compressedPf = document.getElementById('compressed-pf');
                const pf = data.primaryFailure;
                if (pf && pf.description) {{
                    const cpfBadge = document.getElementById('cpf-badge');
                    cpfBadge.textContent = pf.type.replace('_', ' ').toUpperCase() + ' \u00B7 ' + pf.severity.toUpperCase();
                    cpfBadge.className = 'cpf-badge severity-' + pf.severity;
                    document.getElementById('cpf-description').textContent = pf.description;
                    compressedPf.classList.remove('hidden');
                }} else {{
                    // Fallback: show signal-based message
                    const cpfBadge = document.getElementById('cpf-badge');
                    cpfBadge.textContent = (si.label || 'SOLID').toUpperCase();
                    cpfBadge.className = 'cpf-badge signal-' + (si.signal || 'green');
                    document.getElementById('cpf-description').textContent = si.signalLine || 'This parlay structure is reasonable.';
                    compressedPf.classList.remove('hidden');
                }}

                // === B. FASTEST FIX CTA ===
                const fixCta = document.getElementById('compressed-fix-cta');
                if (pf && pf.fastestFix && pf.fastestFix.description) {{
                    fixCta.textContent = '\u2192 ' + pf.fastestFix.description;
                    fixCta.classList.remove('hidden');
                    // Wire CTA to builder with context (VC-2: must include all required data)
                    fixCta.onclick = function() {{
                        window._fixContext = {{
                            evaluationId: data.evaluationId || null,
                            primaryFailure: pf,
                            fastestFix: pf.fastestFix,
                            deltaPreview: dp || null
                        }};
                        switchToTab('builder');
                    }};
                }} else {{
                    fixCta.classList.add('hidden');
                }}

                // === C. DELTA PREVIEW ===
                const compressedDelta = document.getElementById('compressed-delta');
                const dp = data.deltaPreview;
                if (dp && dp.before && dp.after) {{
                    document.getElementById('cdelta-signal-before').textContent = dp.before.signal.toUpperCase();
                    document.getElementById('cdelta-signal-before').className = 'cdelta-signal signal-' + dp.before.signal;
                    document.getElementById('cdelta-score-before').textContent = dp.before.grade + ' (' + Math.round(dp.before.fragilityScore) + ')';

                    document.getElementById('cdelta-signal-after').textContent = dp.after.signal.toUpperCase();
                    document.getElementById('cdelta-signal-after').className = 'cdelta-signal signal-' + dp.after.signal;
                    document.getElementById('cdelta-score-after').textContent = dp.after.grade + ' (' + Math.round(dp.after.fragilityScore) + ')';

                    compressedDelta.classList.remove('hidden');
                }} else {{
                    compressedDelta.classList.add('hidden');
                }}

                // === D. DETAILS ACCORDION ===
                // Signal + Fragility rows
                document.getElementById('detail-signal').textContent = (si.label || 'Solid') + ' (' + (si.signal || 'green').toUpperCase() + ')';
                document.getElementById('detail-signal').className = 'detail-value signal-' + (si.signal || 'green');
                document.getElementById('detail-fragility').textContent = Math.round(si.fragilityScore || fragility.display_value || 0);

                // Metrics
                document.getElementById('detail-leg-penalty').textContent = '+' + (metrics.leg_penalty || 0).toFixed(1);
                document.getElementById('detail-correlation').textContent = '+' + (metrics.correlation_penalty || 0).toFixed(1);

                // Contributors
                const detailContributors = document.getElementById('detail-contributors');
                const detailContributorsList = document.getElementById('detail-contributors-list');
                const contributors = explain.contributors || [];
                if (contributors.length > 0) {{
                    let contribHtml = '';
                    contributors.forEach(function(c) {{
                        contribHtml += '<div class="detail-contributor">';
                        contribHtml += '<span class="contrib-type">' + c.type + '</span>';
                        contribHtml += '<span class="contrib-impact impact-' + c.impact + '">' + c.impact + '</span>';
                        contribHtml += '</div>';
                    }});
                    detailContributorsList.innerHTML = contribHtml;
                    detailContributors.classList.remove('hidden');
                }} else {{
                    detailContributors.classList.add('hidden');
                }}

                // Secondary Factors (Sprint 2)
                const detailSecondaryFactors = document.getElementById('detail-secondary-factors');
                const detailSecondaryFactorsList = document.getElementById('detail-secondary-factors-list');
                const secondaryFactors = data.secondaryFactors || [];
                if (secondaryFactors.length > 0) {{
                    let sfHtml = '';
                    secondaryFactors.forEach(function(sf) {{
                        sfHtml += '<div class="detail-secondary-factor">';
                        sfHtml += '<span class="sf-type">' + sf.type.replace(/_/g, ' ') + '</span>';
                        sfHtml += '<span class="sf-impact impact-' + sf.impact + '">' + sf.impact + '</span>';
                        sfHtml += '<div class="sf-explanation">' + sf.explanation + '</div>';
                        sfHtml += '</div>';
                    }});
                    detailSecondaryFactorsList.innerHTML = sfHtml;
                    detailSecondaryFactors.classList.remove('hidden');
                }} else {{
                    detailSecondaryFactors.classList.add('hidden');
                }}

                // Warnings
                const detailWarnings = document.getElementById('detail-warnings');
                const detailWarningsList = document.getElementById('detail-warnings-list');
                const warnings = explain.warnings || [];
                if (warnings.length > 0) {{
                    detailWarningsList.innerHTML = warnings.map(function(w) {{ return '<li>' + w + '</li>'; }}).join('');
                    detailWarnings.classList.remove('hidden');
                }} else {{
                    detailWarnings.classList.add('hidden');
                }}

                // Tips
                const detailTips = document.getElementById('detail-tips');
                const detailTipsList = document.getElementById('detail-tips-list');
                const tips = explain.tips || [];
                const whatToDo = fragility.what_to_do || '';
                const meaning = fragility.meaning || '';
                let allTips = tips.slice();
                if (meaning) allTips.push(meaning);
                if (whatToDo) allTips.push(whatToDo);
                if (allTips.length > 0) {{
                    detailTipsList.innerHTML = allTips.map(function(t) {{ return '<li>' + t + '</li>'; }}).join('');
                    detailTips.classList.remove('hidden');
                }} else {{
                    detailTips.classList.add('hidden');
                }}

                // Correlations (BETTER+)
                const detailCorrelations = document.getElementById('detail-correlations');
                const detailCorrelationsList = document.getElementById('detail-correlations-list');
                if ((tier === 'better' || tier === 'best') && correlations.length > 0) {{
                    let corrHtml = '';
                    correlations.forEach(function(c) {{
                        corrHtml += '<div class="detail-corr-item">';
                        corrHtml += '<span>' + c.block_a + ' / ' + c.block_b + '</span>';
                        corrHtml += '<span class="corr-type">' + c.type + '</span>';
                        corrHtml += '<span class="corr-penalty">+' + (c.penalty || 0).toFixed(1) + '</span>';
                        corrHtml += '</div>';
                    }});
                    detailCorrelationsList.innerHTML = corrHtml;
                    detailCorrelations.classList.remove('hidden');
                }} else {{
                    detailCorrelations.classList.add('hidden');
                }}

                // Summary / Insights (BETTER+)
                const detailSummary = document.getElementById('detail-summary');
                const detailSummaryList = document.getElementById('detail-summary-list');
                const summaryItems = explain.summary || [];
                if ((tier === 'better' || tier === 'best') && summaryItems.length > 0) {{
                    detailSummaryList.innerHTML = summaryItems.map(function(s) {{ return '<div class="detail-insight">' + s + '</div>'; }}).join('');
                    detailSummary.classList.remove('hidden');
                }} else {{
                    detailSummary.classList.add('hidden');
                }}

                // Alerts (BEST only)
                const detailAlerts = document.getElementById('detail-alerts');
                const detailAlertsList = document.getElementById('detail-alerts-list');
                const alertItems = explain.alerts || [];
                const contextAlerts = (data.context && data.context.alerts_generated) || 0;
                if (tier === 'best' && (alertItems.length > 0 || contextAlerts > 0)) {{
                    let alertsHtml = '';
                    alertItems.forEach(function(a) {{ alertsHtml += '<div class="detail-alert">' + a + '</div>'; }});
                    if (contextAlerts > 0) {{
                        alertsHtml += '<div class="detail-alert">\u26A0 Live conditions affecting this parlay</div>';
                    }}
                    detailAlertsList.innerHTML = alertsHtml;
                    detailAlerts.classList.remove('hidden');
                }} else {{
                    detailAlerts.classList.add('hidden');
                }}

                // === Context Modifiers (weather/injury) → add to warnings ===
                const ctxMods = (data.context && data.context.impact && data.context.impact.modifiers) || [];
                if (ctxMods.length > 0) {{
                    const weatherMods = ctxMods.filter(function(m) {{ return m.reason && m.reason.toLowerCase().indexOf('weather') !== -1; }});
                    const injuryMods = ctxMods.filter(function(m) {{ return m.affected_players && m.affected_players.length > 0; }});
                    if (weatherMods.length > 0 || injuryMods.length > 0) {{
                        weatherMods.concat(injuryMods).forEach(function(m) {{
                            detailWarningsList.innerHTML += '<li>' + m.reason + '</li>';
                        }});
                        detailWarnings.classList.remove('hidden');
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

                // VC-3: Show/hide "Try Another Fix" button
                const loopTryFix = document.getElementById('loop-try-fix');
                if (loopTryFix) {{
                    if (pf && pf.fastestFix && dp && dp.after) {{
                        loopTryFix.classList.remove('hidden');
                    }} else {{
                        loopTryFix.classList.add('hidden');
                    }}
                }}

                // Store last eval data for re-evaluate
                window._lastEvalData = data;
            }}

            // Staged analysis progress (Ticket 14)
            const analysisProgress = document.getElementById('analysis-progress');
            const apSteps = [
                document.getElementById('ap-step-1'),
                document.getElementById('ap-step-2'),
                document.getElementById('ap-step-3'),
                document.getElementById('ap-step-4'),
                document.getElementById('ap-step-5'),
            ];

            function showAnalysisProgress() {{
                evalResultsPlaceholder.classList.add('hidden');
                evalResultsContent.classList.add('hidden');
                evalErrorPanel.classList.add('hidden');
                analysisProgress.classList.remove('hidden');
                apSteps.forEach(function(s) {{ s.className = 'ap-step'; }});
            }}

            function hideAnalysisProgress() {{
                analysisProgress.classList.add('hidden');
            }}

            async function runProgressSteps() {{
                // Step through each stage with short visible intervals
                for (let i = 0; i < apSteps.length; i++) {{
                    if (i > 0) apSteps[i-1].classList.remove('active');
                    if (i > 0) apSteps[i-1].classList.add('done');
                    apSteps[i].classList.add('active');
                    await new Promise(function(r) {{ setTimeout(r, 120); }});
                }}
            }}

            async function finishProgressSteps() {{
                // Mark all done
                apSteps.forEach(function(s) {{
                    s.classList.remove('active');
                    s.classList.add('done');
                }});
                await new Promise(function(r) {{ setTimeout(r, 100); }});
                hideAnalysisProgress();
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

                        // Show staged progress
                        showAnalysisProgress();
                        const progressPromise = runProgressSteps();

                        response = await fetch('/app/evaluate', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ input, tier }})
                        }});

                        data = await response.json();

                        // Wait for progress animation to reach end, then hide
                        await progressPromise;
                        await finishProgressSteps();

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

            // VC-3: Payoff banner dismiss
            const payoffDismiss = document.getElementById('payoff-dismiss');
            if (payoffDismiss) {{
                payoffDismiss.addEventListener('click', function() {{
                    document.getElementById('payoff-banner').classList.add('hidden');
                    document.getElementById('mini-diff').classList.add('hidden');
                    window._fixApplied = null;
                }});
            }}

            // VC-3: Loop Shortcuts
            // Re-Evaluate button: reset results and focus input
            const loopReeval = document.getElementById('loop-reeval');
            if (loopReeval) {{
                loopReeval.addEventListener('click', function() {{
                    evalResultsContent.classList.add('hidden');
                    evalResultsPlaceholder.classList.remove('hidden');
                    evalErrorPanel.classList.add('hidden');
                    // Clear payoff state
                    document.getElementById('payoff-banner').classList.add('hidden');
                    document.getElementById('mini-diff').classList.add('hidden');
                    window._fixApplied = null;
                    if (currentInputMode === 'text') {{
                        textInput.focus();
                        textInput.select();
                    }}
                    updateEvalSubmitState();
                }});
            }}

            // Try Another Fix button: go to builder with current context
            const loopTryFix = document.getElementById('loop-try-fix');
            if (loopTryFix) {{
                loopTryFix.addEventListener('click', function() {{
                    if (window._lastEvalData) {{
                        const data = window._lastEvalData;
                        const pf = data.primaryFailure;
                        const dp = data.deltaPreview;
                        if (pf && pf.fastestFix) {{
                            window._fixContext = {{
                                evaluationId: data.evaluationId || null,
                                primaryFailure: pf,
                                fastestFix: pf.fastestFix,
                                deltaPreview: dp || null
                            }};
                            switchToTab('builder');
                        }}
                    }}
                }});
            }}

            // Save button: persist evaluation
            const loopSave = document.getElementById('loop-save');
            if (loopSave) {{
                loopSave.addEventListener('click', function() {{
                    if (window._lastEvalData && window._lastEvalData.evaluation_id) {{
                        loopSave.textContent = 'Saved';
                        loopSave.disabled = true;
                        loopSave.style.background = '#4ade80';
                        loopSave.style.color = '#000';
                    }} else {{
                        loopSave.textContent = 'Login to Save';
                        loopSave.disabled = true;
                    }}
                }});
            }}
        }})();

        // ============================================================
        // HISTORY TAB FUNCTIONALITY (Ticket 6)
        // ============================================================
        (function() {{
            let historyLoaded = false;

            // Re-evaluate: load input into Evaluate tab and trigger evaluation
            window.historyReEvaluate = async function(itemId) {{
                try {{
                    const response = await fetch('/app/history/' + itemId);
                    const data = await response.json();
                    if (data.item && data.item.raw) {{
                        const inputText = data.item.inputText || (data.item.raw.input && data.item.raw.input.bet_text) || '';
                        const textInput = document.getElementById('text-input');
                        if (textInput && inputText) {{
                            textInput.value = inputText;
                            switchToTab('evaluate');
                            // Focus the input
                            textInput.focus();
                        }}
                    }}
                }} catch (err) {{
                    console.error('Failed to load history item for re-evaluate:', err);
                }}
            }};

            // Edit: load into Builder with fix context (if available)
            window.historyEdit = async function(itemId) {{
                try {{
                    const response = await fetch('/app/history/' + itemId);
                    const data = await response.json();
                    if (data.item && data.item.raw) {{
                        const raw = data.item.raw;
                        // Set up fix context if we have primaryFailure
                        if (raw.primaryFailure && raw.primaryFailure.fastestFix) {{
                            window._fixContext = {{
                                evaluationId: itemId,
                                primaryFailure: raw.primaryFailure,
                                fastestFix: raw.primaryFailure.fastestFix,
                                deltaPreview: raw.deltaPreview || null
                            }};
                        }}
                        switchToTab('builder');
                    }}
                }} catch (err) {{
                    console.error('Failed to load history item for edit:', err);
                }}
            }};

            window.loadHistory = async function(forceReload) {{
                if (historyLoaded && !forceReload) return;

                const historyContent = document.getElementById('history-content');
                const historyEmpty = document.getElementById('history-empty');

                historyContent.innerHTML = '<div class="history-loading">Loading history...</div>';
                if (historyEmpty) historyEmpty.classList.add('hidden');

                try {{
                    const response = await fetch('/app/history');
                    const data = await response.json();
                    const items = data.items || [];

                    if (items.length === 0) {{
                        historyContent.innerHTML = '';
                        if (historyEmpty) historyEmpty.classList.remove('hidden');
                        historyLoaded = true;
                        return;
                    }}

                    if (historyEmpty) historyEmpty.classList.add('hidden');

                    let html = '';
                    items.forEach(function(item) {{
                        const date = new Date(item.createdAt).toLocaleString();
                        const score = Math.round(item.fragilityScore || 0);
                        const signal = item.signal || 'green';
                        const label = item.label || 'Solid';
                        const sport = item.sport || '';

                        html += '<div class="history-item" data-id="' + item.id + '">';
                        html += '<div class="history-item-header">';
                        html += '<div class="history-item-meta">';
                        html += '<div class="history-date">' + date + '</div>';
                        if (sport) {{ html += '<div class="history-sport">' + sport + '</div>'; }}
                        html += '</div>';
                        html += '<div class="history-item-actions">';
                        html += '<button type="button" class="history-action-btn primary" onclick="historyReEvaluate(\'' + item.id + '\')">Re-Evaluate</button>';
                        html += '<button type="button" class="history-action-btn" onclick="historyEdit(\'' + item.id + '\')">Edit</button>';
                        html += '</div>';
                        html += '</div>';
                        html += '<div class="history-text">' + (item.inputText || 'N/A') + '</div>';
                        html += '<span class="history-grade ' + signal + '">' + score + ' - ' + label + '</span>';
                        html += '</div>';
                    }});

                    historyContent.innerHTML = html;
                    historyLoaded = true;

                }} catch (err) {{
                    console.error('Failed to load history:', err);
                    historyContent.innerHTML = "<div class='history-empty-state'><p>Failed to load history</p></div>";
                }}
            }};

            // Load history if starting on history tab
            const activeTab = new URLSearchParams(window.location.search).get('tab');
            if (activeTab === 'history') {{
                loadHistory();
            }}
        }})();

        // ============================================================
        // PARLAY BUILDER (Sprint 2)
        // ============================================================
        (function() {{
            // Team/Player dictionaries for auto-suggest
            const NBA_TEAMS = {{
                'lakers': 'LAL', 'celtics': 'BOS', 'nuggets': 'DEN', 'bucks': 'MIL',
                'warriors': 'GSW', 'suns': 'PHX', '76ers': 'PHI', 'mavericks': 'DAL',
                'heat': 'MIA', 'nets': 'BKN', 'knicks': 'NYK', 'bulls': 'CHI',
                'clippers': 'LAC', 'thunder': 'OKC', 'timberwolves': 'MIN', 'kings': 'SAC',
                'pelicans': 'NOP', 'grizzlies': 'MEM', 'cavaliers': 'CLE', 'hawks': 'ATL',
                'raptors': 'TOR', 'pacers': 'IND', 'hornets': 'CHA', 'wizards': 'WAS',
                'magic': 'ORL', 'pistons': 'DET', 'jazz': 'UTA', 'rockets': 'HOU',
                'spurs': 'SAS', 'trail blazers': 'POR'
            }};
            const NFL_TEAMS = {{
                'chiefs': 'KC', 'eagles': 'PHI', 'bills': 'BUF', 'cowboys': 'DAL',
                '49ers': 'SF', 'ravens': 'BAL', 'bengals': 'CIN', 'dolphins': 'MIA',
                'lions': 'DET', 'packers': 'GB', 'steelers': 'PIT', 'chargers': 'LAC',
                'rams': 'LAR', 'seahawks': 'SEA', 'jaguars': 'JAX', 'patriots': 'NE',
                'giants': 'NYG', 'jets': 'NYJ', 'broncos': 'DEN', 'texans': 'HOU',
                'titans': 'TEN', 'colts': 'IND', 'raiders': 'LV', 'saints': 'NO',
                'panthers': 'CAR', 'bears': 'CHI', 'commanders': 'WAS', 'falcons': 'ATL',
                'cardinals': 'ARI', 'buccaneers': 'TB', 'vikings': 'MIN'
            }};
            const NBA_PLAYERS = [
                'LeBron James', 'Anthony Davis', 'Jayson Tatum', 'Jaylen Brown',
                'Nikola Jokic', 'Jamal Murray', 'Giannis Antetokounmpo', 'Damian Lillard',
                'Stephen Curry', 'Klay Thompson', 'Kevin Durant', 'Devin Booker',
                'Joel Embiid', 'Tyrese Maxey', 'Luka Doncic', 'Kyrie Irving',
                'Jimmy Butler', 'Bam Adebayo', 'Shai Gilgeous-Alexander', 'Donovan Mitchell',
                'Trae Young', 'LaMelo Ball', 'Paolo Banchero', 'Victor Wembanyama',
                'Ja Morant', 'Anthony Edwards', 'De\'Aaron Fox'
            ];
            const NFL_PLAYERS = [
                'Patrick Mahomes', 'Josh Allen', 'Jalen Hurts', 'Lamar Jackson',
                'Joe Burrow', 'Travis Kelce', 'Tyreek Hill', 'Derrick Henry',
                'CeeDee Lamb', 'Justin Jefferson', 'Davante Adams', 'Ja\'Marr Chase',
                'Saquon Barkley', 'Christian McCaffrey', 'Dak Prescott', 'Stefon Diggs'
            ];

            let currentLegCount = 2;
            let selectedTier = 'good';
            let activeDropdownLeg = null;

            // Get suggestions based on sport and query
            function getSuggestions(query, sport) {{
                if (!query || query.length < 2) return [];
                const q = query.toLowerCase();
                const suggestions = [];

                // Teams
                const teams = sport === 'nfl' ? NFL_TEAMS : NBA_TEAMS;
                Object.keys(teams).forEach(function(name) {{
                    if (name.includes(q)) {{
                        suggestions.push({{ name: name.charAt(0).toUpperCase() + name.slice(1), type: 'team', abbr: teams[name] }});
                    }}
                }});

                // Players
                const players = sport === 'nfl' ? NFL_PLAYERS : NBA_PLAYERS;
                players.forEach(function(name) {{
                    if (name.toLowerCase().includes(q)) {{
                        suggestions.push({{ name: name, type: 'player' }});
                    }}
                }});

                return suggestions.slice(0, 8);
            }}

            // Show auto-suggest dropdown
            function showDropdown(legIndex, suggestions) {{
                const dropdown = document.querySelector('.autosuggest-dropdown[data-leg="' + legIndex + '"]');
                if (!dropdown) return;

                if (suggestions.length === 0) {{
                    dropdown.classList.add('hidden');
                    return;
                }}

                let html = '';
                suggestions.forEach(function(s, i) {{
                    html += '<div class="autosuggest-item' + (i === 0 ? ' selected' : '') + '" data-value="' + s.name + '" data-type="' + s.type + '">';
                    html += s.name;
                    html += '<span class="item-type">' + s.type + '</span>';
                    html += '</div>';
                }});
                dropdown.innerHTML = html;
                dropdown.classList.remove('hidden');
                activeDropdownLeg = legIndex;

                // Click handlers
                dropdown.querySelectorAll('.autosuggest-item').forEach(function(item) {{
                    item.addEventListener('click', function() {{
                        selectSuggestion(legIndex, item.dataset.value, item.dataset.type);
                    }});
                }});
            }}

            // Select a suggestion
            function selectSuggestion(legIndex, value, type) {{
                const input = document.querySelector('.team-player-input[data-leg="' + legIndex + '"]');
                if (input) {{
                    input.value = value;
                }}
                hideDropdown(legIndex);
                updateLegExplanation(legIndex, value, type);
            }}

            // Hide dropdown
            function hideDropdown(legIndex) {{
                const dropdown = document.querySelector('.autosuggest-dropdown[data-leg="' + legIndex + '"]');
                if (dropdown) {{
                    dropdown.classList.add('hidden');
                }}
                activeDropdownLeg = null;
            }}

            // Update leg explanation (why this leg matters)
            function updateLegExplanation(legIndex, value, type) {{
                const explanation = document.querySelector('.leg-explanation[data-leg="' + legIndex + '"]');
                if (!explanation) return;

                const market = document.querySelector('.market-select[data-leg="' + legIndex + '"]');
                const marketValue = market ? market.value : 'spread';

                let text = '';
                if (type === 'player') {{
                    if (marketValue === 'prop') {{
                        text = 'Player props add variance — performance depends on game flow, minutes, and matchup.';
                    }} else {{
                        text = 'Player selections correlate with team outcomes — consider how ' + value + '\'s game affects the team line.';
                    }}
                }} else if (type === 'team') {{
                    if (marketValue === 'spread') {{
                        text = 'Spreads balance risk — ' + value + ' must win by the margin for this to hit.';
                    }} else if (marketValue === 'ml') {{
                        text = 'Moneyline is straightforward — ' + value + ' just needs to win outright.';
                    }} else if (marketValue === 'total') {{
                        text = 'Game totals depend on pace and defense — both teams contribute to this outcome.';
                    }} else {{
                        text = 'Player props on team games add correlation — consider same-game dependency.';
                    }}
                }}

                if (text) {{
                    explanation.textContent = text;
                    explanation.classList.remove('hidden');
                }} else {{
                    explanation.classList.add('hidden');
                }}
            }}

            // Setup input listeners
            function setupInputListeners() {{
                document.querySelectorAll('.team-player-input').forEach(function(input) {{
                    const legIndex = input.dataset.leg;

                    input.addEventListener('input', function() {{
                        const sport = document.getElementById('builder-sport').value;
                        const suggestions = getSuggestions(input.value, sport);
                        showDropdown(legIndex, suggestions);
                    }});

                    input.addEventListener('blur', function() {{
                        // Delay to allow click on dropdown
                        setTimeout(function() {{ hideDropdown(legIndex); }}, 200);
                    }});

                    input.addEventListener('keydown', function(e) {{
                        const dropdown = document.querySelector('.autosuggest-dropdown[data-leg="' + legIndex + '"]');
                        if (dropdown.classList.contains('hidden')) return;

                        const items = dropdown.querySelectorAll('.autosuggest-item');
                        const selected = dropdown.querySelector('.autosuggest-item.selected');
                        let selectedIndex = Array.from(items).indexOf(selected);

                        if (e.key === 'ArrowDown') {{
                            e.preventDefault();
                            if (selectedIndex < items.length - 1) {{
                                if (selected) selected.classList.remove('selected');
                                items[selectedIndex + 1].classList.add('selected');
                            }}
                        }} else if (e.key === 'ArrowUp') {{
                            e.preventDefault();
                            if (selectedIndex > 0) {{
                                if (selected) selected.classList.remove('selected');
                                items[selectedIndex - 1].classList.add('selected');
                            }}
                        }} else if (e.key === 'Enter') {{
                            e.preventDefault();
                            if (selected) {{
                                selectSuggestion(legIndex, selected.dataset.value, selected.dataset.type);
                            }}
                        }} else if (e.key === 'Escape') {{
                            hideDropdown(legIndex);
                        }}
                    }});
                }});

                // Market change updates explanation
                document.querySelectorAll('.market-select').forEach(function(select) {{
                    select.addEventListener('change', function() {{
                        const legIndex = select.dataset.leg;
                        const input = document.querySelector('.team-player-input[data-leg="' + legIndex + '"]');
                        if (input && input.value) {{
                            // Re-evaluate explanation
                            const teams = Object.keys(NBA_TEAMS).concat(Object.keys(NFL_TEAMS));
                            const isTeam = teams.some(function(t) {{ return input.value.toLowerCase().includes(t); }});
                            updateLegExplanation(legIndex, input.value, isTeam ? 'team' : 'player');
                        }}
                    }});
                }});
            }}

            // Tier selection
            document.querySelectorAll('.builder-tier-option').forEach(function(option) {{
                option.addEventListener('click', function() {{
                    document.querySelectorAll('.builder-tier-option').forEach(function(o) {{ o.classList.remove('selected'); }});
                    option.classList.add('selected');
                    selectedTier = option.dataset.tier;
                }});
            }});

            // Update leg count display
            function updateLegCountDisplay() {{
                const countEl = document.getElementById('builder-leg-count');
                if (countEl) {{
                    countEl.textContent = currentLegCount + ' leg' + (currentLegCount !== 1 ? 's' : '');
                }}
            }}

            // Add leg
            window.addBuilderLeg = function() {{
                if (currentLegCount >= 6) return;
                currentLegCount++;
                const legsContainer = document.getElementById('builder-legs');
                const legHtml = `
                    <div class="builder-leg" data-leg-index="${{currentLegCount - 1}}">
                        <div class="leg-header">
                            <span class="leg-label">Leg ${{currentLegCount}}</span>
                            <button type="button" class="leg-remove-btn" onclick="removeBuilderLeg(${{currentLegCount - 1}})" title="Remove leg">&times;</button>
                        </div>
                        <div class="leg-field">
                            <label class="leg-field-label">TEAM / PLAYER</label>
                            <div class="autosuggest-wrapper">
                                <input type="text" class="leg-input team-player-input" data-leg="${{currentLegCount - 1}}" placeholder="e.g., Lakers or LeBron James" autocomplete="off">
                                <div class="autosuggest-dropdown hidden" data-leg="${{currentLegCount - 1}}"></div>
                            </div>
                            <div class="leg-explanation hidden" data-leg="${{currentLegCount - 1}}"></div>
                        </div>
                        <div class="leg-row">
                            <div class="leg-field leg-field-half">
                                <label class="leg-field-label">MARKET</label>
                                <select class="leg-select market-select" data-leg="${{currentLegCount - 1}}">
                                    <option value="spread">Spread</option>
                                    <option value="ml">Moneyline</option>
                                    <option value="total">Total (O/U)</option>
                                    <option value="prop">Player Prop</option>
                                </select>
                            </div>
                            <div class="leg-field leg-field-half">
                                <label class="leg-field-label">LINE / CONDITION</label>
                                <input type="text" class="leg-input line-input" data-leg="${{currentLegCount - 1}}" placeholder="e.g., -5.5 or O 220.5">
                            </div>
                        </div>
                        <div class="leg-field">
                            <label class="leg-field-label">ODDS</label>
                            <input type="text" class="leg-input odds-input" data-leg="${{currentLegCount - 1}}" placeholder="e.g., -110">
                        </div>
                    </div>
                `;
                legsContainer.insertAdjacentHTML('beforeend', legHtml);
                updateLegCountDisplay();
                setupInputListeners();

                if (currentLegCount >= 6) {{
                    document.getElementById('add-leg-btn').disabled = true;
                }}
            }};

            // Remove leg
            window.removeBuilderLeg = function(index) {{
                if (currentLegCount <= 2) return;
                const leg = document.querySelector('.builder-leg[data-leg-index="' + index + '"]');
                if (leg) {{
                    leg.remove();
                    currentLegCount--;
                    // Re-number remaining legs
                    document.querySelectorAll('.builder-leg').forEach(function(leg, i) {{
                        leg.dataset.legIndex = i;
                        leg.querySelector('.leg-label').textContent = 'Leg ' + (i + 1);
                        leg.querySelector('.leg-remove-btn').setAttribute('onclick', 'removeBuilderLeg(' + i + ')');
                        leg.querySelectorAll('[data-leg]').forEach(function(el) {{
                            el.dataset.leg = i;
                        }});
                    }});
                    updateLegCountDisplay();
                    document.getElementById('add-leg-btn').disabled = false;
                }}
            }};

            // Evaluate parlay
            window.evaluateBuilderParlay = function() {{
                const legs = [];
                document.querySelectorAll('.builder-leg').forEach(function(leg) {{
                    const teamPlayer = leg.querySelector('.team-player-input').value.trim();
                    const market = leg.querySelector('.market-select').value;
                    const line = leg.querySelector('.line-input').value.trim();

                    if (teamPlayer) {{
                        let legText = teamPlayer;
                        if (market === 'spread' && line) legText += ' ' + line;
                        else if (market === 'ml') legText += ' ML';
                        else if (market === 'total' && line) legText += ' ' + line;
                        else if (market === 'prop' && line) legText += ' ' + line;
                        legs.push(legText);
                    }}
                }});

                if (legs.length < 2) {{
                    alert('Please fill in at least 2 legs');
                    return;
                }}

                // Build bet text and evaluate
                const betText = legs.join(' + ');
                const evaluateInput = document.getElementById('eval-text-input');
                if (evaluateInput) {{
                    evaluateInput.value = betText;
                }}

                // Set tier
                const tierRadio = document.getElementById('eval-tier-' + selectedTier);
                if (tierRadio) tierRadio.checked = true;

                // Switch to evaluate tab and submit
                switchToTab('evaluate');
                setTimeout(function() {{
                    document.getElementById('eval-submit-btn').click();
                }}, 100);
            }};

            // Initialize
            setupInputListeners();
            updateLegCountDisplay();
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
            "primaryFailure": result.primary_failure,
            "deltaPreview": result.delta_preview,
            "signalInfo": result.signal_info,
            "entities": result.entities,
            "secondaryFactors": result.secondary_factors,
            "humanSummary": result.human_summary,
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

        # Ticket 6/6B: Save to history store (in-memory, no auth required)
        try:
            from app.history_store import get_history_store, create_history_item
            history_item = create_history_item(response_data, normalized.input_text)
            get_history_store().add(history_item)
            # Ticket 6B: evaluationId is canonical, historyId is deprecated alias
            response_data["evaluationId"] = history_item.id
            response_data["historyId"] = history_item.id  # Deprecated, use evaluationId
        except Exception as history_err:
            _logger.warning(f"Failed to save to history: {history_err}")

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
# VC-2: Apply Fix API (Fix Mode Only)
# =============================================================================


@router.post("/app/apply-fix")
async def apply_fix(request: ApplyFixRequest, raw_request: Request):
    """
    VC-2: Execute a fix and re-evaluate.

    This endpoint:
    1. Takes a pre-determined fix action from primaryFailure.fastestFix
    2. Simulates the fix by modifying the bet structure
    3. Re-evaluates with the modified structure
    4. Returns the new evaluation result

    No new evaluation math - uses existing pipeline.
    """
    from app.pipeline import run_evaluation
    from auth.middleware import get_session_id
    from auth.service import get_current_user

    request_id = get_request_id(raw_request) or str(uuid.uuid4())[:8]

    # Validate fix action
    valid_actions = ["remove_leg", "split_parlay", "reduce_props", "swap_leg"]
    if request.fix_action not in valid_actions:
        return JSONResponse(
            status_code=400,
            content={
                "request_id": request_id,
                "success": False,
                "detail": f"Invalid fix action: {request.fix_action}",
            },
        )

    # Get the last evaluation data to apply fix
    # In a real implementation, this would fetch from storage using evaluation_id
    # For now, we simulate by creating a modified input

    # Simulate fix by creating a simplified parlay
    # The fix removes affected legs, resulting in a simpler structure
    affected_count = len(request.affected_leg_ids) if request.affected_leg_ids else 1

    # Create a mock fixed input (2-leg parlay with independent teams)
    # This represents the result of applying the fix
    fixed_input = "Lakers -5.5 + Celtics ML parlay"

    # Get session info for tier
    session_id = get_session_id(raw_request)
    user = get_current_user(session_id)
    tier = user.tier if user else "good"

    try:
        # Validate through airlock
        normalized = airlock_ingest(
            input_text=fixed_input,
            tier=tier,
        )

        # Run evaluation with fixed input
        result = run_evaluation(normalized)

        # Build evaluation response data
        eval_response = result.evaluation
        evaluation_data = {
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
        }

        return JSONResponse(
            status_code=200,
            content={
                "request_id": request_id,
                "success": True,
                "evaluation": evaluation_data,
                "fix_applied": {
                    "action": request.fix_action,
                    "affected_legs_removed": affected_count,
                },
            },
        )

    except AirlockError as e:
        return JSONResponse(
            status_code=400,
            content={
                "request_id": request_id,
                "success": False,
                "detail": e.message,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "success": False,
                "detail": str(e),
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
            "primaryFailure": result.primary_failure,
            "deltaPreview": result.delta_preview,
            "signalInfo": result.signal_info,
            "entities": result.entities,
            "secondaryFactors": result.secondary_factors,
            "humanSummary": result.human_summary,
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

        # Ticket 6/6B: Save to history store (in-memory, no auth required)
        try:
            from app.history_store import get_history_store, create_history_item
            history_item = create_history_item(response, normalized.input_text)
            get_history_store().add(history_item)
            # Ticket 6B: evaluationId is canonical, historyId is deprecated alias
            response["evaluationId"] = history_item.id
            response["historyId"] = history_item.id  # Deprecated, use evaluationId
        except Exception as history_err:
            _logger.warning(f"Failed to save image eval to history: {history_err}")

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
# History API (Ticket 6)
# =============================================================================


@router.get("/app/history")
async def get_history(raw_request: Request, limit: int = 50):
    """
    Get evaluation history.

    Returns items in reverse chronological order (newest first).
    No authentication required - uses in-memory store.
    """
    from app.history_store import get_history_store

    request_id = get_request_id(raw_request) or "unknown"
    store = get_history_store()

    items = store.list(limit=limit)
    return {
        "request_id": request_id,
        "items": [item.to_dict() for item in items],
        "count": len(items),
    }


@router.get("/app/history/{item_id}")
async def get_history_item(item_id: str, raw_request: Request):
    """
    Get a specific history item by ID.

    Returns the item with optional raw evaluation data.
    """
    from app.history_store import get_history_store

    request_id = get_request_id(raw_request) or "unknown"
    store = get_history_store()

    item = store.get(item_id)
    if not item:
        return JSONResponse(
            status_code=404,
            content={
                "request_id": request_id,
                "error": "not_found",
                "detail": f"History item {item_id} not found",
            },
        )

    return {
        "request_id": request_id,
        "item": item.to_dict_with_raw(),
    }


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
