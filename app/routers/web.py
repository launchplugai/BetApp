"""
Web UI router - Serves the canonical DNA Bet Engine UI.

S6-REFACTOR: Split into template + static files for token efficiency.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.config import load_config
from app.airlock import airlock_ingest
from app.rate_limiter import get_client_ip, get_rate_limiter
from app.correlation import get_request_id


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
# Router Setup
# =============================================================================

router = APIRouter(tags=["web"])

# Template setup
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Get git SHA for version display
config = load_config()
git_sha = config.git_sha[:8] if config.git_sha else "dev"

# Rate limiter
rate_limiter = get_rate_limiter()


# =============================================================================
# Routes
# =============================================================================

@router.get("/", response_class=RedirectResponse)
async def redirect_root():
    """Redirect / to /app"""
    return RedirectResponse(url="/app")


@router.get("/ui2", response_class=RedirectResponse)
async def redirect_ui2():
    """Redirect /ui2 to /app"""
    return RedirectResponse(url="/app")


@router.get("/app", response_class=HTMLResponse)
async def canonical_app(request: Request):
    """
    Canonical UI - Single source of truth for all UI interactions.

    S6-REFACTOR: Now serves Jinja2 template with external CSS/JS.
    """
    return templates.TemplateResponse(
        request=request,
        name="app/index.html",
        context={"git_sha": git_sha}
    )


@router.post("/app/evaluate")
async def evaluate_proxy(request: WebEvaluateRequest, raw_request: Request):
    """
    Server-side proxy for evaluation requests.

    Rate limited: 10 requests/minute per IP.
    All input passes through Airlock for validation.
    """
    from app.pipeline import run_evaluation

    start_time = time.perf_counter()
    request_id = get_request_id(raw_request) or "unknown"
    client_ip = get_client_ip(raw_request)

    # Rate limiting
    allowed, retry_after = rate_limiter.check(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Retry after {retry_after:.1f} seconds")

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
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Input validation failed: {str(e)}")

    # Run evaluation
    result = run_evaluation(normalized)

    elapsed = time.perf_counter() - start_time
    
    # Convert to dict and add metadata
    from dataclasses import asdict
    result_dict = asdict(result)
    result_dict["_meta"] = {"elapsed_ms": round(elapsed * 1000, 2)}

    return result_dict
