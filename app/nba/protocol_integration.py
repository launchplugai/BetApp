"""
NBA Protocol Integration

Enhances DNA bet analysis with NBA heuristics and context.
"""
import logging
from typing import Dict, List, Optional
from datetime import date
from sqlalchemy.orm import Session

from app.nba.database import get_db_session
from app.nba.models import DimTeam
from app.nba.heuristics import get_comprehensive_edge, NBAHeuristics
from app.nba.cache import get_cache, NBACache

logger = logging.getLogger(__name__)


class NBAProtocolIntegration:
    """Integrate NBA heuristics into bet analysis."""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or get_db_session()
        self.cache = get_cache()
        self.heuristics = NBAHeuristics(self.db)
    
    def enhance_bet_analysis(
        self, 
        bet_text: str,
        teams_involved: List[str],
        game_date: Optional[date] = None
    ) -> Dict:
        """
        Enhance bet analysis with NBA context.
        
        Args:
            bet_text: Raw bet input text
            teams_involved: List of team abbreviations (e.g., ['LAL', 'GSW'])
            game_date: Game date (defaults to today)
        
        Returns:
            Dict with NBA context signals:
            - edge_analysis: Comprehensive heuristics
            - confidence_adjustments: Suggested changes to base confidence
            - risk_flags: List of warning signals
            - context_summary: Human-readable summary
        """
        if not teams_involved or len(teams_involved) < 2:
            return self._empty_response("Insufficient team data")
        
        if game_date is None:
            game_date = date.today()
        
        season = f"{game_date.year}-{str(game_date.year + 1)[-2:]}"
        
        # Normalize team names
        team_ids = []
        for abbrev in teams_involved[:2]:  # Take first two teams
            team = self.db.query(DimTeam).filter_by(
                abbreviation=abbrev.upper()
            ).first()
            if team:
                team_ids.append(team.team_id)
            else:
                # Debug: log missing team
                print(f"DEBUG: Team not found: {abbrev.upper()}")
        
        if len(team_ids) < 2:
            return self._empty_response("Teams not found in database")
        
        team_a_id, team_b_id = team_ids[0], team_ids[1]
        
        # Get comprehensive edge analysis
        edge = get_comprehensive_edge(
            self.db,
            team_a_id,
            team_b_id,
            game_date,
            season
        )
        
        # Analyze for confidence adjustments
        adjustments = self._calculate_confidence_adjustments(edge, bet_text)
        
        # Identify risk flags
        risk_flags = self._identify_risk_flags(edge)
        
        # Generate summary
        summary = self._generate_summary(edge, teams_involved)
        
        return {
            'edge_analysis': edge,
            'confidence_adjustments': adjustments,
            'risk_flags': risk_flags,
            'context_summary': summary,
            'data_quality': self._assess_data_quality(edge)
        }
    
    def _calculate_confidence_adjustments(
        self, 
        edge: Dict, 
        bet_text: str
    ) -> Dict:
        """
        Calculate suggested confidence adjustments based on context.
        
        Returns:
            {
                'rest_adjustment': float (-10 to +10),
                'injury_adjustment': float (-15 to +15),
                'tank_adjustment': float (-20 to +20),
                'playoff_adjustment': float (-5 to +5),
                'total_adjustment': float,
                'reasoning': List[str]
            }
        """
        adjustments = {
            'rest': 0.0,
            'injury': 0.0,
            'tank': 0.0,
            'playoff': 0.0
        }
        reasoning = []
        
        # Rest advantage
        rest = edge.get('rest_advantage', {})
        rest_edge = rest.get('rest_edge', 0)
        
        if abs(rest_edge) > 3:  # Significant rest advantage
            adjustments['rest'] = rest_edge * 1.5  # Scale to confidence points
            reasoning.append(
                f"Rest edge: {rest_edge:+.1f} points "
                f"(Team A: {rest['team_a']['days_rest']}d, "
                f"Team B: {rest['team_b']['days_rest']}d)"
            )
        
        # Injury impact
        injury_a = edge.get('injury_impact', {}).get('team_a', {})
        injury_b = edge.get('injury_impact', {}).get('team_b', {})
        
        war_diff = injury_b.get('total_war_lost', 0) - injury_a.get('total_war_lost', 0)
        
        if abs(war_diff) > 1:
            adjustments['injury'] = war_diff * 3  # WAR to confidence points
            reasoning.append(
                f"Injury impact: {war_diff:+.1f} WAR advantage "
                f"({injury_a.get('severity', 'none')} vs {injury_b.get('severity', 'none')})"
            )
        
        # Tank detection
        tank_a = edge.get('tank_status', {}).get('team_a', {})
        tank_b = edge.get('tank_status', {}).get('team_b', {})
        
        if tank_a.get('is_tanking') or tank_b.get('is_tanking'):
            # Determine bet type from text
            is_underdog_bet = any(x in bet_text.lower() for x in ['+', 'over', 'ml'])
            
            if tank_a.get('is_tanking'):
                adjustment = -10 if not is_underdog_bet else +5
                adjustments['tank'] = adjustment
                reasoning.append(
                    f"Team A likely tanking (confidence: {tank_a.get('confidence', 0):.0%})"
                )
            
            if tank_b.get('is_tanking'):
                adjustment = +10 if not is_underdog_bet else -5
                adjustments['tank'] += adjustment
                reasoning.append(
                    f"Team B likely tanking (confidence: {tank_b.get('confidence', 0):.0%})"
                )
        
        # Playoff context
        playoff_a = edge.get('playoff_context', {}).get('team_a', {})
        playoff_b = edge.get('playoff_context', {}).get('team_b', {})
        
        leverage_diff = playoff_a.get('leverage_index', 50) - playoff_b.get('leverage_index', 50)
        
        if abs(leverage_diff) > 20:
            adjustments['playoff'] = leverage_diff * 0.1
            reasoning.append(
                f"Playoff leverage: Team A {playoff_a.get('leverage_index', 0):.0f}, "
                f"Team B {playoff_b.get('leverage_index', 0):.0f}"
            )
        
        total = sum(adjustments.values())
        
        return {
            **adjustments,
            'total_adjustment': round(total, 1),
            'reasoning': reasoning
        }
    
    def _identify_risk_flags(self, edge: Dict) -> List[str]:
        """Identify warning signals that increase bet risk."""
        flags = []
        
        # Missing data
        if not edge.get('matchup_analysis'):
            flags.append("⚠️ Limited historical matchup data")
        
        # Both teams on back-to-back
        rest = edge.get('rest_advantage', {})
        if (rest.get('team_a', {}).get('days_rest', 99) == 0 and 
            rest.get('team_b', {}).get('days_rest', 99) == 0):
            flags.append("🔴 Both teams on back-to-back (unpredictable)")
        
        # Critical injuries
        injury_a = edge.get('injury_impact', {}).get('team_a', {})
        injury_b = edge.get('injury_impact', {}).get('team_b', {})
        
        if injury_a.get('severity') == 'critical':
            flags.append(f"🔴 Team A: Critical injuries ({injury_a.get('injury_count')} out)")
        if injury_b.get('severity') == 'critical':
            flags.append(f"🔴 Team B: Critical injuries ({injury_b.get('injury_count')} out)")
        
        # Tanking detected
        tank_a = edge.get('tank_status', {}).get('team_a', {})
        tank_b = edge.get('tank_status', {}).get('team_b', {})
        
        if tank_a.get('is_tanking') and tank_a.get('confidence', 0) > 0.7:
            flags.append("🟡 Team A showing tanking behavior")
        if tank_b.get('is_tanking') and tank_b.get('confidence', 0) > 0.7:
            flags.append("🟡 Team B showing tanking behavior")
        
        return flags
    
    def _generate_summary(self, edge: Dict, teams: List[str]) -> str:
        """Generate human-readable context summary."""
        lines = []
        
        # Rest
        rest = edge.get('rest_advantage', {})
        team_a_rest = rest.get('team_a', {}).get('days_rest', 0)
        team_b_rest = rest.get('team_b', {}).get('days_rest', 0)
        
        if team_a_rest == 0 or team_b_rest == 0:
            lines.append(
                f"Rest: {teams[0]} {team_a_rest}d vs {teams[1]} {team_b_rest}d"
            )
        
        # Injuries
        injury_a = edge.get('injury_impact', {}).get('team_a', {})
        injury_b = edge.get('injury_impact', {}).get('team_b', {})
        
        if injury_a.get('injury_count', 0) > 0 or injury_b.get('injury_count', 0) > 0:
            lines.append(
                f"Injuries: {teams[0]} {injury_a.get('injury_count', 0)} out, "
                f"{teams[1]} {injury_b.get('injury_count', 0)} out"
            )
        
        # Matchup
        matchup = edge.get('matchup_analysis', {}).get('head_to_head', {})
        if matchup.get('games_played', 0) > 0:
            lines.append(
                f"H2H: {teams[0]} {matchup.get('team_a_wins', 0)}-"
                f"{matchup.get('team_b_wins', 0)} {teams[1]} this season"
            )
        
        return " | ".join(lines) if lines else "No significant context detected"
    
    def _assess_data_quality(self, edge: Dict) -> str:
        """Assess quality/completeness of data."""
        completeness = 0
        total = 5
        
        if edge.get('rest_advantage'):
            completeness += 1
        if edge.get('injury_impact'):
            completeness += 1
        if edge.get('tank_status'):
            completeness += 1
        if edge.get('playoff_context'):
            completeness += 1
        if edge.get('matchup_analysis'):
            completeness += 1
        
        pct = (completeness / total) * 100
        
        if pct >= 80:
            return "High"
        elif pct >= 60:
            return "Medium"
        else:
            return "Low"
    
    def _empty_response(self, reason: str) -> Dict:
        """Return empty response when data unavailable."""
        return {
            'edge_analysis': {},
            'confidence_adjustments': {
                'total_adjustment': 0.0,
                'reasoning': []
            },
            'risk_flags': [f"⚠️ {reason}"],
            'context_summary': f"No NBA context available: {reason}",
            'data_quality': "None"
        }
    
    def close(self):
        """Close database session."""
        if self.db:
            self.db.close()


# =============================================================================
# Convenience Functions for DNA Pipeline
# =============================================================================

def enhance_nba_bet(bet_text: str, teams: List[str]) -> Dict:
    """
    Quick wrapper for DNA pipeline integration.
    
    Usage:
        from app.nba.protocol_integration import enhance_nba_bet
        
        context = enhance_nba_bet("LAL -4.5", ["LAL", "GSW"])
        if context['confidence_adjustments']['total_adjustment'] < -10:
            # Reduce confidence
    """
    integration = NBAProtocolIntegration()
    try:
        return integration.enhance_bet_analysis(bet_text, teams)
    finally:
        integration.close()
