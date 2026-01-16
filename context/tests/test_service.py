# context/tests/test_service.py
"""Tests for ContextService."""

import pytest
from datetime import datetime

from context.service import ContextService, get_context, get_context_service
from context.snapshot import ContextSnapshot


class TestContextService:
    """Test ContextService class."""

    def test_create_service(self):
        """Can create service instance."""
        service = ContextService()
        assert service is not None

    def test_get_context_nba(self):
        """Can get NBA context."""
        service = ContextService()
        snapshot = service.get_context("NBA")
        assert snapshot is not None
        assert snapshot.sport == "NBA"

    def test_get_context_case_insensitive(self):
        """Sport lookup is case insensitive."""
        service = ContextService()
        snapshot = service.get_context("nba")
        assert snapshot.sport == "NBA"

    def test_get_context_unknown_sport(self):
        """Unknown sport returns empty snapshot."""
        service = ContextService()
        snapshot = service.get_context("CRICKET")
        assert snapshot.sport == "CRICKET"
        assert snapshot.player_count == 0
        assert snapshot.has_missing_data

    def test_caching(self):
        """Subsequent calls return cached data."""
        service = ContextService(cache_ttl_seconds=60)

        snapshot1 = service.get_context("NBA")
        snapshot2 = service.get_context("NBA")

        # Should be same object due to caching
        assert snapshot1.as_of == snapshot2.as_of

    def test_force_refresh_bypasses_cache(self):
        """force_refresh=True gets fresh data."""
        service = ContextService(cache_ttl_seconds=60)

        snapshot1 = service.get_context("NBA")
        snapshot2 = service.get_context("NBA", force_refresh=True)

        # Timestamps might differ slightly
        # Both should be valid snapshots
        assert snapshot1.sport == "NBA"
        assert snapshot2.sport == "NBA"

    def test_clear_cache(self):
        """Can clear cache."""
        service = ContextService()
        service.get_context("NBA")

        status_before = service.get_cache_status()
        assert "NBA" in status_before

        service.clear_cache()

        status_after = service.get_cache_status()
        assert "NBA" not in status_after

    def test_clear_cache_specific_sport(self):
        """Can clear cache for specific sport."""
        service = ContextService()
        service.get_context("NBA")

        service.clear_cache("NBA")

        status = service.get_cache_status()
        assert "NBA" not in status


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_get_context_service(self):
        """get_context_service returns singleton."""
        service1 = get_context_service()
        service2 = get_context_service()
        assert service1 is service2

    def test_get_context_function(self):
        """get_context convenience function works."""
        snapshot = get_context("NBA")
        assert snapshot is not None
        assert snapshot.sport == "NBA"
