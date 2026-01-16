# alerts/tests/test_triggers.py
"""Tests for alert trigger rules."""

import pytest

from alerts.triggers import (
    should_alert_player_change,
    should_alert_confidence_drop,
    generate_alerts_from_delta,
    CONFIDENCE_ALERT_THRESHOLD,
)
from alerts.detector import PlayerDelta, ConfidenceDelta, SourceDelta, SnapshotDelta
from alerts.models import AlertType, AlertSeverity
from context.snapshot import PlayerStatus


class TestShouldAlertPlayerChange:
    """Test player change alert rules."""

    def test_alert_on_out(self):
        delta = PlayerDelta(
            player_name="Test",
            team="TST",
            previous_status=PlayerStatus.AVAILABLE,
            current_status=PlayerStatus.OUT,
        )
        assert should_alert_player_change(delta) is True

    def test_alert_on_doubtful(self):
        delta = PlayerDelta(
            player_name="Test",
            team="TST",
            previous_status=PlayerStatus.QUESTIONABLE,
            current_status=PlayerStatus.DOUBTFUL,
        )
        assert should_alert_player_change(delta) is True

    def test_alert_on_questionable(self):
        delta = PlayerDelta(
            player_name="Test",
            team="TST",
            previous_status=PlayerStatus.AVAILABLE,
            current_status=PlayerStatus.QUESTIONABLE,
        )
        assert should_alert_player_change(delta) is True

    def test_no_alert_on_improvement(self):
        delta = PlayerDelta(
            player_name="Test",
            team="TST",
            previous_status=PlayerStatus.OUT,
            current_status=PlayerStatus.AVAILABLE,
        )
        assert should_alert_player_change(delta) is False

    def test_no_alert_on_probable(self):
        # Probable is not concerning enough
        delta = PlayerDelta(
            player_name="Test",
            team="TST",
            previous_status=PlayerStatus.AVAILABLE,
            current_status=PlayerStatus.PROBABLE,
        )
        assert should_alert_player_change(delta) is False


class TestShouldAlertConfidenceDrop:
    """Test confidence drop alert rules."""

    def test_alert_below_threshold(self):
        assert should_alert_confidence_drop(0.5, -0.3) is True

    def test_alert_significant_drop(self):
        # Even above threshold, significant drop should alert
        assert should_alert_confidence_drop(0.5, 0.2) is True  # 0.3 drop

    def test_no_alert_minor_drop(self):
        assert should_alert_confidence_drop(0.5, 0.4) is False  # 0.1 drop

    def test_no_alert_on_improvement(self):
        assert should_alert_confidence_drop(-0.3, 0.5) is False


class TestGenerateAlertsFromDelta:
    """Test alert generation from deltas."""

    def test_generates_player_alerts(self):
        delta = SnapshotDelta(
            player_changes=(
                PlayerDelta("LeBron", "LAL", PlayerStatus.AVAILABLE, PlayerStatus.OUT),
                PlayerDelta("AD", "LAL", PlayerStatus.AVAILABLE, PlayerStatus.QUESTIONABLE),
            ),
            confidence_change=None,
            source_change=None,
        )

        alerts = generate_alerts_from_delta(delta)

        assert len(alerts) == 2
        assert alerts[0].alert_type == AlertType.PLAYER_NOW_OUT
        assert alerts[1].alert_type == AlertType.PLAYER_NOW_QUESTIONABLE

    def test_generates_confidence_alert(self):
        delta = SnapshotDelta(
            player_changes=(),
            confidence_change=ConfidenceDelta(0.5, -0.3, "Source degraded"),
            source_change=None,
        )

        alerts = generate_alerts_from_delta(delta)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.CONFIDENCE_DROPPED

    def test_generates_source_unreachable_alert(self):
        delta = SnapshotDelta(
            player_changes=(),
            confidence_change=None,
            source_change=SourceDelta(
                "nba-official", "error-fallback",
                is_degraded=False, is_unreachable=True,
                missing_data=(),
            ),
        )

        alerts = generate_alerts_from_delta(delta)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.SOURCE_UNREACHABLE

    def test_generates_source_degraded_alert(self):
        delta = SnapshotDelta(
            player_changes=(),
            confidence_change=None,
            source_change=SourceDelta(
                "nba-official", "sample-fallback",
                is_degraded=True, is_unreachable=False,
                missing_data=(),
            ),
        )

        alerts = generate_alerts_from_delta(delta)

        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.SOURCE_DEGRADED

    def test_correlation_id_propagated(self):
        delta = SnapshotDelta(
            player_changes=(
                PlayerDelta("Test", "TST", PlayerStatus.AVAILABLE, PlayerStatus.OUT),
            ),
            confidence_change=None,
            source_change=None,
        )

        alerts = generate_alerts_from_delta(delta, correlation_id="session-123")

        assert alerts[0].correlation_id == "session-123"

    def test_no_alerts_for_improvement(self):
        delta = SnapshotDelta(
            player_changes=(
                PlayerDelta("Test", "TST", PlayerStatus.OUT, PlayerStatus.AVAILABLE),
            ),
            confidence_change=ConfidenceDelta(-0.3, 0.5, "Improved"),
            source_change=None,
        )

        alerts = generate_alerts_from_delta(delta)

        assert len(alerts) == 0

    def test_multiple_alert_types(self):
        delta = SnapshotDelta(
            player_changes=(
                PlayerDelta("LeBron", "LAL", PlayerStatus.AVAILABLE, PlayerStatus.OUT),
            ),
            confidence_change=ConfidenceDelta(0.5, -0.3, "Source issue"),
            source_change=SourceDelta(
                "nba-official", "error-fallback",
                is_degraded=False, is_unreachable=True,
                missing_data=(),
            ),
        )

        alerts = generate_alerts_from_delta(delta)

        # Should get alerts for all three issues
        assert len(alerts) == 3
        alert_types = {a.alert_type for a in alerts}
        assert AlertType.PLAYER_NOW_OUT in alert_types
        assert AlertType.CONFIDENCE_DROPPED in alert_types
        assert AlertType.SOURCE_UNREACHABLE in alert_types
