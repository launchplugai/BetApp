# core/risk_inductor.py
"""
Risk Inductor Engine - Maps parlay metrics to risk state.

Maps ParlayState metrics into one of four risk inductors:
STABLE, LOADED, TENSE, CRITICAL.

Uses finalFragility, legs, and correlationPenalty as inputs.
CRITICAL is rare and treated as an emotional interrupt.

No outcome prediction. No shaming. No hype.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.models.leading_light import ParlayState


# =============================================================================
# Inductor Enum
# =============================================================================


class RiskInductor(str, Enum):
    """Risk state inductors for a parlay."""
    STABLE = "stable"
    LOADED = "loaded"
    TENSE = "tense"
    CRITICAL = "critical"


# =============================================================================
# Result Type
# =============================================================================


@dataclass(frozen=True)
class InductorResult:
    """
    Result of risk inductor resolution.

    Attributes:
        inductor: The resolved risk inductor
        explanation: One-sentence reason-first explanation
    """
    inductor: RiskInductor
    explanation: str


# =============================================================================
# Threshold Constants (CANON)
# =============================================================================

# Fragility thresholds
THRESHOLD_STABLE = 30
THRESHOLD_LOADED = 55
THRESHOLD_TENSE = 75

# CRITICAL escalation factors (any one required when fragility > 75)
CRITICAL_CORRELATION_PENALTY = 20
CRITICAL_MIN_LEGS = 4


# =============================================================================
# Explanation Templates
# =============================================================================


def _generate_stable_explanation(
    final_fragility: float,
    num_legs: int,
    correlation_penalty: float,
) -> str:
    """Generate explanation for STABLE inductor."""
    if num_legs == 1:
        return "Structure is simple with limited dependency."
    if correlation_penalty == 0:
        return "Structure is straightforward with no correlated dependencies."
    return "Structure remains manageable with minimal correlation risk."


def _generate_loaded_explanation(
    final_fragility: float,
    num_legs: int,
    correlation_penalty: float,
) -> str:
    """Generate explanation for LOADED inductor."""
    if correlation_penalty == 0:
        return "Multiple assumptions present but no correlated dependencies."
    if correlation_penalty < 12:
        return "Multiple assumptions present but correlations remain manageable."
    return "Structural complexity increasing with moderate correlation exposure."


def _generate_tense_explanation(
    final_fragility: float,
    num_legs: int,
    correlation_penalty: float,
) -> str:
    """Generate explanation for TENSE inductor."""
    if correlation_penalty == 0:
        return "Elevated fragility from structure complexity alone."
    if num_legs >= 4:
        return "Several failure paths due to leg count and structural dependencies."
    return "Several failure paths due to structure and dependency."


def _generate_critical_explanation(
    final_fragility: float,
    num_legs: int,
    correlation_penalty: float,
    has_violations: bool,
) -> str:
    """Generate explanation for CRITICAL inductor."""
    factors = []

    if correlation_penalty >= CRITICAL_CORRELATION_PENALTY:
        factors.append("correlated legs")
    if num_legs >= CRITICAL_MIN_LEGS:
        factors.append("leg count")
    if has_violations:
        factors.append("DNA constraint violations")

    if len(factors) == 0:
        # Should not happen per rules, but fallback
        return "High fragility driven by compounding structural assumptions."

    if len(factors) == 1:
        return f"High fragility driven by {factors[0]} and compounding assumptions."

    factors_str = ", ".join(factors[:-1]) + f" and {factors[-1]}"
    return f"High fragility driven by {factors_str}."


# =============================================================================
# Main Resolution Function
# =============================================================================


def resolve_inductor(
    parlay_state: ParlayState,
    dna_violations: Optional[tuple[str, ...]] = None,
) -> InductorResult:
    """
    Resolve the risk inductor for a parlay state.

    Uses finalFragility as primary signal, with CRITICAL requiring
    additional escalation factors.

    Args:
        parlay_state: The parlay state with computed metrics
        dna_violations: Optional tuple of DNA violation strings

    Returns:
        InductorResult with inductor and explanation
    """
    final_fragility = parlay_state.metrics.final_fragility
    num_legs = len(parlay_state.blocks)
    correlation_penalty = parlay_state.metrics.correlation_penalty
    has_violations = bool(dna_violations and len(dna_violations) > 0)

    # ==========================================================================
    # STABLE: finalFragility <= 30
    # ==========================================================================
    if final_fragility <= THRESHOLD_STABLE:
        return InductorResult(
            inductor=RiskInductor.STABLE,
            explanation=_generate_stable_explanation(
                final_fragility, num_legs, correlation_penalty
            ),
        )

    # ==========================================================================
    # LOADED: 31 <= finalFragility <= 55
    # ==========================================================================
    if final_fragility <= THRESHOLD_LOADED:
        return InductorResult(
            inductor=RiskInductor.LOADED,
            explanation=_generate_loaded_explanation(
                final_fragility, num_legs, correlation_penalty
            ),
        )

    # ==========================================================================
    # TENSE or CRITICAL: finalFragility > 55
    # ==========================================================================

    # Check CRITICAL escalation factors (only if fragility > 75)
    if final_fragility > THRESHOLD_TENSE:
        has_escalation = (
            correlation_penalty >= CRITICAL_CORRELATION_PENALTY
            or num_legs >= CRITICAL_MIN_LEGS
            or has_violations
        )

        if has_escalation:
            return InductorResult(
                inductor=RiskInductor.CRITICAL,
                explanation=_generate_critical_explanation(
                    final_fragility, num_legs, correlation_penalty, has_violations
                ),
            )

    # TENSE: 56 <= finalFragility <= 75, OR fragility > 75 without escalation
    return InductorResult(
        inductor=RiskInductor.TENSE,
        explanation=_generate_tense_explanation(
            final_fragility, num_legs, correlation_penalty
        ),
    )


# =============================================================================
# Convenience Function
# =============================================================================


def resolve_inductor_from_metrics(
    final_fragility: float,
    num_legs: int,
    correlation_penalty: float,
    dna_violations: Optional[tuple[str, ...]] = None,
) -> InductorResult:
    """
    Resolve inductor directly from metrics (for testing/simulation).

    This is a convenience function that doesn't require a full ParlayState.
    """
    has_violations = bool(dna_violations and len(dna_violations) > 0)

    # STABLE
    if final_fragility <= THRESHOLD_STABLE:
        return InductorResult(
            inductor=RiskInductor.STABLE,
            explanation=_generate_stable_explanation(
                final_fragility, num_legs, correlation_penalty
            ),
        )

    # LOADED
    if final_fragility <= THRESHOLD_LOADED:
        return InductorResult(
            inductor=RiskInductor.LOADED,
            explanation=_generate_loaded_explanation(
                final_fragility, num_legs, correlation_penalty
            ),
        )

    # Check CRITICAL (fragility > 75 with escalation)
    if final_fragility > THRESHOLD_TENSE:
        has_escalation = (
            correlation_penalty >= CRITICAL_CORRELATION_PENALTY
            or num_legs >= CRITICAL_MIN_LEGS
            or has_violations
        )

        if has_escalation:
            return InductorResult(
                inductor=RiskInductor.CRITICAL,
                explanation=_generate_critical_explanation(
                    final_fragility, num_legs, correlation_penalty, has_violations
                ),
            )

    # TENSE
    return InductorResult(
        inductor=RiskInductor.TENSE,
        explanation=_generate_tense_explanation(
            final_fragility, num_legs, correlation_penalty
        ),
    )
