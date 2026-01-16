# core/parlay_reducer.py
"""
Parlay State Reducer - Deterministic ParlayState construction.

This is the spine of the Parlay Builder. All ParlayState assembly goes through here.
UI calls reducer. API calls reducer. Suggestions simulate reducer.

Order of Operations (non-negotiable):
1. Compute each block.effectiveFragility from baseFragility + contextModifiers
2. Compute correlations from blocks (correlations list, penalty, multiplier)
3. Compute legPenalty from number of blocks
4. Compute rawFragility and finalFragility
5. Build ParlayState with blocks, metrics, correlations, dnaEnforcement

No step skipping, no caching, no partial updates.
Every update recomputes derived fields from scratch.
"""
from __future__ import annotations

from typing import List, Sequence
from uuid import UUID, uuid4

from core.models.leading_light import (
    BetBlock,
    Correlation,
    DNAEnforcement,
    ParlayMetrics,
    ParlayState,
)
from core.correlation_engine import compute_correlations
from core.fragility_engine import (
    compute_leg_penalty,
    compute_sum_blocks,
    compute_raw_fragility,
    compute_final_fragility,
)


def build_parlay_state(
    blocks: Sequence[BetBlock],
    parlay_id: UUID | None = None,
) -> ParlayState:
    """
    Build a complete ParlayState from a list of BetBlocks.

    This is the main entry point for ParlayState construction.
    All derived fields are computed from scratch.

    Order of operations:
    1. effectiveFragility already computed in BetBlock (via BetBlock.create)
    2. Compute correlations (list, penalty, multiplier)
    3. Compute legPenalty
    4. Compute rawFragility and finalFragility
    5. Build ParlayState

    Args:
        blocks: Sequence of BetBlock objects (must have effectiveFragility set)
        parlay_id: Optional UUID for the parlay (generated if not provided)

    Returns:
        Complete ParlayState with all derived fields computed
    """
    if parlay_id is None:
        parlay_id = uuid4()

    # Handle empty parlay
    if not blocks:
        return ParlayState(
            parlay_id=parlay_id,
            blocks=(),
            metrics=ParlayMetrics(
                raw_fragility=0.0,
                leg_penalty=0.0,
                correlation_penalty=0.0,
                correlation_multiplier=1.0,
                final_fragility=0.0,
            ),
            correlations=(),
            dna_enforcement=_empty_dna_enforcement(),
        )

    # Step 1: effectiveFragility already computed in BetBlock.create()
    # (Blocks are immutable, so we trust they have correct effective fragility)

    # Step 2: Compute correlations
    correlation_result = compute_correlations(blocks)

    # Step 3: Compute legPenalty
    num_legs = len(blocks)
    leg_penalty = compute_leg_penalty(num_legs)

    # Step 4: Compute rawFragility and finalFragility
    sum_blocks = compute_sum_blocks(blocks)
    raw_fragility = compute_raw_fragility(
        sum_blocks=sum_blocks,
        leg_penalty=leg_penalty,
        correlation_penalty=correlation_result.correlation_penalty,
    )
    final_fragility = compute_final_fragility(
        raw_fragility=raw_fragility,
        correlation_multiplier=correlation_result.correlation_multiplier,
    )

    # Step 5: Build ParlayState
    metrics = ParlayMetrics(
        raw_fragility=raw_fragility,
        leg_penalty=leg_penalty,
        correlation_penalty=correlation_result.correlation_penalty,
        correlation_multiplier=correlation_result.correlation_multiplier,
        final_fragility=final_fragility,
    )

    return ParlayState(
        parlay_id=parlay_id,
        blocks=tuple(blocks),
        metrics=metrics,
        correlations=correlation_result.correlations,
        dna_enforcement=_empty_dna_enforcement(),
    )


def add_block(parlay_state: ParlayState, block: BetBlock) -> ParlayState:
    """
    Add a block to the parlay and recompute all derived fields.

    Returns a new ParlayState with the block added.
    The original ParlayState is not modified (immutable update).

    Args:
        parlay_state: Current parlay state
        block: Block to add

    Returns:
        New ParlayState with block added and all fields recomputed
    """
    new_blocks = list(parlay_state.blocks) + [block]
    return build_parlay_state(new_blocks, parlay_id=parlay_state.parlay_id)


def remove_block(parlay_state: ParlayState, block_id: UUID) -> ParlayState:
    """
    Remove a block from the parlay and recompute all derived fields.

    Returns a new ParlayState with the block removed.
    The original ParlayState is not modified (immutable update).

    Args:
        parlay_state: Current parlay state
        block_id: UUID of block to remove

    Returns:
        New ParlayState with block removed and all fields recomputed

    Raises:
        ValueError: If block_id not found in parlay
    """
    new_blocks = [b for b in parlay_state.blocks if b.block_id != block_id]

    if len(new_blocks) == len(parlay_state.blocks):
        raise ValueError(f"Block with id {block_id} not found in parlay")

    return build_parlay_state(new_blocks, parlay_id=parlay_state.parlay_id)


def _empty_dna_enforcement() -> DNAEnforcement:
    """
    Create an empty (placeholder) DNAEnforcement.

    DNA enforcement is computed in TASK 6, but we need a structurally
    valid placeholder here.
    """
    return DNAEnforcement(
        max_legs=10,  # Default max
        fragility_tolerance=100.0,  # Default tolerance
        stake_cap=0.0,  # No stake cap by default
        violations=(),  # Empty violations list
    )
