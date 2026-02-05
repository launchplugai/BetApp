# app/structure_snapshot.py
"""
Structural Snapshot Generator (Ticket 38B-A)

Generates machine-readable structural snapshots of evaluated parlays.

Purpose:
- Capture "what was actually analyzed" in a deterministic, testable format
- Enable structural comparison across evaluations
- Support delta tracking (Ticket 38B-B)

Design Principles:
1. Snapshot is DERIVED from evaluated data (not re-parsed)
2. Order is preserved (canonical leg order from Ticket 37)
3. Deterministic (same input → same snapshot)
4. Engine-independent (no frozen code dependencies)

Snapshot Contract:
{
  "structure": {
    "leg_count": int,
    "leg_ids": [str, ...],  # Ticket 37 deterministic IDs, canonical order
    "leg_types": [str, ...],  # BetType values, same order as leg_ids
    "props": int,  # Count of player_prop legs
    "totals": int,  # Count of total + team_total legs
    "correlation_flags": [str, ...],  # e.g., ["same_game"]
    "volatility_sources": [str, ...]  # e.g., ["player_prop", "totals"]
  }
}
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import List, Optional

from core.models.leading_light import BetBlock, BetType


@dataclass(frozen=True)
class StructureSnapshot:
    """
    Machine-readable structural snapshot of an evaluated parlay.

    Attributes:
        leg_count: Number of legs analyzed
        leg_ids: Deterministic leg IDs (Ticket 37), in canonical order
        leg_types: BetType values, same order as leg_ids
        props: Count of player_prop legs
        totals: Count of total + team_total legs
        correlation_flags: Structural correlation indicators (e.g., "same_game")
        volatility_sources: Sources of volatility (e.g., "player_prop", "totals")
    """
    leg_count: int
    leg_ids: tuple[str, ...]
    leg_types: tuple[str, ...]
    props: int
    totals: int
    correlation_flags: tuple[str, ...]
    volatility_sources: tuple[str, ...]

    def to_dict(self) -> dict:
        """Convert snapshot to JSON-serializable dict."""
        return {
            "leg_count": self.leg_count,
            "leg_ids": list(self.leg_ids),
            "leg_types": list(self.leg_types),
            "props": self.props,
            "totals": self.totals,
            "correlation_flags": list(self.correlation_flags),
            "volatility_sources": list(self.volatility_sources),
        }


def generate_leg_id(block: BetBlock) -> str:
    """
    Generate deterministic leg ID from BetBlock content.

    Uses SHA-256 hash of canonical fields (Ticket 37 contract).

    Format: First 16 chars of SHA-256(entity|bet_type|selection|sport)

    Args:
        block: BetBlock to generate ID for

    Returns:
        16-character deterministic ID
    """
    # Construct entity from player_id or team_id
    entity = block.player_id or block.team_id or block.game_id or "unknown"
    
    # Canonical fields for leg identity (Ticket 37)
    canonical = f"{entity}|{block.bet_type.value}|{block.selection}|{block.sport}"
    hash_digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return hash_digest[:16]


def detect_correlation_flags(blocks: List[BetBlock]) -> tuple[str, ...]:
    """
    Detect structural correlation flags from blocks.

    Current flags:
    - "same_game": Multiple legs reference the same game/matchup

    Args:
        blocks: List of BetBlocks

    Returns:
        Tuple of correlation flag strings
    """
    flags = []

    # Same-game detection: Check if multiple blocks reference same game_id
    if len(blocks) >= 2:
        game_ids_seen = set()
        same_game_detected = False
        for block in blocks:
            if block.game_id in game_ids_seen:
                same_game_detected = True
                break
            game_ids_seen.add(block.game_id)

        if same_game_detected:
            flags.append("same_game")

    return tuple(flags)


def detect_volatility_sources(blocks: List[BetBlock]) -> tuple[str, ...]:
    """
    Detect sources of volatility from leg types.

    Volatility sources:
    - "player_prop": Contains player prop bets
    - "totals": Contains total or team_total bets

    Args:
        blocks: List of BetBlocks

    Returns:
        Tuple of volatility source strings
    """
    sources = set()

    for block in blocks:
        if block.bet_type == BetType.PLAYER_PROP:
            sources.add("player_prop")
        if block.bet_type in (BetType.TOTAL, BetType.TEAM_TOTAL):
            sources.add("totals")

    return tuple(sorted(sources))  # Sort for determinism


def generate_structure_snapshot(
    blocks: List[BetBlock],
    canonical_legs: Optional[List] = None
) -> StructureSnapshot:
    """
    Generate structural snapshot from evaluated bet blocks.

    This is the ONLY function that builds snapshots.
    All snapshot generation MUST go through this function.

    Args:
        blocks: Parsed BetBlocks from evaluation
        canonical_legs: Optional canonical legs from builder (Ticket 37)
                       Can be list of dicts or list of CanonicalLegData objects

    Returns:
        StructureSnapshot with deterministic structure

    Design Notes:
    - Snapshot is derived from blocks, not re-parsed
    - Order is preserved (blocks are in canonical order)
    - Deterministic (same blocks → same snapshot)
    - No engine dependencies (uses only BetBlock data)
    """
    # Leg count: Use canonical legs if present, else blocks
    if canonical_legs:
        leg_count = len(canonical_legs)
        # Use canonical leg IDs/types if present (handle both dict and dataclass)
        leg_ids = []
        leg_types = []
        for leg in canonical_legs:
            # Handle dict or dataclass (hasattr works for both)
            if hasattr(leg, 'leg_id'):
                leg_ids.append(leg.leg_id if leg.leg_id else "")
            elif isinstance(leg, dict):
                leg_ids.append(leg.get("leg_id", ""))
            else:
                leg_ids.append("")
            
            if hasattr(leg, 'market'):
                leg_types.append(leg.market)
            elif isinstance(leg, dict):
                leg_types.append(leg.get("market", ""))
            else:
                leg_types.append("")
        
        leg_ids = tuple(leg_ids)
        leg_types = tuple(leg_types)
    else:
        leg_count = len(blocks)
        # Generate deterministic leg IDs from blocks
        leg_ids = tuple(generate_leg_id(block) for block in blocks)
        # Extract leg types from blocks
        leg_types = tuple(block.bet_type.value for block in blocks)

    # Count props and totals
    props = sum(1 for block in blocks if block.bet_type == BetType.PLAYER_PROP)
    totals = sum(
        1 for block in blocks
        if block.bet_type in (BetType.TOTAL, BetType.TEAM_TOTAL)
    )

    # Detect correlation flags
    correlation_flags = detect_correlation_flags(blocks)

    # Detect volatility sources
    volatility_sources = detect_volatility_sources(blocks)

    return StructureSnapshot(
        leg_count=leg_count,
        leg_ids=leg_ids,
        leg_types=leg_types,
        props=props,
        totals=totals,
        correlation_flags=correlation_flags,
        volatility_sources=volatility_sources,
    )
