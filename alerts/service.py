# alerts/service.py
"""
Alert service - main entry point for alert operations.

Coordinates:
- Snapshot tracking (previous state)
- Delta detection
- Alert generation
- Alert storage (in-memory + persistent)

Sprint 5: Added persistence layer integration.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

from alerts.models import Alert
from alerts.store import AlertStore, get_alert_store
from alerts.detector import detect_delta, SnapshotDelta
from alerts.triggers import generate_alerts_from_delta
from context.snapshot import ContextSnapshot


_logger = logging.getLogger(__name__)

# Enable/disable persistence (for testing)
PERSISTENCE_ENABLED = os.environ.get("DNA_PERSISTENCE", "true").lower() == "true"


class AlertService:
    """
    Main service for alert operations.

    Tracks previous snapshots per sport to detect changes.
    Generates and stores alerts when changes are detected.

    Sprint 5: Uses both in-memory store (fast) and SQLite persistence (durable).
    """

    def __init__(
        self,
        store: Optional[AlertStore] = None,
        enable_persistence: bool = PERSISTENCE_ENABLED,
    ):
        """
        Initialize alert service.

        Args:
            store: Alert store (uses singleton if not provided)
            enable_persistence: Whether to persist to SQLite
        """
        self._store = store or get_alert_store()
        self._previous_snapshots: dict[str, ContextSnapshot] = {}
        self._lock = threading.RLock()
        self._persist = enable_persistence

    def check_snapshot(
        self,
        snapshot: ContextSnapshot,
        player_names: Optional[list[str]] = None,
        team_names: Optional[list[str]] = None,
        correlation_id: Optional[str] = None,
    ) -> list[Alert]:
        """
        Check a snapshot for changes and generate alerts.

        Args:
            snapshot: Current context snapshot
            player_names: Optional filter for specific players
            team_names: Optional filter for specific teams
            correlation_id: Optional ID to link alerts to session

        Returns:
            List of newly generated alerts
        """
        sport = snapshot.sport.upper()

        with self._lock:
            # Get previous snapshot for this sport
            previous = self._previous_snapshots.get(sport)

            # Detect changes
            delta = detect_delta(
                previous=previous,
                current=snapshot,
                player_names=player_names,
                team_names=team_names,
            )

            # Generate alerts
            alerts = generate_alerts_from_delta(delta, correlation_id)

            # Store alerts (in-memory)
            for alert in alerts:
                self._store.add(alert)

            # Persist alerts (Sprint 5)
            if self._persist and alerts:
                self._persist_alerts(alerts)

            # Update previous snapshot
            self._previous_snapshots[sport] = snapshot

            if alerts:
                _logger.info(
                    f"Generated {len(alerts)} alert(s) for {sport}",
                    extra={"correlation_id": correlation_id},
                )

            return alerts

    def _persist_alerts(self, alerts: list[Alert]) -> None:
        """Persist alerts to SQLite (Sprint 5)."""
        try:
            from persistence.alerts import save_alert
            from persistence.metrics import record_alert_generated

            for alert in alerts:
                save_alert(
                    alert_id=alert.alert_id,
                    alert_type=alert.alert_type.value,
                    severity=alert.severity.value,
                    title=alert.title,
                    message=alert.message,
                    player_name=alert.player_name,
                    team=alert.team,
                    previous_value=alert.previous_value,
                    current_value=alert.current_value,
                    correlation_id=alert.correlation_id,
                    source=alert.source,
                    sport=alert.sport,
                    created_at=alert.created_at,
                )
                # Record metric
                record_alert_generated(alert.alert_type.value, alert.severity.value)

        except Exception as e:
            # Don't fail the alert generation if persistence fails
            _logger.warning(f"Failed to persist alerts: {e}")

    def get_alerts(
        self,
        correlation_id: Optional[str] = None,
        player_name: Optional[str] = None,
        team: Optional[str] = None,
        limit: int = 50,
    ) -> list[Alert]:
        """
        Get alerts with optional filtering.

        Args:
            correlation_id: Filter by session/evaluation ID
            player_name: Filter by player
            team: Filter by team
            limit: Maximum alerts to return

        Returns:
            List of alerts, newest first
        """
        if correlation_id:
            return self._store.get_by_correlation(correlation_id)[:limit]
        elif player_name:
            return self._store.get_by_player(player_name)[:limit]
        elif team:
            return self._store.get_by_team(team)[:limit]
        else:
            return self._store.get_recent(limit)

    def get_recent_alerts(self, limit: int = 50) -> list[Alert]:
        """Get most recent alerts."""
        return self._store.get_recent(limit)

    def get_alert_count(self) -> int:
        """Get total active alert count."""
        return self._store.count()

    def clear_alerts(self) -> None:
        """Clear all alerts (for testing/admin)."""
        self._store.clear()

    def reset_snapshots(self) -> None:
        """Reset snapshot tracking (for testing)."""
        with self._lock:
            self._previous_snapshots.clear()

    def get_delta(
        self,
        snapshot: ContextSnapshot,
        player_names: Optional[list[str]] = None,
        team_names: Optional[list[str]] = None,
    ) -> SnapshotDelta:
        """
        Get delta without generating alerts (for inspection).

        Useful for debugging or preview.
        """
        sport = snapshot.sport.upper()
        with self._lock:
            previous = self._previous_snapshots.get(sport)
            return detect_delta(
                previous=previous,
                current=snapshot,
                player_names=player_names,
                team_names=team_names,
            )


# Module-level singleton
_service: Optional[AlertService] = None
_service_lock = threading.Lock()


def get_alert_service() -> AlertService:
    """Get the singleton alert service."""
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = AlertService()
    return _service


def reset_alert_service() -> None:
    """Reset the singleton service (for testing)."""
    global _service
    with _service_lock:
        if _service:
            _service.clear_alerts()
            _service.reset_snapshots()
        _service = None


def check_for_alerts(
    snapshot: ContextSnapshot,
    player_names: Optional[list[str]] = None,
    team_names: Optional[list[str]] = None,
    correlation_id: Optional[str] = None,
) -> list[Alert]:
    """
    Convenience function to check for alerts.

    This is the main entry point for the pipeline integration.
    """
    service = get_alert_service()
    return service.check_snapshot(
        snapshot=snapshot,
        player_names=player_names,
        team_names=team_names,
        correlation_id=correlation_id,
    )
