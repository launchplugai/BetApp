"""DNA Matrix API - FastAPI application entrypoint."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import leading_light
from app.voice.router import router as voice_router


# =============================================================================
# Build Identity (for deployment verification)
# =============================================================================

def _get_build_info() -> dict:
    """Get build/deployment identity info."""
    return {
        "commit": os.environ.get("RAILWAY_GIT_COMMIT_SHA", os.environ.get("GIT_COMMIT", "unknown"))[:7]
            if os.environ.get("RAILWAY_GIT_COMMIT_SHA") or os.environ.get("GIT_COMMIT")
            else "unknown",
        "branch": os.environ.get("RAILWAY_GIT_BRANCH", os.environ.get("GIT_BRANCH", "unknown")),
        "deploy_id": os.environ.get("RAILWAY_DEPLOYMENT_ID", "local"),
    }

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


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "dna-matrix"}


@app.get("/health")
async def health():
    """Health check for Railway with build identity."""
    return {
        "status": "healthy",
        "service": "dna-matrix",
        "version": _get_build_info(),
    }
