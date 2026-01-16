# persistence/__init__.py
"""
Persistence layer for Sprint 5.

Provides SQLite-backed storage for:
- Evaluation results (for sharing)
- Alerts (replaces in-memory store)
- Metrics/observability data
"""

from persistence.db import get_db, init_db, close_db
from persistence.evaluations import save_evaluation, get_evaluation, get_evaluation_by_token
from persistence.shares import create_share, get_share

__all__ = [
    "get_db",
    "init_db",
    "close_db",
    "save_evaluation",
    "get_evaluation",
    "get_evaluation_by_token",
    "create_share",
    "get_share",
]
