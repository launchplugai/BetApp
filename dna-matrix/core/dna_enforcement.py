# core/dna_enforcement.py
"""
DNA Enforcement Engine - Profile-driven risk constraints.

Implements profile-driven risk constraints that can only reduce risk (never upgrade).
DNA does not modify fragility values; it reacts to finalFragility and structure.

Rules (V1 CANON):
1. Fragility tolerance - If finalFragility > tolerance, add violation and reduce stake
2. Max legs - If legs > max_parlay_legs, add violation
3. Avoid props - If avoid_props and any block is player_prop, add violation
4. Avoid live - If avoid_live_bets and any block is live, add violation
5. Stake cap - Base stake cap = bankroll * max_stake_pct
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from core.models.leading_light import (
    BetBlock,
    BetType,
    DNAEnforcement,
    ParlayState,
)


# =============================================================================
# DNA Profile
# =============================================================================


@dataclass(frozen=True)
class RiskProfile:
    """
    Risk-related settings from user's DNA profile.

    Attributes:
        tolerance: Fragility tolerance threshold (0-100)
        max_parlay_legs: Maximum allowed legs in a parlay
        max_stake_pct: Maximum stake as percentage of bankroll (0.01-0.25)
        avoid_live_bets: Whether to avoid live/in-play bets
        avoid_props: Whether to avoid player prop bets
    """
    tolerance: float
    max_parlay_legs: int
    max_stake_pct: float
    avoid_live_bets: bool
    avoid_props: bool

    def __post_init__(self) -> None:
        # Tolerance validation (0-100)
        if not isinstance(self.tolerance, (int, float)):
            raise TypeError("tolerance must be a number")
        if self.tolerance < 0 or self.tolerance > 100:
            raise ValueError("tolerance must be between 0 and 100")

        # Max legs validation (positive integer)
        if not isinstance(self.max_parlay_legs, int):
            raise TypeError("max_parlay_legs must be an integer")
        if self.max_parlay_legs < 1:
            raise ValueError("max_parlay_legs must be at least 1")

        # Max stake pct validation (0.01-0.25)
        if not isinstance(self.max_stake_pct, (int, float)):
            raise TypeError("max_stake_pct must be a number")
        if self.max_stake_pct < 0.01 or self.max_stake_pct > 0.25:
            raise ValueError("max_stake_pct must be between 0.01 and 0.25")

        # Boolean validations
        if not isinstance(self.avoid_live_bets, bool):
            raise TypeError("avoid_live_bets must be a boolean")
        if not isinstance(self.avoid_props, bool):
            raise TypeError("avoid_props must be a boolean")


@dataclass(frozen=True)
class BehaviorProfile:
    """
    Behavior-related settings from user's DNA profile.

    Attributes:
        discipline: Discipline score (0.0-1.0), higher = more disciplined
    """
    discipline: float

    def __post_init__(self) -> None:
        if not isinstance(self.discipline, (int, float)):
            raise TypeError("discipline must be a number")
        if self.discipline < 0.0 or self.discipline > 1.0:
            raise ValueError("discipline must be between 0.0 and 1.0")


@dataclass(frozen=True)
class DNAProfile:
    """
    Complete DNA profile for a user.

    Contains risk and behavior settings that drive enforcement rules.
    """
    risk: RiskProfile
    behavior: BehaviorProfile

    def __post_init__(self) -> None:
        if not isinstance(self.risk, RiskProfile):
            raise TypeError("risk must be a RiskProfile")
        if not isinstance(self.behavior, BehaviorProfile):
            raise TypeError("behavior must be a BehaviorProfile")

    @classmethod
    def from_dict(cls, data: dict) -> DNAProfile:
        """Create DNAProfile from dictionary."""
        risk_data = data.get("risk", {})
        behavior_data = data.get("behavior", {})

        risk = RiskProfile(
            tolerance=risk_data.get("tolerance", 50),
            max_parlay_legs=risk_data.get("max_parlay_legs", 4),
            max_stake_pct=risk_data.get("max_stake_pct", 0.05),
            avoid_live_bets=risk_data.get("avoid_live_bets", False),
            avoid_props=risk_data.get("avoid_props", False),
        )

        behavior = BehaviorProfile(
            discipline=behavior_data.get("discipline", 0.5),
        )

        return cls(risk=risk, behavior=behavior)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "risk": {
                "tolerance": self.risk.tolerance,
                "max_parlay_legs": self.risk.max_parlay_legs,
                "max_stake_pct": self.risk.max_stake_pct,
                "avoid_live_bets": self.risk.avoid_live_bets,
                "avoid_props": self.risk.avoid_props,
            },
            "behavior": {
                "discipline": self.behavior.discipline,
            },
        }


# =============================================================================
# Enforcement Result
# =============================================================================


@dataclass(frozen=True)
class EnforcementResult:
    """
    Result of applying DNA enforcement to a parlay.

    Attributes:
        dna_enforcement: The DNAEnforcement object for the parlay
        recommended_stake: Recommended stake amount (respects all constraints)
        base_stake_cap: Base stake cap before any reductions
    """
    dna_enforcement: DNAEnforcement
    recommended_stake: float
    base_stake_cap: float


# =============================================================================
# Violation Constants
# =============================================================================

VIOLATION_FRAGILITY_OVER_TOLERANCE = "fragility_over_tolerance"
VIOLATION_MAX_LEGS_EXCEEDED = "max_legs_exceeded"
VIOLATION_PROPS_NOT_ALLOWED = "props_not_allowed"
VIOLATION_LIVE_BETS_NOT_ALLOWED = "live_bets_not_allowed"


# =============================================================================
# Detection Functions
# =============================================================================


def has_player_prop(blocks: Sequence[BetBlock]) -> bool:
    """Check if any block is a player prop bet."""
    return any(block.bet_type == BetType.PLAYER_PROP for block in blocks)


def has_live_bet(blocks: Sequence[BetBlock]) -> bool:
    """
    Check if any block is a live bet.

    Live bets are detected by:
    - "live" in correlation_tags
    """
    for block in blocks:
        if "live" in block.correlation_tags:
            return True
    return False


# =============================================================================
# Main Enforcement Function
# =============================================================================


def apply_dna_enforcement(
    parlay_state: ParlayState,
    dna_profile: DNAProfile,
    bankroll: float,
) -> EnforcementResult:
    """
    Apply DNA enforcement rules to a parlay.

    DNA may DOWNGRADE decisions, never upgrade them.
    DNA does not modify fragility values; it reacts to finalFragility and structure.

    Args:
        parlay_state: Current parlay state with computed fragility
        dna_profile: User's DNA profile with risk/behavior settings
        bankroll: User's current bankroll amount

    Returns:
        EnforcementResult with DNAEnforcement, recommended stake, and base cap
    """
    if bankroll < 0:
        raise ValueError("bankroll must be non-negative")

    violations: List[str] = []
    risk = dna_profile.risk

    # Extract parlay info
    final_fragility = parlay_state.metrics.final_fragility
    num_legs = len(parlay_state.blocks)
    blocks = parlay_state.blocks

    # ==========================================================================
    # Rule 1: Fragility tolerance
    # ==========================================================================
    fragility_over_tolerance = final_fragility > risk.tolerance
    if fragility_over_tolerance:
        violations.append(VIOLATION_FRAGILITY_OVER_TOLERANCE)

    # ==========================================================================
    # Rule 2: Max legs
    # ==========================================================================
    if num_legs > risk.max_parlay_legs:
        violations.append(VIOLATION_MAX_LEGS_EXCEEDED)

    # ==========================================================================
    # Rule 3: Avoid props
    # ==========================================================================
    if risk.avoid_props and has_player_prop(blocks):
        violations.append(VIOLATION_PROPS_NOT_ALLOWED)

    # ==========================================================================
    # Rule 4: Avoid live
    # ==========================================================================
    if risk.avoid_live_bets and has_live_bet(blocks):
        violations.append(VIOLATION_LIVE_BETS_NOT_ALLOWED)

    # ==========================================================================
    # Rule 5: Stake cap computation
    # ==========================================================================
    # Base stake cap = bankroll * max_stake_pct
    base_stake_cap = bankroll * risk.max_stake_pct

    # Recommended stake starts at base cap
    recommended_stake = base_stake_cap

    # If fragility over tolerance, reduce stake proportionally
    # recommendedStake = base_cap * (tolerance / finalFragility)
    if fragility_over_tolerance and final_fragility > 0:
        reduction_factor = risk.tolerance / final_fragility
        recommended_stake = base_stake_cap * reduction_factor

    # Ensure stake is non-negative
    recommended_stake = max(0.0, recommended_stake)

    # Final recommended stake cannot exceed base cap
    recommended_stake = min(recommended_stake, base_stake_cap)

    # ==========================================================================
    # Build DNAEnforcement
    # ==========================================================================
    dna_enforcement = DNAEnforcement(
        max_legs=risk.max_parlay_legs,
        fragility_tolerance=risk.tolerance,
        stake_cap=base_stake_cap,
        violations=tuple(violations),
    )

    return EnforcementResult(
        dna_enforcement=dna_enforcement,
        recommended_stake=recommended_stake,
        base_stake_cap=base_stake_cap,
    )


# =============================================================================
# Compatibility Check for Suggestions
# =============================================================================


def check_dna_compatible(
    candidate: BetBlock,
    current_legs: int,
    dna_profile: DNAProfile,
) -> bool:
    """
    Check if a candidate block is compatible with DNA profile.

    Used by suggestion engine to mark dnaCompatible.

    A candidate is incompatible if:
    - Adding it would exceed max_parlay_legs
    - It's a player_prop and avoid_props is true
    - It's a live bet and avoid_live_bets is true

    Args:
        candidate: The candidate BetBlock to check
        current_legs: Number of legs in current parlay
        dna_profile: User's DNA profile

    Returns:
        True if compatible, False if incompatible
    """
    risk = dna_profile.risk

    # Check max legs (adding this would make current_legs + 1)
    if current_legs + 1 > risk.max_parlay_legs:
        return False

    # Check avoid props
    if risk.avoid_props and candidate.bet_type == BetType.PLAYER_PROP:
        return False

    # Check avoid live
    if risk.avoid_live_bets and "live" in candidate.correlation_tags:
        return False

    return True
