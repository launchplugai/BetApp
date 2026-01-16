# alerts/tests/test_detector.py
"""Tests for delta detection."""

import pytest
from datetime import datetime

from alerts.detector import (
    detect_delta,
    PlayerDelta,
    ConfidenceDelta,
    SourceDelta,
    STATUS_SEVERITY,
)
from context.snapshot import ContextSnapshot, PlayerAvailability, PlayerStatus


def make_snapshot(
    players: list[tuple[str, str, PlayerStatus]] = None,
    source: str = "nba-official",
    confidence: float = 0.5,
    missing: tuple[str, ...] = (),
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
        missing_data=missing,
    )


class TestPlayerDelta:
    """Test PlayerDelta dataclass."""

    def test_is_worsened(self):
        delta = PlayerDelta(
            player_name="Test",
            team="TST",
            previous_status=PlayerStatus.AVAILABLE,
            current_status=PlayerStatus.OUT,
        )
        assert delta.is_worsened is True
        assert delta.is_improved is False

    def test_is_improved(self):
        delta = PlayerDelta(
            player_name="Test",
            team="TST",
            previous_status=PlayerStatus.OUT,
            current_status=PlayerStatus.AVAILABLE,
        )
        assert delta.is_worsened is False
        assert delta.is_improved is True

    def test_no_change(self):
        delta = PlayerDelta(
            player_name="Test",
            team="TST",
            previous_status=PlayerStatus.QUESTIONABLE,
            current_status=PlayerStatus.QUESTIONABLE,
        )
        assert delta.is_worsened is False
        assert delta.is_improved is False

    def test_severity_change(self):
        delta = PlayerDelta(
            player_name="Test",
            team="TST",
            previous_status=PlayerStatus.AVAILABLE,
            current_status=PlayerStatus.OUT,
        )
        # OUT (4) - AVAILABLE (0) = 4
        assert delta.severity_change == 4


class TestConfidenceDelta:
    """Test ConfidenceDelta dataclass."""

    def test_is_dropped(self):
        delta = ConfidenceDelta(
            previous_confidence=0.5,
            current_confidence=-0.3,
            reason="Test",
        )
        assert delta.is_dropped is True
        assert delta.drop_amount == 0.8

    def test_not_dropped(self):
        delta = ConfidenceDelta(
            previous_confidence=0.0,
            current_confidence=0.5,
            reason="Improved",
        )
        assert delta.is_dropped is False


class TestDetectDeltaNoPreivous:
    """Test delta detection with no previous snapshot."""

    def test_first_snapshot_clean(self):
        current = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
            source="nba-official",
        )

        delta = detect_delta(previous=None, current=current)

        assert not delta.has_changes  # No concerns on clean first load

    def test_first_snapshot_source_fallback(self):
        current = make_snapshot(source="sample-fallback")

        delta = detect_delta(previous=None, current=current)

        assert delta.source_change is not None
        assert delta.source_change.is_degraded is True

    def test_first_snapshot_filtered_player_out(self):
        current = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.OUT)],
        )

        delta = detect_delta(
            previous=None,
            current=current,
            player_names=["LeBron James"],
        )

        # Should report as concern even on first load
        assert len(delta.player_changes) == 1
        assert delta.player_changes[0].current_status == PlayerStatus.OUT


class TestDetectDeltaPlayerChanges:
    """Test player status change detection."""

    def test_player_worsened(self):
        previous = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
        )
        current = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.OUT)],
        )

        delta = detect_delta(previous, current)

        assert len(delta.player_changes) == 1
        assert delta.player_changes[0].player_name == "LeBron James"
        assert delta.player_changes[0].is_worsened is True

    def test_player_improved(self):
        previous = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.QUESTIONABLE)],
        )
        current = make_snapshot(
            players=[("LeBron James", "LAL", PlayerStatus.AVAILABLE)],
        )

        delta = detect_delta(previous, current)

        assert len(delta.player_changes) == 1
        assert delta.player_changes[0].is_improved is True

    def test_multiple_players_changed(self):
        previous = make_snapshot(
            players=[
                ("LeBron James", "LAL", PlayerStatus.AVAILABLE),
                ("Anthony Davis", "LAL", PlayerStatus.AVAILABLE),
            ],
        )
        current = make_snapshot(
            players=[
                ("LeBron James", "LAL", PlayerStatus.OUT),
                ("Anthony Davis", "LAL", PlayerStatus.QUESTIONABLE),
            ],
        )

        delta = detect_delta(previous, current)

        assert len(delta.player_changes) == 2
        assert len(delta.worsened_players) == 2

    def test_player_filter(self):
        previous = make_snapshot(
            players=[
                ("LeBron James", "LAL", PlayerStatus.AVAILABLE),
                ("Jayson Tatum", "BOS", PlayerStatus.AVAILABLE),
            ],
        )
        current = make_snapshot(
            players=[
                ("LeBron James", "LAL", PlayerStatus.OUT),
                ("Jayson Tatum", "BOS", PlayerStatus.OUT),
            ],
        )

        # Only filter for LeBron
        delta = detect_delta(
            previous, current,
            player_names=["LeBron James"],
        )

        assert len(delta.player_changes) == 1
        assert delta.player_changes[0].player_name == "LeBron James"

    def test_team_filter(self):
        previous = make_snapshot(
            players=[
                ("LeBron James", "LAL", PlayerStatus.AVAILABLE),
                ("Anthony Davis", "LAL", PlayerStatus.AVAILABLE),
                ("Jayson Tatum", "BOS", PlayerStatus.AVAILABLE),
            ],
        )
        current = make_snapshot(
            players=[
                ("LeBron James", "LAL", PlayerStatus.OUT),
                ("Anthony Davis", "LAL", PlayerStatus.OUT),
                ("Jayson Tatum", "BOS", PlayerStatus.OUT),
            ],
        )

        # Only filter for LAL
        delta = detect_delta(
            previous, current,
            team_names=["LAL"],
        )

        assert len(delta.player_changes) == 2


class TestDetectDeltaConfidence:
    """Test confidence change detection."""

    def test_confidence_dropped(self):
        previous = make_snapshot(confidence=0.5)
        current = make_snapshot(confidence=-0.3)

        delta = detect_delta(previous, current)

        assert delta.confidence_change is not None
        assert delta.confidence_change.is_dropped is True
        assert delta.confidence_change.drop_amount == 0.8

    def test_confidence_improved(self):
        previous = make_snapshot(confidence=-0.3)
        current = make_snapshot(confidence=0.5)

        delta = detect_delta(previous, current)

        assert delta.confidence_change is not None
        assert delta.confidence_change.is_dropped is False


class TestDetectDeltaSource:
    """Test source change detection."""

    def test_source_degraded(self):
        previous = make_snapshot(source="nba-official")
        current = make_snapshot(source="sample-fallback")

        delta = detect_delta(previous, current)

        assert delta.source_change is not None
        assert delta.source_change.is_degraded is True

    def test_source_unreachable(self):
        previous = make_snapshot(source="nba-official")
        current = make_snapshot(source="error-fallback")

        delta = detect_delta(previous, current)

        assert delta.source_change is not None
        assert delta.source_change.is_unreachable is True

    def test_source_improved(self):
        previous = make_snapshot(source="sample-fallback")
        current = make_snapshot(source="nba-official")

        delta = detect_delta(previous, current)

        assert delta.source_change is not None
        assert delta.source_change.is_degraded is False
        assert delta.source_change.is_unreachable is False
