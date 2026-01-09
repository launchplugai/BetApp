# core/models/leading_light.py
"""
Leading Light Core Types

Implements the canonical data structures for the Leading Light betting evaluation system.
These types evaluate structural fragility, not outcome prediction.

System Invariants (enforced by validation):
- Fragility never decreases due to context
- Context signals never generate bets
- All context deltas must be >= 0
- effectiveFragility >= baseFragility
- finalFragility clamped [0, 100]
- correlationMultiplier must be one of [1.0, 1.15, 1.3, 1.5]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class BetType(str, Enum):
    """Types of bets supported by the system."""
    PLAYER_PROP = "player_prop"
    SPREAD = "spread"
    TOTAL = "total"
    ML = "ml"
    TEAM_TOTAL = "team_total"


class ContextSignalType(str, Enum):
    """Types of context signals (facts)."""
    WEATHER = "weather"
    INJURY = "injury"
    TRADE = "trade"


class ContextTarget(str, Enum):
    """What entity a context signal targets."""
    PLAYER = "player"
    TEAM = "team"
    GAME = "game"


class SuggestedBlockLabel(str, Enum):
    """Labels for suggested blocks indicating risk level."""
    LOWEST_ADDED_RISK = "Lowest added risk"
    BALANCED = "Balanced"
    AGGRESSIVE_WITHIN_LIMITS = "Aggressive but within limits"


# =============================================================================
# Supporting Types
# =============================================================================


@dataclass(frozen=True, slots=True)
class ContextModifier:
    """
    A single context modifier applied to a bet block.
    Represents impact category, not the raw signal.
    """
    applied: bool
    delta: float
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.applied, bool):
            raise TypeError("applied must be a boolean")
        if not isinstance(self.delta, (int, float)):
            raise TypeError("delta must be a number")
        if self.delta < 0:
            raise ValueError("delta must be >= 0 (context never reduces fragility)")
        if self.reason is not None and not isinstance(self.reason, str):
            raise TypeError("reason must be a string or None")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextModifier":
        return cls(
            applied=data["applied"],
            delta=data["delta"],
            reason=data.get("reason")
        )

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "applied": self.applied,
            "delta": self.delta,
        }
        if self.reason is not None:
            result["reason"] = self.reason
        return result


@dataclass(frozen=True, slots=True)
class ContextModifiers:
    """
    Collection of all context modifiers for a bet block.
    Maps signal facts to impact categories.
    - weather: from weather signals
    - injury: from injury signals
    - trade: from trade signals
    - role: DERIVED from trade and injury signals (role instability)
    """
    weather: ContextModifier
    injury: ContextModifier
    trade: ContextModifier
    role: ContextModifier

    def __post_init__(self) -> None:
        for name in ["weather", "injury", "trade", "role"]:
            val = getattr(self, name)
            if not isinstance(val, ContextModifier):
                raise TypeError(f"{name} must be a ContextModifier")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextModifiers":
        return cls(
            weather=ContextModifier.from_dict(data["weather"]),
            injury=ContextModifier.from_dict(data["injury"]),
            trade=ContextModifier.from_dict(data["trade"]),
            role=ContextModifier.from_dict(data["role"])
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "weather": self.weather.to_dict(),
            "injury": self.injury.to_dict(),
            "trade": self.trade.to_dict(),
            "role": self.role.to_dict(),
        }

    def total_delta(self) -> float:
        """Sum of all applied deltas."""
        total = 0.0
        for name in ["weather", "injury", "trade", "role"]:
            modifier = getattr(self, name)
            if modifier.applied:
                total += modifier.delta
        return total


@dataclass(frozen=True, slots=True)
class ContextImpact:
    """Impact specification for a context signal."""
    fragility_delta: float
    confidence_delta: float

    def __post_init__(self) -> None:
        if not isinstance(self.fragility_delta, (int, float)):
            raise TypeError("fragility_delta must be a number")
        if self.fragility_delta < 0:
            raise ValueError("fragility_delta must be >= 0 (context never reduces fragility)")
        if not isinstance(self.confidence_delta, (int, float)):
            raise TypeError("confidence_delta must be a number")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextImpact":
        return cls(
            fragility_delta=data.get("fragilityDelta", data.get("fragility_delta", 0)),
            confidence_delta=data.get("confidenceDelta", data.get("confidence_delta", 0))
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fragilityDelta": self.fragility_delta,
            "confidenceDelta": self.confidence_delta,
        }


@dataclass(frozen=True, slots=True)
class Correlation:
    """Correlation between two bet blocks in a parlay."""
    block_a: UUID
    block_b: UUID
    type: str
    penalty: float

    def __post_init__(self) -> None:
        if not isinstance(self.block_a, UUID):
            raise TypeError("block_a must be a UUID")
        if not isinstance(self.block_b, UUID):
            raise TypeError("block_b must be a UUID")
        if not isinstance(self.type, str) or not self.type.strip():
            raise ValueError("type must be a non-empty string")
        if not isinstance(self.penalty, (int, float)):
            raise TypeError("penalty must be a number")
        if self.penalty < 0:
            raise ValueError("penalty must be >= 0")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Correlation":
        return cls(
            block_a=UUID(data["blockA"]) if isinstance(data["blockA"], str) else data["blockA"],
            block_b=UUID(data["blockB"]) if isinstance(data["blockB"], str) else data["blockB"],
            type=data["type"],
            penalty=data["penalty"]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blockA": str(self.block_a),
            "blockB": str(self.block_b),
            "type": self.type,
            "penalty": self.penalty,
        }


@dataclass(frozen=True, slots=True)
class ParlayMetrics:
    """Computed metrics for a parlay."""
    raw_fragility: float
    leg_penalty: float
    correlation_penalty: float
    correlation_multiplier: float
    final_fragility: float

    # Valid correlation multipliers per specification
    VALID_MULTIPLIERS = frozenset({1.0, 1.15, 1.3, 1.5})

    def __post_init__(self) -> None:
        for name in ["raw_fragility", "leg_penalty", "correlation_penalty",
                     "correlation_multiplier", "final_fragility"]:
            val = getattr(self, name)
            if not isinstance(val, (int, float)):
                raise TypeError(f"{name} must be a number")

        if self.correlation_multiplier not in self.VALID_MULTIPLIERS:
            raise ValueError(
                f"correlation_multiplier must be one of {sorted(self.VALID_MULTIPLIERS)}, "
                f"got {self.correlation_multiplier}"
            )

        if self.final_fragility < 0 or self.final_fragility > 100:
            raise ValueError("final_fragility must be clamped between 0 and 100")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParlayMetrics":
        return cls(
            raw_fragility=data.get("rawFragility", data.get("raw_fragility", 0)),
            leg_penalty=data.get("legPenalty", data.get("leg_penalty", 0)),
            correlation_penalty=data.get("correlationPenalty", data.get("correlation_penalty", 0)),
            correlation_multiplier=data.get("correlationMultiplier", data.get("correlation_multiplier", 1.0)),
            final_fragility=data.get("finalFragility", data.get("final_fragility", 0))
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rawFragility": self.raw_fragility,
            "legPenalty": self.leg_penalty,
            "correlationPenalty": self.correlation_penalty,
            "correlationMultiplier": self.correlation_multiplier,
            "finalFragility": self.final_fragility,
        }


@dataclass(frozen=True, slots=True)
class DNAEnforcement:
    """DNA Matrix enforcement rules for a parlay."""
    max_legs: int
    fragility_tolerance: float
    stake_cap: float
    violations: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.max_legs, int):
            raise TypeError("max_legs must be an integer")
        if self.max_legs < 1:
            raise ValueError("max_legs must be >= 1")
        if not isinstance(self.fragility_tolerance, (int, float)):
            raise TypeError("fragility_tolerance must be a number")
        if not isinstance(self.stake_cap, (int, float)):
            raise TypeError("stake_cap must be a number")
        if self.stake_cap < 0:
            raise ValueError("stake_cap must be >= 0")
        if not isinstance(self.violations, tuple):
            raise TypeError("violations must be a tuple of strings")
        for v in self.violations:
            if not isinstance(v, str):
                raise TypeError("each violation must be a string")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DNAEnforcement":
        violations = data.get("violations", [])
        if isinstance(violations, list):
            violations = tuple(violations)
        return cls(
            max_legs=data.get("maxLegs", data.get("max_legs", 1)),
            fragility_tolerance=data.get("fragilityTolerance", data.get("fragility_tolerance", 0)),
            stake_cap=data.get("stakeCap", data.get("stake_cap", 0)),
            violations=violations
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "maxLegs": self.max_legs,
            "fragilityTolerance": self.fragility_tolerance,
            "stakeCap": self.stake_cap,
            "violations": list(self.violations),
        }


# =============================================================================
# Core Types (The Four Canonical Schemas)
# =============================================================================


@dataclass(frozen=True, slots=True)
class BetBlock:
    """
    A single bet with fragility calculation.

    Rules:
    - baseFragility is immutable after creation
    - effectiveFragility is computed, never user-supplied
    - effectiveFragility >= baseFragility
    - context deltas must be >= 0
    """
    block_id: UUID
    sport: str
    game_id: str
    bet_type: BetType
    selection: str
    base_fragility: float
    context_modifiers: ContextModifiers
    correlation_tags: tuple[str, ...]
    effective_fragility: float
    player_id: Optional[str] = None
    team_id: Optional[str] = None

    def __post_init__(self) -> None:
        # Type validation
        if not isinstance(self.block_id, UUID):
            raise TypeError("block_id must be a UUID")
        if not isinstance(self.sport, str) or not self.sport.strip():
            raise ValueError("sport must be a non-empty string")
        if not isinstance(self.game_id, str) or not self.game_id.strip():
            raise ValueError("game_id must be a non-empty string")

        # Normalize bet_type to enum
        if isinstance(self.bet_type, str):
            object.__setattr__(self, "bet_type", BetType(self.bet_type))
        elif not isinstance(self.bet_type, BetType):
            raise TypeError("bet_type must be a BetType enum")

        if not isinstance(self.selection, str) or not self.selection.strip():
            raise ValueError("selection must be a non-empty string")

        if not isinstance(self.base_fragility, (int, float)):
            raise TypeError("base_fragility must be a number")

        if not isinstance(self.context_modifiers, ContextModifiers):
            raise TypeError("context_modifiers must be a ContextModifiers")

        if not isinstance(self.correlation_tags, tuple):
            raise TypeError("correlation_tags must be a tuple of strings")
        for tag in self.correlation_tags:
            if not isinstance(tag, str):
                raise TypeError("each correlation_tag must be a string")

        if not isinstance(self.effective_fragility, (int, float)):
            raise TypeError("effective_fragility must be a number")

        # INVARIANT: effectiveFragility >= baseFragility
        if self.effective_fragility < self.base_fragility:
            raise ValueError(
                f"INVARIANT VIOLATION: effective_fragility ({self.effective_fragility}) "
                f"must be >= base_fragility ({self.base_fragility}). "
                "Fragility never decreases due to context."
            )

        # Optional fields
        if self.player_id is not None and not isinstance(self.player_id, str):
            raise TypeError("player_id must be a string or None")
        if self.team_id is not None and not isinstance(self.team_id, str):
            raise TypeError("team_id must be a string or None")

    @classmethod
    def create(
        cls,
        sport: str,
        game_id: str,
        bet_type: BetType,
        selection: str,
        base_fragility: float,
        context_modifiers: ContextModifiers,
        correlation_tags: List[str],
        player_id: Optional[str] = None,
        team_id: Optional[str] = None,
        block_id: Optional[UUID] = None,
    ) -> "BetBlock":
        """
        Factory method that computes effective_fragility automatically.
        This ensures the invariant is maintained.
        """
        if block_id is None:
            block_id = uuid4()

        # Compute effective fragility
        effective = base_fragility + context_modifiers.total_delta()

        return cls(
            block_id=block_id,
            sport=sport,
            game_id=game_id,
            bet_type=bet_type,
            selection=selection,
            base_fragility=base_fragility,
            context_modifiers=context_modifiers,
            correlation_tags=tuple(correlation_tags),
            effective_fragility=effective,
            player_id=player_id,
            team_id=team_id,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BetBlock":
        block_id = data.get("blockId", data.get("block_id"))
        if isinstance(block_id, str):
            block_id = UUID(block_id)

        correlation_tags = data.get("correlationTags", data.get("correlation_tags", []))
        if isinstance(correlation_tags, list):
            correlation_tags = tuple(correlation_tags)

        return cls(
            block_id=block_id,
            sport=data["sport"],
            game_id=data.get("gameId", data.get("game_id")),
            bet_type=BetType(data.get("betType", data.get("bet_type"))),
            selection=data["selection"],
            base_fragility=data.get("baseFragility", data.get("base_fragility")),
            context_modifiers=ContextModifiers.from_dict(
                data.get("contextModifiers", data.get("context_modifiers"))
            ),
            correlation_tags=correlation_tags,
            effective_fragility=data.get("effectiveFragility", data.get("effective_fragility")),
            player_id=data.get("playerId", data.get("player_id")),
            team_id=data.get("teamId", data.get("team_id")),
        )

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "blockId": str(self.block_id),
            "sport": self.sport,
            "gameId": self.game_id,
            "betType": self.bet_type.value,
            "selection": self.selection,
            "baseFragility": self.base_fragility,
            "contextModifiers": self.context_modifiers.to_dict(),
            "correlationTags": list(self.correlation_tags),
            "effectiveFragility": self.effective_fragility,
        }
        if self.player_id is not None:
            result["playerId"] = self.player_id
        if self.team_id is not None:
            result["teamId"] = self.team_id
        return result


@dataclass(frozen=True, slots=True)
class ContextSignal:
    """
    A context signal representing a fact that may affect fragility.

    Rules:
    - Context signals never decide bets
    - fragilityDelta must be >= 0
    - confidence is signal confidence, not bet confidence
    """
    context_id: UUID
    type: ContextSignalType
    target: ContextTarget
    status: str
    confidence: float
    impact: ContextImpact
    explanation: str

    def __post_init__(self) -> None:
        if not isinstance(self.context_id, UUID):
            raise TypeError("context_id must be a UUID")

        # Normalize type to enum
        if isinstance(self.type, str):
            object.__setattr__(self, "type", ContextSignalType(self.type))
        elif not isinstance(self.type, ContextSignalType):
            raise TypeError("type must be a ContextSignalType enum")

        # Normalize target to enum
        if isinstance(self.target, str):
            object.__setattr__(self, "target", ContextTarget(self.target))
        elif not isinstance(self.target, ContextTarget):
            raise TypeError("target must be a ContextTarget enum")

        if not isinstance(self.status, str):
            raise TypeError("status must be a string")

        if not isinstance(self.confidence, (int, float)):
            raise TypeError("confidence must be a number")
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        if not isinstance(self.impact, ContextImpact):
            raise TypeError("impact must be a ContextImpact")

        if not isinstance(self.explanation, str):
            raise TypeError("explanation must be a string")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextSignal":
        context_id = data.get("contextId", data.get("context_id"))
        if isinstance(context_id, str):
            context_id = UUID(context_id)

        return cls(
            context_id=context_id,
            type=ContextSignalType(data["type"]),
            target=ContextTarget(data["target"]),
            status=data["status"],
            confidence=data["confidence"],
            impact=ContextImpact.from_dict(data["impact"]),
            explanation=data["explanation"]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contextId": str(self.context_id),
            "type": self.type.value,
            "target": self.target.value,
            "status": self.status,
            "confidence": self.confidence,
            "impact": self.impact.to_dict(),
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class ParlayState:
    """
    Derived state for a parlay (collection of bet blocks).

    Rules:
    - ParlayState is derived state, not user input
    - finalFragility must be clamped between 0 and 100
    - correlationMultiplier must be one of [1.0, 1.15, 1.3, 1.5]
    """
    parlay_id: UUID
    blocks: tuple[BetBlock, ...]
    metrics: ParlayMetrics
    correlations: tuple[Correlation, ...]
    dna_enforcement: DNAEnforcement

    def __post_init__(self) -> None:
        if not isinstance(self.parlay_id, UUID):
            raise TypeError("parlay_id must be a UUID")

        if not isinstance(self.blocks, tuple):
            raise TypeError("blocks must be a tuple of BetBlock")
        for block in self.blocks:
            if not isinstance(block, BetBlock):
                raise TypeError("each block must be a BetBlock")

        if not isinstance(self.metrics, ParlayMetrics):
            raise TypeError("metrics must be a ParlayMetrics")

        if not isinstance(self.correlations, tuple):
            raise TypeError("correlations must be a tuple of Correlation")
        for corr in self.correlations:
            if not isinstance(corr, Correlation):
                raise TypeError("each correlation must be a Correlation")

        if not isinstance(self.dna_enforcement, DNAEnforcement):
            raise TypeError("dna_enforcement must be a DNAEnforcement")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParlayState":
        parlay_id = data.get("parlayId", data.get("parlay_id"))
        if isinstance(parlay_id, str):
            parlay_id = UUID(parlay_id)

        blocks = data.get("blocks", [])
        if isinstance(blocks, list):
            blocks = tuple(BetBlock.from_dict(b) for b in blocks)

        correlations = data.get("correlations", [])
        if isinstance(correlations, list):
            correlations = tuple(Correlation.from_dict(c) for c in correlations)

        return cls(
            parlay_id=parlay_id,
            blocks=blocks,
            metrics=ParlayMetrics.from_dict(data["metrics"]),
            correlations=correlations,
            dna_enforcement=DNAEnforcement.from_dict(
                data.get("dnaEnforcement", data.get("dna_enforcement"))
            )
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "parlayId": str(self.parlay_id),
            "blocks": [b.to_dict() for b in self.blocks],
            "metrics": self.metrics.to_dict(),
            "correlations": [c.to_dict() for c in self.correlations],
            "dnaEnforcement": self.dna_enforcement.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SuggestedBlock:
    """
    A suggestion for adding a block to a parlay.

    Rules:
    - deltaFragility must be > 0
    - SuggestedBlock never mutates ParlayState directly
    """
    candidate_block_id: UUID
    delta_fragility: float
    added_correlation: float
    dna_compatible: bool
    label: SuggestedBlockLabel
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_block_id, UUID):
            raise TypeError("candidate_block_id must be a UUID")

        if not isinstance(self.delta_fragility, (int, float)):
            raise TypeError("delta_fragility must be a number")
        if self.delta_fragility <= 0:
            raise ValueError("delta_fragility must be > 0 (adding a block always adds risk)")

        if not isinstance(self.added_correlation, (int, float)):
            raise TypeError("added_correlation must be a number")

        if not isinstance(self.dna_compatible, bool):
            raise TypeError("dna_compatible must be a boolean")

        # Normalize label to enum
        if isinstance(self.label, str):
            object.__setattr__(self, "label", SuggestedBlockLabel(self.label))
        elif not isinstance(self.label, SuggestedBlockLabel):
            raise TypeError("label must be a SuggestedBlockLabel enum")

        if not isinstance(self.reason, str):
            raise TypeError("reason must be a string")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SuggestedBlock":
        candidate_block_id = data.get("candidateBlockId", data.get("candidate_block_id"))
        if isinstance(candidate_block_id, str):
            candidate_block_id = UUID(candidate_block_id)

        return cls(
            candidate_block_id=candidate_block_id,
            delta_fragility=data.get("deltaFragility", data.get("delta_fragility")),
            added_correlation=data.get("addedCorrelation", data.get("added_correlation")),
            dna_compatible=data.get("dnaCompatible", data.get("dna_compatible")),
            label=SuggestedBlockLabel(data["label"]),
            reason=data["reason"]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidateBlockId": str(self.candidate_block_id),
            "deltaFragility": self.delta_fragility,
            "addedCorrelation": self.added_correlation,
            "dnaCompatible": self.dna_compatible,
            "label": self.label.value,
            "reason": self.reason,
        }
