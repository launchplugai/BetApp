"""Soccer Heuristics Module."""

from typing import List, Dict, Any, Optional
import random

from app.heuristics.base import (
    SportHeuristics, GameContext, PlayerStats, EdgeAssessment,
    Insight, ConfidenceLevel, BetType
)


class SoccerHeuristics:
    """Soccer analytics and heuristics."""
    
    PLAYERS = {
        "erling_haaland": {"name": "Erling Haaland", "team": "MCI", "goals": 25, "xG": 22.5},
        "mohamed_salah": {"name": "Mohamed Salah", "team": "LIV", "goals": 18, "xG": 16.8},
    }
    
    def get_game_context(self, game_id: str) -> GameContext:
        """Get Soccer game context."""
        return GameContext(
            game_id=game_id,
            home_team="Man City" if "mci" in game_id else "Home",
            away_team="Liverpool" if "liv" in game_id else "Away",
            home_team_stats={
                "xg_for": 2.15,
                "xg_against": 0.85,
                "possession": 62.5,
                "shots_per_game": 16.5,
                "home_record": "12-2-1",
                "form": [3, 3, 1, 3, 3],  # Points last 5 (3=win, 1=draw, 0=loss)
            },
            away_team_stats={
                "xg_for": 1.95,
                "xg_against": 1.05,
                "possession": 58.0,
                "shots_per_game": 14.2,
                "away_record": "9-4-2",
                "form": [3, 3, 3, 0, 3],
            },
            situational_factors={
                "title_race": True,
                "derby": False,
                "european_midweek": False,
                "home_advantage": 0.35,  # xG boost
            }
        )
    
    def get_player_stats(self, player_id: str) -> PlayerStats:
        """Get Soccer player stats."""
        player = self.PLAYERS.get(player_id, {"name": "Unknown", "goals": 10, "xG": 9.0})
        return PlayerStats(
            player_id=player_id,
            player_name=player["name"],
            recent_form=[1, 0, 1, 2, 1],  # Shots on target
            season_average=1.4,
            vs_opponent_average=1.6,
            custom_metrics={
                "goals": player["goals"],
                "xG": player["xG"],
                "conversion_rate": player["goals"] / max(player["xG"], 1),
                "shots_per_90": 3.8,
            }
        )
    
    def calculate_edge(self, game_id: str, bet_type: BetType,
                      selection: str, line: Optional[float] = None) -> EdgeAssessment:
        """Calculate edge for Soccer bet."""
        context = self.get_game_context(game_id)
        
        if bet_type == BetType.TOTAL:
            # xG-based total estimate
            projected_total = context.home_team_stats["xg_for"] + context.away_team_stats["xg_against"]
            edge = (projected_total - 2.5) / 2.0
        elif "btts" in selection.lower():
            edge = random.uniform(-0.10, 0.10)
        elif "goal" in selection.lower():
            edge = random.uniform(-0.12, 0.12)
        else:
            edge = random.uniform(-0.08, 0.08)
        
        edge = max(-1.0, min(1.0, edge))
        
        return EdgeAssessment(
            edge_score=edge,
            confidence=ConfidenceLevel.MEDIUM,
            reasoning=f"Soccer heuristic: {bet_type.value} based on xG analysis",
            factors={"home_xg": context.home_team_stats["xg_for"], "away_xg": context.away_team_stats["xg_for"]}
        )
    
    def generate_insights(self, game_id: str, tier: str = "GOOD") -> List[Insight]:
        """Generate Soccer insights."""
        context = self.get_game_context(game_id)
        insights = []
        
        if tier in ["GOOD", "BETTER", "BEST"]:
            insights.append(Insight(
                category="Attack",
                title="High xG Matchup",
                description=f"Combined {context.home_team_stats['xg_for'] + context.away_team_stats['xg_for']:.2f} xG per game",
                confidence=ConfidenceLevel.HIGH,
            ))
        
        if tier in ["BETTER", "BEST"]:
            insights.append(Insight(
                category="Form",
                title="Title Race Intensity",
                description="Both teams in top form - expect full effort",
                confidence=ConfidenceLevel.MEDIUM,
            ))
        
        return insights
    
    def assess_matchup(self, game_id: str) -> Dict[str, Any]:
        """Assess Soccer matchup."""
        context = self.get_game_context(game_id)
        return {
            "attack_advantage": "HOME",
            "defense_advantage": "HOME",
            "possession_battle": "City dominant" if context.home_team_stats["possession"] > 60 else "Even",
            "projected_xg": context.home_team_stats["xg_for"] + context.away_team_stats["xg_against"],
            "likely_result": "Home win or draw",
        }


def get_soccer_heuristics() -> SoccerHeuristics:
    return SoccerHeuristics()
