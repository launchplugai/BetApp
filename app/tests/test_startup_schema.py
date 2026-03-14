from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.db import get_engine, reset_engine
from app.models import Base
from app.startup import ensure_governance_schema_ready


@pytest.fixture
def isolated_governance_db(tmp_path, monkeypatch):
    db_path = tmp_path / "startup-schema.sqlite"
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.delenv("SKIP_STARTUP_SCHEMA_CHECK", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    reset_engine()
    try:
        yield db_path
    finally:
        reset_engine()


def test_schema_check_skips_when_explicitly_disabled(isolated_governance_db, monkeypatch):
    monkeypatch.setenv("SKIP_STARTUP_SCHEMA_CHECK", "true")
    ensure_governance_schema_ready()


def test_schema_check_fails_when_governance_tables_missing(isolated_governance_db, monkeypatch):
    import app.startup as startup_module

    monkeypatch.setattr(startup_module, "should_enforce_governance_schema", lambda: True)
    with pytest.raises(RuntimeError, match="Governance schema missing required tables"):
        ensure_governance_schema_ready()


def test_schema_check_fails_without_alembic_tracking(isolated_governance_db, monkeypatch):
    import app.startup as startup_module

    monkeypatch.setattr(startup_module, "should_enforce_governance_schema", lambda: True)
    Base.metadata.create_all(bind=get_engine())

    with pytest.raises(RuntimeError, match="without Alembic tracking"):
        ensure_governance_schema_ready()


def test_schema_check_passes_after_alembic_upgrade(isolated_governance_db, monkeypatch):
    import subprocess
    import app.startup as startup_module

    repo_root = Path(__file__).resolve().parents[2]
    alembic_bin = repo_root / ".venv312" / "bin" / "alembic"
    env = os.environ.copy()
    env["APP_DATABASE_URL"] = f"sqlite:///{isolated_governance_db}"
    subprocess.run(
        [str(alembic_bin), "upgrade", "head"],
        cwd=repo_root,
        check=True,
        env=env,
    )

    monkeypatch.setattr(startup_module, "should_enforce_governance_schema", lambda: True)
    ensure_governance_schema_ready()
