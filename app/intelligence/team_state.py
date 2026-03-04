"""
Team State Detection

Deterministic competitive state classification.
No ML. Pure signal aggregation.
"""

from typing import Optional
from datetime import datetime
from app.intelligence import TeamCompetitiveState, IncentiveIntelligence, AlignmentType


def calculate_tanking_score(
    wins: int,
    losses: int,
    games_remaining: int,
    star_players_sitting: int = 0,
    youth_minutes_pct: float = 0.0,
    defensive_effort_drop: float = 0.0,  # vs season avg
    trade_asset_pct: float = 0.0,        # key players traded
) -> float:
    """
    Bounded tanking detection. Returns 0.0-1.0.
    
    Signals (weighted):
    - Record context (30%): Bad record + games remaining
    - Star sitting (25%): Load management in losses
    - Youth minutes (20%): Playing young players heavy minutes
    - Defensive effort (15%): Easier to tank via defense
    - Trade activity (10%): Trading away win-now players
    """
    # Guardrails: clamp inputs
    youth_minutes_pct = max(0.0, min(1.0, youth_minutes_pct))
    defensive_effort_drop = max(0.0, min(1.0, defensive_effort_drop))
    trade_asset_pct = max(0.0, min(1.0, trade_asset_pct))
    star_players_sitting = max(0, min(5, star_players_sitting))
    
    total_games = wins + losses + games_remaining
    if total_games == 0:
        return 0.0
    
    # Record context: worse record + more games left = higher tank probability
    win_pct = wins / (wins + losses) if (wins + losses) > 0 else 0.5
    record_score = (1.0 - win_pct) * (games_remaining / 20)  # max at 20 games left
    record_component = min(1.0, record_score) * 0.30
    
    # Star sitting: normalized by expected stars (assume 2-3)
    star_component = min(1.0, star_players_sitting / 2.5) * 0.25
    
    # Youth minutes: direct pct
    youth_component = youth_minutes_pct * 0.20
    
    # Defensive effort drop: direct pct
    defense_component = defensive_effort_drop * 0.15
    
    # Trade assets: direct pct
    trade_component = trade_asset_pct * 0.10
    
    total = record_component + star_component + youth_component + defense_component + trade_component
    return round(min(1.0, max(0.0, total)), 4)


def classify_competitive_state(
    wins: int,
    losses: int,
    games_remaining: int,
    playoff_position: Optional[int] = None,
    games_back: float = 0.0,
    clinch_number: Optional[int] = None,
    elimination_number: Optional[int] = None,
    tanking_score: float = 0.0,
) -> TeamCompetitiveState:
    """
    Deterministic state classification.
    Priority: Eliminated -> Clinched -> Tanking -> Playoff hunt -> Contending
    """
    # Guardrails
    tanking_score = max(0.0, min(1.0, tanking_score))
    
    # Clear conflict: contract year but minutes dropping
    if elimination_number is not None and elimination_number <= 0:
        return TeamCompetitiveState.DEVELOPMENT
    
    if clinch_number is not None and clinch_number <= 0:
        return TeamCompetitiveState.RESTING
    
    # Tanking threshold (explicit)
    if tanking_score > 0.70:
        return TeamCompetitiveState.TANKING
    
    # Playoff context
    if playoff_position is not None:
        if playoff_position <= 6:
            return TeamCompetitiveState.CONTENDING
        elif playoff_position <= 10:
            return TeamCompetitiveState.PLAY_IN
    
    # Games back heuristic
    if games_back > 3.0 and games_remaining < 15:
        return TeamCompetitiveState.PLAY_IN
    
    if games_back > 6.0:
        return TeamCompetitiveState.PLAYOFF_HUNTING
    
    return TeamCompetitiveState.CONTENDING


def calculate_rotation_stability(
    lineup_changes_last_10: int = 0,
    minutes_variance_pct: float = 0.0,
    back_to_backs: int = 0,
    rest_days_avg: float = 2.0,
) -> float:
    """
    Rotation stability score. Higher = more predictable minutes.
    Returns 0.0-1.0.
    
    Factors:
    - Lineup consistency (40%)
    - Minutes distribution (30%)
    - Rest schedule (30%)
    """
    # Guardrails
    lineup_changes_last_10 = max(0, min(10, lineup_changes_last_10))
    minutes_variance_pct = max(0.0, min(1.0, minutes_variance_pct))
    back_to_backs = max(0, min(5, back_to_backs))
    rest_days_avg = max(0.0, min(7.0, rest_days_avg))
    
    # Lineup consistency: fewer changes = higher stability
    lineup_score = 1.0 - (lineup_changes_last_10 / 10)
    lineup_component = lineup_score * 0.40
    
    # Minutes variance: lower variance = higher stability
    minutes_score = 1.0 - minutes_variance_pct
    minutes_component = minutes_score * 0.30
    
    # Rest schedule: more rest = higher stability
    rest_score = min(1.0, rest_days_avg / 3.0)  # 3+ days = full score
    rest_penalty = back_to_backs * 0.15  # each B2B penalizes
    rest_component = max(0.0, rest_score - rest_penalty) * 0.30
    
    # Aggregate
    total = lineup_component + minutes_component + rest_component
    return round(min(1.0, max(0.0, total)), 4)