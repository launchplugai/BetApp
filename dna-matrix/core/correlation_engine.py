# core/correlation_engine.py
"""
Correlation Engine - Deterministic correlation detection and penalty computation.

Detects pairwise correlations between bet blocks and computes:
- correlations list with {blockA, blockB, type, penalty}
- correlationPenalty (sum of all pair penalties)
- correlationMultiplier (from thresholds)

Correlation Types and Penalties:
1. same_player_multi_props: +12
2. script_dependency: +8
3. volume_dependency: +10
4. td_dependency: +10
5. pace_dependency: +8

Multiplier Thresholds:
- ≤20: 1.0
- 21–35: 1.15
- 36–50: 1.30
- >50: 1.50

Rules:
- Penalties apply per pair
- If multiple types match same pair, apply highest penalty only
- Deterministic, no randomness
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple
from uuid import UUID

from core.models.leading_light import BetBlock, BetType, Correlation


# =============================================================================
# Constants
# =============================================================================

# Correlation penalties by type
PENALTY_SAME_PLAYER_MULTI_PROPS = 12
PENALTY_SCRIPT_DEPENDENCY = 8
PENALTY_VOLUME_DEPENDENCY = 10
PENALTY_TD_DEPENDENCY = 10
PENALTY_PACE_DEPENDENCY = 8

# Correlation type names
TYPE_SAME_PLAYER_MULTI_PROPS = "same_player_multi_props"
TYPE_SCRIPT_DEPENDENCY = "script_dependency"
TYPE_VOLUME_DEPENDENCY = "volume_dependency"
TYPE_TD_DEPENDENCY = "td_dependency"
TYPE_PACE_DEPENDENCY = "pace_dependency"


# =============================================================================
# Correlation Detection Functions
# =============================================================================


def detect_same_player_multi_props(block_a: BetBlock, block_b: BetBlock) -> bool:
    """
    Detect same_player_multi_props correlation.

    Trigger:
    - blockA.playerId == blockB.playerId (both non-None)
    - and both blocks are player_prop
    """
    if block_a.player_id is None or block_b.player_id is None:
        return False
    if block_a.player_id != block_b.player_id:
        return False
    if block_a.bet_type != BetType.PLAYER_PROP:
        return False
    if block_b.bet_type != BetType.PLAYER_PROP:
        return False
    return True


def detect_script_dependency(block_a: BetBlock, block_b: BetBlock) -> bool:
    """
    Detect script_dependency correlation.

    Trigger:
    - both blocks same gameId
    - and one is ml/spread AND the other is total/team_total
    - OR correlationTags include "script_dependency"
    """
    # Check for explicit tag
    if "script_dependency" in block_a.correlation_tags:
        if block_a.game_id == block_b.game_id:
            return True
    if "script_dependency" in block_b.correlation_tags:
        if block_a.game_id == block_b.game_id:
            return True

    # Check game id match
    if block_a.game_id != block_b.game_id:
        return False

    # Check bet type combination
    game_script_types = {BetType.ML, BetType.SPREAD}
    total_types = {BetType.TOTAL, BetType.TEAM_TOTAL}

    a_is_script = block_a.bet_type in game_script_types
    b_is_script = block_b.bet_type in game_script_types
    a_is_total = block_a.bet_type in total_types
    b_is_total = block_b.bet_type in total_types

    # One must be script type, other must be total type
    return (a_is_script and b_is_total) or (a_is_total and b_is_script)


def detect_volume_dependency(block_a: BetBlock, block_b: BetBlock) -> bool:
    """
    Detect volume_dependency correlation.

    Trigger:
    - same gameId
    - QB passing prop + WR/TE receiving prop
    - OR correlationTags include "volume_dependency"
    """
    # Check for explicit tag
    if "volume_dependency" in block_a.correlation_tags:
        if block_a.game_id == block_b.game_id:
            return True
    if "volume_dependency" in block_b.correlation_tags:
        if block_a.game_id == block_b.game_id:
            return True

    # Check game id match
    if block_a.game_id != block_b.game_id:
        return False

    # Check for QB/WR correlation via tags
    # (Selection text matching would require NLP, so we use tags)
    a_tags = set(block_a.correlation_tags)
    b_tags = set(block_b.correlation_tags)

    a_is_qb_passing = "qb_passing" in a_tags
    b_is_qb_passing = "qb_passing" in b_tags
    a_is_receiving = "wr_receiving" in a_tags or "te_receiving" in a_tags
    b_is_receiving = "wr_receiving" in b_tags or "te_receiving" in b_tags

    return (a_is_qb_passing and b_is_receiving) or (a_is_receiving and b_is_qb_passing)


def detect_td_dependency(block_a: BetBlock, block_b: BetBlock) -> bool:
    """
    Detect td_dependency correlation.

    Trigger:
    - any player TD prop + team spread/ml in same game
    - OR correlationTags include "td_dependency"
    """
    # Check for explicit tag
    if "td_dependency" in block_a.correlation_tags:
        if block_a.game_id == block_b.game_id:
            return True
    if "td_dependency" in block_b.correlation_tags:
        if block_a.game_id == block_b.game_id:
            return True

    # Check game id match
    if block_a.game_id != block_b.game_id:
        return False

    # Check for TD prop + team spread/ml
    a_tags = set(block_a.correlation_tags)
    b_tags = set(block_b.correlation_tags)

    a_is_td_prop = "td_prop" in a_tags
    b_is_td_prop = "td_prop" in b_tags

    team_types = {BetType.SPREAD, BetType.ML}
    a_is_team_bet = block_a.bet_type in team_types
    b_is_team_bet = block_b.bet_type in team_types

    return (a_is_td_prop and b_is_team_bet) or (a_is_team_bet and b_is_td_prop)


def detect_pace_dependency(block_a: BetBlock, block_b: BetBlock) -> bool:
    """
    Detect pace_dependency correlation.

    Trigger:
    - total over/under + passing/receiving volume props in same game
    - OR correlationTags include "pace_dependency"
    """
    # Check for explicit tag
    if "pace_dependency" in block_a.correlation_tags:
        if block_a.game_id == block_b.game_id:
            return True
    if "pace_dependency" in block_b.correlation_tags:
        if block_a.game_id == block_b.game_id:
            return True

    # Check game id match
    if block_a.game_id != block_b.game_id:
        return False

    # Check for total + volume prop
    a_tags = set(block_a.correlation_tags)
    b_tags = set(block_b.correlation_tags)

    a_is_total = block_a.bet_type == BetType.TOTAL
    b_is_total = block_b.bet_type == BetType.TOTAL

    volume_tags = {"passing_volume", "receiving_volume", "qb_passing", "wr_receiving", "te_receiving"}
    a_is_volume = bool(a_tags & volume_tags)
    b_is_volume = bool(b_tags & volume_tags)

    return (a_is_total and b_is_volume) or (a_is_volume and b_is_total)


# =============================================================================
# Main Correlation Functions
# =============================================================================


def detect_pair_correlations(
    block_a: BetBlock,
    block_b: BetBlock,
) -> List[Tuple[str, int]]:
    """
    Detect all correlation types between a pair of blocks.

    Returns list of (type, penalty) tuples for all matching correlations.
    """
    correlations: List[Tuple[str, int]] = []

    if detect_same_player_multi_props(block_a, block_b):
        correlations.append((TYPE_SAME_PLAYER_MULTI_PROPS, PENALTY_SAME_PLAYER_MULTI_PROPS))

    if detect_script_dependency(block_a, block_b):
        correlations.append((TYPE_SCRIPT_DEPENDENCY, PENALTY_SCRIPT_DEPENDENCY))

    if detect_volume_dependency(block_a, block_b):
        correlations.append((TYPE_VOLUME_DEPENDENCY, PENALTY_VOLUME_DEPENDENCY))

    if detect_td_dependency(block_a, block_b):
        correlations.append((TYPE_TD_DEPENDENCY, PENALTY_TD_DEPENDENCY))

    if detect_pace_dependency(block_a, block_b):
        correlations.append((TYPE_PACE_DEPENDENCY, PENALTY_PACE_DEPENDENCY))

    return correlations


def get_highest_penalty_correlation(
    correlations: List[Tuple[str, int]],
) -> Tuple[str, int] | None:
    """
    Given multiple correlations for a pair, return the one with highest penalty.

    Rule: If multiple types match the same pair, apply the highest penalty only.
    """
    if not correlations:
        return None
    return max(correlations, key=lambda x: x[1])


def compute_correlation_multiplier(total_penalty: float) -> float:
    """
    Compute correlation multiplier from total penalty using thresholds.

    Thresholds:
    - ≤20: 1.0
    - 21–35: 1.15
    - 36–50: 1.30
    - >50: 1.50
    """
    if total_penalty <= 20:
        return 1.0
    elif total_penalty <= 35:
        return 1.15
    elif total_penalty <= 50:
        return 1.3
    else:
        return 1.5


@dataclass
class CorrelationResult:
    """Result of correlation analysis."""
    correlations: Tuple[Correlation, ...]
    correlation_penalty: float
    correlation_multiplier: float


def compute_correlations(blocks: Sequence[BetBlock]) -> CorrelationResult:
    """
    Compute all correlations between blocks in a parlay.

    Analyzes all pairs of blocks, detects correlations, and computes:
    - correlations: list of Correlation objects for each penalized pair
    - correlation_penalty: sum of all pair penalties
    - correlation_multiplier: from threshold table

    Args:
        blocks: Sequence of BetBlock objects

    Returns:
        CorrelationResult with all computed values
    """
    if len(blocks) < 2:
        return CorrelationResult(
            correlations=(),
            correlation_penalty=0.0,
            correlation_multiplier=1.0,
        )

    correlation_list: List[Correlation] = []
    total_penalty = 0.0

    # Check all unique pairs
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            block_a = blocks[i]
            block_b = blocks[j]

            # Detect all correlations for this pair
            pair_correlations = detect_pair_correlations(block_a, block_b)

            if pair_correlations:
                # Apply highest penalty only (avoid double counting)
                highest = get_highest_penalty_correlation(pair_correlations)
                if highest:
                    corr_type, penalty = highest
                    correlation_list.append(
                        Correlation(
                            block_a=block_a.block_id,
                            block_b=block_b.block_id,
                            type=corr_type,
                            penalty=float(penalty),
                        )
                    )
                    total_penalty += penalty

    multiplier = compute_correlation_multiplier(total_penalty)

    return CorrelationResult(
        correlations=tuple(correlation_list),
        correlation_penalty=total_penalty,
        correlation_multiplier=multiplier,
    )
