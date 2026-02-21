"""
Pydantic schemas for analytics enrichment
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class TeamContext(BaseModel):
    """Team-specific context within a game"""
    team_id: str
    team_name: str
    stats: dict = Field(default_factory=dict, description="Raw advanced stats")
    
    # NBA specific
    pace: Optional[float] = None  # possessions per 48 min
    offensive_rating: Optional[float] = None  # points per 100 possessions
    defensive_rating: Optional[float] = None
    net_rating: Optional[float] = None
    rest_days: int = 0
    back_to_back: bool = False
    injury_count: int = 0  # starters out
    injury_impact_score: float = 0.0  # 0.0-1.0 proxy
    
    # NFL specific
    epa_per_play: Optional[float] = None
    success_rate: Optional[float] = None  # % of plays with positive EPA
    plays_per_game: Optional[float] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "team_id": "bos",
                "team_name": "Boston Celtics",
                "pace": 98.5,
                "offensive_rating": 118.2,
                "defensive_rating": 110.4,
                "net_rating": 7.8,
                "rest_days": 2,
                "back_to_back": False,
                "injury_count": 1,
                "injury_impact_score": 0.15,
            }
        }


class GameContext(BaseModel):
    """Enriched game context with advanced statistics"""
    game_id: str
    sport: Literal["nba", "nfl", "mlb", "nhl"]
    home_team: TeamContext
    away_team: TeamContext
    
    # Game-level metadata
    scheduled_at: Optional[datetime] = None
    venue: Optional[str] = None
    
    # Market data
    opening_line: Optional[float] = None
    current_line: Optional[float] = None
    line_movement_delta: Optional[float] = None  # points moved
    public_betting_pct: Optional[float] = None  # % on favorite
    
    # NFL specific
    weather_temp: Optional[float] = None
    weather_wind: Optional[float] = None
    weather_precip: Optional[str] = None  # 'clear', 'rain', 'snow'
    weather_impact: Optional[str] = None  # 'clear', 'wind', 'precip', 'extreme'
    
    # Data quality tracking
    data_source: Literal["api", "cache", "degraded", "fallback"] = "api"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    cache_ttl_seconds: int = 3600
    
    # Degraded mode indicators
    is_enriched: bool = True
    enrichment_errors: list[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "game_id": "nba-20260221-bos-lal",
                "sport": "nba",
                "home_team": {"team_id": "lal", "team_name": "Lakers", "pace": 99.2},
                "away_team": {"team_id": "bos", "team_name": "Celtics", "pace": 98.1},
                "data_source": "api",
                "is_enriched": True,
            }
        }


class EnrichmentResult(BaseModel):
    """Result wrapper for enrichment operations"""
    success: bool
    game_context: Optional[GameContext] = None
    error_message: Optional[str] = None
    raw_data: Optional[dict] = None
    
    
class CacheEntry(BaseModel):
    """Cache entry metadata"""
    key: str
    data: dict
    created_at: datetime
    expires_at: datetime
    hit_count: int = 0
