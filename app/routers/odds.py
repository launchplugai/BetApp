"""
S19-C: Odds & Games API Endpoints

Replaces mock sources with provider-based architecture.
Includes caching layer for performance.
"""

from fastapi import APIRouter, Query, HTTPException, Response
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import time

from app.providers import Sport, Game, MarketOdds, LiveScore, ProviderConfig
from app.providers.mock_provider import MockOddsProvider, MockScoreProvider
from app.providers.live_provider import LiveOddsProvider, LiveScoreProvider
from app.providers.odds_api import OddsApiProvider
from app.config import load_config
from analytics import enrich_game
from analytics.schemas import GameContext

router = APIRouter(prefix="/api", tags=["odds"])


# =============================================================================
# In-Memory Cache
# =============================================================================

class SimpleCache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self, default_ttl_seconds: int = 60):
        self.cache = {}
        self.default_ttl = default_ttl_seconds

    def get_entry(self, key: str) -> Optional[dict]:
        """Get raw cache entry if present and not expired."""
        if key not in self.cache:
            return None

        entry = self.cache[key]
        expires_at = entry["expires_at"]

        if time.time() > expires_at:
            # Expired, remove from cache
            del self.cache[key]
            return None

        return entry

    def get(self, key: str) -> Optional[any]:
        """Get value from cache if not expired."""
        entry = self.get_entry(key)
        if entry is None:
            return None
        return entry["value"]
    
    def set(self, key: str, value: any, ttl_seconds: Optional[int] = None):
        """Set value in cache with TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        now = time.time()
        self.cache[key] = {
            "value": value,
            "stored_at": now,
            "expires_at": now + ttl,
            "ttl_seconds": ttl,
        }

    def describe(self, key: str) -> Optional[dict]:
        """Return cache metadata for a key."""
        entry = self.get_entry(key)
        if entry is None:
            return None

        return {
            "stored_at": datetime.fromtimestamp(entry["stored_at"], tz=timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(entry["expires_at"], tz=timezone.utc).isoformat(),
            "ttl_seconds": entry["ttl_seconds"],
            "age_seconds": round(time.time() - entry["stored_at"], 3),
        }
    
    def clear(self):
        """Clear all cache entries."""
        self.cache = {}

    def stats(self) -> dict:
        """Return lightweight cache stats."""
        active_keys = []
        for key in list(self.cache.keys()):
            if self.get_entry(key) is not None:
                active_keys.append(key)

        return {
            "entries": len(active_keys),
            "default_ttl_seconds": self.default_ttl,
            "keys": active_keys,
        }


# Global cache instance
_cache = SimpleCache(default_ttl_seconds=60)


# =============================================================================
# Provider Selection
# =============================================================================

def get_odds_provider() -> any:
    """
    Get the active odds provider.
    
    R0.3: Deterministic provider selection based on ODDS_PROVIDER config.
    Explicit flag-based selection, not env var presence.
    """
    # Load config fresh each time to pick up env var changes
    config = load_config(fail_fast=False)
    provider_type = config.odds_provider
    
    if provider_type == "oddsapi":
        provider_config = ProviderConfig(
            provider_type="live",
            api_key=config.the_odds_api_key
        )
        return OddsApiProvider(provider_config)
    else:
        # Default: mock provider
        return MockOddsProvider()


def get_score_provider() -> any:
    """Get the active score provider."""
    # Load config fresh each time to pick up env var changes
    config = load_config(fail_fast=False)
    
    if config.odds_provider == "oddsapi":
        provider_config = ProviderConfig(
            provider_type="live",
            api_key=config.the_odds_api_key
        )
        return OddsApiProvider(provider_config)
    else:
        return MockScoreProvider()


def _provider_status() -> dict:
    """Return current provider and cache status."""
    config = load_config(fail_fast=False)
    odds_provider = get_odds_provider()
    score_provider = get_score_provider()

    odds_source = getattr(odds_provider, "source_name", config.odds_provider)
    score_source = getattr(score_provider, "source_name", config.odds_provider)

    return {
        "mode": config.odds_provider,
        "odds_provider": odds_source,
        "score_provider": score_source,
        "api_key_present": bool(config.the_odds_api_key),
        "live_ready": config.odds_provider == "mock" or bool(config.the_odds_api_key),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "cache": _cache.stats(),
    }


def _set_data_headers(
    response: Response,
    *,
    provider: str,
    mode: str,
    cache_hit: bool,
    cache_meta: Optional[dict] = None,
) -> None:
    """Attach non-sensitive data provenance headers to a response."""
    response.headers["X-Data-Provider"] = provider
    response.headers["X-Data-Mode"] = mode
    response.headers["X-Data-Cache-Hit"] = "true" if cache_hit else "false"

    if cache_meta:
        response.headers["X-Data-Stored-At"] = cache_meta["stored_at"]
        response.headers["X-Data-Expires-At"] = cache_meta["expires_at"]
        response.headers["X-Data-TTL-Seconds"] = str(cache_meta["ttl_seconds"])
        response.headers["X-Data-Age-Seconds"] = str(cache_meta["age_seconds"])


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/sports", response_model=List[Sport])
async def get_sports(response: Response):
    """
    Get list of available sports.
    
    Cached for 5 minutes (sports list changes infrequently).
    """
    cache_key = "sports:all"
    cache_meta = _cache.describe(cache_key)
    provider_status = _provider_status()

    if cache_meta is not None:
        cached = _cache.get(cache_key)
        _set_data_headers(
            response,
            provider=provider_status["odds_provider"],
            mode=provider_status["mode"],
            cache_hit=True,
            cache_meta=cache_meta,
        )
        return cached
    
    provider = get_odds_provider()
    # Handle both sync and async providers
    if hasattr(provider.get_sports, '__call__'):
        import inspect
        if inspect.iscoroutinefunction(provider.get_sports):
            sports = await provider.get_sports()
        else:
            sports = provider.get_sports()
    else:
        sports = provider.get_sports()
    
    _cache.set(cache_key, sports, ttl_seconds=300)  # 5 min cache
    _set_data_headers(
        response,
        provider=provider_status["odds_provider"],
        mode=provider_status["mode"],
        cache_hit=False,
        cache_meta=_cache.describe(cache_key),
    )
    return sports


@router.get("/games", response_model=List[Game])
async def get_games(
    response: Response,
    sport: str = Query(..., description="Sport ID (e.g., NBA, NFL)"),
):
    """
    Get games for a specific sport.
    
    Cached for 60 seconds.
    """
    cache_key = f"games:{sport}"
    cache_meta = _cache.describe(cache_key)
    provider_status = _provider_status()

    if cache_meta is not None:
        cached = _cache.get(cache_key)
        _set_data_headers(
            response,
            provider=provider_status["odds_provider"],
            mode=provider_status["mode"],
            cache_hit=True,
            cache_meta=cache_meta,
        )
        return cached
    
    provider = get_odds_provider()
    # Handle both sync and async providers
    import inspect
    if inspect.iscoroutinefunction(provider.get_games):
        games = await provider.get_games(sport)
    else:
        games = provider.get_games(sport)
    
    _cache.set(cache_key, games, ttl_seconds=60)
    _set_data_headers(
        response,
        provider=provider_status["odds_provider"],
        mode=provider_status["mode"],
        cache_hit=False,
        cache_meta=_cache.describe(cache_key),
    )
    return games


@router.get("/odds/{game_id}", response_model=List[MarketOdds])
async def get_odds(game_id: str, response: Response):
    """
    Get odds for a specific game.
    
    Cached for 30 seconds (odds update frequently).
    """
    cache_key = f"odds:{game_id}"
    cache_meta = _cache.describe(cache_key)
    provider_status = _provider_status()

    if cache_meta is not None:
        cached = _cache.get(cache_key)
        _set_data_headers(
            response,
            provider=provider_status["odds_provider"],
            mode=provider_status["mode"],
            cache_hit=True,
            cache_meta=cache_meta,
        )
        return cached
    
    provider = get_odds_provider()
    
    # Handle both sync and async providers
    import inspect
    if inspect.iscoroutinefunction(provider.get_odds):
        odds = await provider.get_odds(game_id)
    else:
        odds = provider.get_odds(game_id)
    
    if not odds:
        raise HTTPException(status_code=404, detail="Odds not found for game")
    
    _cache.set(cache_key, odds, ttl_seconds=30)
    _set_data_headers(
        response,
        provider=provider_status["odds_provider"],
        mode=provider_status["mode"],
        cache_hit=False,
        cache_meta=_cache.describe(cache_key),
    )
    return odds


@router.get("/score/{game_id}", response_model=Optional[LiveScore])
async def get_score(game_id: str, response: Response):
    """
    Get live score for a game.
    
    Cached for 10 seconds (scores update very frequently).
    Returns null if game is not live.
    """
    cache_key = f"score:{game_id}"
    cache_meta = _cache.describe(cache_key)
    provider_status = _provider_status()

    if cache_meta is not None:
        cached = _cache.get(cache_key)
        _set_data_headers(
            response,
            provider=provider_status["score_provider"],
            mode=provider_status["mode"],
            cache_hit=True,
            cache_meta=cache_meta,
        )
        return cached
    
    provider = get_score_provider()
    # Handle both sync and async providers
    import inspect
    if inspect.iscoroutinefunction(provider.get_score):
        score = await provider.get_score(game_id)
    else:
        score = provider.get_score(game_id)
    
    # Cache even if None (game not live)
    _cache.set(cache_key, score, ttl_seconds=10)
    _set_data_headers(
        response,
        provider=provider_status["score_provider"],
        mode=provider_status["mode"],
        cache_hit=False,
        cache_meta=_cache.describe(cache_key),
    )
    return score


@router.post("/cache/clear")
async def clear_cache():
    """
    Clear all cached data.

    Useful for development/testing.
    """
    _cache.clear()
    return {"success": True, "message": "Cache cleared"}


@router.get("/provider/status")
async def get_provider_status():
    """Return non-sensitive odds/score provider status and cache summary."""
    return _provider_status()


@router.get("/odds/{game_id}/diagnostics")
async def get_odds_diagnostics(game_id: str):
    """Return provider and cache diagnostics for a game's odds lookup."""
    cache_key = f"odds:{game_id}"
    provider_status = _provider_status()
    cache_entry = _cache.describe(cache_key)

    return {
        "game_id": game_id,
        "provider": provider_status["odds_provider"],
        "mode": provider_status["mode"],
        "cache_hit": cache_entry is not None,
        "cache": cache_entry,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/context/{sport}/{game_id}", response_model=GameContext)
async def get_game_context(sport: str, game_id: str, response: Response):
    """
    Get enriched statistical context for a specific game.

    Looks up the game from the active provider then enriches it with
    advanced team stats fetched from free public APIs:
      - NBA: pace, off/def/net rating from stats.nba.com
      - NFL: plays/game, points/game from ESPN

    On success, returns GameContext with is_enriched=True and real stats.
    If the stats source is unreachable, returns is_enriched=False with
    enrichment_errors populated (degraded mode — never a hard 5xx).

    Supported sports: nba, nfl
    """
    sport_lower = sport.lower()
    if sport_lower not in ("nba", "nfl"):
        raise HTTPException(
            status_code=400,
            detail=f"Enrichment not available for '{sport}'. Supported: nba, nfl",
        )

    # Pull games from provider (uses shared cache when warm)
    cache_key = f"games:{sport.upper()}"
    cache_meta = _cache.describe(cache_key)
    provider_status = _provider_status()
    games: Optional[List[Game]] = _cache.get(cache_key)
    games_cache_hit = cache_meta is not None

    if games is None:
        provider = get_odds_provider()
        import inspect
        if inspect.iscoroutinefunction(provider.get_games):
            games = await provider.get_games(sport.upper())
        else:
            games = provider.get_games(sport.upper())
        _cache.set(cache_key, games, ttl_seconds=60)
        cache_meta = _cache.describe(cache_key)
        games_cache_hit = False

    # Find the requested game
    target: Optional[Game] = next((g for g in games if g.id == game_id), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")

    # Build the raw_odds_data dict enrichment expects
    raw_odds_data = {
        "id": target.id,
        "home_team": target.home,
        "away_team": target.away,
        "home_team_name": target.home,
        "away_team_name": target.away,
    }

    result = enrich_game(raw_odds_data, sport_lower)

    if not result.success or result.game_context is None:
        raise HTTPException(
            status_code=502,
            detail=result.error_message or "Enrichment failed",
        )

    _set_data_headers(
        response,
        provider=provider_status["odds_provider"],
        mode=provider_status["mode"],
        cache_hit=games_cache_hit,
        cache_meta=cache_meta,
    )
    return result.game_context
