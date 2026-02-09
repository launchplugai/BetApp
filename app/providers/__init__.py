"""
S19-A: Odds Provider Architecture

Defines interfaces for odds and score providers.
Enables mock and live data sources with normalized output.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime


# =============================================================================
# Canonical Data Shapes (S19-B)
# =============================================================================

class Sport(BaseModel):
    """Canonical sport representation."""
    id: str  # e.g., "NBA", "NFL"
    label: str  # Display name
    active: bool  # Is sport currently in season / available


class Game(BaseModel):
    """Canonical game representation."""
    id: str  # e.g., "lal-gsw-2026-02-08"
    league: str  # e.g., "NBA"
    home: str  # Home team name
    away: str  # Away team name
    start_time: str  # ISO 8601 timestamp
    status: str  # "SCHEDULED", "LIVE", "FINAL"


class Selection(BaseModel):
    """A single betting selection within a market."""
    label: str  # e.g., "Lakers -4.5"
    line: Optional[float] = None  # The line value (-4.5, 220.5, etc.)
    odds: int  # American odds (-110, +150, etc.)


class MarketOdds(BaseModel):
    """Odds for a specific market."""
    market: str  # "spread", "total", "moneyline", "player_prop"
    selections: List[Selection]


class LiveScore(BaseModel):
    """Live score data."""
    game_id: str
    home_score: int
    away_score: int
    period: str  # "Q1", "Q2", "4th", etc.
    clock: Optional[str] = None  # "5:23" in current period
    status: str  # "LIVE", "HALFTIME", "FINAL"


# =============================================================================
# Provider Interfaces
# =============================================================================

class OddsProvider(ABC):
    """
    Abstract interface for odds data providers.
    
    Implementations:
    - MockProvider: Returns hardcoded mock data (existing behavior)
    - LiveProvider: Fetches from external API (stubbed, no keys yet)
    """
    
    @abstractmethod
    def get_sports(self) -> List[Sport]:
        """Get list of available sports."""
        pass
    
    @abstractmethod
    def get_games(self, sport: str) -> List[Game]:
        """Get games for a specific sport."""
        pass
    
    @abstractmethod
    def get_odds(self, game_id: str) -> List[MarketOdds]:
        """Get odds for a specific game."""
        pass


class ScoreProvider(ABC):
    """
    Abstract interface for live score providers.
    
    Implementations:
    - MockScoreProvider: Returns mock score data
    - LiveScoreProvider: Fetches from external API (stubbed)
    """
    
    @abstractmethod
    def get_score(self, game_id: str) -> Optional[LiveScore]:
        """Get live score for a game."""
        pass


# =============================================================================
# Configuration
# =============================================================================

class ProviderConfig(BaseModel):
    """Provider configuration."""
    provider_type: str = "mock"  # "mock" or "live"
    cache_ttl_seconds: int = 60  # Default cache TTL
    api_key: Optional[str] = None  # For live providers
