"""MLB Heuristics Module."""

from typing import List, Dict, Any, Optional
import random

from app.heuristics.base import (
    SportHeuristics, GameContext, PlayerStats, EdgeAssessment,
    Insight, ConfidenceLevel, BetType
)


class MLBHeuristics:
    """MLB analytics and heuristics."""
    
    PITCHERS = {
        "gerrit_cole": {"name": "Gerrit Cole", "team": "NYY", "era": 3.15, "whip": 1.08},
        "chris_sale": {"name": "Chris Sale", "team": "BOS", "era": 3.45, "whip": 1.12},
    }
    
    BATTERS = {
        "aaron_judge": {"name": "Aaron Judge", "team": "NYY", "avg": 0.285, "ops": 0.985, "hr": 45},
        "rafael_devers": {"name": "Rafael Devers", "team": "BOS", "avg": 0.275, "ops": 0.890, "hr": 35},
    }
    
    def get_game_context(self, game_id: str) -> GameContext:
        """Get MLB game context."""
        return GameContext(
            game_id=game_id,
            home_team="Yankees" if "nyy" in game_id else "Home",
            away_team="Red Sox" if "bos" in game_id else "Away",
            home_team_stats={
                "team_avg": 0.265,
                "team_era": 3.85,
                "bullpen_era": 3.45,
                "runs_per_game": 5.2,
                "home_record": "45-30",
                "vs_lefties": 0.275,
                "vs_righties": 0.260,
            },
            away_team_stats={
                "team_avg": 0.258,
                "team_era": 4.15,
                "bullpen_era": 3.95,
                "runs_per_game": 4.8,
                "away_record": "38-37",
                "vs_lefties": 0.250,
                "vs_righties": 0.265,
            },
            situational_factors={
                "park_factor": 1.08,  # Yankee Stadium slightly hitter-friendly
                "wind_impact": "neutral",
                "day_night": "night",
                "travel": "normal",
            },
            weather={
                "temp": 72,
                "wind_speed": 8,
                "wind_direction": "out",
                "precip_chance": 10,
            }
        )
    
    def get_player_stats(self, player_id: str) -> PlayerStats:
        """Get MLB player stats (pitcher or batter)."""
        if player_id in self.PITCHERS:
            pitcher = self.PITCHERS[player_id]
            return PlayerStats(
                player_id=player_id,
                player_name=pitcher["name"],
                recent_form=[6.2, 7.0, 6.1, 8.0, 5.2],  # Innings pitched
                season_average=6.5,
                vs_opponent_average=6.8,
                home_away_split={"home": 6.8, "away": 6.2},
                custom_metrics={
                    "era": pitcher["era"],
                    "whip": pitcher["whip"],
                    "k_per_9": 9.8,
                    "bb_per_9": 2.1,
                    "swinging_strike_pct": 12.5,
                }
            )
        else:
            batter = self.BATTERS.get(player_id, {"name": "Unknown", "avg": 0.250, "ops": 0.750, "hr": 15})
            return PlayerStats(
                player_id=player_id,
                player_name=batter["name"],
                recent_form=[1, 0, 2, 1, 0],  # Hits last 5 games
                season_average=0.280,
                vs_opponent_average=0.265,
                home_away_split={"home": 0.295, "away": 0.265},
                custom_metrics={
                    "avg": batter["avg"],
                    "ops": batter["ops"],
                    "hr": batter["hr"],
                    "babip": 0.310,
                    "hard_contact_pct": 42.5,
                }
            )
    
    def calculate_edge(self, game_id: str, bet_type: BetType,
                      selection: str, line: Optional[float] = None) -> EdgeAssessment:
        """Calculate edge for MLB bet."""
        context = self.get_game_context(game_id)
        
        if bet_type == BetType.TOTAL:
            # Park factor and pitching matchup
            park_adj = (context.situational_factors["park_factor"] - 1.0) * 2
            era_diff = context.away_team_stats["team_era"] - context.home_team_stats["team_era"]
            edge = park_adj + (era_diff * 0.05)
        elif "pitcher" in selection.lower() or "strikeout" in selection.lower():
            edge = random.uniform(-0.12, 0.12)
        elif "batter" in selection.lower() or "hit" in selection.lower():
            edge = random.uniform(-0.10, 0.10)
        else:
            edge = random.uniform(-0.08, 0.08)
        
        edge = max(-1.0, min(1.0, edge))
        
        return EdgeAssessment(
            edge_score=edge,
            confidence=ConfidenceLevel.MEDIUM,
            reasoning=f"MLB heuristic: {bet_type.value} with park factor {context.situational_factors['park_factor']:.2f}",
            factors={"park_factor": context.situational_factors["park_factor"], "weather": context.weather}
        )
    
    def generate_insights(self, game_id: str, tier: str = "GOOD") -> List[Insight]:
        """Generate MLB insights."""
        context = self.get_game_context(game_id)
        insights = []
        
        if tier in ["GOOD", "BETTER", "BEST"]:
            insights.append(Insight(
                category="Pitching",
                title="Ace on Mound",
                description="Gerrit Cole's 3.15 ERA vs league average 4.25",
                confidence=ConfidenceLevel.HIGH,
            ))
        
        if tier in ["BETTER", "BEST"]:
            insights.append(Insight(
                category="Park",
                title="Hitter-Friendly Venue",
                description=f"Yankee Stadium park factor {context.situational_factors['park_factor']:.2f} favors hitters",
                confidence=ConfidenceLevel.MEDIUM,
            ))
        
        if tier == "BEST":
            insights.append(Insight(
                category="Weather",
                title="Wind Carrying Out",
                description=f"{context.weather['wind_speed']}mph wind out - HR prop value up",
                confidence=ConfidenceLevel.MEDIUM,
            ))
        
        return insights
    
    def assess_matchup(self, game_id: str) -> Dict[str, Any]:
        """Assess MLB matchup."""
        context = self.get_game_context(game_id)
        return {
            "pitching_advantage": "HOME",
            "bullpen_advantage": "HOME",
            "park_factor": context.situational_factors["park_factor"],
            "weather_boost": "NEUTRAL",
            "projected_runs": context.home_team_stats["runs_per_game"] + context.away_team_stats["runs_per_game"],
        }


def get_mlb_heuristics() -> MLBHeuristics:
    return MLBHeuristics()
