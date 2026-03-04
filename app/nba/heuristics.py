"""
NBA Heuristics Engine

Industry-standard calculations for edge detection:
- Rest advantage (Kubatko/Hollinger research)
- Tank detection (behavioral signals)
- Injury impact (RPM/RAPTOR-based)
- Playoff context (leverage index)
- Matchup analysis (style clashes)
"""
import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.nba.models import (
    DimGame, DimTeam, DimPlayer,
    FactBoxScore, FactTeamBoxScore,
    ContextRestDays, ContextInjury, ContextPlayoffStandings,
    ContextMatchupHistory
)

logger = logging.getLogger(__name__)


class NBAHeuristics:
    """Main heuristics calculation engine."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    # =========================================================================
    # REST ADVANTAGE
    # =========================================================================
    
    def calculate_rest_advantage(
        self, 
        team_id: int, 
        game_date: date
    ) -> Dict[str, float]:
        """
        Calculate rest advantage/disadvantage.
        
        Based on research:
        - Back-to-backs: -4.5 points average
        - 3-in-4 nights: -2.5 points average
        - 3+ days rest: +1.5 points average
        
        Returns dict with:
          - days_rest: int
          - advantage_points: float
          - fatigue_score: float (0-100)
          - games_in_7_days: int
        """
        # Find last game
        last_game = self.db.query(DimGame).filter(
            and_(
                DimGame.game_date < game_date,
                (DimGame.home_team_id == team_id) | 
                (DimGame.away_team_id == team_id),
                DimGame.status == "Final"
            )
        ).order_by(DimGame.game_date.desc()).first()
        
        if not last_game:
            # First game of season or no recent games
            return {
                'days_rest': 7,
                'advantage_points': 0.0,
                'fatigue_score': 0.0,
                'games_in_7_days': 0
            }
        
        days_rest = (game_date - last_game.game_date).days
        
        # Calculate games in last 7 days
        week_ago = game_date - timedelta(days=7)
        games_last_week = self.db.query(func.count(DimGame.game_id)).filter(
            and_(
                DimGame.game_date >= week_ago,
                DimGame.game_date < game_date,
                (DimGame.home_team_id == team_id) | 
                (DimGame.away_team_id == team_id),
                DimGame.status == "Final"
            )
        ).scalar()
        
        # Rest advantage mapping (research-based)
        rest_map = {
            0: -4.5,   # Back-to-back
            1: -2.0,   # 1 day rest
            2: 0.0,    # Normal (2 days)
            3: +1.0,   # Good rest
            4: +1.5,   # Very rested
        }
        advantage = rest_map.get(min(days_rest, 4), +1.5)
        
        # Fatigue score (0 = fresh, 100 = exhausted)
        fatigue = min(100, (games_last_week * 15) + (5 - days_rest) * 10)
        fatigue = max(0, fatigue)
        
        return {
            'days_rest': days_rest,
            'advantage_points': advantage,
            'fatigue_score': fatigue,
            'games_in_7_days': games_last_week
        }
    
    def compare_rest_advantage(
        self, 
        team_a_id: int, 
        team_b_id: int, 
        game_date: date
    ) -> Dict:
        """Compare rest advantage between two teams."""
        team_a_rest = self.calculate_rest_advantage(team_a_id, game_date)
        team_b_rest = self.calculate_rest_advantage(team_b_id, game_date)
        
        return {
            'team_a': team_a_rest,
            'team_b': team_b_rest,
            'rest_edge': team_a_rest['advantage_points'] - team_b_rest['advantage_points'],
            'fatigue_edge': team_b_rest['fatigue_score'] - team_a_rest['fatigue_score']
        }
    
    # =========================================================================
    # TANK DETECTOR
    # =========================================================================
    
    def detect_tanking(
        self, 
        team_id: int, 
        season: str,
        as_of_date: date
    ) -> Dict:
        """
        Detect tanking behavior based on multiple signals.
        
        Signals:
        1. Out of playoff contention (>10 games back after ASB)
        2. Star players sitting frequently ("load management")
        3. Young players getting heavy minutes in blowouts
        4. Defensive effort decline (net rating trend)
        5. Trade activity (selling vets for picks)
        
        Returns:
          - is_tanking: bool
          - confidence: float (0-1)
          - signals: Dict of individual signal scores
        """
        # Signal 1: Playoff elimination status
        standings = self.db.query(ContextPlayoffStandings).filter(
            and_(
                ContextPlayoffStandings.team_id == team_id,
                ContextPlayoffStandings.season == season,
                ContextPlayoffStandings.as_of_date <= as_of_date
            )
        ).order_by(ContextPlayoffStandings.as_of_date.desc()).first()
        
        playoff_signal = 0.0
        if standings:
            if standings.eliminated or standings.games_back > 10:
                playoff_signal = 0.8
            elif standings.games_back > 6:
                playoff_signal = 0.5
        
        # Signal 2: Star player availability (simplified for now)
        # TODO: Track "load management" games vs injury games
        star_availability_signal = 0.0
        
        # Signal 3: Young player minutes (need roster age data)
        # TODO: Track minutes distribution by player age
        youth_minutes_signal = 0.0
        
        # Signal 4: Defensive decline
        # Compare recent net rating to season average
        recent_games = self.db.query(FactTeamBoxScore).join(DimGame).filter(
            and_(
                FactTeamBoxScore.team_id == team_id,
                DimGame.game_date >= as_of_date - timedelta(days=14),
                DimGame.game_date <= as_of_date,
                DimGame.status == "Final"
            )
        ).all()
        
        if len(recent_games) >= 5:
            recent_net_rating = sum(
                bs.net_rating for bs in recent_games if bs.net_rating
            ) / len(recent_games)
            
            # If recent net rating is significantly worse, signal goes up
            # TODO: Compare to season average
            if recent_net_rating and recent_net_rating < -8:
                defensive_signal = 0.6
            else:
                defensive_signal = 0.0
        else:
            defensive_signal = 0.0
        
        # Combine signals (weighted)
        weights = {
            'playoff': 0.5,
            'star_availability': 0.2,
            'youth_minutes': 0.1,
            'defensive': 0.2
        }
        
        tank_score = (
            playoff_signal * weights['playoff'] +
            star_availability_signal * weights['star_availability'] +
            youth_minutes_signal * weights['youth_minutes'] +
            defensive_signal * weights['defensive']
        )
        
        return {
            'is_tanking': tank_score > 0.6,
            'confidence': tank_score,
            'signals': {
                'playoff_elimination': playoff_signal,
                'star_availability': star_availability_signal,
                'youth_minutes': youth_minutes_signal,
                'defensive_decline': defensive_signal
            }
        }
    
    # =========================================================================
    # INJURY IMPACT
    # =========================================================================
    
    def calculate_injury_impact(
        self, 
        team_id: int, 
        as_of_date: date
    ) -> Dict:
        """
        Calculate cumulative injury impact on team.
        
        Uses simplified RAPTOR/BPM-style impact estimation:
        - Average player: 0 WAR
        - Star player: +5 to +10 WAR over replacement
        - Minutes replacement matters (starter vs bench)
        
        Returns:
          - injured_players: List[Dict]
          - total_war_lost: float
          - severity: str (minor, moderate, critical)
        """
        # Get current injuries
        injuries = self.db.query(ContextInjury).join(DimPlayer).filter(
            and_(
                ContextInjury.team_id == team_id,
                ContextInjury.status.in_(['Out', 'Doubtful']),
                ContextInjury.injury_date <= as_of_date,
                (ContextInjury.return_date.is_(None) | 
                 (ContextInjury.return_date > as_of_date))
            )
        ).all()
        
        injured_list = []
        total_impact = 0.0
        
        for injury in injuries:
            player = self.db.query(DimPlayer).filter_by(
                player_id=injury.player_id
            ).first()
            
            # Estimate player value (TODO: use actual RAPTOR/BPM data)
            # For now, use games missed as proxy for impact
            estimated_war = injury.games_missed * 0.1  # Rough estimate
            
            injured_list.append({
                'player_name': player.full_name,
                'injury_type': injury.injury_type,
                'status': injury.status,
                'games_missed': injury.games_missed,
                'estimated_impact': estimated_war
            })
            
            total_impact += estimated_war
        
        # Severity classification
        if total_impact > 5:
            severity = 'critical'
        elif total_impact > 2:
            severity = 'moderate'
        else:
            severity = 'minor'
        
        return {
            'injured_players': injured_list,
            'total_war_lost': round(total_impact, 2),
            'severity': severity,
            'injury_count': len(injured_list)
        }
    
    # =========================================================================
    # PLAYOFF CONTEXT
    # =========================================================================
    
    def get_playoff_context(
        self, 
        team_id: int, 
        season: str,
        as_of_date: date
    ) -> Dict:
        """
        Determine playoff context and game importance.
        
        Returns:
          - current_seed: int
          - games_back: float
          - clinch_number: Optional[int]
          - elimination_number: Optional[int]
          - position_battles: List[str]
          - leverage_index: float (0-100)
        """
        standings = self.db.query(ContextPlayoffStandings).filter(
            and_(
                ContextPlayoffStandings.team_id == team_id,
                ContextPlayoffStandings.season == season,
                ContextPlayoffStandings.as_of_date <= as_of_date
            )
        ).order_by(ContextPlayoffStandings.as_of_date.desc()).first()
        
        if not standings:
            return {
                'current_seed': None,
                'games_back': None,
                'clinch_number': None,
                'elimination_number': None,
                'position_battles': [],
                'leverage_index': 50.0
            }
        
        # Calculate leverage index (game importance)
        # Higher when:
        # - Close to playoff cutoff
        # - Position battles (tied records)
        # - End of season approaching
        
        leverage = 50.0  # Base
        
        if standings.playoff_seed:
            if 7 <= standings.playoff_seed <= 10:
                leverage += 20  # Play-in territory
            elif standings.playoff_seed in [6, 11]:
                leverage += 15  # On the bubble
        
        if standings.clinch_number and standings.clinch_number <= 5:
            leverage += 15  # Close to clinching
        
        if standings.elimination_number and standings.elimination_number <= 5:
            leverage += 20  # Desperation mode
        
        return {
            'current_seed': standings.playoff_seed,
            'games_back': standings.games_back,
            'clinch_number': standings.clinch_number,
            'elimination_number': standings.elimination_number,
            'position_battles': [],  # TODO: Identify tied teams
            'leverage_index': min(100, leverage)
        }
    
    # =========================================================================
    # MATCHUP ANALYSIS
    # =========================================================================
    
    def analyze_matchup(
        self, 
        team_a_id: int, 
        team_b_id: int,
        season: str
    ) -> Dict:
        """
        Deep matchup analysis with historical context.
        
        Returns:
          - head_to_head: Dict (W-L this season)
          - recent_form: Dict (last 10 games for each team)
          - style_clash: Dict (pace, shooting, defense)
          - plus_minus_trend: Dict
        """
        # H2H record this season
        h2h_games = self.db.query(DimGame).filter(
            and_(
                DimGame.season == season,
                ((DimGame.home_team_id == team_a_id) & 
                 (DimGame.away_team_id == team_b_id)) |
                ((DimGame.home_team_id == team_b_id) & 
                 (DimGame.away_team_id == team_a_id)),
                DimGame.status == "Final"
            )
        ).all()
        
        team_a_wins = sum(
            1 for g in h2h_games 
            if (g.home_team_id == team_a_id and g.home_score > g.away_score) or
               (g.away_team_id == team_a_id and g.away_score > g.home_score)
        )
        team_b_wins = len(h2h_games) - team_a_wins
        
        # Recent form (last 10 games)
        team_a_recent = self._get_recent_form(team_a_id, season, n=10)
        team_b_recent = self._get_recent_form(team_b_id, season, n=10)
        
        return {
            'head_to_head': {
                'games_played': len(h2h_games),
                'team_a_wins': team_a_wins,
                'team_b_wins': team_b_wins
            },
            'recent_form': {
                'team_a': team_a_recent,
                'team_b': team_b_recent
            },
            'style_clash': {
                'pace_differential': 0.0,  # TODO: Calculate from box scores
                'shooting_styles': 'similar',  # TODO: 3pt rate comparison
            }
        }
    
    def _get_recent_form(
        self, 
        team_id: int, 
        season: str, 
        n: int = 10
    ) -> Dict:
        """Get recent form (W-L record, scoring)."""
        recent_games = self.db.query(DimGame).filter(
            and_(
                DimGame.season == season,
                (DimGame.home_team_id == team_id) | 
                (DimGame.away_team_id == team_id),
                DimGame.status == "Final"
            )
        ).order_by(DimGame.game_date.desc()).limit(n).all()
        
        wins = 0
        total_pts = 0
        total_pts_allowed = 0
        
        for game in recent_games:
            if game.home_team_id == team_id:
                is_win = game.home_score > game.away_score
                pts = game.home_score
                pts_allowed = game.away_score
            else:
                is_win = game.away_score > game.home_score
                pts = game.away_score
                pts_allowed = game.home_score
            
            if is_win:
                wins += 1
            total_pts += pts or 0
            total_pts_allowed += pts_allowed or 0
        
        games = len(recent_games)
        
        return {
            'record': f"{wins}-{games - wins}",
            'avg_points': round(total_pts / games, 1) if games > 0 else 0,
            'avg_points_allowed': round(total_pts_allowed / games, 1) if games > 0 else 0,
            'net_rating': round((total_pts - total_pts_allowed) / games, 1) if games > 0 else 0
        }


# =============================================================================
# COMPREHENSIVE EDGE ANALYSIS
# =============================================================================

def get_comprehensive_edge(
    db_session: Session,
    team_a_id: int,
    team_b_id: int,
    game_date: date,
    season: str
) -> Dict:
    """
    Get ALL heuristics for a matchup in one call.
    
    This is the main function protocols will call.
    """
    heuristics = NBAHeuristics(db_session)
    
    return {
        'rest_advantage': heuristics.compare_rest_advantage(
            team_a_id, team_b_id, game_date
        ),
        'tank_status': {
            'team_a': heuristics.detect_tanking(team_a_id, season, game_date),
            'team_b': heuristics.detect_tanking(team_b_id, season, game_date)
        },
        'injury_impact': {
            'team_a': heuristics.calculate_injury_impact(team_a_id, game_date),
            'team_b': heuristics.calculate_injury_impact(team_b_id, game_date)
        },
        'playoff_context': {
            'team_a': heuristics.get_playoff_context(team_a_id, season, game_date),
            'team_b': heuristics.get_playoff_context(team_b_id, season, game_date)
        },
        'matchup_analysis': heuristics.analyze_matchup(team_a_id, team_b_id, season)
    }
