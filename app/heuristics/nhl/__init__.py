"""NHL Heuristics Module."""

from typing import List, Dict, Any, Optional
import random

from app.heuristics.base import (
    SportHeuristics, GameContext, PlayerStats, EdgeAssessment,
    Insight, ConfidenceLevel, BetType
)


class NHLHeuristics:
    """NHL analytics and heuristics."""
    
    SKATERS = {
        "auston_matthews": {"name": "Auston Matthews", "team": "TOR", "goals": 45, "points": 85},
        "david_pastrnak": {"name": "David Pastrnak", "team": "BOS", "goals": 42, "points": 82},
    }
    
    GOALIES = {
        "ilya_samsonov": {"name": "Ilya Samsonov", "team": "TOR", "sv_pct": 0.912, "gaa": 2.45},
        "jeremy_swayman": {"name": "Jeremy Swayman", "team": "BOS", "sv_pct": 0.915, "gaa": 2.35},
    }
    
    def get_game_context(self, game_id: str) -> GameContext:
        """Get NHL game context."""
        return GameContext(
            game_id=game_id,
            home_team="Maple Leafs" if "leafs" in game_id else "Home",
            away_team="Bruins" if "bruins" in game_id else "Away",
            home_team_stats={
                "goals_per_game": 3.45,
                "goals_against": 2.85,
                "power_play_pct": 24.5,
                "penalty_kill_pct": 82.0,
                "shots_per_game": 32.5,
                "home_record": "28-8-3",
            },
            away_team_stats={
                "goals_per_game": 3.15,
                "goals_against": 2.55,
                "power_play_pct": 22.0,
                "penalty_kill_pct": 85.5,
                "shots_per_game": 30.2,
                "away_record": "22-12-4",
            },
            situational_factors={
                "rest_days": 2,
                "back_to_back": False,
                "goalie_matchup": "Samsonov vs Swayman",
                "special_teams_diff": 2.5,  # PP% diff - PK% diff
            }
        )
    
    def get_player_stats(self, player_id: str) -> PlayerStats:
        """Get NHL player stats."""
        if player_id in self.GOALIES:
            goalie = self.GOALIES[player_id]
            return PlayerStats(
                player_id=player_id,
                player_name=goalie["name"],
                recent_form=[28, 31, 26, 29, 30],  # Saves
                season_average=28.5,
                vs_opponent_average=29.2,
                custom_metrics={
                    "sv_pct": goalie["sv_pct"],
                    "gaa": goalie["gaa"],
                    "quality_starts": 35,
                    "shutouts": 3,
                }
            )
        else:
            skater = self.SKATERS.get(player_id, {"name": "Unknown", "goals": 20, "points": 50})
            return PlayerStats(
                player_id=player_id,
                player_name=skater["name"],
                recent_form=[1, 0, 1, 2, 0],  # Points
                season_average=0.95,
                vs_opponent_average=1.1,
                custom_metrics={
                    "goals": skater["goals"],
                    "points": skater["points"],
                    "shots_per_game": 3.8,
                    "ice_time": 19.5,
                }
            )
    
    def calculate_edge(self, game_id: str, bet_type: BetType,
                      selection: str, line: Optional[float] = None) -> EdgeAssessment:
        """Calculate edge for NHL bet."""
        context = self.get_game_context(game_id)
        
        if bet_type == BetType.TOTAL:
            # Low-scoring sport - totals around 6
            avg_goals = context.home_team_stats["goals_per_game"] + context.away_team_stats["goals_against"]
            edge = (avg_goals - 6.0) / 4.0
        elif "goalie" in selection.lower() or "saves" in selection.lower():
            edge = random.uniform(-0.10, 0.10)
        else:
            edge = random.uniform(-0.12, 0.12)
        
        edge = max(-1.0, min(1.0, edge))
        
        return EdgeAssessment(
            edge_score=edge,
            confidence=ConfidenceLevel.MEDIUM,
            reasoning=f"NHL heuristic: {bet_type.value} analysis with goalie matchup",
            factors={"rest_days": context.situational_factors["rest_days"]}
        )
    
    def generate_insights(self, game_id: str, tier: str = "GOOD") -> List[Insight]:
        """Generate NHL insights."""
        context = self.get_game_context(game_id)
        insights = []
        
        if tier in ["GOOD", "BETTER", "BEST"]:
            insights.append(Insight(
                category="Goaltending",
                title="Elite Goalie Duel",
                description="Both goalies above .910 SV% - expect low-scoring",
                confidence=ConfidenceLevel.HIGH,
            ))
        
        if tier in ["BETTER", "BEST"]:
            pp_diff = context.home_team_stats["power_play_pct"] - context.away_team_stats["penalty_kill_pct"]
            insights.append(Insight(
                category="Special Teams",
                title="PP Advantage",
                description=f"Leafs PP {context.home_team_stats['power_play_pct']:.1f}% vs Bruins PK {context.away_team_stats['penalty_kill_pct']:.1f}%",
                confidence=ConfidenceLevel.MEDIUM,
            ))
        
        return insights
    
    def assess_matchup(self, game_id: str) -> Dict[str, Any]:
        """Assess NHL matchup."""
        context = self.get_game_context(game_id)
        return {
            "goaltending_advantage": "EVEN",
            "offense_advantage": "HOME",
            "special_teams": "HOME",
            "projected_goals": context.home_team_stats["goals_per_game"] + context.away_team_stats["goals_per_game"],
            "likely_first_period": "TIGHT CHECKING",
        }


def get_nhl_heuristics() -> NHLHeuristics:
    return NHLHeuristics()
