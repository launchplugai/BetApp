# context/service.py
"""
Context Service - Orchestrates providers and caching.

This is the main entry point for getting context data.
Routes and other consumers should use this service rather than
accessing providers directly.

Features:
- Provider registration and management
- In-memory caching with TTL
- Graceful degradation when providers fail
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

from context.providers.base import ContextProvider
from context.providers.nba_availability import NBAAvailabilityProvider
from context.snapshot import ContextSnapshot, empty_snapshot


@dataclass
class CacheEntry:
    """Cached context snapshot with expiration."""

    snapshot: ContextSnapshot
    expires_at: datetime

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() > self.expires_at


class ContextService:
    """
    Central service for context data management.

    Handles:
    - Provider registration
    - Caching with configurable TTL
    - Fallback to empty snapshots on failure
    """

    # Default cache TTL: 5 minutes
    DEFAULT_TTL_SECONDS = 300

    def __init__(self, cache_ttl_seconds: int = DEFAULT_TTL_SECONDS):
        """
        Initialize context service.

        Args:
            cache_ttl_seconds: How long to cache snapshots (default 5 min)
        """
        self._providers: dict[str, ContextProvider] = {}
        self._cache: dict[str, CacheEntry] = {}
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._lock = Lock()

        # Register default providers
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register default providers for Sprint 3."""
        self.register_provider(NBAAvailabilityProvider())

    def register_provider(self, provider: ContextProvider) -> None:
        """
        Register a context provider.

        Args:
            provider: Provider instance to register
        """
        key = f"{provider.sport}:{provider.source_name}"
        self._providers[key] = provider

    def get_context(
        self,
        sport: str,
        force_refresh: bool = False,
    ) -> ContextSnapshot:
        """
        Get context snapshot for a sport.

        Args:
            sport: Sport to get context for (e.g., "NBA")
            force_refresh: If True, bypass cache and fetch fresh

        Returns:
            ContextSnapshot (may be empty if no providers available)
        """
        sport_upper = sport.upper()

        # Check cache first (unless force refresh)
        if not force_refresh:
            cached = self._get_cached(sport_upper)
            if cached is not None:
                return cached

        # Find provider for this sport
        provider = self._find_provider(sport_upper)
        if provider is None:
            return empty_snapshot(sport_upper, "no-provider")

        # Fetch fresh data
        snapshot = provider.fetch()
        if snapshot is None:
            return empty_snapshot(sport_upper, provider.source_name)

        # Cache the result
        self._set_cached(sport_upper, snapshot)

        return snapshot

    def _get_cached(self, sport: str) -> Optional[ContextSnapshot]:
        """Get cached snapshot if available and not expired."""
        with self._lock:
            entry = self._cache.get(sport)
            if entry is not None and not entry.is_expired():
                return entry.snapshot
            return None

    def _set_cached(self, sport: str, snapshot: ContextSnapshot) -> None:
        """Cache a snapshot."""
        with self._lock:
            self._cache[sport] = CacheEntry(
                snapshot=snapshot,
                expires_at=datetime.utcnow() + self._cache_ttl,
            )

    def _find_provider(self, sport: str) -> Optional[ContextProvider]:
        """Find a provider for the given sport."""
        for key, provider in self._providers.items():
            if provider.sport.upper() == sport and provider.is_available():
                return provider
        return None

    def clear_cache(self, sport: Optional[str] = None) -> None:
        """
        Clear cached data.

        Args:
            sport: Specific sport to clear, or None for all
        """
        with self._lock:
            if sport is None:
                self._cache.clear()
            else:
                self._cache.pop(sport.upper(), None)

    def get_cache_status(self) -> dict:
        """Get cache status for monitoring."""
        with self._lock:
            return {
                sport: {
                    "expires_at": entry.expires_at.isoformat(),
                    "is_expired": entry.is_expired(),
                    "source": entry.snapshot.source,
                    "player_count": entry.snapshot.player_count,
                }
                for sport, entry in self._cache.items()
            }


# Singleton instance for app-wide use
_service_instance: Optional[ContextService] = None


def get_context_service() -> ContextService:
    """Get the singleton context service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ContextService()
    return _service_instance


def get_context(sport: str, force_refresh: bool = False) -> ContextSnapshot:
    """
    Convenience function to get context for a sport.

    This is the primary entry point for getting context data.

    Args:
        sport: Sport to get context for (e.g., "NBA")
        force_refresh: Bypass cache if True

    Returns:
        ContextSnapshot for the sport
    """
    return get_context_service().get_context(sport, force_refresh)
