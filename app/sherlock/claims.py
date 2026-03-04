"""
Sherlock Claims - S-INT-2

Models specific claims with evidence for incentive intelligence.
Linking to outputs without impacting projections.
"""

from typing import Dict, Any, List
from app.sherlock.audit import Claim, ClaimStatus
from app.intelligence import IncentiveIntelligence, TeamCompetitiveState, AlignmentType


def evaluate_team_tanking(intel: IncentiveIntelligence) -> Claim:
    """
    Claim: Team is actively tanking.
    
    Evidence rules, adjusted:
    - tanking_score > 0.6 → base confidence
    - rotation_stability < 0.5 → increases confidence
    - rotation_stability > 0.65 → decreases confidence
    """
    tanking_score = intel.tanking_score
    rotation_stability = intel.rotation_stability_score

    # Base confidence from tanking score
    if tanking_score < 0.3:
        confidence = tanking_score * 0.5
        status = ClaimStatus.INSUFFICIENT
    elif tanking_score < 0.6:
        confidence = 0.3 + (tanking_score - 0.3) * 0.67
        status = ClaimStatus.CONTESTED
    else:
        confidence = 0.6 + (tanking_score - 0.6) * 1.0
        status = ClaimStatus.SUPPORTED

    support = []
    counter = []
    
    if rotation_stability < 0.4:
        confidence = min(1.0, confidence * 1.2)
        support.append(f"rotation_chaos={rotation_stability:.2f}")
    elif rotation_stability > 0.65:
        confidence *= 0.7
        counter.append("high_rotation_stability_contradicts_tanking")
    
    # Always add tanking_score to support if meaningful
    if tanking_score > 0.3:
        support.append(f"tanking_score={tanking_score:.2f}")

    # Determine action
    if confidence > 0.7:
        action = "Increase prop volatility penalty; avoid minutes overs"
    elif confidence > 0.4:
        action = "Monitor rotation closely; reduce exposure"
    else:
        action = ""
    
    return Claim(
        id="team_tanking",
        claim="Team is tanking",
        confidence=round(confidence, 4),
        support=support,
        counter=counter,
        falsifier="If rotation stability > 0.65 for next 3 games",
        recommended_action=action,
        status=status
    )


def evaluate_minutes_suppression(intel: IncentiveIntelligence) -> Claim:
    """
    Claim: Player minutes suppression risk detected.
    """
    alignment = intel.alignment_type
    rotation_stability = intel.rotation_stability_score

    # Define base context
    if alignment == AlignmentType.LOAD_MANAGEMENT:
        confidence = 0.75
        status = ClaimStatus.SUPPORTED
    elif alignment == AlignmentType.CONFLICTED:
        confidence = 0.55
        status = ClaimStatus.CONTESTED
    else:
        confidence = 0.2
        status = ClaimStatus.INSUFFICIENT

    # Rotation stability modifier
    if rotation_stability < 0.4:
        confidence += 0.2

    return Claim(
        id="minutes_suppression_risk",
        claim="Player minutes suppression risk detected",
        confidence=round(confidence, 4),
        support=[],
        counter=[],
        falsifier="If player plays >32 minutes in 3 consecutive games",
        recommended_action="Monitor closely; adjust minutes",
        status=status
    )


def evaluate_effort_decay_pace(intel: IncentiveIntelligence) -> Claim:
    """
    Claim: Effort decay will slow game pace.
    """
    effort_modifier = intel.effort_decay_modifier

    if effort_modifier > 0.95:
        confidence = 0.15
        status = ClaimStatus.INSUFFICIENT
    else:
        confidence = 0.75
        status = ClaimStatus.SUPPORTED

    # Team state modifier
    current_state = intel.team_competitive_state
    if current_state == TeamCompetitiveState.TANKING:
        confidence += 0.2
        support = ["Team in tanking mode"]
    else:
        support = []

    return Claim(
        id="effort_decay_pace_down",
        claim="Effort decay will slow game pace",
        confidence=round(confidence, 4),
        support=support,
        counter=[],
        falsifier="If game pace exceeds season average by >5 possessions",
        recommended_action="Discount pace-dependent props",
        status=status
    )
