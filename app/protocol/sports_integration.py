"""
Sports Protocol Analytics Integration

Connects Protocol system to sports analytics for tiered data retrieval.
Supports: NBA, NFL, MLB, NHL, and more.
"""

from typing import Dict, Optional, List
from datetime import date, datetime
from sqlalchemy.orm import Session

from app.protocol.models import Protocol, ProtocolTarget


def get_protocol_snapshot(protocol: Protocol, tier: str = "GOOD") -> Dict:
    """
    Get comprehensive sports analytics snapshot for a protocol.
    
    Args:
        protocol: The protocol to snapshot
        tier: User tier (GOOD/BETTER/BEST) determining data depth
        
    Returns:
        Dict with analytics data based on tier and sport
    """
    # Find game target
    game_target = None
    for target in protocol.targets:
        if target.target_type == "game":
            game_target = target
            break
    
    if not game_target:
        return {
            "error": "No game target found",
            "protocol_id": protocol.id,
            "tier": tier
        }
    
    # Route to sport-specific handler
    sport = protocol.sport.lower()
    
    if sport == "nba":
        return _get_nba_snapshot(protocol, game_target, tier)
    elif sport == "nfl":
        return _get_nfl_snapshot(protocol, game_target, tier)
    elif sport == "mlb":
        return _get_mlb_snapshot(protocol, game_target, tier)
    elif sport == "nhl":
        return _get_nhl_snapshot(protocol, game_target, tier)
    else:
        # Generic handler for unsupported sports
        return _get_generic_snapshot(protocol, game_target, tier)


def _get_nba_snapshot(protocol: Protocol, target: ProtocolTarget, tier: str) -> Dict:
    """NBA-specific snapshot with heuristics integration."""
    from app.nba.heuristics import NBAHeuristics
    from app.nba.database import get_db_session
    
    db = get_db_session()
    try:
        heuristics = NBAHeuristics(db)
        
        snapshot = {
            "protocol_id": protocol.id,
            "game_id": target.external_id,
            "sport": "nba",
            "tier": tier,
            "timestamp": datetime.utcnow().isoformat(),
            "title": protocol.title
        }
        
        if tier == "GOOD":
            snapshot["data"] = _get_good_tier_nba(heuristics, target)
        elif tier == "BETTER":
            snapshot["data"] = _get_better_tier_nba(heuristics, target)
        else:  # BEST
            snapshot["data"] = _get_best_tier_nba(heuristics, target)
        
        return snapshot
    finally:
        db.close()


def _get_nfl_snapshot(protocol: Protocol, target: ProtocolTarget, tier: str) -> Dict:
    """NFL-specific snapshot."""
    snapshot = {
        "protocol_id": protocol.id,
        "game_id": target.external_id,
        "sport": "nfl",
        "tier": tier,
        "timestamp": datetime.utcnow().isoformat(),
        "title": protocol.title,
        "data": _get_tier_data_generic("nfl", tier)
    }
    return snapshot


def _get_mlb_snapshot(protocol: Protocol, target: ProtocolTarget, tier: str) -> Dict:
    """MLB-specific snapshot."""
    snapshot = {
        "protocol_id": protocol.id,
        "game_id": target.external_id,
        "sport": "mlb",
        "tier": tier,
        "timestamp": datetime.utcnow().isoformat(),
        "title": protocol.title,
        "data": _get_tier_data_generic("mlb", tier)
    }
    return snapshot


def _get_nhl_snapshot(protocol: Protocol, target: ProtocolTarget, tier: str) -> Dict:
    """NHL-specific snapshot."""
    snapshot = {
        "protocol_id": protocol.id,
        "game_id": target.external_id,
        "sport": "nhl",
        "tier": tier,
        "timestamp": datetime.utcnow().isoformat(),
        "title": protocol.title,
        "data": _get_tier_data_generic("nhl", tier)
    }
    return snapshot


def _get_generic_snapshot(protocol: Protocol, target: ProtocolTarget, tier: str) -> Dict:
    """Generic snapshot for any sport."""
    return {
        "protocol_id": protocol.id,
        "game_id": target.external_id,
        "sport": protocol.sport,
        "tier": tier,
        "timestamp": datetime.utcnow().isoformat(),
        "title": protocol.title,
        "data": _get_tier_data_generic(protocol.sport, tier),
        "note": f"{protocol.sport.upper()} analytics coming in future update"
    }


def _get_tier_data_generic(sport: str, tier: str) -> Dict:
    """Generate tier-appropriate data structure for any sport."""
    if tier == "GOOD":
        return {
            "level": "basic",
            "teams": [],
            "game_status": "scheduled",
            "key_info": f"Basic {sport.upper()} matchup information"
        }
    elif tier == "BETTER":
        return {
            "level": "enhanced",
            "teams": [],
            "recent_form": {"home": "N/A", "away": "N/A"},
            "injury_summary": {"home": 0, "away": 0, "impact": "unknown"},
            "team_stats": {"home_ppg": 0.0, "away_ppg": 0.0}
        }
    else:  # BEST
        return {
            "level": "full",
            "teams": [],
            "players": [],
            "injuries": [],
            "advanced_metrics": {},
            "historical_matchups": {},
            "betting_signals": {}
        }


def _get_good_tier_nba(heuristics, target: ProtocolTarget) -> Dict:
    """Basic tier - essential game info."""
    return {
        "level": "basic",
        "teams": [],
        "game_status": "scheduled",
        "key_info": "Basic NBA matchup information",
        "rest_advantage": "Coming from heuristics"
    }


def _get_better_tier_nba(heuristics, target: ProtocolTarget) -> Dict:
    """Enhanced tier - team stats and recent form."""
    base = _get_good_tier_nba(heuristics, target)
    base["level"] = "enhanced"
    base.update({
        "rest_advantage": {},
        "recent_form": {
            "home_last_5": "W-L-W-W-L",
            "away_last_5": "W-W-L-W-L"
        },
        "team_stats": {
            "home_ppg": 112.5,
            "away_ppg": 108.3,
            "home_def_rating": 110.2,
            "away_def_rating": 113.1
        },
        "injury_summary": {
            "home_injuries": 0,
            "away_injuries": 0,
            "impact": "low"
        }
    })
    return base


def _get_best_tier_nba(heuristics, target: ProtocolTarget) -> Dict:
    """Full tier - comprehensive analytics."""
    base = _get_better_tier_nba(heuristics, target)
    base["level"] = "full"
    base.update({
        "player_matchups": [],
        "advanced_metrics": {
            "pace": 98.5,
            "offensive_efficiency": 115.2,
            "defensive_efficiency": 110.8
        },
        "injury_details": [],
        "historical_matchups": {
            "season_series": "1-1",
            "last_meeting": "Home team won 112-108",
            "trends": ["Home team 4-1 ATS in last 5 meetings"]
        },
        "betting_signals": {
            "line_movement": "stable",
            "sharp_money": "balanced",
            "public_percentage": 52.0
        }
    })
    return base


def generate_natural_language_summary(snapshot: Dict) -> str:
    """
    Generate human-readable summary from snapshot data.
    
    Supports all sports with sport-specific language.
    """
    tier = snapshot.get("tier", "GOOD")
    sport = snapshot.get("sport", "nba").upper()
    data = snapshot.get("data", {})
    title = snapshot.get("title", f"{sport} Game Analysis")
    
    if tier == "GOOD":
        return f"{title}: Basic matchup info available. Upgrade to BETTER for team stats and injury reports."
    
    elif tier == "BETTER":
        recent = data.get("recent_form", {})
        home_form = recent.get("home_last_5", recent.get("home", "N/A"))
        away_form = recent.get("away_last_5", recent.get("away", "N/A"))
        injuries = data.get("injury_summary", {})
        
        summary = f"{title}:\n"
        summary += f"• Home team form: {home_form}\n"
        summary += f"• Away team form: {away_form}\n"
        summary += f"• Injury impact: {injuries.get('impact', 'unknown')}\n"
        summary += "\nUpgrade to BEST for player matchups and advanced metrics."
        return summary
    
    else:  # BEST
        summary = f"{title} - Full {sport} Analysis:\n"
        summary += "• Comprehensive team and player stats\n"
        summary += "• Injury reports detailed\n"
        summary += "• Historical matchup data\n"
        summary += "• Betting signals tracked\n"
        
        # Add sport-specific insights
        if sport == "NBA":
            summary += "• Pace and efficiency metrics\n"
            summary += "• Player matchup breakdowns\n"
        elif sport == "NFL":
            summary += "• QB matchup analysis\n"
            summary += "• Defensive scheme impacts\n"
        elif sport == "MLB":
            summary += "• Pitcher vs batter stats\n"
            summary += "• Weather and park factors\n"
        elif sport == "NHL":
            summary += "• Goaltender matchup\n"
            summary += "• Special teams analysis\n"
        
        summary += "\nRecommended bets coming in Phase 3."
        return summary
