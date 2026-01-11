# core/evaluation.py
"""
Evaluation Output Contract - Canonical PRD Response.

Provides a single canonical response object for evaluating a parlay/bet.
Orchestrates all engines: reducer -> correlation -> dna enforcement ->
risk inductor -> suggestions.

No HTTP endpoints. No persistence. No external data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Sequence
from uuid import UUID

from core.models.leading_light import (
    BetBlock,
    Correlation,
    SuggestedBlock,
)
from core.dna_enforcement import (
    DNAProfile,
    EnforcementResult,
    apply_dna_enforcement,
)
from core.parlay_reducer import build_parlay_state
from core.risk_inductor import (
    InductorResult,
    RiskInductor,
    resolve_inductor,
)
from core.suggestion_engine import compute_suggestions


# =============================================================================
# Enums
# =============================================================================


class RecommendationAction(str, Enum):
    """Recommended action for the parlay."""
    ACCEPT = "accept"
    REDUCE = "reduce"
    AVOID = "avoid"


# =============================================================================
# Response Components
# =============================================================================


@dataclass(frozen=True)
class InductorInfo:
    """Risk inductor information in response."""
    level: RiskInductor
    explanation: str


@dataclass(frozen=True)
class MetricsInfo:
    """Parlay metrics in response."""
    raw_fragility: float
    final_fragility: float
    leg_penalty: float
    correlation_penalty: float
    correlation_multiplier: float


@dataclass(frozen=True)
class DNAInfo:
    """DNA enforcement information in response."""
    violations: tuple[str, ...]
    base_stake_cap: Optional[float]
    recommended_stake: Optional[float]
    max_legs: Optional[int]
    fragility_tolerance: Optional[float]


@dataclass(frozen=True)
class Recommendation:
    """
    Recommendation for the parlay.

    Rules (v1):
    - STABLE => ACCEPT
    - LOADED => ACCEPT (or REDUCE if DNA violations exist)
    - TENSE => REDUCE
    - CRITICAL => AVOID

    DNA can only downgrade (ACCEPT -> REDUCE -> AVOID), never upgrade.
    """
    action: RecommendationAction
    reason: str


# =============================================================================
# Request/Response
# =============================================================================


@dataclass(frozen=True)
class EvaluationRequest:
    """
    Minimal request for parlay evaluation.

    Attributes:
        blocks: List of BetBlock objects to evaluate
        dna_profile: Optional DNA profile for enforcement
        bankroll: Optional bankroll for stake calculations
        candidates: Optional candidate blocks for suggestions
        max_suggestions: Maximum suggestions to return (default 5)
    """
    blocks: Sequence[BetBlock]
    dna_profile: Optional[DNAProfile] = None
    bankroll: Optional[float] = None
    candidates: Optional[Sequence[BetBlock]] = None
    max_suggestions: int = 5


@dataclass(frozen=True)
class EvaluationResponse:
    """
    Canonical response for parlay evaluation.

    All fields are stable and documented. Deterministic for same inputs.

    Attributes:
        parlay_id: Unique identifier for this parlay evaluation
        inductor: Risk inductor level and explanation
        metrics: Computed parlay metrics
        correlations: List of detected correlations
        dna: DNA enforcement info (violations, stake caps)
        recommendation: Recommended action (ACCEPT/REDUCE/AVOID)
        suggestions: Optional list of suggested blocks to add
    """
    parlay_id: UUID
    inductor: InductorInfo
    metrics: MetricsInfo
    correlations: tuple[Correlation, ...]
    dna: DNAInfo
    recommendation: Recommendation
    suggestions: Optional[tuple[SuggestedBlock, ...]] = None


# =============================================================================
# Recommendation Logic
# =============================================================================


def _compute_base_action(inductor: RiskInductor) -> RecommendationAction:
    """
    Compute base action from inductor level.

    - STABLE => ACCEPT
    - LOADED => ACCEPT
    - TENSE => REDUCE
    - CRITICAL => AVOID
    """
    if inductor == RiskInductor.STABLE:
        return RecommendationAction.ACCEPT
    elif inductor == RiskInductor.LOADED:
        return RecommendationAction.ACCEPT
    elif inductor == RiskInductor.TENSE:
        return RecommendationAction.REDUCE
    else:  # CRITICAL
        return RecommendationAction.AVOID


def _downgrade_action(
    action: RecommendationAction,
    has_violations: bool,
) -> RecommendationAction:
    """
    Downgrade action based on DNA violations.

    DNA can only downgrade, never upgrade:
    - ACCEPT -> REDUCE (if violations exist)
    - REDUCE -> AVOID (if violations exist)
    - AVOID stays AVOID
    """
    if not has_violations:
        return action

    if action == RecommendationAction.ACCEPT:
        return RecommendationAction.REDUCE
    elif action == RecommendationAction.REDUCE:
        return RecommendationAction.AVOID
    else:
        return RecommendationAction.AVOID


def _generate_recommendation_reason(
    action: RecommendationAction,
    inductor: RiskInductor,
    has_violations: bool,
    was_downgraded: bool,
) -> str:
    """Generate one-sentence reason for recommendation."""
    if action == RecommendationAction.ACCEPT:
        if inductor == RiskInductor.STABLE:
            return "Structure is simple and within acceptable risk parameters."
        else:  # LOADED
            return "Multiple assumptions present but overall risk is acceptable."

    elif action == RecommendationAction.REDUCE:
        if was_downgraded:
            return "DNA constraints violated; consider reducing stake or removing legs."
        elif inductor == RiskInductor.TENSE:
            return "Elevated structural risk; consider reducing stake size."
        else:
            return "Risk factors present; consider reducing exposure."

    else:  # AVOID
        if was_downgraded:
            return "Critical risk level combined with DNA violations; strongly recommend avoiding."
        elif inductor == RiskInductor.CRITICAL:
            return "Critical structural risk with compounding failure paths; recommend avoiding."
        else:
            return "Risk exceeds acceptable thresholds; recommend avoiding."


def compute_recommendation(
    inductor: RiskInductor,
    violations: tuple[str, ...],
) -> Recommendation:
    """
    Compute recommendation based on inductor and DNA violations.

    DNA can only downgrade the recommendation, never upgrade.
    """
    base_action = _compute_base_action(inductor)
    has_violations = len(violations) > 0
    final_action = _downgrade_action(base_action, has_violations)
    was_downgraded = final_action != base_action

    reason = _generate_recommendation_reason(
        final_action,
        inductor,
        has_violations,
        was_downgraded,
    )

    return Recommendation(action=final_action, reason=reason)


# =============================================================================
# Main Evaluation Function
# =============================================================================


def evaluate_parlay(
    blocks: Sequence[BetBlock],
    dna_profile: Optional[DNAProfile] = None,
    bankroll: Optional[float] = None,
    candidates: Optional[Sequence[BetBlock]] = None,
    max_suggestions: int = 5,
) -> EvaluationResponse:
    """
    Evaluate a parlay and return canonical response.

    Orchestrates all engines in order:
    1. Parlay Reducer - builds state with correlations and metrics
    2. DNA Enforcement - applies profile constraints (if provided)
    3. Risk Inductor - resolves risk level
    4. Suggestion Engine - computes suggestions (if candidates provided)

    Args:
        blocks: List of BetBlock objects to evaluate
        dna_profile: Optional DNA profile for enforcement
        bankroll: Optional bankroll for stake calculations
        candidates: Optional candidate blocks for suggestions
        max_suggestions: Maximum suggestions to return (default 5)

    Returns:
        EvaluationResponse with all computed fields
    """
    # ==========================================================================
    # Step 1: Build parlay state (reducer handles correlations + metrics)
    # ==========================================================================
    parlay_state = build_parlay_state(blocks)

    # ==========================================================================
    # Step 2: Apply DNA enforcement (if profile provided)
    # ==========================================================================
    violations: tuple[str, ...] = ()
    base_stake_cap: Optional[float] = None
    recommended_stake: Optional[float] = None
    max_legs: Optional[int] = None
    fragility_tolerance: Optional[float] = None

    if dna_profile is not None and bankroll is not None:
        enforcement_result = apply_dna_enforcement(
            parlay_state,
            dna_profile,
            bankroll,
        )
        violations = enforcement_result.dna_enforcement.violations
        base_stake_cap = enforcement_result.base_stake_cap
        recommended_stake = enforcement_result.recommended_stake
        max_legs = enforcement_result.dna_enforcement.max_legs
        fragility_tolerance = enforcement_result.dna_enforcement.fragility_tolerance
    elif dna_profile is not None:
        # Profile without bankroll: extract limits but no stake calculation
        max_legs = dna_profile.risk.max_parlay_legs
        fragility_tolerance = dna_profile.risk.tolerance

    # ==========================================================================
    # Step 3: Resolve risk inductor
    # ==========================================================================
    inductor_result = resolve_inductor(parlay_state, dna_violations=violations)

    # ==========================================================================
    # Step 4: Compute recommendation
    # ==========================================================================
    recommendation = compute_recommendation(inductor_result.inductor, violations)

    # ==========================================================================
    # Step 5: Compute suggestions (if candidates provided)
    # ==========================================================================
    suggestions: Optional[tuple[SuggestedBlock, ...]] = None

    if candidates is not None and len(candidates) > 0:
        suggestion_list = compute_suggestions(
            parlay_state,
            candidates,
            max_suggestions=max_suggestions,
            dna_profile=dna_profile,
        )
        suggestions = tuple(suggestion_list)

    # ==========================================================================
    # Build response
    # ==========================================================================
    return EvaluationResponse(
        parlay_id=parlay_state.parlay_id,
        inductor=InductorInfo(
            level=inductor_result.inductor,
            explanation=inductor_result.explanation,
        ),
        metrics=MetricsInfo(
            raw_fragility=parlay_state.metrics.raw_fragility,
            final_fragility=parlay_state.metrics.final_fragility,
            leg_penalty=parlay_state.metrics.leg_penalty,
            correlation_penalty=parlay_state.metrics.correlation_penalty,
            correlation_multiplier=parlay_state.metrics.correlation_multiplier,
        ),
        correlations=parlay_state.correlations,
        dna=DNAInfo(
            violations=violations,
            base_stake_cap=base_stake_cap,
            recommended_stake=recommended_stake,
            max_legs=max_legs,
            fragility_tolerance=fragility_tolerance,
        ),
        recommendation=recommendation,
        suggestions=suggestions,
    )


# =============================================================================
# Convenience Function
# =============================================================================


def evaluate_from_request(request: EvaluationRequest) -> EvaluationResponse:
    """
    Evaluate from a request object.

    Convenience wrapper around evaluate_parlay.
    """
    return evaluate_parlay(
        blocks=request.blocks,
        dna_profile=request.dna_profile,
        bankroll=request.bankroll,
        candidates=request.candidates,
        max_suggestions=request.max_suggestions,
    )
