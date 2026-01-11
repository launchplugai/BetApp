# core/suggestion_engine.py
"""
Suggestion Engine - Least-Offensive Block Suggestions.

Given a current ParlayState and candidate BetBlocks, produces a ranked list
of SuggestedBlock outputs based on added risk.

This engine:
- Simulates adding each candidate using build_parlay_state
- Computes deltaFragility and addedCorrelation
- Ranks by lowest added risk
- Assigns labels based on risk thresholds

No outcome prediction. No external data. Pure simulation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence
from uuid import UUID

from core.models.leading_light import (
    BetBlock,
    ParlayState,
    SuggestedBlock,
    SuggestedBlockLabel,
)
from core.parlay_reducer import build_parlay_state


# =============================================================================
# Constants
# =============================================================================

# Label thresholds
THRESHOLD_LOWEST_RISK = 8
THRESHOLD_BALANCED = 18

DEFAULT_MAX_SUGGESTIONS = 5
DEFAULT_MAX_LEGS = 10


# =============================================================================
# Internal Types
# =============================================================================


@dataclass
class CandidateEvaluation:
    """Internal evaluation of a candidate block."""
    block: BetBlock
    delta_fragility: float
    added_correlation: float
    dna_compatible: bool
    label: SuggestedBlockLabel
    reason: str


# =============================================================================
# Label Assignment
# =============================================================================


def assign_label(delta_fragility: float) -> SuggestedBlockLabel:
    """
    Assign label based on deltaFragility thresholds.

    - "Lowest added risk": deltaFragility <= 8
    - "Balanced": 9 <= deltaFragility <= 18
    - "Aggressive but within limits": deltaFragility > 18
    """
    if delta_fragility <= THRESHOLD_LOWEST_RISK:
        return SuggestedBlockLabel.LOWEST_ADDED_RISK
    elif delta_fragility <= THRESHOLD_BALANCED:
        return SuggestedBlockLabel.BALANCED
    else:
        return SuggestedBlockLabel.AGGRESSIVE_WITHIN_LIMITS


def generate_reason(
    delta_fragility: float,
    added_correlation: float,
    dna_compatible: bool,
    label: SuggestedBlockLabel,
) -> str:
    """
    Generate a one-sentence reason for the suggestion.

    If dnaCompatible is false, mention incompatibility.
    """
    if not dna_compatible:
        return f"Adds {delta_fragility:.1f} fragility but exceeds DNA constraints."

    if label == SuggestedBlockLabel.LOWEST_ADDED_RISK:
        if added_correlation == 0:
            return f"Minimal impact with {delta_fragility:.1f} added fragility and no correlation."
        else:
            return f"Low risk with {delta_fragility:.1f} added fragility and {added_correlation:.1f} correlation."

    elif label == SuggestedBlockLabel.BALANCED:
        if added_correlation == 0:
            return f"Moderate risk with {delta_fragility:.1f} added fragility."
        else:
            return f"Balanced option with {delta_fragility:.1f} fragility and {added_correlation:.1f} correlation."

    else:  # AGGRESSIVE_WITHIN_LIMITS
        if added_correlation == 0:
            return f"Higher risk with {delta_fragility:.1f} added fragility but within limits."
        else:
            return f"Aggressive with {delta_fragility:.1f} fragility and {added_correlation:.1f} correlation penalty."


# =============================================================================
# DNA Compatibility Check
# =============================================================================


def check_dna_compatible(
    current_parlay: ParlayState,
    new_parlay: ParlayState,
    max_legs: int = DEFAULT_MAX_LEGS,
) -> bool:
    """
    Check if adding the block would violate DNA constraints.

    Placeholder rules (full implementation in TASK 6):
    - Must not exceed maxLegs
    """
    return len(new_parlay.blocks) <= max_legs


# =============================================================================
# Candidate Evaluation
# =============================================================================


def evaluate_candidate(
    current_parlay: ParlayState,
    candidate: BetBlock,
    max_legs: int = DEFAULT_MAX_LEGS,
) -> CandidateEvaluation | None:
    """
    Evaluate a single candidate block.

    Returns None if deltaFragility <= 0 (should not happen, but enforced).
    """
    # Build new parlay state with candidate added
    new_blocks = list(current_parlay.blocks) + [candidate]
    new_parlay = build_parlay_state(new_blocks, parlay_id=current_parlay.parlay_id)

    # Compute deltas
    delta_fragility = new_parlay.metrics.final_fragility - current_parlay.metrics.final_fragility
    added_correlation = new_parlay.metrics.correlation_penalty - current_parlay.metrics.correlation_penalty

    # Enforce deltaFragility > 0 (adding a leg always increases risk)
    if delta_fragility <= 0:
        return None

    # Check DNA compatibility
    dna_compatible = check_dna_compatible(current_parlay, new_parlay, max_legs)

    # Assign label
    label = assign_label(delta_fragility)

    # Generate reason
    reason = generate_reason(delta_fragility, added_correlation, dna_compatible, label)

    return CandidateEvaluation(
        block=candidate,
        delta_fragility=delta_fragility,
        added_correlation=added_correlation,
        dna_compatible=dna_compatible,
        label=label,
        reason=reason,
    )


# =============================================================================
# Ranking
# =============================================================================


def rank_candidates(evaluations: List[CandidateEvaluation]) -> List[CandidateEvaluation]:
    """
    Rank candidates by preference.

    Ranking:
    - Primary: lowest deltaFragility
    - Secondary: lowest addedCorrelation
    - Tertiary: prefer dnaCompatible=True
    """
    return sorted(
        evaluations,
        key=lambda e: (
            e.delta_fragility,           # Primary: lowest delta
            e.added_correlation,          # Secondary: lowest correlation
            not e.dna_compatible,         # Tertiary: True (0) before False (1)
        )
    )


# =============================================================================
# Main Entry Point
# =============================================================================


def compute_suggestions(
    current_parlay: ParlayState,
    candidates: Sequence[BetBlock],
    max_suggestions: int = DEFAULT_MAX_SUGGESTIONS,
    max_legs: int = DEFAULT_MAX_LEGS,
) -> List[SuggestedBlock]:
    """
    Compute ranked suggestions for adding blocks to a parlay.

    For each candidate:
    - Simulates adding it using build_parlay_state
    - Computes deltaFragility and addedCorrelation
    - Assigns label and generates reason
    - Ranks by lowest added risk

    Args:
        current_parlay: Current parlay state
        candidates: List of candidate BetBlock objects
        max_suggestions: Maximum number of suggestions to return (default 5)
        max_legs: Maximum legs allowed in parlay (default 10)

    Returns:
        List of SuggestedBlock objects, ranked by preference
    """
    # Evaluate all candidates
    evaluations: List[CandidateEvaluation] = []
    for candidate in candidates:
        eval_result = evaluate_candidate(current_parlay, candidate, max_legs)
        if eval_result is not None:
            evaluations.append(eval_result)

    # Rank candidates
    ranked = rank_candidates(evaluations)

    # Convert to SuggestedBlock and limit to max_suggestions
    suggestions: List[SuggestedBlock] = []
    for eval_result in ranked[:max_suggestions]:
        suggestion = SuggestedBlock(
            candidate_block_id=eval_result.block.block_id,
            delta_fragility=eval_result.delta_fragility,
            added_correlation=eval_result.added_correlation,
            dna_compatible=eval_result.dna_compatible,
            label=eval_result.label,
            reason=eval_result.reason,
        )
        suggestions.append(suggestion)

    return suggestions
