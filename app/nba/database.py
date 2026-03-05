"""
NBA Database Management

SQLite for development, PostgreSQL-ready for production.
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.nba.models import Base

logger = logging.getLogger(__name__)

# =============================================================================
# Database Configuration
# =============================================================================

# Use SQLite for now (can switch to PostgreSQL with env var)
DATABASE_URL = os.environ.get(
    "NBA_DATABASE_URL",
    "sqlite:///./data/nba_analytics.db"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False  # Set True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# =============================================================================
# Session Management
# =============================================================================

def get_db_session() -> Session:
    """Get a new database session."""
    return SessionLocal()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints.
    
    Usage:
        @router.get("/...")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Initialization
# =============================================================================

def init_database():
    """
    Initialize database schema.

    Creates all tables if they don't exist.
    Safe to call multiple times.
    """
    logger.info(f"Initializing NBA database: {DATABASE_URL}")

    # Ensure data directory exists
    if "sqlite" in DATABASE_URL:
        db_path = DATABASE_URL.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Migrate: add photo_url column if missing (SQLite doesn't support ALTER TABLE IF NOT EXISTS)
    if "sqlite" in DATABASE_URL:
        from sqlalchemy import text, inspect
        insp = inspect(engine)
        if "dim_players" in insp.get_table_names():
            columns = [c["name"] for c in insp.get_columns("dim_players")]
            if "photo_url" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE dim_players ADD COLUMN photo_url VARCHAR(300)"))
                    conn.commit()
                logger.info("Migrated dim_players: added photo_url column")

    logger.info("NBA database tables created successfully")


def drop_all_tables():
    """
    Drop all tables. USE WITH CAUTION.
    
    Only for development/testing.
    """
    logger.warning("Dropping all NBA database tables!")
    Base.metadata.drop_all(bind=engine)


# =============================================================================
# Bootstrap Data
# =============================================================================

def bootstrap_teams():
    """
    Load initial team data from nba_api.
    
    Should be run once on first setup.
    """
    from app.nba.ingestion import NBADataIngestion
    
    logger.info("Bootstrapping NBA teams...")
    
    db = get_db_session()
    try:
        ingestion = NBADataIngestion(db)
        count = ingestion.sync_teams()
        logger.info(f"Bootstrapped {count} teams")
        return count
    finally:
        db.close()


def bootstrap_players():
    """
    Load initial player data from nba_api.
    
    Should be run once on first setup.
    """
    from app.nba.ingestion import NBADataIngestion
    
    logger.info("Bootstrapping NBA players...")
    
    db = get_db_session()
    try:
        ingestion = NBADataIngestion(db)
        count = ingestion.sync_players(active_only=True)
        logger.info(f"Bootstrapped {count} players")
        return count
    finally:
        db.close()


def bootstrap_rosters():
    """
    Sync current team rosters to assign team_id and position to players.
    """
    from app.nba.ingestion import NBADataIngestion

    logger.info("Bootstrapping rosters...")

    db = get_db_session()
    try:
        ingestion = NBADataIngestion(db)
        count = ingestion.sync_rosters()
        logger.info(f"Bootstrapped {count} roster assignments")
        return count
    finally:
        db.close()


def full_bootstrap():
    """
    Run complete bootstrap sequence.

    1. Initialize database
    2. Load teams
    3. Load players
    4. Sync rosters (team_id + position)
    """
    logger.info("Starting full NBA database bootstrap...")

    init_database()
    teams = bootstrap_teams()
    players = bootstrap_players()
    rosters = bootstrap_rosters()

    logger.info(f"Bootstrap complete: {teams} teams, {players} players, {rosters} roster assignments")
    return {"teams": teams, "players": players, "rosters": rosters}
