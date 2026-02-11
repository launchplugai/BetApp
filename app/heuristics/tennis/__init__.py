"""Tennis Heuristics Module."""

from typing import List, Dict, Any, Optional
import random

from app.heuristics.base import (
    SportHeuristics, GameContext, PlayerStats, EdgeAssessment,
    Insight, ConfidenceLevel, BetType
)


class TennisHeuristics:
    """Tennis analytics and heuristics."""
    
    PLAYERS = {
        "carlos_alcaraz": {"name": "Carlos Alcaraz", "rank": 2, "surface": "grass"},
        "novak_djokovic": {"name": "Novak Djokovic", "rank": 1, "surface": "grass"},
        "iga_swiatek": {"name": "Iga Swiatek", "rank": 1, "surface": "hard"},
    }
    
    def get_game_context(self, game_id: str) -> GameContext:
        """Get Tennis match context."""
        is_grand_slam = "wimbledon" in game_id or "uso" in game_id or "french" in game_id or "aus" in game_id
        is_grass = "wimbledon" in game_id
        
        return GameContext(
            game_id=game_id,
            home_team="Carlos Alcaraz" if "alcaraz" in game_id else "Player A",
            away_team="Novak Djokovic" if "djokovic" in game_id else "Player B",
            home_team_stats={
                "first_serve_pct": 62.5,
                "first_serve_win_pct": 75.0,
                "second_serve_win_pct": 55.0,
                "break_point_save": 65.0,
                "return_points_won": 42.0,
                "aces_per_match": 8.5,
            },
            away_team_stats={
                "first_serve_pct": 68.0,
                "first_serve_win_pct": 78.0,
                "second_serve_win_pct": 58.0,
                "break_point_save": 72.0,
                "return_points_won": 45.0,
                "aces_per_match": 6.2,
            },
            situational_factors={
                "grand_slam": is_grand_slam,
                "best_of": 5 if is_grand_slam else 3,
                "surface": "grass" if is_grass else "hard",
                "sets_for_win": 3 if is_grand_slam else 2,
            }
        )
    
    def get_player_stats(self, player_id: str) -> PlayerStats:
        """Get Tennis player stats."""
        player = self.PLAYERS.get(player_id, {"name": "Unknown", "rank": 50, "surface": "hard"})
        return PlayerStats(
            player_id=player_id,
            player_name=player["name"],
            recent_form=[20, 18, 22, 25, 19],  # Games won per match
            season_average=20.5,
            vs_opponent_average=21.0,
            custom_metrics={
                "rank": player["rank"],
                "surface": player["surface"],
                "tiebreak_win_pct": 58.5,
                "deciding_set_record": "12-3",
                "grand_slam_titles": 2 if "alcaraz" in player_id else 24 if "djokovic" in player_id else 5,
            }
        )
    
    def calculate_edge(self, game_id: str, bet_type: BetType,
                      selection: str, line: Optional[float] = None) -> EdgeAssessment:
        """Calculate edge for Tennis bet."""
        context = self.get_game_context(game_id)
        
        if "set" in selection.lower() and "spread" not in selection.lower():
            # Exact sets
            edge = random.uniform(-0.10, 0.10)
        elif "game" in selection.lower() or "total" in selection.lower():
            # Game totals
            serve_advantage = context.home_team_stats["first_serve_win_pct"] - context.away_team_stats["return_points_won"]
            edge = (serve_advantage - 30) / 100
        else:
            edge = random.uniform(-0.12, 0.12)
        
        edge = max(-1.0, min(1.0, edge))
        
        return EdgeAssessment(
            edge_score=edge,
            confidence=ConfidenceLevel.MEDIUM,
            reasoning=f"Tennis heuristic: {context.situational_factors['surface']} court analysis",
            factors={"grand_slam": context.situational_factors["grand_slam"], "surface": context.situational_factors["surface"]}
        )
    
    def generate_insights(self, game_id: str, tier: str = "GOOD") -> List[Insight]:
        """Generate Tennis insights."""
        context = self.get_game_context(game_id)
        insights = []
        
        if tier in ["GOOD", "BETTER", "BEST"]:
            insights.append(Insight(
                category="Serving",
                title="Serve Battle",
                description=f"Djokovic {context.away_team_stats['first_serve_win_pct']:.0f}% 1st serve vs Alcaraz {context.home_team_stats['return_points_won']:.0f}% return",
                confidence=ConfidenceLevel.HIGH,
            ))
        
        if tier in ["BETTER", "BEST"]:
            format_note = "Best of 5" if context.situational_factors["grand_slam"] else "Best of 3"
            insights.append(Insight(
                category="Format",
                title=f"{format_note} Format",
                description="Fitness and mental strength magnified in longer matches",
                confidence=ConfidenceLevel.MEDIUM,
            ))
        
        return insights
    
    def assess_matchup(self, game_id: str) -> Dict[str, Any]:
        """Assess Tennis matchup."""
        context = self.get_game_context(game_id)
        return {
            "serve_advantage": "PLAYER_B" if context.away_team_stats["first_serve_win_pct"] > context.home_team_stats["first_serve_win_pct"] else "PLAYER_A",
            "return_advantage": "PLAYER_B" if context.away_team_stats["return_points_won"] > context.home_team_stats["return_points_won"] else "EVEN",
            "experience_edge": "PLAYER_B",  # Djokovic
            "projected_sets": 4 if context.situational_factors["grand_slam"] else 2,
            "likely_duration": "Long (4+ hours)" if context.situational_factors["grand_slam"] else "Medium (2-3 hours)",
        }


def get_tennis_heuristics() -> TennisHeuristics:
    return TennisHeuristics()
