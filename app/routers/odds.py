"""
S19-C: Odds & Games API Endpoints

Replaces mock sources with provider-based architecture.
Includes caching layer for performance.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta
import time

from app.providers import Sport, Game, MarketOdds, LiveScore, ProviderConfig
from app.providers.mock_provider import MockOddsProvider, MockScoreProvider
from app.providers.live_provider import LiveOddsProvider, LiveScoreProvider

router = APIRouter(prefix="/api", tags=["odds"])


# =============================================================================
# In-Memory Cache
# =============================================================================

class SimpleCache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self, default_ttl_seconds: int = 60):
        self.cache = {}
        self.default_ttl = default_ttl_seconds
    
    def get(self, key: str) -> Optional[any]:
        """Get value from cache if not expired."""
        if key not in self.cache:
            return None
        
        value, expires_at = self.cache[key]
        
        if time.time() > expires_at:
            # Expired, remove from cache
            del self.cache[key]
            return None
        
        return value
    
    def set(self, key: str, value: any, ttl_seconds: Optional[int] = None):
        """Set value in cache with TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = time.time() + ttl
        self.cache[key] = (value, expires_at)
    
    def clear(self):
        """Clear all cache entries."""
        self.cache = {}


# Global cache instance
_cache = SimpleCache(default_ttl_seconds=60)


# =============================================================================
# Provider Selection
# =============================================================================

def get_odds_provider() -> any:
    """
    Get the active odds provider.
    
    Uses MockProvider for now. Can switch to LiveProvider when API keys are configured.
    """
    # TODO: Read from config to determine provider type
    provider_type = "mock"  # or "live"
    
    if provider_type == "live":
        config = ProviderConfig(provider_type="live", api_key=None)
        return LiveOddsProvider(config)
    else:
        return MockOddsProvider()


def get_score_provider() -> any:
    """Get the active score provider."""
    provider_type = "mock"  # or "live"
    
    if provider_type == "live":
        config = ProviderConfig(provider_type="live", api_key=None)
        return LiveScoreProvider(config)
    else:
        return MockScoreProvider()


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("/sports", response_model=List[Sport])
async def get_sports():
    """
    Get list of available sports.
    
    Cached for 5 minutes (sports list changes infrequently).
    """
    cache_key = "sports:all"
    cached = _cache.get(cache_key)
    
    if cached:
        return cached
    
    provider = get_odds_provider()
    sports = provider.get_sports()
    
    _cache.set(cache_key, sports, ttl_seconds=300)  # 5 min cache
    return sports


@router.get("/games", response_model=List[Game])
async def get_games(sport: str = Query(..., description="Sport ID (e.g., NBA, NFL)")):
    """
    Get games for a specific sport.
    
    Cached for 60 seconds.
    """
    cache_key = f"games:{sport}"
    cached = _cache.get(cache_key)
    
    if cached:
        return cached
    
    provider = get_odds_provider()
    games = provider.get_games(sport)
    
    _cache.set(cache_key, games, ttl_seconds=60)
    return games


@router.get("/odds/{game_id}", response_model=List[MarketOdds])
async def get_odds(game_id: str):
    """
    Get odds for a specific game.
    
    Cached for 30 seconds (odds update frequently).
    """
    cache_key = f"odds:{game_id}"
    cached = _cache.get(cache_key)
    
    if cached:
        return cached
    
    provider = get_odds_provider()
    odds = provider.get_odds(game_id)
    
    if not odds:
        raise HTTPException(status_code=404, detail="Odds not found for game")
    
    _cache.set(cache_key, odds, ttl_seconds=30)
    return odds


@router.get("/score/{game_id}", response_model=Optional[LiveScore])
async def get_score(game_id: str):
    """
    Get live score for a game.
    
    Cached for 10 seconds (scores update very frequently).
    Returns null if game is not live.
    """
    cache_key = f"score:{game_id}"
    cached = _cache.get(cache_key)
    
    if cached:
        return cached
    
    provider = get_score_provider()
    score = provider.get_score(game_id)
    
    # Cache even if None (game not live)
    _cache.set(cache_key, score, ttl_seconds=10)
    return score


@router.post("/cache/clear")
async def clear_cache():
    """
    Clear all cached data.
    
    Useful for development/testing.
    """
    _cache.clear()
    return {"success": True, "message": "Cache cleared"}
