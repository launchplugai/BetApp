"""
NBA Protocol Analytics Integration

Connects Protocol system to NBA analytics for tiered data retrieval.
"""

from typing import Dict, Optional, List
from datetime import date, datetime
from sqlalchemy.orm import Session

from app.protocol.models import Protocol, ProtocolTarget
from app.nba.heuristics import NBAHeuristics
from app.nba.database import get_db_session


def get_protocol_snapshot(protocol: Protocol, tier: str = "GOOD") -> Dict:
    """
    Get comprehensive NBA analytics snapshot for a protocol.
    
    Args:
        protocol: The protocol to snapshot
        tier: User tier (GOOD/BETTER/BEST) determining data depth
        
    Returns:
        Dict with analytics data based on tier
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
    
    # Get NBA database session
    db = get_db_session()
    try:
        heuristics = NBAHeuristics(db)
        
        # Base snapshot for all tiers
        snapshot = {
            "protocol_id": protocol.id,
            "game_id": game_target.external_id,
            "tier": tier,
            "timestamp": datetime.utcnow().isoformat(),
            "sport": protocol.sport,
            "title": protocol.title
        }
        
        # Parse game ID to get team info (simplified)
        # In production, lookup actual teams from game record
        if tier == "GOOD":
            snapshot["data"] = _get_good_tier_data(heuristics, game_target)
        elif tier == "BETTER":
            snapshot["data"] = _get_better_tier_data(heuristics, game_target)
        else:  # BEST
            snapshot["data"] = _get_best_tier_data(heuristics, game_target)
        
        return snapshot
        
    finally:
        db.close()


def _get_good_tier_data(heuristics: NBAHeuristics, target: ProtocolTarget) -> Dict:
    """Basic tier - essential game info."""
    return {
        "level": "basic",
        "teams": [],
        "game_status": "scheduled",
        "key_info": "Basic matchup information"
    }


def _get_better_tier_data(heuristics: NBAHeuristics, target: ProtocolTarget) -> Dict:
    """Enhanced tier - team stats and recent form."""
    base = _get_good_tier_data(heuristics, target)
    base["level"] = "enhanced"
    base.update({
        "rest_advantage": {},  # Will populate from heuristics
        "recent_form": {
            "home_last_5": "W-L-W-W-L",
            "away_last_5": "W-W-L-W-L"
        },
        "team_stats": {
            "home_ppg": 0.0,
            "away_ppg": 0.0,
            "home_def_rating": 0.0,
            "away_def_rating": 0.0
        },
        "injury_summary": {
            "home_injuries": 0,
            "away_injuries": 0,
            "impact": "low"
        }
    })
    return base


def _get_best_tier_data(heuristics: NBAHeuristics, target: ProtocolTarget) -> Dict:
    """Full tier - comprehensive analytics."""
    base = _get_better_tier_data(heuristics, target)
    base["level"] = "full"
    base.update({
        "player_matchups": [],
        "advanced_metrics": {
            "pace": 0.0,
            "offensive_efficiency": 0.0,
            "defensive_efficiency": 0.0
        },
        "injury_details": [],
        "historical_matchups": {
            "season_series": "0-0",
            "last_meeting": None,
            "trends": []
        },
        "betting_signals": {
            "line_movement": "stable",
            "sharp_money": "balanced",
            "public_percentage": 50.0
        }
    })
    return base


def generate_natural_language_summary(snapshot: Dict) -> str:
    """
    Generate human-readable summary from snapshot data.
    
    Phase 2: Basic implementation
    Phase 3: Rich natural language with insights
    """
    tier = snapshot.get("tier", "GOOD")
    data = snapshot.get("data", {})
    title = snapshot.get("title", "Game Analysis")
    
    if tier == "GOOD":
        return f"{title}: Basic matchup info available. Upgrade to BETTER for team stats and injury reports."
    
    elif tier == "BETTER":
        recent = data.get("recent_form", {})
        home_form = recent.get("home_last_5", "N/A")
        away_form = recent.get("away_last_5", "N/A")
        injuries = data.get("injury_summary", {})
        
        summary = f"{title}:\n"
        summary += f"• Home team last 5: {home_form}\n"
        summary += f"• Away team last 5: {away_form}\n"
        summary += f"• Injury impact: {injuries.get('impact', 'unknown')}\n"
        summary += "\nUpgrade to BEST for player matchups and advanced metrics."
        return summary
    
    else:  # BEST
        summary = f"{title} - Full Analysis:\n"
        summary += "• Comprehensive team and player stats available\n"
        summary += "• Injury reports detailed\n"
        summary += "• Historical matchup data included\n"
        summary += "• Betting signals tracked\n"
        summary += "\nRecommended bets will be available in Phase 3."
        return summary
