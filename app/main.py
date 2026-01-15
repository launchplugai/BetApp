"""DNA Matrix API - FastAPI application entrypoint."""
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import leading_light
from app.routers import panel
from app.voice.router import router as voice_router

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
