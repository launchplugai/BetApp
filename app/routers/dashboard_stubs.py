"""
Dashboard API Stubs - Slice 1
Minimal endpoints to support dashboard UI without pulling in full S-PROT-4 systems.

All endpoints gated behind FEATURE_DASHBOARD_COMMAND_CENTER env var (default: false).
"""

import os
from fastapi import APIRouter, HTTPException
from typing import List

router = APIRouter(prefix="/api", tags=["dashboard-stubs"])

# Feature flag: dashboard command center (default OFF)
DASHBOARD_ENABLED = os.getenv("FEATURE_DASHBOARD_COMMAND_CENTER", "false").lower() == "true"


def require_dashboard():
    """Guard: raise 404 if dashboard feature is disabled."""
    if not DASHBOARD_ENABLED:
        raise HTTPException(status_code=404, detail="Dashboard feature not enabled")


@router.get("/edge-feed")
async def get_edge_feed():
    """
    Stub: Edge feed endpoint.
    Returns empty list until edge_feed.py is integrated (Slice 2).
    """
    require_dashboard()
    return {
        "edges": [],
        "last_updated": None
    }


@router.get("/risk-profile")
async def get_risk_profile():
    """
    Stub: Risk profile endpoint.
    Returns minimal structure until risk_profile.py is integrated (Slice 2).
    """
    require_dashboard()
    return {
        "tier": "GOOD",
        "features_enabled": [],
        "risk_tolerance": "medium"
    }


@router.get("/system/health")
async def get_system_health():
    """
    Stub: System health endpoint.
    Returns basic status until system_health.py is integrated (Slice 2).
    """
    require_dashboard()
    return {
        "status": "healthy",
        "uptime": "unknown",
        "services": []
    }
