"""
Provider interfaces for live data ingestion.
Abstract base classes define the contract for all data providers.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class MarketLine(BaseModel):
    """Single line (spread, total, etc.) with odds."""
    line: float
    odds: int


class PlayerProp(BaseModel):
    """Player prop bet."""
    player: str
    prop: str
    line: float
    over_odds: int
    under_odds: int


class MarketsData(BaseModel):
    """All available markets for a game."""
    spread: Optional[dict] = None
    total: Optional[dict] = None
    moneyline: Optional[dict] = None
    player_props: Optional[List[PlayerProp]] = None


class OddsResponse(BaseModel):
    """Standardized odds response."""
    game_id: str
    timestamp: datetime
    markets: MarketsData


class ScoreData(BaseModel):
    """Game score data."""
    home: int
    away: int


class ScoreResponse(BaseModel):
    """Standardized score response."""
    game_id: str
    status: str  # "UPCOMING" | "LIVE" | "FINAL"
    clock: Optional[str] = None
    score: Optional[ScoreData] = None
    quarter: Optional[int] = None
    period: Optional[int] = None


class OddsProvider(ABC):
    """
    Abstract base class for odds providers.
    
    All odds providers must implement this interface.
    Returns normalized OddsResponse regardless of source.
    """
    
    @abstractmethod
    async def get_odds(self, game_id: str) -> OddsResponse:
        """
        Get current odds for a game.
        
        Args:
            game_id: Unique game identifier
            
        Returns:
            OddsResponse with normalized market data
        """
        pass
    
    @abstractmethod
    async def get_odds_batch(self, game_ids: List[str]) -> List[OddsResponse]:
        """
        Get odds for multiple games.
        
        Args:
            game_ids: List of game identifiers
            
        Returns:
            List of OddsResponse
        """
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Provider identifier (e.g., 'mock', 'odds_api')."""
        pass


class ScoreProvider(ABC):
    """
    Abstract base class for score providers.
    
    All score providers must implement this interface.
    Returns normalized ScoreResponse regardless of source.
    """
    
    @abstractmethod
    async def get_score(self, game_id: str) -> ScoreResponse:
        """
        Get current score for a game.
        
        Args:
            game_id: Unique game identifier
            
        Returns:
            ScoreResponse with normalized score data
        """
        pass
    
    @abstractmethod
    async def get_scores_batch(self, game_ids: List[str]) -> List[ScoreResponse]:
        """
        Get scores for multiple games.
        
        Args:
            game_ids: List of game identifiers
            
        Returns:
            List of ScoreResponse
        """
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Provider identifier (e.g., 'mock', 'sportsdata')."""
        pass
