# core/fragility_engine.py
"""
Fragility Engine - Deterministic fragility computation.

Pure functions for computing:
- BetBlock effective fragility from base + context modifiers
- ParlayState metrics (rawFragility, legPenalty, finalFragility)

Canonical Formulas:
- effectiveFragility = baseFragility + sum(applied context deltas)
- legPenalty = 8 × (legs ^ 1.5)
- sumBlocks = sum(block.effectiveFragility for all blocks)
- rawFragility = sumBlocks + legPenalty + correlationPenalty
- finalFragility = rawFragility × correlationMultiplier, clamped [0, 100]

Invariants enforced:
- Context deltas never reduce fragility (deltas >= 0)
- effectiveFragility >= baseFragility
- finalFragility clamped [0, 100]
"""
from __future__ import annotations

from typing import List, Sequence

from core.models.leading_light import (
    BetBlock,
    ContextModifiers,
    ParlayMetrics,
)


def compute_effective_fragility(
    base_fragility: float,
    context_modifiers: ContextModifiers,
) -> float:
    """
    Compute effective fragility from base fragility and context modifiers.

    Formula: effectiveFragility = baseFragility + sum(applied context deltas)

    Args:
        base_fragility: The base fragility score
        context_modifiers: Context modifiers (weather, injury, trade, role)

    Returns:
        Effective fragility (always >= base_fragility)

    Raises:
        ValueError: If any delta is negative (invariant violation)
    """
    total_delta = 0.0

    for name in ["weather", "injury", "trade", "role"]:
        modifier = getattr(context_modifiers, name)
        if modifier.delta < 0:
            raise ValueError(
                f"INVARIANT VIOLATION: {name} delta ({modifier.delta}) must be >= 0. "
                "Context never reduces fragility."
            )
        if modifier.applied:
            total_delta += modifier.delta

    effective = base_fragility + total_delta

    # Invariant: effectiveFragility >= baseFragility
    # This is guaranteed by the math (total_delta >= 0), but assert for safety
    assert effective >= base_fragility, (
        f"INVARIANT VIOLATION: effective ({effective}) < base ({base_fragility})"
    )

    return effective


def compute_leg_penalty(num_legs: int) -> float:
    """
    Compute leg penalty for a parlay.

    Formula: legPenalty = 8 × (legs ^ 1.5)

    Args:
        num_legs: Number of legs in the parlay

    Returns:
        Leg penalty value

    Raises:
        ValueError: If num_legs < 1
    """
    if num_legs < 1:
        raise ValueError(f"num_legs must be >= 1, got {num_legs}")

    return 8.0 * (num_legs ** 1.5)


def compute_sum_blocks(blocks: Sequence[BetBlock]) -> float:
    """
    Compute sum of all block effective fragilities.

    Args:
        blocks: Sequence of BetBlock objects

    Returns:
        Sum of effective fragilities (sumBlocks)
    """
    return sum(block.effective_fragility for block in blocks)


def compute_raw_fragility(
    sum_blocks: float,
    leg_penalty: float,
    correlation_penalty: float,
) -> float:
    """
    Compute raw fragility per canonical formula.

    Formula: rawFragility = sumBlocks + legPenalty + correlationPenalty

    Args:
        sum_blocks: Sum of block effective fragilities
        leg_penalty: Penalty based on number of legs
        correlation_penalty: Penalty for correlated blocks (INPUT)

    Returns:
        Raw fragility value
    """
    return sum_blocks + leg_penalty + correlation_penalty


def compute_final_fragility(
    raw_fragility: float,
    correlation_multiplier: float,
) -> float:
    """
    Compute final fragility with clamping.

    Formula: finalFragility = rawFragility × correlationMultiplier
    Then clamp to [0, 100].

    Args:
        raw_fragility: rawFragility = sumBlocks + legPenalty + correlationPenalty
        correlation_multiplier: Multiplier for correlations (INPUT)

    Returns:
        Final fragility clamped to [0, 100]
    """
    unclamped = raw_fragility * correlation_multiplier
    return max(0.0, min(100.0, unclamped))


def compute_parlay_metrics(
    blocks: Sequence[BetBlock],
    correlation_penalty: float,
    correlation_multiplier: float,
) -> ParlayMetrics:
    """
    Compute all parlay metrics from blocks and correlation inputs.

    Canonical formulas:
    - sumBlocks = sum(block.effectiveFragility)
    - legPenalty = 8 × (legs ^ 1.5)
    - rawFragility = sumBlocks + legPenalty + correlationPenalty
    - finalFragility = rawFragility × correlationMultiplier, clamped [0, 100]

    Args:
        blocks: Sequence of BetBlock objects
        correlation_penalty: Penalty for correlated blocks (INPUT)
        correlation_multiplier: Multiplier for correlations (INPUT)

    Returns:
        ParlayMetrics with all computed values

    Raises:
        ValueError: If blocks is empty or correlation_multiplier is invalid
    """
    if not blocks:
        raise ValueError("blocks cannot be empty")

    # Validate correlation_multiplier is in valid set
    valid_multipliers = {1.0, 1.15, 1.3, 1.5}
    if correlation_multiplier not in valid_multipliers:
        raise ValueError(
            f"correlation_multiplier must be one of {sorted(valid_multipliers)}, "
            f"got {correlation_multiplier}"
        )

    num_legs = len(blocks)
    sum_blocks = compute_sum_blocks(blocks)
    leg_penalty = compute_leg_penalty(num_legs)
    raw_fragility = compute_raw_fragility(
        sum_blocks=sum_blocks,
        leg_penalty=leg_penalty,
        correlation_penalty=correlation_penalty,
    )
    final_fragility = compute_final_fragility(
        raw_fragility=raw_fragility,
        correlation_multiplier=correlation_multiplier,
    )

    return ParlayMetrics(
        raw_fragility=raw_fragility,
        leg_penalty=leg_penalty,
        correlation_penalty=correlation_penalty,
        correlation_multiplier=correlation_multiplier,
        final_fragility=final_fragility,
    )
