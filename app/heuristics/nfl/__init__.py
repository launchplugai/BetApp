"""NFL Heuristics Module."""

from typing import List, Dict, Any, Optional
import random

from app.heuristics.base import (
    SportHeuristics, GameContext, PlayerStats, EdgeAssessment, 
    Insight, ConfidenceLevel, BetType
)


class NFLHeuristics:
    """NFL analytics and heuristics."""
    
    # Mock player database
    PLAYERS = {
        "patrick_mahomes": {"name": "Patrick Mahomes", "team": "KC", "pos": "QB"},
        "josh_allen": {"name": "Josh Allen", "team": "BUF", "pos": "QB"},
        "travis_kelce": {"name": "Travis Kelce", "team": "KC", "pos": "TE"},
        "stefon_diggs": {"name": "Stefon Diggs", "team": "BUF", "pos": "WR"},
    }
    
    def get_game_context(self, game_id: str) -> GameContext:
        """Get NFL game context with team stats."""
        # Mock data - would come from database/API
        return GameContext(
            game_id=game_id,
            home_team="Chiefs" if "chiefs" in game_id else "Home",
            away_team="Bills" if "bills" in game_id else "Away",
            home_team_stats={
                "offense_rank": 3,
                "defense_rank": 15,
                "pass_offense": 2,
                "rush_offense": 12,
                "points_per_game": 28.5,
                "points_allowed": 20.3,
                "turnover_diff": +8,
            },
            away_team_stats={
                "offense_rank": 5,
                "defense_rank": 8,
                "pass_offense": 4,
                "rush_offense": 6,
                "points_per_game": 26.8,
                "points_allowed": 19.5,
                "turnover_diff": +12,
            },
            situational_factors={
                "home_field_advantage": 2.5,
                "rest_advantage": 0,  # Days rest differential
                "weather_impact": "neutral",
                "playoff_implications": "high",
            }
        )
    
    def get_player_stats(self, player_id: str) -> PlayerStats:
        """Get NFL player statistics."""
        player = self.PLAYERS.get(player_id, {"name": "Unknown", "team": "UNK", "pos": "QB"})
        
        # Mock stats based on position
        if player["pos"] == "QB":
            recent_form = [285.5, 310.2, 245.0, 355.8, 290.5]  # Passing yards
            season_avg = 297.4
            vs_opp = 275.5
        elif player["pos"] == "TE":
            recent_form = [72.5, 85.0, 65.5, 90.2, 78.0]  # Receiving yards
            season_avg = 78.2
            vs_opp = 82.5
        else:  # WR
            recent_form = [85.5, 72.0, 95.5, 68.5, 88.0]
            season_avg = 82.0
            vs_opp = 79.5
        
        return PlayerStats(
            player_id=player_id,
            player_name=player["name"],
            recent_form=recent_form,
            season_average=season_avg,
            vs_opponent_average=vs_opp,
            home_away_split={"home": season_avg + 8.5, "away": season_avg - 5.2},
            custom_metrics={
                "red_zone_targets": 4.5,
                "snap_count_pct": 88.5,
                "fantasy_points_per_game": 18.5,
            }
        )
    
    def calculate_edge(self, game_id: str, bet_type: BetType, 
                      selection: str, line: Optional[float] = None) -> EdgeAssessment:
        """Calculate edge for NFL bet."""
        context = self.get_game_context(game_id)
        
        # Simple edge calculation based on matchup
        if bet_type == BetType.SPREAD:
            home_advantage = context.situational_factors["home_field_advantage"]
            off_rank_diff = context.away_team_stats["offense_rank"] - context.home_team_stats["offense_rank"]
            edge = (home_advantage + off_rank_diff * 0.3) / 10
        elif bet_type == BetType.TOTAL:
            # High-powered offenses = over lean
            combined_ppg = context.home_team_stats["points_per_game"] + context.away_team_stats["points_per_game"]
            edge = (combined_ppg - 45) / 20  # Normalize around 45
        elif bet_type == BetType.PLAYER_PROP:
            edge = random.uniform(-0.15, 0.15)  # Mock player analysis
        else:
            edge = random.uniform(-0.1, 0.1)
        
        # Clamp to -1, 1
        edge = max(-1.0, min(1.0, edge))
        
        return EdgeAssessment(
            edge_score=edge,
            confidence=ConfidenceLevel.MEDIUM if abs(edge) > 0.1 else ConfidenceLevel.LOW,
            reasoning=f"NFL heuristic: {bet_type.value} analysis based on team rankings and matchup history",
            factors={"home_advantage": context.situational_factors["home_field_advantage"]}
        )
    
    def generate_insights(self, game_id: str, tier: str = "GOOD") -> List[Insight]:
        """Generate NFL-specific insights."""
        context = self.get_game_context(game_id)
        insights = []
        
        if tier in ["GOOD", "BETTER", "BEST"]:
            insights.append(Insight(
                category="Offense",
                title="High-Powered Matchup",
                description=f"Combined {context.home_team_stats['points_per_game'] + context.away_team_stats['points_per_game']:.1f} PPG expected",
                confidence=ConfidenceLevel.MEDIUM,
                supporting_data={"home_ppg": context.home_team_stats["points_per_game"]}
            ))
        
        if tier in ["BETTER", "BEST"]:
            insights.append(Insight(
                category="Matchup",
                title="Pass Defense Test",
                description="Both teams top-10 in pass offense vs average pass defense",
                confidence=ConfidenceLevel.HIGH,
            ))
        
        if tier == "BEST":
            insights.append(Insight(
                category="Situational",
                title="Rest Advantage",
                description="Home team on extra rest, historically 55% ATS in this spot",
                confidence=ConfidenceLevel.MEDIUM,
            ))
        
        return insights
    
    def assess_matchup(self, game_id: str) -> Dict[str, Any]:
        """Assess NFL matchup."""
        context = self.get_game_context(game_id)
        
        return {
            "offense_advantage": "EVEN" if abs(context.home_team_stats["offense_rank"] - context.away_team_stats["offense_rank"]) < 5 else "HOME" if context.home_team_stats["offense_rank"] < context.away_team_stats["offense_rank"] else "AWAY",
            "defense_advantage": "HOME" if context.home_team_stats["defense_rank"] < context.away_team_stats["defense_rank"] else "AWAY",
            "projected_total": context.home_team_stats["points_per_game"] + context.away_team_stats["points_per_game"],
            "pace_factor": "UP-TEMPO",  # Would calculate from play-by-play
            "key_matchup": "Chiefs Pass Rush vs Bills OL",
        }


def get_nfl_heuristics() -> NFLHeuristics:
    """Factory function for NFL heuristics."""
    return NFLHeuristics()
