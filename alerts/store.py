# alerts/store.py
"""
In-memory alert storage for Sprint 4.

Simple store with:
- TTL-based expiry (alerts don't live forever)
- Correlation ID indexing for traceability
- Thread-safe operations
"""

from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from alerts.models import Alert


class AlertStore:
    """
    In-memory alert storage with TTL and indexing.

    Thread-safe for concurrent access.
    Alerts expire after configured TTL (default 1 hour).
    """

    def __init__(self, ttl_seconds: int = 3600, max_alerts: int = 1000):
        """
        Initialize alert store.

        Args:
            ttl_seconds: How long alerts live (default 1 hour)
            max_alerts: Maximum alerts to keep (FIFO eviction)
        """
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_alerts = max_alerts
        self._lock = threading.RLock()

        # Primary storage: alert_id -> Alert
        self._alerts: dict[UUID, Alert] = {}

        # Indexes for fast lookup
        self._by_correlation: dict[str, list[UUID]] = defaultdict(list)
        self._by_player: dict[str, list[UUID]] = defaultdict(list)
        self._by_team: dict[str, list[UUID]] = defaultdict(list)

        # Insertion order for FIFO eviction
        self._order: list[UUID] = []

    def add(self, alert: Alert) -> None:
        """Add an alert to the store."""
        with self._lock:
            # Evict oldest if at capacity
            while len(self._alerts) >= self._max_alerts:
                self._evict_oldest()

            # Store alert
            self._alerts[alert.alert_id] = alert
            self._order.append(alert.alert_id)

            # Update indexes
            if alert.correlation_id:
                self._by_correlation[alert.correlation_id].append(alert.alert_id)
            if alert.player_name:
                self._by_player[alert.player_name.lower()].append(alert.alert_id)
            if alert.team:
                self._by_team[alert.team.upper()].append(alert.alert_id)

    def get(self, alert_id: UUID) -> Optional[Alert]:
        """Get a specific alert by ID."""
        with self._lock:
            alert = self._alerts.get(alert_id)
            if alert and self._is_expired(alert):
                self._remove(alert_id)
                return None
            return alert

    def get_by_correlation(self, correlation_id: str) -> list[Alert]:
        """Get all alerts for a correlation ID (session/evaluation)."""
        with self._lock:
            self._cleanup_expired()
            alert_ids = self._by_correlation.get(correlation_id, [])
            return [self._alerts[aid] for aid in alert_ids if aid in self._alerts]

    def get_by_player(self, player_name: str) -> list[Alert]:
        """Get all alerts for a player."""
        with self._lock:
            self._cleanup_expired()
            alert_ids = self._by_player.get(player_name.lower(), [])
            return [self._alerts[aid] for aid in alert_ids if aid in self._alerts]

    def get_by_team(self, team: str) -> list[Alert]:
        """Get all alerts for a team."""
        with self._lock:
            self._cleanup_expired()
            alert_ids = self._by_team.get(team.upper(), [])
            return [self._alerts[aid] for aid in alert_ids if aid in self._alerts]

    def get_recent(self, limit: int = 50) -> list[Alert]:
        """Get most recent alerts, newest first."""
        with self._lock:
            self._cleanup_expired()
            recent_ids = reversed(self._order[-limit:])
            return [self._alerts[aid] for aid in recent_ids if aid in self._alerts]

    def get_all(self) -> list[Alert]:
        """Get all non-expired alerts."""
        with self._lock:
            self._cleanup_expired()
            return list(self._alerts.values())

    def count(self) -> int:
        """Get count of active alerts."""
        with self._lock:
            self._cleanup_expired()
            return len(self._alerts)

    def clear(self) -> None:
        """Clear all alerts."""
        with self._lock:
            self._alerts.clear()
            self._by_correlation.clear()
            self._by_player.clear()
            self._by_team.clear()
            self._order.clear()

    def _is_expired(self, alert: Alert) -> bool:
        """Check if an alert has expired."""
        return datetime.utcnow() - alert.created_at > self._ttl

    def _evict_oldest(self) -> None:
        """Remove the oldest alert (FIFO)."""
        if self._order:
            oldest_id = self._order[0]
            self._remove(oldest_id)

    def _remove(self, alert_id: UUID) -> None:
        """Remove an alert and update indexes."""
        alert = self._alerts.pop(alert_id, None)
        if alert:
            # Remove from order
            if alert_id in self._order:
                self._order.remove(alert_id)

            # Remove from indexes
            if alert.correlation_id and alert_id in self._by_correlation.get(alert.correlation_id, []):
                self._by_correlation[alert.correlation_id].remove(alert_id)
            if alert.player_name and alert_id in self._by_player.get(alert.player_name.lower(), []):
                self._by_player[alert.player_name.lower()].remove(alert_id)
            if alert.team and alert_id in self._by_team.get(alert.team.upper(), []):
                self._by_team[alert.team.upper()].remove(alert_id)

    def _cleanup_expired(self) -> None:
        """Remove all expired alerts."""
        expired = [aid for aid, alert in self._alerts.items() if self._is_expired(alert)]
        for aid in expired:
            self._remove(aid)


# Module-level singleton
_store: Optional[AlertStore] = None
_store_lock = threading.Lock()


def get_alert_store() -> AlertStore:
    """Get the singleton alert store."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = AlertStore()
    return _store


def reset_alert_store() -> None:
    """Reset the singleton store (for testing)."""
    global _store
    with _store_lock:
        _store = None
