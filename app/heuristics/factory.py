"""Unified heuristics factory - all sports."""

from typing import Optional, Dict, Any

from app.heuristics.base import SportHeuristics, EdgeAssessment, Insight, GameContext, BetType

# Import all sport heuristics
try:
    from app.heuristics.nba import get_nba_heuristics
except ImportError:
    get_nba_heuristics = None

try:
    from app.heuristics.nfl import get_nfl_heuristics
except ImportError:
    get_nfl_heuristics = None

try:
    from app.heuristics.mlb import get_mlb_heuristics
except ImportError:
    get_mlb_heuristics = None

try:
    from app.heuristics.nhl import get_nhl_heuristics
except ImportError:
    get_nhl_heuristics = None

try:
    from app.heuristics.soccer import get_soccer_heuristics
except ImportError:
    get_soccer_heuristics = None

try:
    from app.heuristics.ufc import get_ufc_heuristics
except ImportError:
    get_ufc_heuristics = None

try:
    from app.heuristics.tennis import get_tennis_heuristics
except ImportError:
    get_tennis_heuristics = None


class HeuristicsFactory:
    """Factory for sport-specific heuristics."""
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def get_heuristics(cls, sport: str) -> Optional[SportHeuristics]:
        """Get heuristics instance for a sport."""
        sport = sport.upper()
        
        if sport in cls._instances:
            return cls._instances[sport]
        
        heuristics = None
        
        if sport == "NBA" and get_nba_heuristics:
            heuristics = get_nba_heuristics()
        elif sport == "NFL" and get_nfl_heuristics:
            heuristics = get_nfl_heuristics()
        elif sport == "MLB" and get_mlb_heuristics:
            heuristics = get_mlb_heuristics()
        elif sport == "NHL" and get_nhl_heuristics:
            heuristics = get_nhl_heuristics()
        elif sport in ["SOCCER", "EPL", "LALIGA", "UCL"] and get_soccer_heuristics:
            heuristics = get_soccer_heuristics()
        elif sport == "UFC" and get_ufc_heuristics:
            heuristics = get_ufc_heuristics()
        elif sport == "TENNIS" and get_tennis_heuristics:
            heuristics = get_tennis_heuristics()
        
        if heuristics:
            cls._instances[sport] = heuristics
        
        return heuristics
    
    @classmethod
    def has_heuristics(cls, sport: str) -> bool:
        """Check if heuristics available for sport."""
        return cls.get_heuristics(sport) is not None
    
    @classmethod
    def list_supported_sports(cls) -> list:
        """List all sports with heuristics support."""
        sports = []
        for sport in ["NBA", "NFL", "MLB", "NHL", "SOCCER", "UFC", "TENNIS"]:
            if cls.has_heuristics(sport):
                sports.append(sport)
        return sports


# Convenience functions
def get_game_insights(sport: str, game_id: str, tier: str = "GOOD") -> list:
    """Get insights for any sport."""
    heuristics = HeuristicsFactory.get_heuristics(sport)
    if heuristics:
        return heuristics.generate_insights(game_id, tier)
    return []


def get_matchup_assessment(sport: str, game_id: str) -> Optional[Dict[str, Any]]:
    """Get matchup assessment for any sport."""
    heuristics = HeuristicsFactory.get_heuristics(sport)
    if heuristics:
        return heuristics.assess_matchup(game_id)
    return None


def get_edge_assessment(sport: str, game_id: str, bet_type: str, 
                        selection: str, line: Optional[float] = None) -> Optional[EdgeAssessment]:
    """Get edge assessment for any sport."""
    heuristics = HeuristicsFactory.get_heuristics(sport)
    if heuristics:
        try:
            bet_type_enum = BetType(bet_type)
            return heuristics.calculate_edge(game_id, bet_type_enum, selection, line)
        except ValueError:
            pass
    return None
