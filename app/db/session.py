"""
Central database session management for app persistence.

This keeps engine configuration in one place so future SQLite -> Postgres
migration work does not require editing model modules directly.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

DEFAULT_APP_DATABASE_URL = "sqlite:///./dna_bets.db"

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def get_app_database_url() -> str:
    """Return the canonical application database URL."""
    return os.environ.get("APP_DATABASE_URL", DEFAULT_APP_DATABASE_URL)


def get_app_database_backend() -> str:
    """Return a safe backend label for health/debug visibility."""
    database_url = get_app_database_url()
    if database_url.startswith("postgresql") or database_url.startswith("postgres"):
        return "postgres"
    if database_url.startswith("sqlite"):
        return "sqlite"
    return "unknown"


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


def init_engine(database_url: Optional[str] = None) -> Engine:
    """Initialize the shared engine and session factory if needed."""
    global _engine, _session_factory

    target_url = database_url or get_app_database_url()
    if _engine is None:
        _engine = create_engine(target_url, **_engine_kwargs(target_url))
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine,
        )
    return _engine


def get_engine() -> Engine:
    """Get the shared application engine."""
    return init_engine()


def get_session() -> Session:
    """Get a new application database session."""
    global _session_factory
    if _session_factory is None:
        init_engine()
    return _session_factory()


@contextmanager
def session_scope() -> Session:
    """Provide a transactional scope for additive repository/service work."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Dispose shared engine/session state. Intended for tests and local resets."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
