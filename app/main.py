"""DNA Matrix API - FastAPI application entrypoint."""
import logging
import os
from datetime import datetime, timezone

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import load_config, log_config_snapshot
from app.correlation import CorrelationIdMiddleware
from app.routers import leading_light
from app.routers import panel
from app.routers import web
from app.routers import history
from app.routers import v1_ui
from app.routers import debug
from app.routers import metrics
from app.routers import mock_api
from app.routers import protocols
from app.routers import auth
from app.voice.router import router as voice_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Load and validate configuration at startup
_config = load_config()
log_config_snapshot(_config)

# Export config value for middleware (validated)
MAX_REQUEST_SIZE_BYTES = _config.max_request_size_bytes


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding size limit to prevent payload bombs."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_SIZE_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request entity too large"},
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-store"
        return response


# Capture service start time for uptime reporting
_SERVICE_START_TIME = datetime.now(timezone.utc)

app = FastAPI(
    title="DNA Matrix",
    description="Semantic identity management system",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware stack (order matters - added in reverse execution order)
# 1. CorrelationId: First to run, wraps everything, adds X-Request-Id to responses
# 2. SecurityHeaders: Adds security headers to responses
# 3. RequestSizeLimit: Rejects oversized requests early
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

# Mount static files for extracted web assets (CSS, JS)
_STATIC_DIR = Path(__file__).resolve().parent / "web_assets" / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Include routers
# Web router first (handles / and /app)
app.include_router(web.router)
app.include_router(mock_api.router)
app.include_router(protocols.router)
app.include_router(auth.router)
app.include_router(leading_light.router)
app.include_router(voice_router)
app.include_router(panel.router)
app.include_router(history.router)
app.include_router(v1_ui.router)
app.include_router(metrics.router)


# S18: Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables."""
    from app.models import init_db
    init_db()
    print("✅ Database initialized")


@app.get("/health")
async def health():
    """Health check for Railway with service observability."""
    return {
        "status": "healthy",
        "service": _config.service_name,
        "version": _config.service_version,
        "environment": _config.environment,
        "git_sha": _config.git_sha,
        "build_time_utc": _config.build_time_utc,
        "started_at": _SERVICE_START_TIME.isoformat(),
    }


@app.get("/build")
async def build_info():
    """
    Build info endpoint (Ticket 10).

    Returns deployment visibility information.
    """
    from dataclasses import asdict
    from app.build_info import get_build_info
    return asdict(get_build_info())


@app.get("/debug/contracts")
async def debug_contracts():
    """
    Debug endpoint for contract verification (Ticket 17).

    Returns current contract versions, feature flags, and build info.
    BEST-tier or internal use only.

    Contracts referenced:
    - docs/contracts/SYSTEM_CONTRACT_SDS.md
    - docs/contracts/SCH_SDK_CONTRACT.md
    - docs/contracts/DNA_PRIMITIVES_CONTRACT.md
    """
    # Contract versions (from docs)
    contract_versions = {
        "SYSTEM_CONTRACT_SDS": "1.0.0",
        "SCH_SDK_CONTRACT": "1.0.0",
        "DNA_PRIMITIVES_CONTRACT": "1.0.0",
        "MAP_SHERLOCK_TO_DNA": "1.0.0",
    }

    # Sherlock module version
    try:
        from sherlock import __version__ as sherlock_version
    except ImportError:
        sherlock_version = "not_installed"

    return {
        "contracts": contract_versions,
        "sherlock_version": sherlock_version,
        "flags": {
            "sherlock_enabled": _config.sherlock_enabled,
            "dna_recording_enabled": _config.dna_recording_enabled,
            "leading_light_enabled": _config.leading_light_enabled,
            "voice_enabled": _config.voice_enabled,
        },
        "build": {
            "git_sha": _config.git_sha,
            "build_time_utc": _config.build_time_utc,
            "environment": _config.environment,
        },
        "service": {
            "name": _config.service_name,
            "version": _config.service_version,
            "started_at": _SERVICE_START_TIME.isoformat(),
        },
    }

# Include debug router for /debug/sherlock-dna/* endpoints
# Note: inline /debug/contracts above takes precedence over debug.router version
app.include_router(debug.router)
