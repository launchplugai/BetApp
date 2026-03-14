"""
Dashboard API - Slice 2A
Live endpoints for dashboard/protocol features.

All endpoints gated behind FEATURE_DASHBOARD_COMMAND_CENTER env var (default: false).
"""

import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from typing import List

from app.build_info import get_short_commit_sha

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

    version = get_short_commit_sha()

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
    Protocol feed endpoint (Slice 2B).
    Returns latest protocol activity from database.
    Shows user's recent protocols with latest snapshot data.
    """
    require_dashboard()
    
    # Import protocol models and DB session
    from app.models import get_session
    from app.protocol.models import Protocol
    from sqlalchemy import desc
    
    db = get_session()
    try:
        # Fetch latest 10 protocols (most recent first)
        protocols = db.query(Protocol).order_by(desc(Protocol.updated_at)).limit(10).all()
        
        items = []
        for protocol in protocols:
            # Get latest snapshot if available
            latest_snapshot = None
            if protocol.snapshots:
                latest_snapshot = protocol.snapshots[-1]  # Last snapshot
            
            items.append({
                "protocol_id": protocol.id,
                "name": protocol.name or f"Protocol {protocol.id[:8]}",
                "created_at": protocol.created_at.isoformat() if protocol.created_at else None,
                "updated_at": protocol.updated_at.isoformat() if protocol.updated_at else None,
                "snapshot_count": len(protocol.snapshots) if protocol.snapshots else 0,
                "latest_confidence": latest_snapshot.confidence_score if latest_snapshot and hasattr(latest_snapshot, 'confidence_score') else None,
                "latest_conclusion": latest_snapshot.conclusion if latest_snapshot and hasattr(latest_snapshot, 'conclusion') else "No analysis yet"
            })
        
        return {"items": items}
    finally:
        db.close()


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
