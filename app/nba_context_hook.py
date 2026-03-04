"""
NBA Context Hook for DNA Pipeline

Injects NBA heuristics into bet evaluation.
"""
import logging
from typing import Optional, List, Dict
from datetime import date

logger = logging.getLogger(__name__)


def inject_nba_context(
    bet_text: str,
    parsed_legs: List,
    tier: str
) -> Optional[Dict]:
    """
    Inject NBA context into bet evaluation.
    
    Args:
        bet_text: Raw bet input text
        parsed_legs: Parsed BetBlock legs
        tier: User tier (GOOD/BETTER/BEST)
        
    Returns:
        NBA context dict or None if not applicable
    """
    # Only run for BETTER/BEST tiers or if NBA teams detected
    if tier == "GOOD":
        return None
    
    # Extract NBA teams from legs
    nba_teams = _extract_nba_teams(parsed_legs)
    
    if not nba_teams or len(nba_teams) < 2:
        return None
    
    try:
        from app.nba.protocol_integration import enhance_nba_bet
        
        context = enhance_nba_bet(
            bet_text=bet_text,
            teams=nba_teams
        )
        
        # Only return if data quality is sufficient
        if context['data_quality'] in ['High', 'Medium']:
            return context
        
        return None
        
    except Exception as e:
        logger.error(f"NBA context injection failed: {e}")
        return None


def _extract_nba_teams(legs: List) -> List[str]:
    """
    Extract NBA team abbreviations from parsed legs.
    
    Returns list of 2-3 letter team codes (e.g., ['LAL', 'GSW'])
    """
    teams = []
    
    # Common NBA team patterns
    nba_abbrevs = {
        'LAL', 'GSW', 'LAC', 'BOS', 'MIL', 'PHI', 'BRK', 'TOR',
        'CHI', 'CLE', 'DET', 'IND', 'MIA', 'ATL', 'CHA', 'ORL',
        'WAS', 'NYK', 'DEN', 'MIN', 'OKC', 'POR', 'UTA', 'PHX',
        'SAC', 'DAL', 'HOU', 'MEM', 'NOP', 'SAS'
    }
    
    for leg in legs:
        entity = getattr(leg, 'entity', '').upper()
        
        # Check if entity is NBA team code
        if entity in nba_abbrevs:
            if entity not in teams:
                teams.append(entity)
        
        # Extract from common formats like "Lakers" → "LAL"
        team_map = {
            'LAKERS': 'LAL', 'WARRIORS': 'GSW', 'CLIPPERS': 'LAC',
            'CELTICS': 'BOS', 'BUCKS': 'MIL', 'SIXERS': 'PHI',
            # Add more as needed
        }
        
        for keyword, abbrev in team_map.items():
            if keyword in entity and abbrev not in teams:
                teams.append(abbrev)
    
    return teams


def format_nba_context_for_ui(context: Dict) -> Dict:
    """
    Format NBA context for UI display.
    
    Converts backend format to frontend-friendly structure.
    """
    if not context:
        return {}
    
    adjustments = context.get('confidence_adjustments', {})
    
    return {
        'nba_context_available': True,
        'confidence_adjustment': adjustments.get('total_adjustment', 0),
        'context_summary': context.get('context_summary', ''),
        'risk_flags': context.get('risk_flags', []),
        'data_quality': context.get('data_quality', 'None'),
        'details': {
            'rest': adjustments.get('rest', 0),
            'injury': adjustments.get('injury', 0),
            'tank': adjustments.get('tank', 0),
            'playoff': adjustments.get('playoff', 0)
        },
        'reasoning': adjustments.get('reasoning', [])
    }
