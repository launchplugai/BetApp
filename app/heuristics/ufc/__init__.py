"""UFC Heuristics Module."""

from typing import List, Dict, Any, Optional
import random

from app.heuristics.base import (
    SportHeuristics, GameContext, PlayerStats, EdgeAssessment,
    Insight, ConfidenceLevel, BetType
)


class UFCHeuristics:
    """UFC/MMA analytics and heuristics."""
    
    FIGHTERS = {
        "islam_makhachev": {"name": "Islam Makhachev", "record": "25-1", "weight": "Lightweight"},
        "charles_oliveira": {"name": "Charles Oliveira", "record": "34-9", "weight": "Lightweight"},
        "sean_omalley": {"name": "Sean O'Malley", "record": "17-1", "weight": "Bantamweight"},
    }
    
    def get_game_context(self, game_id: str) -> GameContext:
        """Get UFC fight context."""
        return GameContext(
            game_id=game_id,
            home_team="Islam Makhachev" if "makhachev" in game_id else "Fighter A",
            away_team="Charles Oliveira" if "oliveira" in game_id else "Fighter B",
            home_team_stats={
                "striking_accuracy": 58.5,
                "takedown_accuracy": 65.0,
                "significant_strikes_per_min": 4.2,
                "takedowns_per_15min": 3.5,
                "submission_avg": 1.2,
                "reach_inches": 70,
            },
            away_team_stats={
                "striking_accuracy": 52.0,
                "takedown_accuracy": 42.0,
                "significant_strikes_per_min": 3.8,
                "takedowns_per_15min": 1.8,
                "submission_avg": 2.5,
                "reach_inches": 74,
            },
            situational_factors={
                "title_fight": True,
                "five_rounds": True,
                "weight_class": "Lightweight",
                "championship_pressure": "high",
            }
        )
    
    def get_player_stats(self, player_id: str) -> PlayerStats:
        """Get UFC fighter stats."""
        fighter = self.FIGHTERS.get(player_id, {"name": "Unknown", "record": "0-0", "weight": "Unknown"})
        return PlayerStats(
            player_id=player_id,
            player_name=fighter["name"],
            recent_form=[1, 1, 1, 1, 1],  # Win streak
            season_average=1.0,  # Win rate
            vs_opponent_average=0.0,  # No prior meeting
            custom_metrics={
                "record": fighter["record"],
                "weight_class": fighter["weight"],
                "knockout_power": 7.5,
                "grappling_skill": 9.0 if "makhachev" in player_id else 8.5,
                "cardio": 8.5,
            }
        )
    
    def calculate_edge(self, game_id: str, bet_type: BetType,
                      selection: str, line: Optional[float] = None) -> EdgeAssessment:
        """Calculate edge for UFC bet."""
        context = self.get_game_context(game_id)
        
        if "submission" in selection.lower():
            edge = 0.15 if "makhachev" in selection.lower() else 0.10
        elif "ko" in selection.lower() or "tko" in selection.lower():
            edge = random.uniform(-0.05, 0.15)
        elif "decision" in selection.lower():
            edge = random.uniform(-0.10, 0.10)
        else:
            edge = random.uniform(-0.08, 0.08)
        
        edge = max(-1.0, min(1.0, edge))
        
        return EdgeAssessment(
            edge_score=edge,
            confidence=ConfidenceLevel.MEDIUM,
            reasoning=f"UFC heuristic: Grappling advantage in 5-round title fight",
            factors={"takedown_diff": context.home_team_stats["takedowns_per_15min"] - context.away_team_stats["takedowns_per_15min"]}
        )
    
    def generate_insights(self, game_id: str, tier: str = "GOOD") -> List[Insight]:
        """Generate UFC insights."""
        context = self.get_game_context(game_id)
        insights = []
        
        if tier in ["GOOD", "BETTER", "BEST"]:
            insights.append(Insight(
                category="Grappling",
                title="Wrestling Advantage",
                description=f"Makhachev's {context.home_team_stats['takedown_accuracy']:.0f}% TD accuracy vs Oliveira's {context.away_team_stats['takedown_accuracy']:.0f}% defense",
                confidence=ConfidenceLevel.HIGH,
            ))
        
        if tier in ["BETTER", "BEST"]:
            insights.append(Insight(
                category="Striking",
                title="Reach Disadvantage",
                description=f"Makhachev -4 inch reach but better accuracy ({context.home_team_stats['striking_accuracy']:.1f}%)",
                confidence=ConfidenceLevel.MEDIUM,
            ))
        
        return insights
    
    def assess_matchup(self, game_id: str) -> Dict[str, Any]:
        """Assess UFC matchup."""
        context = self.get_game_context(game_id)
        return {
            "grappling_advantage": "FIGHTER_A",
            "striking_advantage": "EVEN",
            "cardio_advantage": "FIGHTER_A",
            "submission_threat": "BOTH",
            "likely_finish": "Submission or Late TKO",
        }


def get_ufc_heuristics() -> UFCHeuristics:
    return UFCHeuristics()
