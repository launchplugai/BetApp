# persistence/evaluations.py
"""
Evaluation result storage.

Stores evaluation results for:
- Shareable links
- History/audit
- Session continuity
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from persistence.db import get_db, init_db

_logger = logging.getLogger(__name__)

# Default retention period (7 days)
DEFAULT_RETENTION_DAYS = 7


def save_evaluation(
    parlay_id: str,
    tier: str,
    input_text: str,
    result: dict,
    correlation_id: Optional[str] = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    user_id: Optional[str] = None,
) -> str:
    """
    Save an evaluation result.

    Args:
        parlay_id: The parlay ID from evaluation
        tier: User tier (good/better/best)
        input_text: Original bet text
        result: Full evaluation result dict
        correlation_id: Optional session/request ID
        retention_days: How long to keep (default 7 days)
        user_id: Optional user ID (for logged-in users)

    Returns:
        Evaluation ID for retrieval
    """
    init_db()

    eval_id = str(uuid4())
    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(days=retention_days)

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO evaluations
            (id, parlay_id, created_at, tier, input_text, result_json, correlation_id, expires_at, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eval_id,
                parlay_id,
                created_at.isoformat(),
                tier.lower(),
                input_text,
                json.dumps(result),
                correlation_id,
                expires_at.isoformat(),
                user_id,
            ),
        )

    _logger.debug(f"Saved evaluation {eval_id} for parlay {parlay_id}")
    return eval_id


def get_evaluation(eval_id: str) -> Optional[dict]:
    """
    Get an evaluation by ID.

    Returns None if not found or expired.
    """
    init_db()

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM evaluations
            WHERE id = ? AND (expires_at IS NULL OR expires_at > ?)
            """,
            (eval_id, datetime.utcnow().isoformat()),
        ).fetchone()

    if row is None:
        return None

    return _row_to_dict(row)


def get_evaluation_by_parlay(parlay_id: str) -> Optional[dict]:
    """Get the most recent evaluation for a parlay ID."""
    init_db()

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM evaluations
            WHERE parlay_id = ? AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (parlay_id, datetime.utcnow().isoformat()),
        ).fetchone()

    if row is None:
        return None

    return _row_to_dict(row)


def get_evaluation_by_token(token: str) -> Optional[dict]:
    """
    Get an evaluation by share token.

    Also increments view count on the share.
    """
    init_db()

    with get_db() as conn:
        # Get share and evaluation in one query
        row = conn.execute(
            """
            SELECT e.*, s.token, s.view_count
            FROM shares s
            JOIN evaluations e ON s.evaluation_id = e.id
            WHERE s.token = ?
            AND (s.expires_at IS NULL OR s.expires_at > ?)
            AND (e.expires_at IS NULL OR e.expires_at > ?)
            """,
            (token, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()),
        ).fetchone()

        if row is None:
            return None

        # Increment view count
        conn.execute(
            "UPDATE shares SET view_count = view_count + 1 WHERE token = ?",
            (token,),
        )

    result = _row_to_dict(row)
    result["share_token"] = row["token"]
    result["view_count"] = row["view_count"] + 1  # Include the current view
    return result


def get_evaluations_by_correlation(
    correlation_id: str,
    limit: int = 50,
) -> list[dict]:
    """Get evaluations for a correlation ID (session)."""
    init_db()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM evaluations
            WHERE correlation_id = ?
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (correlation_id, datetime.utcnow().isoformat(), limit),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def get_evaluations_by_user(
    user_id: str,
    limit: int = 50,
) -> list[dict]:
    """Get evaluations for a user (saved history)."""
    init_db()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM evaluations
            WHERE user_id = ?
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, datetime.utcnow().isoformat(), limit),
        ).fetchall()

    return [_row_to_dict(row) for row in rows]


def cleanup_expired() -> int:
    """
    Remove expired evaluations.

    Returns count of removed records.
    """
    init_db()

    with get_db() as conn:
        # First delete shares referencing expired evaluations
        conn.execute(
            """
            DELETE FROM shares
            WHERE evaluation_id IN (
                SELECT id FROM evaluations WHERE expires_at < ?
            )
            """,
            (datetime.utcnow().isoformat(),),
        )

        # Then delete expired evaluations
        cursor = conn.execute(
            "DELETE FROM evaluations WHERE expires_at < ?",
            (datetime.utcnow().isoformat(),),
        )
        count = cursor.rowcount

    if count > 0:
        _logger.info(f"Cleaned up {count} expired evaluations")

    return count


def _row_to_dict(row) -> dict:
    """Convert a database row to a dict."""
    return {
        "id": row["id"],
        "parlay_id": row["parlay_id"],
        "created_at": row["created_at"],
        "tier": row["tier"],
        "input_text": row["input_text"],
        "result": json.loads(row["result_json"]),
        "correlation_id": row["correlation_id"],
        "expires_at": row["expires_at"],
        "user_id": row["user_id"] if "user_id" in row.keys() else None,
    }
