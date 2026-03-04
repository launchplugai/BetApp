"""
Simple in-memory cache for advanced stats
TTL-based expiration with basic LRU eviction
"""

import time
from datetime import datetime, timedelta
from typing import Optional, Any
from .schemas import CacheEntry


# In-memory cache storage
_cache: dict[str, CacheEntry] = {}
_MAX_CACHE_SIZE = 1000  # Prevent unbounded growth


def _generate_key(sport: str, team_id: str, date_str: str, stat_type: str = "advanced") -> str:
    """Generate cache key for stats lookup"""
    return f"{sport}:{team_id}:{date_str}:{stat_type}"


def get_cached_stats(sport: str, team_id: str, date_str: str, stat_type: str = "advanced") -> Optional[dict]:
    """
    Retrieve cached stats if they exist and haven't expired
    
    Args:
        sport: 'nba', 'nfl', etc.
        team_id: Team identifier
        date_str: Date in YYYY-MM-DD format
        stat_type: Category of stats
        
    Returns:
        Cached data dict or None if miss/expired
    """
    key = _generate_key(sport, team_id, date_str, stat_type)
    entry = _cache.get(key)
    
    if not entry:
        return None
    
    # Check expiration
    if datetime.utcnow() > entry.expires_at:
        del _cache[key]
        return None
    
    # Update hit count
    entry.hit_count += 1
    return entry.data


def set_cached_stats(
    sport: str, 
    team_id: str, 
    date_str: str, 
    data: dict,
    stat_type: str = "advanced",
    ttl_seconds: int = 3600
) -> None:
    """
    Store stats in cache with TTL
    
    Args:
        sport: 'nba', 'nfl', etc.
        team_id: Team identifier
        date_str: Date in YYYY-MM-DD format
        data: Stats data to cache
        stat_type: Category of stats
        ttl_seconds: Time to live (default 1 hour)
    """
    # Simple LRU eviction if cache is full
    if len(_cache) >= _MAX_CACHE_SIZE:
        _evict_oldest()
    
    key = _generate_key(sport, team_id, date_str, stat_type)
    now = datetime.utcnow()
    
    _cache[key] = CacheEntry(
        key=key,
        data=data,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
        hit_count=0,
    )


def _evict_oldest() -> None:
    """Remove oldest entries when cache is full"""
    if not _cache:
        return
    
    # Remove 10% oldest entries
    sorted_entries = sorted(_cache.items(), key=lambda x: x[1].created_at)
    to_remove = len(sorted_entries) // 10 or 1
    
    for key, _ in sorted_entries[:to_remove]:
        del _cache[key]


def clear_cache() -> None:
    """Clear all cached entries (useful for testing)"""
    _cache.clear()


def get_cache_stats() -> dict:
    """Get cache statistics"""
    now = datetime.utcnow()
    expired = sum(1 for e in _cache.values() if e.expires_at < now)
    
    return {
        "total_entries": len(_cache),
        "expired_entries": expired,
        "total_hits": sum(e.hit_count for e in _cache.values()),
    }
