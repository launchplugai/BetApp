"""
Alignment Detection

Player-team incentive correlation analysis.
Deterministic classification based on contract/game theory signals.
"""

from typing import Optional
from datetime import datetime
from enum import Enum

from app.intelligence import AlignmentType


class ContractIncentive(str, Enum):
    """Contract-driven incentive states."""
    CONTRACT_YEAR = "contract_year"           # Expiring, needs stats
    RFA_PENDING = "rfa_pending"               # Restricted free agency
    MAX_EXTENSION_ELIGIBLE = "max_extension"  # Supermax eligible
    PLAYER_OPTION = "player_option"           # Can opt out
    TEAM_OPTION = "team_option"               # Team decision
    LONG_TERM_SECURED = "long_term_secured"   # Already got paid


def classify_alignment(
    team_competitive_state: str,
    contract_incentive: ContractIncentive,
    minutes_trend_last_10: float = 0.0,  # +5 = increasing, -5 = decreasing
    usage_trend_last_10: float = 0.0,    # usage rate change
    is_star_player: bool = False,
    playoff_eligible: bool = True,
) -> AlignmentType:
    """
    Determine player-team incentive alignment type.
    
    Conflict patterns:
    - Contract year + decreasing minutes = CONFLICTED
    - Tanking team + star chasing stats = CONFLICTED
    - Load management in playoff hunt = LOAD_MANAGEMENT
    - Contract year + high usage = CONTRACT_CHASE
    """
    # Guardrails
    minutes_trend_last_10 = max(-15.0, min(15.0, minutes_trend_last_10))
    usage_trend_last_10 = max(-10.0, min(10.0, usage_trend_last_10))
    
    # Clear conflict: contract year but minutes dropping
    if contract_incentive in (ContractIncentive.CONTRACT_YEAR, ContractIncentive.RFA_PENDING):
        if minutes_trend_last_10 < -3.0 or usage_trend_last_10 < -3.0:
            return AlignmentType.CONFLICTED
        if usage_trend_last_10 > 3.0:
            return AlignmentType.CONTRACT_CHASE
    
    # Load management pattern
    if is_star_player:
        if team_competitive_state in ("contending", "playoff_hunting"):
            if minutes_trend_last_10 < -2.0 and not playoff_eligible:
                return AlignmentType.LOAD_MANAGEMENT
    
    # Tank team + stat chaser
    if team_competitive_state == "tanking":
        if contract_incentive == ContractIncentive.CONTRACT_YEAR:
            if usage_trend_last_10 > 2.0:
                return AlignmentType.CONTRACT_CHASE
    
    # Secure long-term: aligned unless weird patterns
    if contract_incentive == ContractIncentive.LONG_TERM_SECURED:
        return AlignmentType.ALIGNED
    
    # Default: aligned (most players are)
    return AlignmentType.ALIGNED


def calculate_alignment_confidence(
    data_points_available: int = 0,
    has_contract_data: bool = False,
    has_usage_data: bool = False,
    has_minutes_data: bool = False,
) -> float:
    """
    Confidence in alignment classification based on data quality.
    Returns 0.0-1.0. Used for audit weighting, not projection.
    """
    if not has_contract_data:
        return 0.3  # Low confidence without contract context
    
    base = 0.5
    
    if has_usage_data:
        base += 0.25
    if has_minutes_data:
        base += 0.25
    
    # More data points = higher confidence (diminishing returns)
    data_bonus = min(0.15, data_points_available / 50)
    
    return round(min(1.0, base + data_bonus), 4)