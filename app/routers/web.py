"""
Web UI router - Serves the canonical BetApp UI.

S6-REFACTOR: Split into template + static files for token efficiency.
"""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import load_config
from app.airlock import airlock_ingest, AirlockError, airlock_shape_evaluate_response
from app.rate_limiter import get_client_ip, get_rate_limiter
from app.schemas.frontend_contracts import WebEvaluateRequestSchema, WebEvaluateResponseSchema

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

@router.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Serve landing page at root"""
    return templates.TemplateResponse(request, "screens/landing.html")


@router.get("/ui2", response_class=RedirectResponse)
async def redirect_ui2():
    """Redirect /ui2 to /app"""
    return RedirectResponse(url="/app")


@router.get("/app", response_class=HTMLResponse)
async def canonical_app(request: Request, screen: str = "dashboard"):
    """
    S-PROT-4B: Dashboard-first routing - dashboard is primary surface.
    Navigation priority: Dashboard → Protocols → Builder
    
    Core Design Rule: Dashboard = orchestration surface
    Builder = execution tool (secondary access)
    """
    from fastapi.responses import HTMLResponse
    from pathlib import Path
    
    screens = {
        "landing": "screens/landing.html",
        "dashboard": "screens/dashboard.html",
        "browse": "screens/browse.html",
        "builder": "screens/builder.html",
        "auth": "screens/auth.html",
        "history": "screens/history.html",
        "protocols": "screens/protocol.html",
        "protocol": "screens/protocol.html"
    }
    
    template_name = screens.get(screen, "screens/dashboard.html")
    template_path = Path(__file__).parent.parent / "templates" / template_name
    
    if not template_path.exists():
        return HTMLResponse(content="<h1>Screen not found</h1>", status_code=404)
    
    return HTMLResponse(content=template_path.read_text())


@router.post(
    "/app/evaluate",
    response_model=WebEvaluateResponseSchema,
    summary="Evaluate a bet for the frontend app",
)
async def evaluate_proxy(request: WebEvaluateRequestSchema, raw_request: Request):
    """
    Server-side proxy for evaluation requests.

    Rate limited: 10 requests/minute per IP.
    All input passes through Airlock for validation.
    """
    from app.pipeline import run_evaluation

    start_time = time.perf_counter()
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
    except AirlockError as e:
        # Return structured error with code for tests
        return JSONResponse(
            status_code=400,
            content={"error": str(e), "code": e.code, "detail": str(e)}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Input validation failed: {str(e)}")

    # Run evaluation
    try:
        result = run_evaluation(normalized)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": f"INTERNAL_ERROR: {exc}"},
        )

    elapsed = time.perf_counter() - start_time
    
    return airlock_shape_evaluate_response(
        result=result,
        normalized=normalized,
        elapsed_ms=elapsed * 1000,
    )

# S16: Legacy route redirects
@router.get("/new")
async def redirect_new(screen: str = "dashboard"):
    """Redirect old /new routes to /app"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/app?screen={screen}")


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Admin control panel."""
    from pathlib import Path
    template_path = Path(__file__).parent.parent / "templates" / "admin" / "dashboard.html"
    return HTMLResponse(content=template_path.read_text())
