# persistence/metrics.py
"""
Metrics and observability storage.

Records metrics for:
- Provider health (nba-official vs espn fallback rates)
- Alert generation counts
- Cache hit rates
- Evaluation latency
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from persistence.db import get_db, init_db

_logger = logging.getLogger(__name__)

# Metric names
METRIC_PROVIDER_SUCCESS = "provider.success"
METRIC_PROVIDER_FALLBACK = "provider.fallback"
METRIC_PROVIDER_ERROR = "provider.error"
METRIC_CACHE_HIT = "cache.hit"
METRIC_CACHE_MISS = "cache.miss"
METRIC_ALERT_GENERATED = "alert.generated"
METRIC_EVALUATION_LATENCY = "evaluation.latency_ms"
METRIC_SHARE_CREATED = "share.created"
METRIC_SHARE_VIEWED = "share.viewed"


def record_metric(
    metric_name: str,
    value: float = 1.0,
    labels: Optional[dict] = None,
) -> None:
    """
    Record a metric data point.

    Args:
        metric_name: Name of the metric (use constants above)
        value: Numeric value (default 1.0 for counters)
        labels: Optional labels/tags as dict
    """
    init_db()

    recorded_at = datetime.utcnow()
    labels_json = json.dumps(labels) if labels else None

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO metrics (metric_name, metric_value, labels_json, recorded_at)
            VALUES (?, ?, ?, ?)
            """,
            (metric_name, value, labels_json, recorded_at.isoformat()),
        )


def record_counter(metric_name: str, labels: Optional[dict] = None) -> None:
    """Record a counter increment (value=1)."""
    record_metric(metric_name, 1.0, labels)


def record_provider_result(source: str, success: bool = True) -> None:
    """Record a context provider fetch result."""
    if success:
        if source in ("nba-official", "espn-injuries"):
            record_counter(METRIC_PROVIDER_SUCCESS, {"source": source})
        else:
            record_counter(METRIC_PROVIDER_FALLBACK, {"source": source})
    else:
        record_counter(METRIC_PROVIDER_ERROR, {"source": source})


def record_cache_result(hit: bool, cache_name: str = "context") -> None:
    """Record a cache hit/miss."""
    if hit:
        record_counter(METRIC_CACHE_HIT, {"cache": cache_name})
    else:
        record_counter(METRIC_CACHE_MISS, {"cache": cache_name})


def record_alert_generated(alert_type: str, severity: str) -> None:
    """Record an alert generation."""
    record_counter(METRIC_ALERT_GENERATED, {"type": alert_type, "severity": severity})


def record_evaluation_latency(latency_ms: float, tier: str) -> None:
    """Record evaluation latency."""
    record_metric(METRIC_EVALUATION_LATENCY, latency_ms, {"tier": tier})


def get_metric_count(
    metric_name: str,
    since: Optional[datetime] = None,
    labels: Optional[dict] = None,
) -> int:
    """
    Get count of metric occurrences.

    Args:
        metric_name: Name of the metric
        since: Only count after this time (default: last 24 hours)
        labels: Optional label filter (exact match)
    """
    init_db()

    if since is None:
        since = datetime.utcnow() - timedelta(hours=24)

    with get_db() as conn:
        if labels:
            # Filter by labels (exact JSON match - simple but works)
            row = conn.execute(
                """
                SELECT COUNT(*) as count FROM metrics
                WHERE metric_name = ? AND recorded_at > ? AND labels_json = ?
                """,
                (metric_name, since.isoformat(), json.dumps(labels)),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT COUNT(*) as count FROM metrics
                WHERE metric_name = ? AND recorded_at > ?
                """,
                (metric_name, since.isoformat()),
            ).fetchone()

    return row["count"] if row else 0


def get_metric_sum(
    metric_name: str,
    since: Optional[datetime] = None,
) -> float:
    """Get sum of metric values."""
    init_db()

    if since is None:
        since = datetime.utcnow() - timedelta(hours=24)

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT SUM(metric_value) as total FROM metrics
            WHERE metric_name = ? AND recorded_at > ?
            """,
            (metric_name, since.isoformat()),
        ).fetchone()

    return row["total"] if row and row["total"] else 0.0


def get_metric_average(
    metric_name: str,
    since: Optional[datetime] = None,
) -> Optional[float]:
    """Get average of metric values."""
    init_db()

    if since is None:
        since = datetime.utcnow() - timedelta(hours=24)

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT AVG(metric_value) as avg FROM metrics
            WHERE metric_name = ? AND recorded_at > ?
            """,
            (metric_name, since.isoformat()),
        ).fetchone()

    return row["avg"] if row and row["avg"] is not None else None


def get_provider_health_summary(since_hours: int = 24) -> dict:
    """
    Get provider health summary.

    Returns:
        Dict with success/fallback/error counts and rates
    """
    since = datetime.utcnow() - timedelta(hours=since_hours)

    success = get_metric_count(METRIC_PROVIDER_SUCCESS, since)
    fallback = get_metric_count(METRIC_PROVIDER_FALLBACK, since)
    error = get_metric_count(METRIC_PROVIDER_ERROR, since)

    total = success + fallback + error

    return {
        "success_count": success,
        "fallback_count": fallback,
        "error_count": error,
        "total_requests": total,
        "success_rate": success / total if total > 0 else 1.0,
        "fallback_rate": fallback / total if total > 0 else 0.0,
        "error_rate": error / total if total > 0 else 0.0,
        "period_hours": since_hours,
    }


def get_cache_hit_rate(since_hours: int = 24, cache_name: str = "context") -> float:
    """Get cache hit rate."""
    since = datetime.utcnow() - timedelta(hours=since_hours)

    hits = get_metric_count(METRIC_CACHE_HIT, since, {"cache": cache_name})
    misses = get_metric_count(METRIC_CACHE_MISS, since, {"cache": cache_name})

    total = hits + misses
    return hits / total if total > 0 else 0.0


def get_alert_summary(since_hours: int = 24) -> dict:
    """Get alert generation summary."""
    since = datetime.utcnow() - timedelta(hours=since_hours)

    total = get_metric_count(METRIC_ALERT_GENERATED, since)

    # Get breakdown by type (simplified - would need more complex query for full breakdown)
    return {
        "total_generated": total,
        "period_hours": since_hours,
    }


def cleanup_old_metrics(retention_days: int = 7) -> int:
    """Remove old metrics."""
    init_db()

    cutoff = datetime.utcnow() - timedelta(days=retention_days)

    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM metrics WHERE recorded_at < ?",
            (cutoff.isoformat(),),
        )
        count = cursor.rowcount

    if count > 0:
        _logger.info(f"Cleaned up {count} old metrics")

    return count
