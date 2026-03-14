"""Application startup orchestration."""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta

from sqlalchemy import inspect, text

from app.db import get_engine

logger = logging.getLogger(__name__)

REQUIRED_GOVERNANCE_TABLES = (
    "model_registry",
    "evaluation_logs",
    "learning_proposals",
    "promotion_audit",
)
REQUIRED_ALEMBIC_REVISION = "20260309_0003"


def should_enforce_governance_schema() -> bool:
    """Return True when startup should fail on missing governed schema."""
    if os.environ.get("SKIP_STARTUP_SCHEMA_CHECK", "").lower() in {"1", "true", "yes", "on"}:
        return False
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    environment = (
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("ENVIRONMENT")
        or "development"
    ).lower()
    return environment not in {"test", "ci"}


def ensure_governance_schema_ready() -> None:
    """Fail clearly if the governed control-plane schema is not Alembic-ready."""
    if not should_enforce_governance_schema():
        return

    engine = get_engine()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    missing_tables = [name for name in REQUIRED_GOVERNANCE_TABLES if name not in table_names]
    if missing_tables:
        raise RuntimeError(
            "Governance schema missing required tables: "
            f"{', '.join(missing_tables)}. "
            "Run `alembic upgrade head` before starting the app."
        )

    if "alembic_version" not in table_names:
        raise RuntimeError(
            "Governance schema exists without Alembic tracking. "
            "Stamp/apply migrations with `alembic stamp 20260308_0001 && alembic upgrade head`."
        )

    with engine.connect() as conn:
        revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()

    if revision != REQUIRED_ALEMBIC_REVISION:
        raise RuntimeError(
            "Governance schema revision mismatch: "
            f"expected {REQUIRED_ALEMBIC_REVISION}, got {revision or 'none'}. "
            "Run `alembic upgrade head` before starting the app."
        )


def initialize_application_databases() -> None:
    """Initialize primary application and NBA schemas."""
    from app.models import init_db
    from app.nba.database import init_database as init_nba_db

    init_db()
    logger.info("User database initialized")

    init_nba_db()
    logger.info("NBA analytics database initialized")


def ensure_nba_seed_data() -> None:
    """Bootstrap or repair NBA reference data when needed."""
    from app.nba.database import full_bootstrap, get_db_session
    from app.nba.ingestion import NBADataIngestion
    from app.nba.models import DimPlayer, DimTeam

    db = get_db_session()
    try:
        team_count = db.query(DimTeam).count()
        if team_count == 0:
            logger.info("NBA tables empty; starting bootstrap")
            result = full_bootstrap()
            logger.info("NBA bootstrap complete: %s", result)
            return

        logger.info("NBA data present: %s teams loaded", team_count)
        ingestion = NBADataIngestion(db)

        missing_photos = (
            db.query(DimPlayer)
            .filter(DimPlayer.photo_url.is_(None), DimPlayer.active.is_(True))
            .count()
        )
        if missing_photos > 0:
            logger.info("Updating %s players with missing photo URLs", missing_photos)
            ingestion.sync_players(active_only=True)
            logger.info("Player photos updated")

        missing_teams = (
            db.query(DimPlayer)
            .filter(DimPlayer.team_id.is_(None), DimPlayer.active.is_(True))
            .count()
        )
        if missing_teams > 0:
            logger.info(
                "Syncing rosters for %s players missing team assignments",
                missing_teams,
            )
            count = ingestion.sync_rosters()
            logger.info("Roster sync complete: %s players updated", count)
    except Exception:
        logger.exception("NBA bootstrap failed (non-fatal)")
    finally:
        db.close()


def run_nba_daily_refresh() -> None:
    """Run daily ETL and fetch today's scheduled NBA games."""
    from app.nba.database import get_db_session
    from app.nba.ingestion import NBADataIngestion, run_daily_etl

    yesterday = date.today() - timedelta(days=1)
    etl_db = get_db_session()
    try:
        logger.info("Running daily ETL for %s", yesterday)
        run_daily_etl(etl_db, yesterday)
        logger.info("Daily ETL complete")
    except Exception:
        logger.exception("Daily ETL failed (non-fatal)")
        return
    finally:
        etl_db.close()

    schedule_db = get_db_session()
    try:
        ingestion = NBADataIngestion(schedule_db)
        today = date.today()
        season = f"{today.year}-{str(today.year + 1)[-2:]}"
        games = ingestion.fetch_games_for_date(today)
        for game_data in games:
            ingestion.ingest_game(game_data, season)
        logger.info("Fetched %s games scheduled for today", len(games))
    except Exception:
        logger.exception("Scheduled game fetch failed (non-fatal)")
    finally:
        schedule_db.close()


def run_application_startup() -> None:
    """Run startup tasks in the current operational order."""
    initialize_application_databases()
    ensure_governance_schema_ready()
    ensure_nba_seed_data()
    run_nba_daily_refresh()
