# alerts/tests/test_models.py
"""Tests for alert models."""

import pytest
from datetime import datetime

from alerts.models import (
    Alert,
    AlertType,
    AlertSeverity,
    create_player_status_alert,
    create_confidence_alert,
    create_source_alert,
)


class TestAlertType:
    """Test AlertType enum."""

    def test_player_status_types(self):
        assert AlertType.PLAYER_STATUS_WORSENED
        assert AlertType.PLAYER_NOW_OUT
        assert AlertType.PLAYER_NOW_DOUBTFUL
        assert AlertType.PLAYER_NOW_QUESTIONABLE

    def test_confidence_type(self):
        assert AlertType.CONFIDENCE_DROPPED

    def test_source_types(self):
        assert AlertType.SOURCE_UNREACHABLE
        assert AlertType.SOURCE_DEGRADED


class TestAlertSeverity:
    """Test AlertSeverity enum."""

    def test_all_severities(self):
        assert AlertSeverity.INFO
        assert AlertSeverity.WARNING
        assert AlertSeverity.CRITICAL


class TestAlert:
    """Test Alert dataclass."""

    def test_create_basic_alert(self):
        alert = Alert(
            alert_type=AlertType.PLAYER_NOW_OUT,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
        )
        assert alert.alert_id is not None
        assert alert.alert_type == AlertType.PLAYER_NOW_OUT
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.title == "Test Alert"

    def test_alert_is_frozen(self):
        alert = Alert()
        with pytest.raises(Exception):
            alert.title = "New Title"

    def test_to_dict(self):
        alert = Alert(
            alert_type=AlertType.PLAYER_NOW_OUT,
            severity=AlertSeverity.CRITICAL,
            title="LeBron is OUT",
            message="Status changed from PROBABLE to OUT",
            player_name="LeBron James",
            team="LAL",
            previous_value="probable",
            current_value="out",
            correlation_id="test-123",
        )
        d = alert.to_dict()

        assert d["alert_type"] == "player_now_out"
        assert d["severity"] == "critical"
        assert d["title"] == "LeBron is OUT"
        assert d["player_name"] == "LeBron James"
        assert d["team"] == "LAL"
        assert d["correlation_id"] == "test-123"
        assert "alert_id" in d
        assert "created_at" in d


class TestCreatePlayerStatusAlert:
    """Test player status alert factory."""

    def test_create_out_alert(self):
        alert = create_player_status_alert(
            player_name="LeBron James",
            team="LAL",
            previous_status="probable",
            current_status="out",
        )
        assert alert.alert_type == AlertType.PLAYER_NOW_OUT
        assert alert.severity == AlertSeverity.CRITICAL
        assert "LeBron James" in alert.title
        assert "OUT" in alert.title

    def test_create_doubtful_alert(self):
        alert = create_player_status_alert(
            player_name="Anthony Davis",
            team="LAL",
            previous_status="questionable",
            current_status="doubtful",
        )
        assert alert.alert_type == AlertType.PLAYER_NOW_DOUBTFUL
        assert alert.severity == AlertSeverity.CRITICAL

    def test_create_questionable_alert(self):
        alert = create_player_status_alert(
            player_name="Jayson Tatum",
            team="BOS",
            previous_status="available",
            current_status="questionable",
        )
        assert alert.alert_type == AlertType.PLAYER_NOW_QUESTIONABLE
        assert alert.severity == AlertSeverity.WARNING

    def test_includes_correlation_id(self):
        alert = create_player_status_alert(
            player_name="Test Player",
            team="TST",
            previous_status="available",
            current_status="out",
            correlation_id="session-abc",
        )
        assert alert.correlation_id == "session-abc"


class TestCreateConfidenceAlert:
    """Test confidence alert factory."""

    def test_create_confidence_alert(self):
        alert = create_confidence_alert(
            previous_confidence=0.5,
            current_confidence=-0.3,
            reason="Data source degraded",
        )
        assert alert.alert_type == AlertType.CONFIDENCE_DROPPED
        assert "confidence" in alert.title.lower()
        assert alert.previous_value == "0.50"
        assert alert.current_value == "-0.30"

    def test_critical_for_low_confidence(self):
        alert = create_confidence_alert(
            previous_confidence=0.5,
            current_confidence=-0.5,
            reason="Source failed",
        )
        assert alert.severity == AlertSeverity.CRITICAL

    def test_warning_for_moderate_drop(self):
        alert = create_confidence_alert(
            previous_confidence=0.5,
            current_confidence=0.0,
            reason="Some degradation",
        )
        assert alert.severity == AlertSeverity.WARNING


class TestCreateSourceAlert:
    """Test source alert factory."""

    def test_create_unreachable_alert(self):
        alert = create_source_alert(
            source_name="nba-official",
            is_degraded=False,
        )
        assert alert.alert_type == AlertType.SOURCE_UNREACHABLE
        assert alert.severity == AlertSeverity.CRITICAL
        assert "unreachable" in alert.title.lower()

    def test_create_degraded_alert(self):
        alert = create_source_alert(
            source_name="espn-injuries",
            is_degraded=True,
        )
        assert alert.alert_type == AlertType.SOURCE_DEGRADED
        assert alert.severity == AlertSeverity.WARNING
        assert "degraded" in alert.title.lower()
