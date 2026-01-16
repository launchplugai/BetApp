# persistence/db.py
"""
SQLite database connection and schema management.

Uses a file-based SQLite database for persistence.
On Railway, use a persistent volume to survive restarts.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

_logger = logging.getLogger(__name__)

# Database file location (configurable via env var)
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "dna.db"
DB_PATH = Path(os.environ.get("DNA_DB_PATH", str(DEFAULT_DB_PATH)))

# Connection pool (one connection per thread)
_local = threading.local()
_init_lock = threading.Lock()
_initialized = False


def _get_connection() -> sqlite3.Connection:
    """Get thread-local database connection."""
    if not hasattr(_local, "connection") or _local.connection is None:
        # Ensure directory exists
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(
            str(DB_PATH),
            timeout=30.0,
            check_same_thread=False,
        )
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        # Return rows as dicts
        conn.row_factory = sqlite3.Row
        _local.connection = conn

    return _local.connection


@contextmanager
def get_db():
    """
    Get database connection context manager.

    Usage:
        with get_db() as conn:
            cursor = conn.execute("SELECT ...")
    """
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db() -> None:
    """
    Initialize database schema.

    Creates tables if they don't exist.
    Safe to call multiple times (idempotent).
    """
    global _initialized

    with _init_lock:
        if _initialized:
            return

        with get_db() as conn:
            # Evaluations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    id TEXT PRIMARY KEY,
                    parlay_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    tier TEXT NOT NULL,
                    input_text TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    correlation_id TEXT,
                    expires_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_evaluations_parlay
                ON evaluations(parlay_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_evaluations_correlation
                ON evaluations(correlation_id)
            """)

            # Shares table (for shareable links)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shares (
                    token TEXT PRIMARY KEY,
                    evaluation_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    view_count INTEGER DEFAULT 0,
                    FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_shares_evaluation
                ON shares(evaluation_id)
            """)

            # Alerts table (persistent alerts)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    player_name TEXT,
                    team TEXT,
                    previous_value TEXT,
                    current_value TEXT,
                    created_at TEXT NOT NULL,
                    correlation_id TEXT,
                    source TEXT,
                    sport TEXT,
                    expires_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_correlation
                ON alerts(correlation_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_created
                ON alerts(created_at DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_player
                ON alerts(player_name)
            """)

            # Metrics table (for observability)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    labels_json TEXT,
                    recorded_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_name
                ON metrics(metric_name, recorded_at DESC)
            """)

            _logger.info(f"Database initialized at {DB_PATH}")
            _initialized = True


def close_db() -> None:
    """Close thread-local database connection."""
    if hasattr(_local, "connection") and _local.connection is not None:
        _local.connection.close()
        _local.connection = None


def reset_db() -> None:
    """Reset database (for testing). Drops all tables."""
    global _initialized

    with _init_lock:
        with get_db() as conn:
            conn.execute("DROP TABLE IF EXISTS metrics")
            conn.execute("DROP TABLE IF EXISTS shares")
            conn.execute("DROP TABLE IF EXISTS alerts")
            conn.execute("DROP TABLE IF EXISTS evaluations")
        _initialized = False


def get_db_path() -> Path:
    """Get the database file path."""
    return DB_PATH
