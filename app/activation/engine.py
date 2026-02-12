"""
S-INT-3: Activation Engine

Applies incentive intelligence to projections with controlled weights.
"""

from typing import Dict, Any, List, Optional
import os

from app.activation import (
    ActivationWeight,
    ActivationResult,
    ProjectionAdjustment,
    get_weight_config
)
from app.intelligence import IncentiveIntelligence, TeamCompetitiveState, AlignmentType
from app.sherlock.audit import IncentiveAudit, Claim, ClaimStatus


# Environment-based weight configuration
# Set INCENTIVE_ACTIVATION_WEIGHT=medium (or low/high/full/etc)
DEFAULT_WEIGHT = os.getenv("INCENTIVE_ACTIVATION_WEIGHT", "off").lower()


def parse_weight(weight_str: str) -> ActivationWeight:
    """Parse weight string to enum."""
    mapping = {
        "off": ActivationWeight.OFF,
        "minimal": ActivationWeight.MINIMAL,
        "low": ActivationWeight.LOW,
        "medium": ActivationWeight.MEDIUM,
        "high": ActivationWeight.HIGH,
        "full": ActivationWeight.FULL
    }
    return mapping.get(weight_str.lower(), ActivationWeight.OFF)


def get_current_weight() -> ActivationWeight:
    """Get current activation weight from environment."""
    return parse_weight(DEFAULT_WEIGHT)


def apply_claim_adjustment(
    claim: Claim,
    base_projection: float,
    weight_config: Dict[str, Any]
) -> Optional[ProjectionAdjustment]:
    """
    Apply single claim to projection with weight caps.
    
    Returns None if:
    - Claim confidence below threshold
    - Weight tier is OFF
    - No recommended action
    """
    max_adj = weight_config["max_adjustment_pct"]
    min_conf = weight_config["min_confidence_threshold"]
    
    # Skip if weight is off or confidence too low
    if max_adj == 0.0 or claim.confidence < min_conf:
        return None
    
    # Skip if no action recommended
    if not claim.recommended_action:
        return None
    
    # Calculate adjustment based on claim type
    adjustment_pct = 0.0
    rationale = ""
    
    if claim.id == "team_tanking":
        # Tanking reduces player performance expectations
        # Scale by confidence and cap at weight limit
        adjustment_pct = -0.05 * claim.confidence  # Max -5% per claim
        adjustment_pct = max(-max_adj, adjustment_pct)
        rationale = f"Tanking signal (conf={claim.confidence:.2f}): reduce projections"
        
    elif claim.id == "minutes_suppression_risk":
        # Minutes suppression → reduce minutes projection
        adjustment_pct = -0.08 * claim.confidence  # Max -8% for minutes
        adjustment_pct = max(-max_adj, adjustment_pct)
        rationale = f"Minutes suppression risk (conf={claim.confidence:.2f}): reduce minutes"
        
    elif claim.id == "effort_decay_pace_down":
        # Pace down → reduce pace-dependent stats
        adjustment_pct = -0.06 * claim.confidence  # Max -6% for pace
        adjustment_pct = max(-max_adj, adjustment_pct)
        rationale = f"Pace decay (conf={claim.confidence:.2f}): reduce pace stats"
    else:
        # Unknown claim type - skip
        return None
    
    # Apply adjustment
    adjusted_value = base_projection * (1 + adjustment_pct)
    
    return ProjectionAdjustment(
        signal_source=claim.id,
        original_value=base_projection,
        adjusted_value=round(adjusted_value, 2),
        adjustment_pct=round(adjustment_pct, 4),
        confidence=claim.confidence,
        weight_applied=weight_config["max_adjustment_pct"],
        rationale=rationale
    )


def activate_intelligence(
    intelligence: IncentiveIntelligence,
    audit: IncentiveAudit,
    base_projections: Dict[str, float],
    weight: Optional[ActivationWeight] = None
) -> ActivationResult:
    """
    Main activation entry point.
    
    Applies incentive intelligence to base projections with controlled weights.
    
    Args:
        intelligence: Computed incentive intelligence (S-INT-1)
        audit: Sherlock audit with claims (S-INT-2)
        base_projections: Dict of stat_name -> projected_value
        weight: Override weight tier (default: from environment)
    
    Returns:
        ActivationResult with all adjustments and receipt
    """
    # Determine weight tier
    if weight is None:
        weight = get_current_weight()
    
    weight_config = get_weight_config(weight)
    
    # If weight is OFF, return empty result
    if weight == ActivationWeight.OFF:
        return ActivationResult(
            intelligence=intelligence,
            audit=audit,
            weight_tier=weight,
            max_adjustment_pct=0.0,
            adjustments=[]
        )
    
    # Apply each claim to relevant projections
    adjustments: List[ProjectionAdjustment] = []
    
    for claim in audit.claims:
        # Determine which projections this claim affects
        affected_stats = _get_affected_stats(claim.id)
        
        for stat_name in affected_stats:
            if stat_name in base_projections:
                base_value = base_projections[stat_name]
                adjustment = apply_claim_adjustment(
                    claim, base_value, weight_config
                )
                if adjustment:
                    adjustments.append(adjustment)
    
    return ActivationResult(
        intelligence=intelligence,
        audit=audit,
        weight_tier=weight,
        max_adjustment_pct=weight_config["max_adjustment_pct"],
        adjustments=adjustments
    )


def _get_affected_stats(claim_id: str) -> List[str]:
    """Map claim types to affected projection categories."""
    mapping = {
        "team_tanking": ["pts", "reb", "ast", "efficiency", "win_prob"],
        "minutes_suppression_risk": ["minutes", "pts", "reb", "ast", "stl", "blk"],
        "effort_decay_pace_down": ["pace", "possessions", "fast_break_pts", "transition_pct"]
    }
    return mapping.get(claim_id, [])


def quick_activate(
    intelligence: IncentiveIntelligence,
    base_projections: Dict[str, float]
) -> ActivationResult:
    """
    Convenience function: audit + activate in one call.
    Uses current environment weight.
    """
    from app.sherlock.audit import run_incentive_audit
    
    audit = run_incentive_audit(intelligence, context={})
    return activate_intelligence(intelligence, audit, base_projections)
