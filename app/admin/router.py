"""
Admin API Router

Configuration management and reporting endpoints.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.admin.config import get_config, update_config, ConfigManager
from app.admin.reports import generate_super_report, export_report_json

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
