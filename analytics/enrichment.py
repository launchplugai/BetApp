"""
Advanced statistical enrichment for games
Transforms raw odds data into context-rich GameContext objects
"""

import logging
from datetime import datetime
from typing import Optional, Literal

import httpx

from .schemas import GameContext, TeamContext, EnrichmentResult
from .cache import get_cached_stats, set_cached_stats
from .heuristics import HeuristicEngine

_heuristic_engine = HeuristicEngine()

logger = logging.getLogger(__name__)

# Current NBA season (2025-26 as of Feb 2026)
_NBA_SEASON = "2025-26"

# Required headers for stats.nba.com (blocks requests without them)
_NBA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nba.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "x-nba-stats-token": "true",
    "x-nba-stats-origin": "stats",
    "Connection": "keep-alive",
}

# NFL team full name -> ESPN team abbreviation slug
_NFL_ESPN_SLUGS: dict[str, str] = {
    "Arizona Cardinals": "ari",
    "Atlanta Falcons": "atl",
    "Baltimore Ravens": "bal",
    "Buffalo Bills": "buf",
    "Carolina Panthers": "car",
    "Chicago Bears": "chi",
    "Cincinnati Bengals": "cin",
    "Cleveland Browns": "cle",
    "Dallas Cowboys": "dal",
    "Denver Broncos": "den",
    "Detroit Lions": "det",
    "Green Bay Packers": "gb",
    "Houston Texans": "hou",
    "Indianapolis Colts": "ind",
    "Jacksonville Jaguars": "jax",
    "Kansas City Chiefs": "kc",
    "Las Vegas Raiders": "lv",
    "Los Angeles Chargers": "lac",
    "Los Angeles Rams": "lar",
    "Miami Dolphins": "mia",
    "Minnesota Vikings": "min",
    "New England Patriots": "ne",
    "New Orleans Saints": "no",
    "New York Giants": "nyg",
    "New York Jets": "nyj",
    "Philadelphia Eagles": "phi",
    "Pittsburgh Steelers": "pit",
    "San Francisco 49ers": "sf",
    "Seattle Seahawks": "sea",
    "Tampa Bay Buccaneers": "tb",
    "Tennessee Titans": "ten",
    "Washington Commanders": "wsh",
}


def enrich_game(
    raw_odds_data: dict,
    sport: Literal["nba", "nfl"],
    use_cache: bool = True
) -> EnrichmentResult:
    """
    Main entry point: enrich raw odds data with advanced statistics

    Args:
        raw_odds_data: Raw data from odds API (must include 'id', 'home_team', 'away_team')
        sport: 'nba' or 'nfl'
        use_cache: Whether to use in-memory cache

    Returns:
        EnrichmentResult with GameContext or error details
    """
    try:
        if sport == "nba":
            return enrich_nba_game(raw_odds_data, use_cache)
        elif sport == "nfl":
            return enrich_nfl_game(raw_odds_data, use_cache)
        else:
            return EnrichmentResult(
                success=False,
                error_message=f"Unsupported sport: {sport}",
                raw_data=raw_odds_data,
            )
    except Exception as e:
        logger.error(f"Enrichment failed: {e}")
        return EnrichmentResult(
            success=False,
            error_message=str(e),
            raw_data=raw_odds_data,
        )


def enrich_nba_game(raw_odds_data: dict, use_cache: bool = True) -> EnrichmentResult:
    """
    Enrich NBA game data with advanced statistics from stats.nba.com.

    Fetches via leaguedashteamstats (Advanced measure, no API key required):
      pace, offensive_rating, defensive_rating, net_rating

    Batch-loads all 30 teams in one request and caches for 1 hour.
    Falls back to degraded mode (is_enriched=False) if the source is unreachable.
    """
    try:
        game_id = raw_odds_data.get("id", "unknown")
        home_name = raw_odds_data.get("home_team", "unknown")
        away_name = raw_odds_data.get("away_team", "unknown")
        errors: list[str] = []

        # _fetch_nba_team_stats does a single batch call for all teams and caches
        # the result, so calling it twice hits the cache on the second call.
        home_raw = _fetch_nba_team_stats(home_name, use_cache=use_cache)
        away_raw = _fetch_nba_team_stats(away_name, use_cache=use_cache)

        if home_raw is None:
            errors.append(f"NBA stats unavailable for {home_name}")
        if away_raw is None:
            errors.append(f"NBA stats unavailable for {away_name}")

        home_team = TeamContext(
            team_id=home_name,
            team_name=raw_odds_data.get("home_team_name", home_name),
            stats=home_raw or {},
            pace=home_raw.get("pace") if home_raw else None,
            offensive_rating=home_raw.get("offensive_rating") if home_raw else None,
            defensive_rating=home_raw.get("defensive_rating") if home_raw else None,
            net_rating=home_raw.get("net_rating") if home_raw else None,
        )

        away_team = TeamContext(
            team_id=away_name,
            team_name=raw_odds_data.get("away_team_name", away_name),
            stats=away_raw or {},
            pace=away_raw.get("pace") if away_raw else None,
            offensive_rating=away_raw.get("offensive_rating") if away_raw else None,
            defensive_rating=away_raw.get("defensive_rating") if away_raw else None,
            net_rating=away_raw.get("net_rating") if away_raw else None,
        )

        is_enriched = home_raw is not None or away_raw is not None

        game_context = GameContext(
            game_id=game_id,
            sport="nba",
            home_team=home_team,
            away_team=away_team,
            data_source="api" if is_enriched else "degraded",
            is_enriched=is_enriched,
            enrichment_errors=errors,
        )
        
        # Phase 2: Run heuristic analysis
        heuristics = _heuristic_engine.analyze(game_context)
        game_context.heuristics = [h.dict() for h in heuristics]

        return EnrichmentResult(
            success=True,
            game_context=game_context,
            raw_data=raw_odds_data,
        )

    except Exception as e:
        logger.error(f"NBA enrichment failed: {e}")
        return EnrichmentResult(
            success=False,
            error_message=str(e),
            raw_data=raw_odds_data,
        )


def enrich_nfl_game(raw_odds_data: dict, use_cache: bool = True) -> EnrichmentResult:
    """
    Enrich NFL game data with stats from ESPN's public team statistics API.

    Fetches per team (no API key required):
      plays_per_game, points_per_game, and raw stats dict

    EPA/play and success_rate require play-by-play data and are not populated here.
    Falls back to degraded mode if ESPN is unreachable.
    """
    try:
        game_id = raw_odds_data.get("id", "unknown")
        home_name = raw_odds_data.get("home_team", "unknown")
        away_name = raw_odds_data.get("away_team", "unknown")
        errors: list[str] = []

        home_raw = _fetch_nfl_team_stats(home_name, use_cache=use_cache)
        away_raw = _fetch_nfl_team_stats(away_name, use_cache=use_cache)

        if home_raw is None:
            errors.append(f"NFL stats unavailable for {home_name}")
        if away_raw is None:
            errors.append(f"NFL stats unavailable for {away_name}")

        home_team = TeamContext(
            team_id=home_name,
            team_name=raw_odds_data.get("home_team_name", home_name),
            stats=home_raw.get("raw_stats", {}) if home_raw else {},
            plays_per_game=home_raw.get("plays_per_game") if home_raw else None,
        )

        away_team = TeamContext(
            team_id=away_name,
            team_name=raw_odds_data.get("away_team_name", away_name),
            stats=away_raw.get("raw_stats", {}) if away_raw else {},
            plays_per_game=away_raw.get("plays_per_game") if away_raw else None,
        )

        is_enriched = home_raw is not None or away_raw is not None

        game_context = GameContext(
            game_id=game_id,
            sport="nfl",
            home_team=home_team,
            away_team=away_team,
            data_source="api" if is_enriched else "degraded",
            is_enriched=is_enriched,
            enrichment_errors=errors,
        )

        return EnrichmentResult(
            success=True,
            game_context=game_context,
            raw_data=raw_odds_data,
        )

    except Exception as e:
        logger.error(f"NFL enrichment failed: {e}")
        return EnrichmentResult(
            success=False,
            error_message=str(e),
            raw_data=raw_odds_data,
        )


# =============================================================================
# Private helpers — API integration
# =============================================================================

def _fetch_nba_team_stats(team_name: str, use_cache: bool = True) -> Optional[dict]:
    """
    Batch-fetch all 30 NBA team advanced stats and return the named team's entry.

    Source: stats.nba.com/stats/leaguedashteamstats
    No API key required. Requires specific request headers.

    Caches the full 30-team batch under key ("nba", "_batch", date, "advanced")
    for 1 hour. Second call for same date always hits cache.

    Returns dict with keys: pace, offensive_rating, defensive_rating, net_rating
    Returns None on fetch failure or unrecognised team name.
    """
    today = datetime.utcnow().strftime("%Y-%m-%d")

    if use_cache:
        batch = get_cached_stats("nba", "_batch", today, "advanced")
        if batch is not None:
            return batch.get(team_name)

    url = "https://stats.nba.com/stats/leaguedashteamstats"
    params = {
        "Conference": "",
        "DateFrom": "",
        "DateTo": "",
        "Division": "",
        "GameScope": "",
        "GameSegment": "",
        "Height": "",
        "ISTRound": "",
        "LastNGames": "0",
        "LeagueID": "00",
        "Location": "",
        "MeasureType": "Advanced",
        "Month": "0",
        "OpponentTeamID": "0",
        "Outcome": "",
        "PORound": "0",
        "PaceAdjust": "N",
        "PerMode": "PerGame",
        "Period": "0",
        "PlayerExperience": "",
        "PlayerPosition": "",
        "PlusMinus": "N",
        "Rank": "N",
        "Season": _NBA_SEASON,
        "SeasonSegment": "",
        "SeasonType": "Regular Season",
        "ShotClockRange": "",
        "StarterBench": "",
        "TeamID": "0",
        "TwoWay": "0",
        "VsConference": "",
        "VsDivision": "",
    }

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            response = client.get(url, params=params, headers=_NBA_HEADERS)
            response.raise_for_status()
            data = response.json()

        result_set = data["resultSets"][0]
        col_names: list[str] = result_set["headers"]
        rows: list[list] = result_set["rowSet"]

        col_idx = {col: i for i, col in enumerate(col_names)}

        def _safe_float(row: list, col: str) -> Optional[float]:
            idx = col_idx.get(col)
            if idx is None:
                return None
            val = row[idx]
            if val is None:
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        name_col = col_idx.get("TEAM_NAME")
        if name_col is None:
            logger.warning("NBA stats API response missing TEAM_NAME column")
            return None

        batch: dict[str, dict] = {}
        for row in rows:
            name = row[name_col]
            batch[name] = {
                "pace": _safe_float(row, "PACE"),
                "offensive_rating": _safe_float(row, "OFF_RATING"),
                "defensive_rating": _safe_float(row, "DEF_RATING"),
                "net_rating": _safe_float(row, "NET_RATING"),
            }

        set_cached_stats("nba", "_batch", today, batch, "advanced", ttl_seconds=3600)
        logger.info(f"NBA batch stats loaded: {len(batch)} teams from stats.nba.com")

        return batch.get(team_name)

    except Exception as e:
        logger.warning(f"NBA stats.nba.com fetch failed: {e}")
        return None


def _fetch_nfl_team_stats(team_name: str, use_cache: bool = True) -> Optional[dict]:
    """
    Fetch NFL team season stats from ESPN's public API.

    Source: site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{slug}/statistics
    No API key required.

    Requires team_name to be a full franchise name (e.g. "Kansas City Chiefs").
    Unknown names return None immediately (no request made).

    Returns dict with keys: plays_per_game, points_per_game, raw_stats
    Returns None on fetch failure or unrecognised team name.
    """
    slug = _NFL_ESPN_SLUGS.get(team_name)
    if not slug:
        logger.warning(f"No ESPN slug mapping for NFL team: {team_name!r}")
        return None

    today = datetime.utcnow().strftime("%Y-%m-%d")

    if use_cache:
        cached = get_cached_stats("nfl", slug, today, "espn_stats")
        if cached is not None:
            return cached

    url = (
        f"https://site.api.espn.com/apis/site/v2/sports/football/nfl"
        f"/teams/{slug}/statistics"
    )

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()

        # ESPN returns nested results -> splits -> categories[]
        categories: list = (
            data.get("results", {})
            .get("splits", {})
            .get("categories", [])
        )

        # Flatten all stats into {category_statname: float}
        flat: dict[str, float] = {}
        for cat in categories:
            cat_name = cat.get("name", "")
            for stat in cat.get("stats", []):
                key = f"{cat_name}_{stat.get('name', '')}"
                val = stat.get("value")
                if val is not None:
                    try:
                        flat[key] = float(val)
                    except (TypeError, ValueError):
                        pass

        games = flat.get("general_gamesPlayed") or 17.0
        # Prefer pre-computed totalPlays; fall back to pass attempts + rush attempts
        total_plays = flat.get("general_totalPlays") or (
            (flat.get("passing_passingAttempts") or 0.0)
            + (flat.get("rushing_rushingAttempts") or 0.0)
        )

        result = {
            "plays_per_game": round(total_plays / games, 1) if games else None,
            "points_per_game": flat.get("scoring_pointsPerGame"),
            "raw_stats": flat,
        }

        set_cached_stats("nfl", slug, today, result, "espn_stats", ttl_seconds=3600)
        logger.info(f"NFL ESPN stats loaded: {team_name} ({slug})")

        return result

    except Exception as e:
        logger.warning(f"NFL ESPN fetch failed for {team_name} ({slug}): {e}")
        return None


def _fetch_weather_data(game_id: str, venue: str) -> Optional[dict]:
    """
    Fetch weather data for an NFL game venue.
    Not yet implemented — placeholder for Sprint 3+ context layer.
    """
    logger.info(f"Weather fetch not implemented for {game_id} @ {venue}")
    return None


def _calculate_line_movement(opening: float, current: float) -> float:
    """Calculate line movement delta (current minus opening)."""
    return current - opening if opening and current else 0.0


def _calculate_rest_days(last_game_date: Optional[str]) -> int:
    """Calculate rest days since last game. Returns 99 if unknown."""
    if not last_game_date:
        return 99
    try:
        last = datetime.strptime(last_game_date, "%Y-%m-%d")
        today = datetime.utcnow()
        return (today - last).days
    except ValueError:
        return 99
