"""
Admin API Router

Configuration management and reporting endpoints.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from app.admin.config import get_config, update_config, ConfigManager
from app.admin.reports import generate_super_report, export_report_json
from app.admin.notifications import (
    get_notification_stats,
    get_recent_notifications,
    get_dashboard_summary,
    toggle_kill_switch,
    get_kill_switch,
    get_user_notification_summary
)
from app.models import get_session

router = APIRouter(prefix="/api/admin", tags=["admin"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ConfigUpdateRequest(BaseModel):
    """Configuration update request."""
    updates: Dict[str, Any]


class ConfigResponse(BaseModel):
    """Configuration response."""
    version: str
    last_updated: str
    nba: Dict
    heuristics: Dict
    features: Dict


# =============================================================================
# Configuration Endpoints
# =============================================================================

@router.get("/config", response_model=ConfigResponse)
async def get_configuration():
    """Get current configuration."""
    config = get_config()
    
    from dataclasses import asdict
    return ConfigResponse(**asdict(config))


@router.post("/config/update")
async def update_configuration(request: ConfigUpdateRequest):
    """
    Update configuration.
    
    Example:
        POST /api/admin/config/update
        {
            "updates": {
                "nba": {
                    "rest_coefficient": -5.0
                },
                "features": {
                    "advanced_stats": true
                }
            }
        }
    """
    success = update_config(request.updates)
    
    if not success:
        raise HTTPException(status_code=400, detail="Config update failed")
    
    return {"success": True, "message": "Configuration updated"}


@router.post("/config/reset")
async def reset_configuration():
    """Reset configuration to defaults."""
    ConfigManager().reset_to_defaults()
    return {"success": True, "message": "Configuration reset to defaults"}


# =============================================================================
# Reporting Endpoints
# =============================================================================

@router.get("/report/super")
async def get_super_report():
    """
    Get comprehensive platform report.
    
    Returns health checks, performance metrics, NBA stats, API usage.
    """
    report = generate_super_report()
    return export_report_json(report)


@router.get("/report/health")
async def get_health_check():
    """Quick health check of all components."""
    report = generate_super_report()
    
    return {
        "status": "healthy" if all(
            h.status == "healthy" for h in report.health
        ) else "degraded",
        "components": [
            {
                "name": h.component,
                "status": h.status,
                "message": h.message
            }
            for h in report.health
        ]
    }


@router.get("/report/nba")
async def get_nba_report():
    """Get NBA analytics-specific report."""
    report = generate_super_report()
    
    from dataclasses import asdict
    return asdict(report.nba)


@router.get("/report/performance")
async def get_performance_report():
    """Get performance metrics report."""
    report = generate_super_report()
    
    from dataclasses import asdict
    return asdict(report.performance)


# =============================================================================
# API Management Endpoints
# =============================================================================

@router.get("/api/endpoints")
async def list_api_endpoints():
    """List all available API endpoints with metadata."""
    return {
        "nba_analytics": [
            {
                "path": "/api/nba/teams",
                "method": "GET",
                "description": "List all NBA teams",
                "cache_ttl": "24h",
                "rate_limit": "100/min"
            },
            {
                "path": "/api/nba/games/today",
                "method": "GET",
                "description": "Today's NBA games",
                "cache_ttl": "5min",
                "rate_limit": "100/min"
            },
            {
                "path": "/api/nba/edge/{team_a}/{team_b}",
                "method": "GET",
                "description": "Comprehensive edge analysis",
                "cache_ttl": "5min",
                "rate_limit": "50/min"
            },
            {
                "path": "/api/nba/rest/{team}",
                "method": "GET",
                "description": "Rest advantage analysis",
                "cache_ttl": "5min",
                "rate_limit": "100/min"
            },
            {
                "path": "/api/nba/tank/{team}",
                "method": "GET",
                "description": "Tank detection",
                "cache_ttl": "5min",
                "rate_limit": "100/min"
            },
            {
                "path": "/api/nba/injuries/{team}",
                "method": "GET",
                "description": "Injury impact analysis",
                "cache_ttl": "5min",
                "rate_limit": "100/min"
            }
        ],
        "admin": [
            {
                "path": "/api/admin/config",
                "method": "GET",
                "description": "Get configuration",
                "auth": "required"
            },
            {
                "path": "/api/admin/config/update",
                "method": "POST",
                "description": "Update configuration",
                "auth": "required"
            },
            {
                "path": "/api/admin/report/super",
                "method": "GET",
                "description": "Comprehensive report",
                "auth": "required"
            }
        ]
    }


@router.post("/cache/clear")
async def clear_cache():
    """Clear NBA analytics cache."""
    from app.nba.cache import get_cache
    
    cache = get_cache()
    count = cache.clear()
    
    return {
        "success": True,
        "message": f"Cleared {count} cache entries"
    }


@router.post("/cache/clear-expired")
async def clear_expired_cache():
    """Clear only expired cache entries."""
    from app.nba.cache import get_cache
    
    cache = get_cache()
    count = cache.clear_expired()
    
    return {
        "success": True,
        "message": f"Cleared {count} expired entries"
    }


# =============================================================================
# Data Management Endpoints
# =============================================================================

@router.post("/nba/sync-teams")
async def sync_nba_teams():
    """Sync NBA teams from nba_api."""
    from app.nba.database import bootstrap_teams
    
    count = bootstrap_teams()
    
    return {
        "success": True,
        "message": f"Synced {count} teams"
    }


@router.post("/nba/sync-players")
async def sync_nba_players():
    """Sync active NBA players from nba_api."""
    from app.nba.database import bootstrap_players
    
    count = bootstrap_players()
    
    return {
        "success": True,
        "message": f"Synced {count} players"
    }


@router.post("/nba/scrape-injuries")
async def scrape_injuries():
    """Run ESPN injury scraper."""
    from app.nba.scrapers import run_injury_scraper
    from app.nba.database import get_db_session
    
    db = get_db_session()
    try:
        count = run_injury_scraper(db)
        return {
            "success": True,
            "message": f"Scraped {count} injuries"
        }
    finally:
        db.close()


@router.post("/nba/run-etl")
async def run_daily_etl():
    """
    Run daily ETL manually.
    
    Fetches yesterday's games and box scores.
    """
    from app.nba.ingestion import run_daily_etl
    from app.nba.database import get_db_session
    from datetime import date, timedelta
    
    db = get_db_session()
    try:
        yesterday = date.today() - timedelta(days=1)
        run_daily_etl(db, yesterday)
        
        return {
            "success": True,
            "message": f"ETL completed for {yesterday}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# =============================================================================
# Notification Admin Endpoints
# =============================================================================

class KillSwitchRequest(BaseModel):
    """Kill switch toggle request."""
    enabled: bool
    reason: str
    triggered_by: str


class KillSwitchResponse(BaseModel):
    """Kill switch status response."""
    enabled: bool
    reason: Optional[str]
    triggered_at: Optional[str]
    triggered_by: Optional[str]


class NotificationStatusUpdateRequest(BaseModel):
    """Notification status update request."""
    status: str  # pending, sent, delivered, read, dismissed, failed
    error_message: Optional[str] = None


@router.get("/notifications/dashboard")
async def get_notifications_dashboard(db=Depends(get_session)):
    """
    Get complete notification dashboard summary.
    
    Returns stats, trends, opportunity metrics, and kill switch status.
    """
    try:
        summary = get_dashboard_summary(db)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/stats")
async def get_notifications_stats(
    period_hours: int = Query(default=24, ge=1, le=168),
    user_id: Optional[str] = None,
    db=Depends(get_session)
):
    """
    Get notification statistics.
    
    Args:
        period_hours: Time period to analyze (1-168 hours, default 24)
        user_id: Optional user ID to filter by
    
    Returns:
        Notification statistics including delivery rate, read rate, opt-out rate
    """
    try:
        stats = get_notification_stats(db, period_hours=period_hours, user_id=user_id)
        return stats.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/recent")
async def get_recent_notifications_list(
    limit: int = Query(default=50, ge=1, le=200),
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    db=Depends(get_session)
):
    """
    Get recent notifications with optional filtering.
    
    Args:
        limit: Maximum number of results (1-200, default 50)
        status: Filter by status (pending, sent, delivered, read, dismissed, failed)
        user_id: Filter by user ID
    
    Returns:
        List of recent notification events
    """
    try:
        notifications = get_recent_notifications(
            db, limit=limit, status=status, user_id=user_id
        )
        return {
            "notifications": notifications,
            "count": len(notifications),
            "filters": {
                "status": status,
                "user_id": user_id
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/kill-switch", response_model=KillSwitchResponse)
async def post_kill_switch(
    request: KillSwitchRequest,
    db=Depends(get_session)
):
    """
    Emergency kill switch for notifications.
    
    When enabled, all notification sending is immediately stopped.
    Use for emergencies like spam detection, system issues, or compliance.
    
    Args:
        enabled: True to engage kill switch, False to disengage
        reason: Reason for the action (required)
        triggered_by: Admin user ID taking the action
    
    Returns:
        Current kill switch status
    """
    try:
        status = toggle_kill_switch(
            db,
            enabled=request.enabled,
            reason=request.reason,
            triggered_by=request.triggered_by
        )
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/kill-switch", response_model=KillSwitchResponse)
async def get_kill_switch_status():
    """
    Get current kill switch status.
    
    Returns whether the notification kill switch is engaged.
    """
    return get_kill_switch().get_status()


@router.get("/notifications/trends")
async def get_notification_trends_endpoint(
    period_hours: int = Query(default=24, ge=1, le=168),
    db=Depends(get_session)
):
    """
    Get notification trends over time.
    
    Args:
        period_hours: Time period to analyze (1-168 hours, default 24)
    
    Returns:
        Hourly breakdown of sent, delivered, and failed notifications
    """
    try:
        from app.admin.notifications import get_notification_trends
        trends = get_notification_trends(db, period_hours=period_hours)
        return {
            "trends": [t.to_dict() for t in trends],
            "period_hours": period_hours
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/opportunities")
async def get_opportunity_stats_endpoint(
    period_hours: int = Query(default=24, ge=1, le=168),
    db=Depends(get_session)
):
    """
    Get eligible opportunity statistics.
    
    Args:
        period_hours: Time period to analyze (1-168 hours, default 24)
    
    Returns:
        Opportunity detection, notification, and conversion statistics
    """
    try:
        from app.admin.notifications import get_opportunity_stats
        stats = get_opportunity_stats(db, period_hours=period_hours)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/users/{user_id}")
async def get_user_notifications(
    user_id: str,
    db=Depends(get_session)
):
    """
    Get notification summary for a specific user.
    
    Args:
        user_id: User ID to query
    
    Returns:
        User notification stats, recent notifications, and preferences
    """
    try:
        summary = get_user_notification_summary(db, user_id=user_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications/{notification_id}/status")
async def update_notification_status(
    notification_id: str,
    request: NotificationStatusUpdateRequest,
    db=Depends(get_session)
):
    """
    Manually update notification status (admin override).
    
    Args:
        notification_id: Notification event ID
        request: Status update with new status and optional error message
    
    Returns:
        Updated notification
    """
    try:
        from app.admin.notifications import mark_notification_status
        notification = mark_notification_status(
            db,
            notification_id=notification_id,
            status=request.status,
            error_message=request.error_message
        )
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        return notification
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
