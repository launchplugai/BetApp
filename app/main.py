"""DNA Matrix API - FastAPI application entrypoint."""
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.routers import leading_light
from app.routers import panel
from app.voice.router import router as voice_router

# Security configuration
MAX_REQUEST_SIZE_BYTES = int(os.environ.get("MAX_REQUEST_SIZE_BYTES", 1_048_576))  # 1MB default


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
_SERVICE_VERSION = "0.1.0"

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

# Security middleware (order matters: size limit first, then headers on response)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)

# Include routers
app.include_router(leading_light.router)
app.include_router(voice_router)
app.include_router(panel.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "dna-matrix"}


@app.get("/health")
async def health():
    """Health check for Railway with service observability."""
    return {
        "status": "healthy",
        "service": "dna-matrix",
        "version": _SERVICE_VERSION,
        "environment": os.environ.get("RAILWAY_ENVIRONMENT", "development"),
        "started_at": _SERVICE_START_TIME.isoformat(),
    }
