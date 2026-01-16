# persistence/shares.py
"""
Share link management.

Generates short, shareable tokens for evaluation results.
Share pages are read-only and safe (no PII).
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional

from persistence.db import get_db, init_db

_logger = logging.getLogger(__name__)

# Token configuration
TOKEN_LENGTH = 8  # Short but collision-resistant enough
TOKEN_ALPHABET = string.ascii_lowercase + string.digits  # URL-safe

# Default share expiry (30 days)
DEFAULT_SHARE_DAYS = 30


def _generate_token() -> str:
    """Generate a random share token."""
    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(TOKEN_LENGTH))


def create_share(
    evaluation_id: str,
    expiry_days: int = DEFAULT_SHARE_DAYS,
    user_id: Optional[str] = None,
) -> Optional[str]:
    """
    Create a shareable link for an evaluation.

    Args:
        evaluation_id: The evaluation to share
        expiry_days: How long the share link is valid
        user_id: Optional user ID (for logged-in users)

    Returns:
        Share token, or None if evaluation not found
    """
    init_db()

    # Verify evaluation exists
    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM evaluations WHERE id = ?",
            (evaluation_id,),
        ).fetchone()

        if not exists:
            _logger.warning(f"Cannot create share: evaluation {evaluation_id} not found")
            return None

        # Check for existing share
        existing = conn.execute(
            """
            SELECT token FROM shares
            WHERE evaluation_id = ?
            AND (expires_at IS NULL OR expires_at > ?)
            """,
            (evaluation_id, datetime.utcnow().isoformat()),
        ).fetchone()

        if existing:
            return existing["token"]

        # Generate unique token
        for _ in range(10):  # Retry on collision
            token = _generate_token()
            try:
                created_at = datetime.utcnow()
                expires_at = created_at + timedelta(days=expiry_days)

                conn.execute(
                    """
                    INSERT INTO shares (token, evaluation_id, created_at, expires_at, user_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (token, evaluation_id, created_at.isoformat(), expires_at.isoformat(), user_id),
                )
                _logger.info(f"Created share {token} for evaluation {evaluation_id}")
                return token
            except Exception:
                continue  # Token collision, retry

    _logger.error("Failed to generate unique share token")
    return None


def get_share(token: str) -> Optional[dict]:
    """
    Get share metadata by token.

    Does NOT increment view count (use get_evaluation_by_token for that).
    """
    init_db()

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM shares
            WHERE token = ?
            AND (expires_at IS NULL OR expires_at > ?)
            """,
            (token, datetime.utcnow().isoformat()),
        ).fetchone()

    if row is None:
        return None

    return {
        "token": row["token"],
        "evaluation_id": row["evaluation_id"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
        "view_count": row["view_count"],
        "user_id": row["user_id"] if "user_id" in row.keys() else None,
    }


def delete_share(token: str) -> bool:
    """Delete a share link."""
    init_db()

    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM shares WHERE token = ?",
            (token,),
        )
        return cursor.rowcount > 0


def get_shares_for_evaluation(evaluation_id: str) -> list[dict]:
    """Get all shares for an evaluation."""
    init_db()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT * FROM shares
            WHERE evaluation_id = ?
            ORDER BY created_at DESC
            """,
            (evaluation_id,),
        ).fetchall()

    return [
        {
            "token": row["token"],
            "evaluation_id": row["evaluation_id"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "view_count": row["view_count"],
            "user_id": row["user_id"] if "user_id" in row.keys() else None,
        }
        for row in rows
    ]


def get_shares_by_user(user_id: str, limit: int = 50) -> list[dict]:
    """Get all shares created by a user."""
    init_db()

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT s.*, e.input_text, e.tier
            FROM shares s
            JOIN evaluations e ON s.evaluation_id = e.id
            WHERE s.user_id = ?
            AND (s.expires_at IS NULL OR s.expires_at > ?)
            ORDER BY s.created_at DESC
            LIMIT ?
            """,
            (user_id, datetime.utcnow().isoformat(), limit),
        ).fetchall()

    return [
        {
            "token": row["token"],
            "evaluation_id": row["evaluation_id"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "view_count": row["view_count"],
            "input_text": row["input_text"],
            "tier": row["tier"],
        }
        for row in rows
    ]


def cleanup_expired() -> int:
    """Remove expired shares."""
    init_db()

    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM shares WHERE expires_at < ?",
            (datetime.utcnow().isoformat(),),
        )
        count = cursor.rowcount

    if count > 0:
        _logger.info(f"Cleaned up {count} expired shares")

    return count
