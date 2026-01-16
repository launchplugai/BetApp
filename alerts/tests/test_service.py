# alerts/tests/test_service.py
"""Tests for AlertService."""

import pytest
from datetime import datetime

from alerts.service import (
    AlertService,
    get_alert_service,
    reset_alert_service,
    check_for_alerts,
)
from alerts.store import AlertStore, reset_alert_store
from alerts.models import AlertType
from context.snapshot import ContextSnapshot, PlayerAvailability, PlayerStatus


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before and after each test."""
    reset_alert_service()
    reset_alert_store()
    yield
    reset_alert_service()
    reset_alert_store()


@pytest.fixture
def fresh_store():
    """Create a fresh isolated store for each test."""
    return AlertStore()


def make_snapshot(
    players: list[tuple[str, str, PlayerStatus]] = None,
    source: str = "nba-official",
    confidence: float = 0.5,
) -> ContextSnapshot:
    """Helper to create test snapshots."""
    player_objs = []
    if players:
        for name, team, status in players:
            player_objs.append(PlayerAvailability(
                player_id=name.lower().replace(" ", "-"),
                player_name=name,
                team=team,
                status=status,
            ))

    return ContextSnapshot(
        sport="NBA",
        as_of=datetime.utcnow(),
        source=source,
        players=tuple(player_objs),
        confidence_hint=confidence,
    )


class TestAlertService:
    """Test AlertService class."""

    def test_create_service(self, fresh_store):
        service = AlertService(store=fresh_store)
        assert service is not None

    def test_check_snapshot_first_time_clean(self, fresh_store):
        service = AlertService(store=fresh_store)
        snapshot = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
        )

        alerts = service.check_snapshot(snapshot)

        # No alerts on clean first load
        assert len(alerts) == 0

    def test_check_snapshot_detects_change(self, fresh_store):
        service = AlertService(store=fresh_store)

        # First snapshot - player available
        snap1 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
        )
        service.check_snapshot(snap1)

        # Second snapshot - player out
        snap2 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.OUT)],
        )
        alerts = service.check_snapshot(snap2)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.PLAYER_NOW_OUT
        assert alerts[0].player_name == "LeBron James"

    def test_alerts_stored(self, fresh_store):
        service = AlertService(store=fresh_store)

        snap1 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
        )
        service.check_snapshot(snap1)

        snap2 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.OUT)],
        )
        service.check_snapshot(snap2)

        assert service.get_alert_count() == 1

    def test_correlation_id_tracked(self, fresh_store):
        service = AlertService(store=fresh_store)

        snap1 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
        )
        service.check_snapshot(snap1, correlation_id="session-1")

        snap2 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.OUT)],
        )
        service.check_snapshot(snap2, correlation_id="session-1")

        alerts = service.get_alerts(correlation_id="session-1")
        assert len(alerts) == 1

    def test_player_filter(self, fresh_store):
        service = AlertService(store=fresh_store)

        snap1 = make_snapshot(
            players=[
                ("LeBron James", "LAL", PlayerStatus.AVAILABLE),
                ("Jayson Tatum", "BOS", PlayerStatus.AVAILABLE),
            ],
        )
        service.check_snapshot(snap1)

        snap2 = make_snapshot(
            players=[
                ("LeBron James", "LAL", PlayerStatus.OUT),
                ("Jayson Tatum", "BOS", PlayerStatus.OUT),
            ],
        )
        # Only check LeBron
        alerts = service.check_snapshot(snap2, player_names=["LeBron James"])

        assert len(alerts) == 1
        assert alerts[0].player_name == "LeBron James"

    def test_get_recent_alerts(self, fresh_store):
        service = AlertService(store=fresh_store)

        # Generate some alerts
        snap1 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
        )
        service.check_snapshot(snap1)

        snap2 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.OUT)],
        )
        service.check_snapshot(snap2)

        recent = service.get_recent_alerts(limit=10)
        assert len(recent) == 1

    def test_clear_alerts(self, fresh_store):
        service = AlertService(store=fresh_store)

        snap1 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
        )
        service.check_snapshot(snap1)

        snap2 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.OUT)],
        )
        service.check_snapshot(snap2)

        assert service.get_alert_count() == 1

        service.clear_alerts()
        assert service.get_alert_count() == 0


class TestServiceSingleton:
    """Test singleton pattern."""

    def test_get_alert_service_singleton(self):
        service1 = get_alert_service()
        service2 = get_alert_service()
        assert service1 is service2

    def test_reset_alert_service(self):
        service1 = get_alert_service()

        # Generate an alert
        snap1 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
        )
        service1.check_snapshot(snap1)

        snap2 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.OUT)],
        )
        service1.check_snapshot(snap2)

        assert service1.get_alert_count() == 1

        reset_alert_service()

        service2 = get_alert_service()
        assert service2.get_alert_count() == 0


class TestConvenienceFunction:
    """Test check_for_alerts convenience function."""

    def test_check_for_alerts_works(self):
        snapshot = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.OUT)],
        )

        # First call - reports existing issue
        alerts = check_for_alerts(
            snapshot,
            player_names=["LeBron James"],
            correlation_id="test-session",
        )

        # Should alert since player is OUT on first check
        assert len(alerts) == 1

    def test_check_for_alerts_tracks_state(self):
        snap1 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
        )
        check_for_alerts(snap1)

        snap2 = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.OUT)],
        )
        alerts = check_for_alerts(snap2)

        assert len(alerts) == 1
        assert alerts[0].player_name == "LeBron James"


class TestMultipleSports:
    """Test handling of multiple sports."""

    def test_tracks_per_sport(self, fresh_store):
        service = AlertService(store=fresh_store)

        nba_snap = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=(
                PlayerAvailability("p1", "Player 1", "LAL", PlayerStatus.AVAILABLE),
            ),
        )
        service.check_snapshot(nba_snap)

        # Different sport should track separately
        # (In Sprint 4 we only do NBA, but architecture supports more)

        nba_snap2 = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=(
                PlayerAvailability("p1", "Player 1", "LAL", PlayerStatus.OUT),
            ),
        )
        alerts = service.check_snapshot(nba_snap2)

        assert len(alerts) == 1
