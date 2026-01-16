# alerts/models.py
"""
Alert data models for Sprint 4.

Defines the Alert schema and related enums.
All alerts must be traceable to snapshot deltas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class AlertType(Enum):
    """Types of alerts the system can generate."""

    # Player status changes
    PLAYER_STATUS_WORSENED = "player_status_worsened"
    PLAYER_NOW_OUT = "player_now_out"
    PLAYER_NOW_DOUBTFUL = "player_now_doubtful"
    PLAYER_NOW_QUESTIONABLE = "player_now_questionable"

    # Confidence changes
    CONFIDENCE_DROPPED = "confidence_dropped"

    # Source issues
    SOURCE_UNREACHABLE = "source_unreachable"
    SOURCE_DEGRADED = "source_degraded"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"           # FYI, no action needed
    WARNING = "warning"     # Worth noting, may affect bet
    CRITICAL = "critical"   # Significant impact, review recommended


@dataclass(frozen=True)
class Alert:
    """
    Immutable alert record.

    Each alert traces back to a specific change in context data.
    correlation_id links to the evaluation/session that triggered it.
    """

    # Unique identifier
    alert_id: UUID = field(default_factory=uuid4)

    # Type and severity
    alert_type: AlertType = AlertType.PLAYER_STATUS_WORSENED
    severity: AlertSeverity = AlertSeverity.WARNING

    # What changed
    title: str = ""
    message: str = ""

    # Affected entities
    player_name: Optional[str] = None
    team: Optional[str] = None

    # Change details (for traceability)
    previous_value: Optional[str] = None
    current_value: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Tracing
    correlation_id: Optional[str] = None  # Links to session/evaluation
    source: str = "nba-availability"      # Data source that triggered alert

    # Metadata
    sport: str = "NBA"

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for API responses."""
        return {
            "alert_id": str(self.alert_id),
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "player_name": self.player_name,
            "team": self.team,
            "previous_value": self.previous_value,
            "current_value": self.current_value,
            "created_at": self.created_at.isoformat(),
            "correlation_id": self.correlation_id,
            "source": self.source,
            "sport": self.sport,
        }


def create_player_status_alert(
    player_name: str,
    team: str,
    previous_status: str,
    current_status: str,
    correlation_id: Optional[str] = None,
) -> Alert:
    """
    Factory for player status change alerts.

    Maps status to appropriate alert type and severity.
    """
    # Determine alert type based on new status
    status_lower = current_status.lower()
    if status_lower == "out":
        alert_type = AlertType.PLAYER_NOW_OUT
        severity = AlertSeverity.CRITICAL
        title = f"{player_name} is OUT"
    elif status_lower == "doubtful":
        alert_type = AlertType.PLAYER_NOW_DOUBTFUL
        severity = AlertSeverity.CRITICAL
        title = f"{player_name} is DOUBTFUL"
    elif status_lower == "questionable":
        alert_type = AlertType.PLAYER_NOW_QUESTIONABLE
        severity = AlertSeverity.WARNING
        title = f"{player_name} is QUESTIONABLE"
    else:
        alert_type = AlertType.PLAYER_STATUS_WORSENED
        severity = AlertSeverity.INFO
        title = f"{player_name} status changed"

    message = f"Status changed from {previous_status.upper()} to {current_status.upper()}"

    return Alert(
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        player_name=player_name,
        team=team,
        previous_value=previous_status,
        current_value=current_status,
        correlation_id=correlation_id,
    )


def create_confidence_alert(
    previous_confidence: float,
    current_confidence: float,
    reason: str,
    correlation_id: Optional[str] = None,
) -> Alert:
    """Factory for confidence drop alerts."""
    severity = AlertSeverity.CRITICAL if current_confidence < -0.3 else AlertSeverity.WARNING

    return Alert(
        alert_type=AlertType.CONFIDENCE_DROPPED,
        severity=severity,
        title="Data confidence dropped",
        message=reason,
        previous_value=f"{previous_confidence:.2f}",
        current_value=f"{current_confidence:.2f}",
        correlation_id=correlation_id,
    )


def create_source_alert(
    source_name: str,
    is_degraded: bool = False,
    correlation_id: Optional[str] = None,
) -> Alert:
    """Factory for source availability alerts."""
    if is_degraded:
        return Alert(
            alert_type=AlertType.SOURCE_DEGRADED,
            severity=AlertSeverity.WARNING,
            title="Data source degraded",
            message=f"{source_name} is returning partial data",
            source=source_name,
            correlation_id=correlation_id,
        )
    else:
        return Alert(
            alert_type=AlertType.SOURCE_UNREACHABLE,
            severity=AlertSeverity.CRITICAL,
            title="Data source unreachable",
            message=f"{source_name} is unavailable, using fallback data",
            source=source_name,
            correlation_id=correlation_id,
        )
