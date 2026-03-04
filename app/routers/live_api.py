"""
Live API routes — serves real data when available, falls back to mock.

This router replaces /api/mock for the frontend while keeping
backward compatibility. Endpoints mirror the mock API structure.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.providers.odds_api import (
    OddsAPIProvider,
    get_team_logo,
    get_league_logo,
    LEAGUE_LOGOS,
)
from app.mock_data import (
    MOCK_GAMES, MOCK_ODDS, MOCK_USER, SPORTS,
    MOCK_PROTOCOLS, MOCK_PROTOCOL_CONTEXTS,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/live", tags=["live"])

# Singleton provider
_odds_provider = None


def _get_provider() -> OddsAPIProvider:
    global _odds_provider
    if _odds_provider is None:
        _odds_provider = OddsAPIProvider()
    return _odds_provider


# Simple in-memory cache to avoid burning API quota
_cache = {}
_cache_ttl = 300  # 5 minutes


def _cache_key(sport: str) -> str:
    return f"games_{sport}"


def _get_cached(key: str):
    import time
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < _cache_ttl:
        return entry["data"]
    return None


def _set_cached(key: str, data):
    import time
    _cache[key] = {"data": data, "ts": time.time()}


# ─── Sports ───────────────────────────────────────────────────────

@router.get("/sports")
async def get_sports():
    """Get all sports with league logos."""
    sports = []
    for s in SPORTS:
        sport = dict(s)
        sport["active"] = True  # Enable all sports
        sport["logo"] = get_league_logo(s["id"])
        sports.append(sport)
    return {"sports": sports}


# ─── Games ────────────────────────────────────────────────────────

@router.get("/games")
async def get_games(sport: Optional[str] = None):
    """Get games — live from Odds API if configured, else mock."""
    provider = _get_provider()
    target_sport = sport or "nba"

    # Try live data first
    if provider.is_configured:
        cache_key = _cache_key(target_sport)
        cached = _get_cached(cache_key)
        if cached:
            games = cached
        else:
            raw = await provider.get_upcoming_games(sport=target_sport)
            if raw:
                games = provider.normalize_games(raw, target_sport)
                _set_cached(cache_key, games)
            else:
                games = _get_mock_games_with_logos(target_sport)
    else:
        games = _get_mock_games_with_logos(target_sport)

    return {"games": games, "source": "live" if provider.is_configured else "mock"}


@router.get("/games/{game_id}")
async def get_game(game_id: str):
    """Get single game details."""
    for sport_games in MOCK_GAMES.values():
        for game in sport_games:
            if game["id"] == game_id:
                enriched = _enrich_mock_game(game)
                return enriched
    raise HTTPException(status_code=404, detail="Game not found")


# ─── Protocols (game cards for browse) ────────────────────────────

@router.get("/protocols/available")
async def get_available_protocols(league: Optional[str] = None):
    """Get protocols with team logos and live data when available."""
    provider = _get_provider()
    target_league = (league or "nba").lower()

    # Try live data
    if provider.is_configured:
        cache_key = f"protocols_{target_league}"
        cached = _get_cached(cache_key)
        if cached:
            return {"protocols": cached, "count": len(cached), "league": league, "source": "live"}

        raw = await provider.get_upcoming_games(sport=target_league)
        if raw:
            protocols = _live_games_to_protocols(raw, target_league, provider)
            _set_cached(cache_key, protocols)
            return {"protocols": protocols, "count": len(protocols), "league": league, "source": "live"}

    # Fallback to mock
    protocols = []
    if target_league in MOCK_PROTOCOLS:
        protocols = [_enrich_protocol(p) for p in MOCK_PROTOCOLS[target_league]]
    else:
        for lp in MOCK_PROTOCOLS.values():
            protocols.extend([_enrich_protocol(p) for p in lp])

    return {"protocols": protocols, "count": len(protocols), "league": league, "source": "mock"}


@router.get("/protocols/{protocol_id}")
async def get_protocol(protocol_id: str):
    """Get specific protocol."""
    for league_protocols in MOCK_PROTOCOLS.values():
        for protocol in league_protocols:
            if protocol["protocolId"] == protocol_id:
                return _enrich_protocol(protocol)
    raise HTTPException(status_code=404, detail="Protocol not found")


# ─── Odds ─────────────────────────────────────────────────────────

@router.get("/odds/{game_id}")
async def get_odds(game_id: str):
    """Get odds for a game."""
    if game_id in MOCK_ODDS:
        return {"game_id": game_id, "odds": MOCK_ODDS[game_id]}
    raise HTTPException(status_code=404, detail="Odds not found")


@router.get("/markets/{game_id}")
async def get_markets(game_id: str):
    """Get betting markets for a game."""
    if game_id in MOCK_ODDS:
        return {"game_id": game_id, "markets": MOCK_ODDS[game_id]}
    raise HTTPException(status_code=404, detail="Markets not found")


# ─── User ─────────────────────────────────────────────────────────

@router.get("/user/me")
async def get_current_user():
    return MOCK_USER


@router.get("/user/stats")
async def get_user_stats():
    return {
        "win_rate": MOCK_USER["win_rate"],
        "total_bets": MOCK_USER["total_bets"],
        "balance": MOCK_USER["balance"],
    }


# ─── Helpers ──────────────────────────────────────────────────────

def _get_mock_games_with_logos(sport: str) -> list:
    """Add logos to mock game data."""
    games = MOCK_GAMES.get(sport, [])
    return [_enrich_mock_game(g) for g in games]


def _enrich_mock_game(game: dict) -> dict:
    """Add logo URLs to a mock game."""
    g = dict(game)
    sport = g.get("sport", "nba")
    if "home_team" in g and isinstance(g["home_team"], dict):
        g["home_team"] = dict(g["home_team"])
        g["home_team"]["logo"] = get_team_logo(g["home_team"]["name"], sport)
    if "away_team" in g and isinstance(g["away_team"], dict):
        g["away_team"] = dict(g["away_team"])
        g["away_team"]["logo"] = get_team_logo(g["away_team"]["name"], sport)
    g["source"] = "mock"
    return g


def _enrich_protocol(protocol: dict) -> dict:
    """Add logos to a mock protocol."""
    p = dict(protocol)
    league = p.get("league", "NBA").lower()
    teams = p.get("teams", [])

    p["homeLogo"] = get_team_logo(teams[0], league) if len(teams) > 0 else ""
    p["awayLogo"] = get_team_logo(teams[1], league) if len(teams) > 1 else ""
    p["leagueLogo"] = get_league_logo(league)
    return p


def _live_games_to_protocols(raw_games: list, sport: str, provider: OddsAPIProvider) -> list:
    """Convert Odds API games to protocol format for the browse page."""
    import uuid
    protocols = []
    games = provider.normalize_games(raw_games, sport)

    for i, game in enumerate(games):
        home = game["home_team"]["name"]
        away = game["away_team"]["name"]

        protocol = {
            "protocolId": f"live_{game['id'][:8]}",
            "league": sport.upper(),
            "gameId": game["id"],
            "teams": [home, away],
            "status": game["status"].upper(),
            "clock": None,
            "score": None,
            "marketsAvailable": list(game.get("odds", {}).keys()),
            "featured": i == 0,
            "aiInsight": None,
            "homeLogo": game["home_team"].get("logo", ""),
            "awayLogo": game["away_team"].get("logo", ""),
            "leagueLogo": get_league_logo(sport),
            "odds": game.get("odds", {}),
            "startTime": game.get("start_time", ""),
            "source": "live",
        }

        if game.get("home_score") is not None:
            protocol["score"] = {
                "home": game["home_score"],
                "away": game["away_score"],
            }

        protocols.append(protocol)

    return protocols
