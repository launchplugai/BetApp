# alerts/triggers.py
"""
Trigger rules for converting deltas to alerts.

Sprint 4 triggers:
1. Player status worsens to OUT/DOUBTFUL/QUESTIONABLE → alert
2. Confidence drops below threshold → alert
3. Source unreachable persists → alert
"""

from __future__ import annotations

from typing import Optional

from alerts.models import (
    Alert,
    create_player_status_alert,
    create_confidence_alert,
    create_source_alert,
)
from alerts.detector import SnapshotDelta, PlayerDelta
from context.snapshot import PlayerStatus


# Confidence threshold for alerts
CONFIDENCE_ALERT_THRESHOLD = -0.2  # Alert if drops below this


def should_alert_player_change(delta: PlayerDelta) -> bool:
    """
    Determine if a player status change warrants an alert.

    Rules:
    - Only alert on worsening status
    - Only alert for significant statuses (OUT, DOUBTFUL, QUESTIONABLE)
    """
    if not delta.is_worsened:
        return False

    # Alert for these target statuses
    alertable_statuses = {
        PlayerStatus.OUT,
        PlayerStatus.DOUBTFUL,
        PlayerStatus.QUESTIONABLE,
    }

    return delta.current_status in alertable_statuses


def should_alert_confidence_drop(
    previous: float,
    current: float,
    threshold: float = CONFIDENCE_ALERT_THRESHOLD,
) -> bool:
    """
    Determine if confidence drop warrants an alert.

    Rules:
    - Alert if dropped AND current is below threshold
    - Don't alert for minor fluctuations
    """
    dropped = current < previous
    below_threshold = current < threshold
    significant_drop = (previous - current) >= 0.2  # At least 0.2 drop

    return dropped and (below_threshold or significant_drop)


def generate_alerts_from_delta(
    delta: SnapshotDelta,
    correlation_id: Optional[str] = None,
) -> list[Alert]:
    """
    Generate alerts from a snapshot delta.

    Applies all trigger rules and returns resulting alerts.
    """
    alerts: list[Alert] = []

    # Rule 1: Player status worsened
    for player_delta in delta.player_changes:
        if should_alert_player_change(player_delta):
            alert = create_player_status_alert(
                player_name=player_delta.player_name,
                team=player_delta.team,
                previous_status=player_delta.previous_status.value,
                current_status=player_delta.current_status.value,
                correlation_id=correlation_id,
            )
            alerts.append(alert)

    # Rule 2: Confidence dropped
    if delta.confidence_change and delta.confidence_change.is_dropped:
        if should_alert_confidence_drop(
            delta.confidence_change.previous_confidence,
            delta.confidence_change.current_confidence,
        ):
            alert = create_confidence_alert(
                previous_confidence=delta.confidence_change.previous_confidence,
                current_confidence=delta.confidence_change.current_confidence,
                reason=delta.confidence_change.reason,
                correlation_id=correlation_id,
            )
            alerts.append(alert)

    # Rule 3: Source unreachable/degraded
    if delta.source_change:
        if delta.source_change.is_unreachable:
            alert = create_source_alert(
                source_name=delta.source_change.current_source,
                is_degraded=False,
                correlation_id=correlation_id,
            )
            alerts.append(alert)
        elif delta.source_change.is_degraded:
            alert = create_source_alert(
                source_name=delta.source_change.current_source,
                is_degraded=True,
                correlation_id=correlation_id,
            )
            alerts.append(alert)

    return alerts
