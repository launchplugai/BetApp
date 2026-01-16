# alerts/tests/test_store.py
"""Tests for alert storage."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from alerts.models import Alert, AlertType, AlertSeverity
from alerts.store import AlertStore, get_alert_store, reset_alert_store


@pytest.fixture
def store():
    """Fresh store for each test."""
    return AlertStore(ttl_seconds=3600, max_alerts=100)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton after each test."""
    yield
    reset_alert_store()


def make_alert(**kwargs) -> Alert:
    """Helper to create test alerts."""
    defaults = {
        "alert_type": AlertType.PLAYER_NOW_OUT,
        "severity": AlertSeverity.CRITICAL,
        "title": "Test Alert",
        "message": "Test message",
    }
    defaults.update(kwargs)
    return Alert(**defaults)


class TestAlertStore:
    """Test AlertStore class."""

    def test_add_and_get(self, store):
        alert = make_alert()
        store.add(alert)

        retrieved = store.get(alert.alert_id)
        assert retrieved is not None
        assert retrieved.alert_id == alert.alert_id

    def test_get_nonexistent(self, store):
        from uuid import uuid4
        result = store.get(uuid4())
        assert result is None

    def test_count(self, store):
        assert store.count() == 0

        store.add(make_alert())
        assert store.count() == 1

        store.add(make_alert())
        assert store.count() == 2

    def test_clear(self, store):
        store.add(make_alert())
        store.add(make_alert())
        assert store.count() == 2

        store.clear()
        assert store.count() == 0

    def test_get_recent(self, store):
        alerts = [make_alert(title=f"Alert {i}") for i in range(5)]
        for a in alerts:
            store.add(a)

        recent = store.get_recent(3)
        assert len(recent) == 3
        # Most recent first
        assert recent[0].title == "Alert 4"

    def test_max_alerts_eviction(self):
        store = AlertStore(max_alerts=3)

        for i in range(5):
            store.add(make_alert(title=f"Alert {i}"))

        assert store.count() == 3
        # Oldest should be evicted
        all_alerts = store.get_all()
        titles = [a.title for a in all_alerts]
        assert "Alert 0" not in titles
        assert "Alert 1" not in titles
        assert "Alert 4" in titles


class TestAlertStoreIndexes:
    """Test index-based lookups."""

    def test_get_by_correlation(self, store):
        alert1 = make_alert(correlation_id="session-1")
        alert2 = make_alert(correlation_id="session-1")
        alert3 = make_alert(correlation_id="session-2")

        store.add(alert1)
        store.add(alert2)
        store.add(alert3)

        results = store.get_by_correlation("session-1")
        assert len(results) == 2

        results = store.get_by_correlation("session-2")
        assert len(results) == 1

    def test_get_by_player(self, store):
        alert1 = make_alert(player_name="LeBron James")
        alert2 = make_alert(player_name="LeBron James")
        alert3 = make_alert(player_name="Anthony Davis")

        store.add(alert1)
        store.add(alert2)
        store.add(alert3)

        results = store.get_by_player("LeBron James")
        assert len(results) == 2

        # Case insensitive
        results = store.get_by_player("lebron james")
        assert len(results) == 2

    def test_get_by_team(self, store):
        alert1 = make_alert(team="LAL")
        alert2 = make_alert(team="LAL")
        alert3 = make_alert(team="BOS")

        store.add(alert1)
        store.add(alert2)
        store.add(alert3)

        results = store.get_by_team("LAL")
        assert len(results) == 2

        # Case insensitive
        results = store.get_by_team("lal")
        assert len(results) == 2


class TestAlertStoreTTL:
    """Test TTL-based expiry."""

    def test_expired_alert_not_returned(self, store):
        # Create alert with old timestamp
        old_time = datetime.utcnow() - timedelta(hours=2)
        alert = Alert(
            alert_type=AlertType.PLAYER_NOW_OUT,
            severity=AlertSeverity.CRITICAL,
            title="Old Alert",
            message="Test",
            created_at=old_time,
        )
        store.add(alert)

        # Should not be returned (expired)
        result = store.get(alert.alert_id)
        assert result is None

    def test_fresh_alert_returned(self, store):
        alert = make_alert()
        store.add(alert)

        result = store.get(alert.alert_id)
        assert result is not None


class TestSingleton:
    """Test singleton pattern."""

    def test_get_alert_store_singleton(self):
        store1 = get_alert_store()
        store2 = get_alert_store()
        assert store1 is store2

    def test_reset_alert_store(self):
        store1 = get_alert_store()
        store1.add(make_alert())
        assert store1.count() == 1

        reset_alert_store()

        store2 = get_alert_store()
        assert store2.count() == 0
