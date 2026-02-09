"""
NBA Real-Time Cache Layer

Multi-tier caching for protocol responses:
- L1: In-memory (60s TTL) - Active games, live odds
- L2: Redis-style (5min TTL) - Today's schedule, injuries  
- L3: Long-term (24h TTL) - Season averages, historical matchups

Uses in-memory dict for now, Redis-compatible interface for easy upgrade.
"""
import time
import hashlib
import json
import logging
from typing import Any, Optional, Dict, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with TTL."""
    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)
    access_count: int = 0


class NBACache:
    """
    Multi-tier in-memory cache with TTL support.
    
    Redis-compatible interface for easy migration later.
    """
    
    # Default TTLs by tier (seconds)
    TTL_L1 = 60       # Live data (60s)
    TTL_L2 = 300      # Fresh data (5min)
    TTL_L3 = 86400    # Historical (24h)
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0
        }
    
    # =========================================================================
    # Core Operations
    # =========================================================================
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        entry = self._cache.get(key)
        
        if entry is None:
            self._stats['misses'] += 1
            return None
        
        if time.time() > entry.expires_at:
            # Expired
            del self._cache[key]
            self._stats['misses'] += 1
            self._stats['evictions'] += 1
            return None
        
        entry.access_count += 1
        self._stats['hits'] += 1
        return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value with optional TTL (defaults to L2)."""
        if ttl is None:
            ttl = self.TTL_L2
        
        self._cache[key] = CacheEntry(
            value=value,
            expires_at=time.time() + ttl,
            created_at=time.time()
        )
        self._stats['sets'] += 1
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists and not expired."""
        return self.get(key) is not None
    
    def clear(self) -> int:
        """Clear all cache entries. Returns count cleared."""
        count = len(self._cache)
        self._cache.clear()
        return count
    
    def clear_expired(self) -> int:
        """Clear only expired entries. Returns count cleared."""
        now = time.time()
        expired = [k for k, v in self._cache.items() if v.expires_at < now]
        for k in expired:
            del self._cache[k]
        self._stats['evictions'] += len(expired)
        return len(expired)
    
    # =========================================================================
    # Tier-Specific Methods
    # =========================================================================
    
    def set_live(self, key: str, value: Any) -> None:
        """Set L1 cache (60s TTL) - for live/active data."""
        self.set(key, value, ttl=self.TTL_L1)
    
    def set_fresh(self, key: str, value: Any) -> None:
        """Set L2 cache (5min TTL) - for today's data."""
        self.set(key, value, ttl=self.TTL_L2)
    
    def set_historical(self, key: str, value: Any) -> None:
        """Set L3 cache (24h TTL) - for historical data."""
        self.set(key, value, ttl=self.TTL_L3)
    
    # =========================================================================
    # Key Builders
    # =========================================================================
    
    @staticmethod
    def key_game_odds(game_id: str) -> str:
        """Cache key for game odds."""
        return f"odds:game:{game_id}"
    
    @staticmethod
    def key_game_score(game_id: str) -> str:
        """Cache key for live score."""
        return f"score:game:{game_id}"
    
    @staticmethod
    def key_team_stats(team_id: int, stat_type: str) -> str:
        """Cache key for team stats."""
        return f"stats:team:{team_id}:{stat_type}"
    
    @staticmethod
    def key_player_stats(player_id: int, stat_type: str) -> str:
        """Cache key for player stats."""
        return f"stats:player:{player_id}:{stat_type}"
    
    @staticmethod
    def key_matchup(team_a_id: int, team_b_id: int, date: str) -> str:
        """Cache key for matchup analysis."""
        # Normalize order for consistent keys
        t1, t2 = min(team_a_id, team_b_id), max(team_a_id, team_b_id)
        return f"matchup:{t1}:{t2}:{date}"
    
    @staticmethod
    def key_heuristics(team_a_id: int, team_b_id: int, date: str) -> str:
        """Cache key for comprehensive heuristics."""
        t1, t2 = min(team_a_id, team_b_id), max(team_a_id, team_b_id)
        return f"heuristics:{t1}:{t2}:{date}"
    
    @staticmethod
    def key_standings(team_id: int, date: str) -> str:
        """Cache key for team standings."""
        return f"standings:{team_id}:{date}"
    
    @staticmethod
    def key_injuries(team_id: int) -> str:
        """Cache key for team injuries."""
        return f"injuries:{team_id}"
    
    # =========================================================================
    # Stats
    # =========================================================================
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total * 100) if total > 0 else 0
        
        return {
            **self._stats,
            'hit_rate': round(hit_rate, 2),
            'size': len(self._cache),
            'total_requests': total
        }


# =============================================================================
# Global Cache Instance
# =============================================================================

_cache_instance: Optional[NBACache] = None


def get_cache() -> NBACache:
    """Get or create global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = NBACache()
    return _cache_instance


# =============================================================================
# Caching Decorator
# =============================================================================

def cached(
    key_func: Callable[..., str], 
    ttl: int = NBACache.TTL_L2
):
    """
    Decorator for caching function results.
    
    Usage:
        @cached(lambda team_id: f"team:{team_id}", ttl=300)
        def get_team_stats(team_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            key = key_func(*args, **kwargs)
            
            # Try cache first
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit: {key}")
                return result
            
            # Cache miss - compute and store
            logger.debug(f"Cache miss: {key}")
            result = func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result
        
        return wrapper
    return decorator


def cached_async(
    key_func: Callable[..., str], 
    ttl: int = NBACache.TTL_L2
):
    """Async version of cached decorator."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            key = key_func(*args, **kwargs)
            
            result = cache.get(key)
            if result is not None:
                return result
            
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result
        
        return wrapper
    return decorator


# =============================================================================
# Cache Warming
# =============================================================================

def warm_cache_for_games(game_ids: list, db_session) -> int:
    """
    Pre-populate cache for upcoming games.
    
    Called by scheduled job before game start.
    Returns count of cache entries created.
    """
    from app.nba.heuristics import get_comprehensive_edge
    from app.nba.models import DimGame
    
    cache = get_cache()
    count = 0
    
    for game_id in game_ids:
        game = db_session.query(DimGame).filter_by(game_id=game_id).first()
        if not game:
            continue
        
        date_str = game.game_date.isoformat()
        
        # Warm heuristics cache
        key = NBACache.key_heuristics(
            game.home_team_id, 
            game.away_team_id, 
            date_str
        )
        
        if not cache.exists(key):
            try:
                heuristics = get_comprehensive_edge(
                    db_session,
                    game.home_team_id,
                    game.away_team_id,
                    game.game_date,
                    game.season
                )
                cache.set_fresh(key, heuristics)
                count += 1
                logger.info(f"Warmed cache for game {game_id}")
            except Exception as e:
                logger.error(f"Failed to warm cache for {game_id}: {e}")
    
    return count
