"""
Dashboard API - Slice 2A
Live endpoints for dashboard/protocol features.

All endpoints gated behind FEATURE_DASHBOARD_COMMAND_CENTER env var (default: false).
"""

import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from typing import List

router = APIRouter(prefix="/api", tags=["dashboard"])

# Feature flag: dashboard command center (default OFF)
DASHBOARD_ENABLED = os.getenv("FEATURE_DASHBOARD_COMMAND_CENTER", "false").lower() == "true"


def require_dashboard():
    """Guard: raise 404 if dashboard feature is disabled."""
    if not DASHBOARD_ENABLED:
        raise HTTPException(status_code=404, detail="Dashboard feature not enabled")


@router.get("/features")
async def get_feature_flags():
    """
    Feature flags endpoint - returns enabled features.
    Public endpoint (not gated) so UI can check what's available.
    """
    return {
        "dashboard_enabled": DASHBOARD_ENABLED,
        "protocol_feed_enabled": DASHBOARD_ENABLED  # Same flag for now
    }


@router.get("/system/health")
async def get_system_health():
    """
    System health endpoint (Slice 2A).
    Returns basic canary status - version, uptime, timestamp.
    Read-only, no dependencies on other systems.
    """
    require_dashboard()
    
    # Get current git commit (if available)
    import subprocess
    try:
        version = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd="/var/lib/openbot/workdir/target",
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        version = "unknown"
    
    # Calculate uptime (using process start time approximation)
    from app.main import _SERVICE_START_TIME
    uptime_sec = int((datetime.now(timezone.utc) - _SERVICE_START_TIME).total_seconds())
    
    return {
        "status": "ok",
        "version": version,
        "uptimeSec": uptime_sec,
        "time": datetime.now(timezone.utc).isoformat()
    }


@router.get("/protocol/feed")
async def get_protocol_feed():
    """
    Protocol feed endpoint (Slice 2A).
    Returns latest protocol activity - minimal live version.
    Empty array acceptable for now - UI just needs stable contract.
    """
    require_dashboard()
    
    # Return empty feed for Slice 2A (persistence integration in Slice 2B)
    return {
        "items": []
    }


@router.get("/edge-feed")
async def get_edge_feed():
    """
    Edge feed stub (Slice 2+).
    Returns empty list until edge_feed.py is integrated.
    """
    require_dashboard()
    return {
        "edges": [],
        "last_updated": None
    }


@router.get("/risk-profile")
async def get_risk_profile():
    """
    Risk profile stub (Slice 2+).
    Returns minimal structure until risk_profile.py is integrated.
    """
    require_dashboard()
    return {
        "tier": "GOOD",
        "features_enabled": [],
        "risk_tolerance": "medium"
    }
