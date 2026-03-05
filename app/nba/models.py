"""
NBA Database Models - Star Schema

Based on NBA analytics industry standards.
"""
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, 
    JSON, ForeignKey, Index, Date, Text
)
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


# =============================================================================
# DIMENSION TABLES (Relatively Static)
# =============================================================================

class DimTeam(Base):
    """Team dimension table."""
    __tablename__ = "dim_teams"
    
    team_id = Column(Integer, primary_key=True)  # NBA API ID
    abbreviation = Column(String(3), nullable=False, index=True)
    nickname = Column(String(50), nullable=False)
    city = Column(String(50), nullable=False)
    full_name = Column(String(100), nullable=False)
    conference = Column(String(4))  # EAST, WEST
    division = Column(String(20))
    
    # Current season context
    active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)


class DimPlayer(Base):
    """Player dimension table."""
    __tablename__ = "dim_players"
    
    player_id = Column(Integer, primary_key=True)  # NBA API ID
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    full_name = Column(String(100), nullable=False, index=True)
    
    # Bio
    position = Column(String(10))  # PG, SG, SF, PF, C
    height = Column(String(10))  # e.g., "6-6"
    weight = Column(Integer)
    birth_date = Column(Date)
    
    # Career
    draft_year = Column(Integer)
    draft_round = Column(Integer)
    draft_number = Column(Integer)
    team_id = Column(Integer, ForeignKey("dim_teams.team_id"))
    
    # Status
    active = Column(Boolean, default=True)

    # Media
    photo_url = Column(String(300))  # NBA CDN headshot URL

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_player_name', 'last_name', 'first_name'),
    )


class DimGame(Base):
    """Game dimension table."""
    __tablename__ = "dim_games"
    
    game_id = Column(String(20), primary_key=True)  # e.g., "0022600123"
    game_date = Column(Date, nullable=False, index=True)
    season = Column(String(7), nullable=False, index=True)  # e.g., "2025-26"
    season_type = Column(String(20))  # Regular Season, Playoffs, Play-In
    
    # Teams
    home_team_id = Column(Integer, ForeignKey("dim_teams.team_id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("dim_teams.team_id"), nullable=False)
    
    # Result
    home_score = Column(Integer)
    away_score = Column(Integer)
    status = Column(String(20))  # Scheduled, Live, Final
    
    # Context
    playoff_round = Column(String(20))  # For playoff games
    game_number = Column(Integer)  # Game number in season
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_game_date_teams', 'game_date', 'home_team_id', 'away_team_id'),
    )


class DimSeason(Base):
    """Season dimension for tracking season-level context."""
    __tablename__ = "dim_seasons"
    
    season = Column(String(7), primary_key=True)  # e.g., "2025-26"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Season structure
    regular_season_games = Column(Integer, default=82)
    all_star_date = Column(Date)
    trade_deadline = Column(Date)
    playoff_start_date = Column(Date)
    
    # Status
    active = Column(Boolean, default=False)


# =============================================================================
# FACT TABLES (High Volume, Append-Only)
# =============================================================================

class FactBoxScore(Base):
    """Player box scores - core stats table."""
    __tablename__ = "fact_box_scores"
    
    # Composite key
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(20), ForeignKey("dim_games.game_id"), nullable=False)
    player_id = Column(Integer, ForeignKey("dim_players.player_id"), nullable=False)
    team_id = Column(Integer, ForeignKey("dim_teams.team_id"), nullable=False)
    
    # Game context
    started = Column(Boolean, default=False)
    minutes = Column(Float)
    
    # Basic stats
    points = Column(Integer, default=0)
    rebounds = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    steals = Column(Integer, default=0)
    blocks = Column(Integer, default=0)
    turnovers = Column(Integer, default=0)
    fouls = Column(Integer, default=0)
    
    # Shooting
    fgm = Column(Integer, default=0)
    fga = Column(Integer, default=0)
    fg_pct = Column(Float)
    fg3m = Column(Integer, default=0)
    fg3a = Column(Integer, default=0)
    fg3_pct = Column(Float)
    ftm = Column(Integer, default=0)
    fta = Column(Integer, default=0)
    ft_pct = Column(Float)
    
    # Advanced
    plus_minus = Column(Integer)
    off_rating = Column(Float)
    def_rating = Column(Float)
    true_shooting_pct = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_box_game_player', 'game_id', 'player_id'),
        Index('idx_box_player_date', 'player_id', 'game_id'),
    )


class FactTeamBoxScore(Base):
    """Team-level box scores."""
    __tablename__ = "fact_team_box_scores"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(20), ForeignKey("dim_games.game_id"), nullable=False)
    team_id = Column(Integer, ForeignKey("dim_teams.team_id"), nullable=False)
    
    # Location
    is_home = Column(Boolean, nullable=False)
    
    # Score
    points = Column(Integer, default=0)
    
    # Shooting
    fgm = Column(Integer, default=0)
    fga = Column(Integer, default=0)
    fg_pct = Column(Float)
    fg3m = Column(Integer, default=0)
    fg3a = Column(Integer, default=0)
    fg3_pct = Column(Float)
    ftm = Column(Integer, default=0)
    fta = Column(Integer, default=0)
    ft_pct = Column(Float)
    
    # Rebounds
    off_reb = Column(Integer, default=0)
    def_reb = Column(Integer, default=0)
    total_reb = Column(Integer, default=0)
    
    # Other
    assists = Column(Integer, default=0)
    steals = Column(Integer, default=0)
    blocks = Column(Integer, default=0)
    turnovers = Column(Integer, default=0)
    fouls = Column(Integer, default=0)
    
    # Advanced
    pace = Column(Float)
    off_rating = Column(Float)
    def_rating = Column(Float)
    net_rating = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_team_box_game_team', 'game_id', 'team_id'),
    )


# =============================================================================
# CONTEXT TABLES (Business Logic / Heuristics)
# =============================================================================

class ContextInjury(Base):
    """Injury reports with impact assessment."""
    __tablename__ = "context_injuries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, ForeignKey("dim_players.player_id"), nullable=False)
    team_id = Column(Integer, ForeignKey("dim_teams.team_id"), nullable=False)
    
    # Injury details
    injury_type = Column(String(100))  # "Ankle sprain", "Load management"
    status = Column(String(20))  # Out, Doubtful, Questionable, Probable, GTD
    
    # Timeline
    injury_date = Column(Date)
    expected_return = Column(Date)
    return_date = Column(Date)  # Actual return
    
    # Impact
    games_missed = Column(Integer, default=0)
    impact_score = Column(Float)  # Calculated based on player value
    
    # Source
    source = Column(String(50))  # ESPN, Rotowire, NBA.com
    reported_at = Column(DateTime, default=datetime.utcnow)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_injury_player_date', 'player_id', 'injury_date'),
    )


class ContextRestDays(Base):
    """Pre-calculated rest days for each game."""
    __tablename__ = "context_rest_days"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(20), ForeignKey("dim_games.game_id"), nullable=False)
    team_id = Column(Integer, ForeignKey("dim_teams.team_id"), nullable=False)
    
    # Rest calculation
    days_rest = Column(Integer, nullable=False)  # 0 = back-to-back
    previous_game_id = Column(String(20))
    next_game_id = Column(String(20))
    
    # Context
    is_back_to_back = Column(Boolean, default=False)
    games_in_last_7_days = Column(Integer)
    travel_miles = Column(Float)  # Distance from last city
    
    # Impact estimate
    rest_advantage_vs_opponent = Column(Float)  # Relative to opponent
    fatigue_score = Column(Float)  # 0-100
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_rest_game_team', 'game_id', 'team_id'),
    )


class ContextPlayoffStandings(Base):
    """Daily snapshot of playoff standings."""
    __tablename__ = "context_playoff_standings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("dim_teams.team_id"), nullable=False)
    as_of_date = Column(Date, nullable=False)
    season = Column(String(7), nullable=False)
    
    # Standings
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    win_pct = Column(Float)
    conference_rank = Column(Integer)
    division_rank = Column(Integer)
    games_back = Column(Float)
    
    # Playoff context
    playoff_seed = Column(Integer)  # 1-10 (with play-in)
    clinched_playoff = Column(Boolean, default=False)
    clinched_division = Column(Boolean, default=False)
    eliminated = Column(Boolean, default=False)
    
    # Magic numbers
    clinch_number = Column(Integer)
    elimination_number = Column(Integer)
    
    # Tank indicator
    tank_probability = Column(Float)  # 0-1 (calculated)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_standings_date_team', 'as_of_date', 'team_id'),
        Index('idx_standings_season_rank', 'season', 'conference_rank'),
    )


class ContextMatchupHistory(Base):
    """Historical matchup data with context."""
    __tablename__ = "context_matchup_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    team_a_id = Column(Integer, ForeignKey("dim_teams.team_id"), nullable=False)
    team_b_id = Column(Integer, ForeignKey("dim_teams.team_id"), nullable=False)
    season = Column(String(7), nullable=False)
    
    # H2H record
    games_played = Column(Integer, default=0)
    team_a_wins = Column(Integer, default=0)
    team_b_wins = Column(Integer, default=0)
    
    # Scoring
    avg_total_points = Column(Float)
    avg_point_diff = Column(Float)
    
    # Style matchup
    pace_differential = Column(Float)
    style_clash_rating = Column(Float)  # How different are the styles?
    
    # Recent form
    last_5_games = Column(JSON)  # Array of last 5 game results
    
    # Venue splits
    team_a_home_record = Column(String(10))  # "3-1"
    team_b_home_record = Column(String(10))
    
    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_matchup_teams_season', 'team_a_id', 'team_b_id', 'season'),
    )


# =============================================================================
# ANALYTICS CACHE TABLE
# =============================================================================

class CacheAnalytics(Base):
    """Pre-calculated analytics for fast protocol responses."""
    __tablename__ = "cache_analytics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(200), unique=True, nullable=False, index=True)
    cache_type = Column(String(50), nullable=False)  # player_stats, team_rating, etc.
    
    # Cache payload
    data = Column(JSON, nullable=False)
    
    # Expiry
    expires_at = Column(DateTime, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    access_count = Column(Integer, default=0)
