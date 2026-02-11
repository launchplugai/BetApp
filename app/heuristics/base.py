"""Base heuristics framework for all sports."""

from typing import List, Optional, Dict, Any, Protocol
from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BetType(Enum):
    SPREAD = "spread"
    MONEYLINE = "moneyline"
    TOTAL = "total"
    PLAYER_PROP = "player_prop"
    TEAM_PROP = "team_prop"
    GAME_PROP = "game_prop"


@dataclass
class EdgeAssessment:
    """Result of edge calculation for a bet."""
    edge_score: float  # -1.0 to 1.0
    confidence: ConfidenceLevel
    reasoning: str
    factors: Dict[str, Any]


@dataclass
class Insight:
    """Analytical insight for display."""
    category: str
    title: str
    description: str
    confidence: ConfidenceLevel
    supporting_data: Optional[Dict[str, Any]] = None


@dataclass
class PlayerStats:
    """Generic player statistics container."""
    player_id: str
    player_name: str
    recent_form: List[float]  # Last N game scores/performances
    season_average: float
    vs_opponent_average: Optional[float] = None
    home_away_split: Optional[Dict[str, float]] = None
    custom_metrics: Optional[Dict[str, Any]] = None


@dataclass
class GameContext:
    """Context for a specific game."""
    game_id: str
    home_team: str
    away_team: str
    home_team_stats: Dict[str, Any]
    away_team_stats: Dict[str, Any]
    situational_factors: Dict[str, Any]
    weather: Optional[Dict[str, Any]] = None
    injuries: Optional[List[Dict[str, Any]]] = None


class SportHeuristics(Protocol):
    """Protocol for sport-specific heuristics implementations."""
    
    def get_game_context(self, game_id: str) -> GameContext:
        """Get full context for a game."""
        ...
    
    def get_player_stats(self, player_id: str) -> PlayerStats:
        """Get player statistics."""
        ...
    
    def calculate_edge(self, game_id: str, bet_type: BetType, 
                      selection: str, line: Optional[float] = None) -> EdgeAssessment:
        """Calculate edge for a specific bet."""
        ...
    
    def generate_insights(self, game_id: str, tier: str = "GOOD") -> List[Insight]:
        """Generate analytical insights for a game."""
        ...
    
    def assess_matchup(self, game_id: str) -> Dict[str, Any]:
        """Assess the matchup between teams."""
        ...
