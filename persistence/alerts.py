# persistence/alerts.py
"""
Persistent alert storage.

Supplements the in-memory alert store with SQLite persistence.
Alerts survive server restarts.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from persistence.db import get_db, init_db

_logger = logging.getLogger(__name__)

# Default alert retention (24 hours)
DEFAULT_ALERT_HOURS = 24


def save_alert(
    alert_id: UUID,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    player_name: Optional[str] = None,
    team: Optional[str] = None,
    previous_value: Optional[str] = None,
    current_value: Optional[str] = None,
    correlation_id: Optional[str] = None,
    source: str = "nba-availability",
    sport: str = "NBA",
    created_at: Optional[datetime] = None,
    retention_hours: int = DEFAULT_ALERT_HOURS,
) -> None:
    """
    Save an alert to persistent storage.

    Called by the AlertService after generating an alert.
    """
    init_db()

    if created_at is None:
        created_at = datetime.utcnow()
    expires_at = created_at + timedelta(hours=retention_hours)

    with get_db() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO alerts
            (id, alert_type, severity, title, message, player_name, team,
             previous_value, current_value, created_at, correlation_id,
             source, sport, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(alert_id),
                alert_type,
                severity,
                title,
                message,
                player_name,
                team,
                previous_value,
                current_value,
                created_at.isoformat(),
                correlation_id,
                source,
                sport,
                expires_at.isoformat(),
            ),
        )


def get_alert(alert_id: str) -> Optional[dict]:
    """Get a specific alert by ID."""
    init_db()

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM alerts
            WHERE id = ? AND (expires_at IS NULL OR expires_at > ?)
            """,
            (alert_id, datetime.utcnow().isoformat()),
        ).fetchone()

    if row is None:
        return None

    return _row_to_dict(row)


def get_recent_alerts(limit: int = 50) -> list[dict]:
    """Get most recent alerts."""
    init_db()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM alerts
            WHERE expires_at IS NULL OR expires_at > ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (datetime.utcnow().isoformat(), limit),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_alerts_by_correlation(correlation_id: str, limit: int = 50) -> list[dict]:
    """Get alerts for a correlation ID."""
    init_db()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM alerts
            WHERE correlation_id = ?
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (correlation_id, datetime.utcnow().isoformat(), limit),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_alerts_by_player(player_name: str, limit: int = 50) -> list[dict]:
    """Get alerts for a player (case-insensitive)."""
    init_db()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM alerts
            WHERE LOWER(player_name) = LOWER(?)
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (player_name, datetime.utcnow().isoformat(), limit),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_alerts_by_team(team: str, limit: int = 50) -> list[dict]:
    """Get alerts for a team."""
    init_db()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM alerts
            WHERE UPPER(team) = UPPER(?)
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (team, datetime.utcnow().isoformat(), limit),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_alert_count() -> int:
    """Get count of active alerts."""
    init_db()

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) as count FROM alerts
            WHERE expires_at IS NULL OR expires_at > ?
            """,
            (datetime.utcnow().isoformat(),),
        ).fetchone()

    return row["count"] if row else 0


def get_alert_counts_by_type() -> dict[str, int]:
    """Get alert counts grouped by type (for metrics)."""
    init_db()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT alert_type, COUNT(*) as count FROM alerts
            WHERE expires_at IS NULL OR expires_at > ?
            GROUP BY alert_type
            """,
            (datetime.utcnow().isoformat(),),
        ).fetchall()

    return {row["alert_type"]: row["count"] for row in rows}


def get_alert_counts_by_severity() -> dict[str, int]:
    """Get alert counts grouped by severity (for metrics)."""
    init_db()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT severity, COUNT(*) as count FROM alerts
            WHERE expires_at IS NULL OR expires_at > ?
            GROUP BY severity
            """,
            (datetime.utcnow().isoformat(),),
        ).fetchall()

    return {row["severity"]: row["count"] for row in rows}


def cleanup_expired() -> int:
    """Remove expired alerts."""
    init_db()

    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM alerts WHERE expires_at < ?",
            (datetime.utcnow().isoformat(),),
        )
        count = cursor.rowcount

    if count > 0:
        _logger.info(f"Cleaned up {count} expired alerts")

    return count


def clear_all() -> int:
    """Clear all alerts (for testing/admin)."""
    init_db()

    with get_db() as conn:
        cursor = conn.execute("DELETE FROM alerts")
        return cursor.rowcount


def _row_to_dict(row) -> dict:
    """Convert database row to dict matching Alert.to_dict() format."""
    return {
        "alert_id": row["id"],
        "alert_type": row["alert_type"],
        "severity": row["severity"],
        "title": row["title"],
        "message": row["message"],
        "player_name": row["player_name"],
        "team": row["team"],
        "previous_value": row["previous_value"],
        "current_value": row["current_value"],
        "created_at": row["created_at"],
        "correlation_id": row["correlation_id"],
        "source": row["source"],
        "sport": row["sport"],
    }
