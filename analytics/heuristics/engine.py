"""
Heuristic Engine for DNA/BetApp
Signal detection layer - Sprint 2 Phase 2
"""

from enum import Enum
from typing import List, Literal
from pydantic import BaseModel

from analytics.schemas import GameContext, TeamContext


class VolatilityImpact(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HeuristicResult(BaseModel):
    """A detected signal with impact assessment"""
    name: str
    score: float  # 0.0 to 1.0
    explanation: str
    volatility_impact: VolatilityImpact
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "pace_shock",
                "score": 0.72,
                "explanation": "Lakers play 4.2 possessions faster than Celtics",
                "volatility_impact": "high"
            }
        }


class HeuristicEngine:
    """
    Analyzes GameContext and returns detected heuristic signals.
    
    No final verdict - just signals for DNA/Sherlock to use.
    """
    
    def analyze(self, game_context: GameContext) -> List[HeuristicResult]:
        """
        Run all heuristics on a game and return detected signals.
        """
        results: List[HeuristicResult] = []
        
        # Pace-based signals
        pace_signal = self._analyze_pace_shock(game_context)
        if pace_signal:
            results.append(pace_signal)
        
        # Rest-based signals
        rest_signal = self._analyze_rest_asymmetry(game_context)
        if rest_signal:
            results.append(rest_signal)
        
        # TODO Sprint 2+: Add more heuristics
        # - injury_leverage
        # - tank_probability
        # - playoff_leverage
        # - line_freeze_anomaly
        
        return results
    
    def _analyze_pace_shock(self, game: GameContext) -> HeuristicResult | None:
        """
        Detect pace mismatch between teams.
        
        High pace vs low pace = more possessions = more variance.
        """
        home_pace = game.home_team.pace
        away_pace = game.away_team.pace
        
        if home_pace is None or away_pace is None:
            return None
        
        diff = abs(home_pace - away_pace)
        
        if diff > 5.0:
            score = min(0.95, 0.7 + (diff - 5) * 0.05)
            impact = VolatilityImpact.HIGH
        elif diff > 3.0:
            score = 0.5 + (diff - 3) * 0.1
            impact = VolatilityImpact.MEDIUM
        elif diff > 1.5:
            score = 0.3 + (diff - 1.5) * 0.13
            impact = VolatilityImpact.LOW
        else:
            return None  # No significant pace shock
        
        faster = game.home_team.team_name if home_pace > away_pace else game.away_team.team_name
        slower = game.away_team.team_name if home_pace > away_pace else game.home_team.team_name
        
        return HeuristicResult(
            name="pace_shock",
            score=round(score, 2),
            explanation=f"{faster} plays {diff:.1f} possessions faster than {slower}",
            volatility_impact=impact
        )
    
    def _analyze_rest_asymmetry(self, game: GameContext) -> HeuristicResult | None:
        """
        Detect rest advantage between teams.
        
        More rest = better recovery = potential advantage.
        """
        home_rest = game.home_team.rest_days
        away_rest = game.away_team.rest_days
        
        diff = abs(home_rest - away_rest)
        
        if diff == 0:
            return None  # Equal rest
        
        if diff > 2:
            score = min(0.9, 0.6 + (diff - 2) * 0.1)
            impact = VolatilityImpact.HIGH
        elif diff == 2:
            score = 0.45
            impact = VolatilityImpact.MEDIUM
        else:  # diff == 1
            score = 0.25
            impact = VolatilityImpact.LOW
        
        rested = game.home_team.team_name if home_rest > away_rest else game.away_team.team_name
        tired = game.away_team.team_name if home_rest > away_rest else game.home_team.team_name
        
        return HeuristicResult(
            name="rest_asymmetry",
            score=round(score, 2),
            explanation=f"{rested} has {diff} more rest day(s) than {tired}",
            volatility_impact=impact
        )
