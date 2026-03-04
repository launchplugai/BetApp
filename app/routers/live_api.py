"""
Live API enrichment routes — adds team logos and league logos to game data.

Complements the existing /api/sports, /api/games, /api/odds endpoints
by providing logo URLs for the frontend.
"""

import logging
from typing import Optional

from fastapi import APIRouter

from app.providers.team_logos import get_team_logo, get_league_logo, LEAGUE_LOGOS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/live", tags=["live-enrichment"])


@router.get("/logos/team")
async def get_team_logo_url(name: str, sport: str = "nba"):
    """Get logo URL for a team."""
    logo = get_team_logo(name, sport)
    return {"team": name, "sport": sport, "logo": logo}


@router.get("/logos/league")
async def get_league_logo_url(sport: str):
    """Get logo URL for a league."""
    logo = get_league_logo(sport)
    return {"sport": sport, "logo": logo}


@router.get("/logos/all-leagues")
async def get_all_league_logos():
    """Get all league logos for the sport selection grid."""
    return {"logos": LEAGUE_LOGOS}
