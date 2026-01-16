# core/builder_contract.py
"""
Parlay Builder UI Contract.

Provides a UI-focused response model for live parlay builders.
Aggregates everything the frontend needs without re-running engines.

No frontend components. No styling. No notification delivery.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence
from uuid import UUID

from core.models.leading_light import (
    BetBlock,
    Correlation,
    SuggestedBlock,
)
from core.evaluation import EvaluationResponse
from core.risk_inductor import RiskInductor
from core.alert_engine import Alert, compute_alerts


# =============================================================================
# Context Deltas
# =============================================================================


@dataclass(frozen=True)
class ContextDeltas:
    """Per-block context delta breakdown."""
    weather: float
    injury: float
    trade: float
    role: float


# =============================================================================
# Block Breakdown
# =============================================================================


@dataclass(frozen=True)
class BlockBreakdown:
    """
    Per-block breakdown for UI display.

    Shows how each block contributes to the parlay's fragility.
    """
    block_id: UUID
    label: str  # Short display name (e.g., "Player X Over 100 yards")
    bet_type: str
    base_fragility: float
    context_deltas: ContextDeltas
    context_delta_total: float
    effective_fragility: float
    notes: tuple[str, ...]  # Factual notes (e.g., "Weather +4", "Role instability +3")


# =============================================================================
# Meter Values
# =============================================================================


@dataclass(frozen=True)
class MeterValues:
    """Fragility meter values for UI display."""
    final_fragility: float
    raw_fragility: float
    leg_penalty: float
    correlation_penalty: float
    correlation_multiplier: float


# =============================================================================
# Inductor Display
# =============================================================================


@dataclass(frozen=True)
class InductorDisplay:
    """Inductor state for UI display."""
    level: str  # stable, loaded, tense, critical
    explanation: str


# =============================================================================
# DNA Display
# =============================================================================


@dataclass(frozen=True)
class DNADisplay:
    """DNA enforcement info for UI display."""
    violations: tuple[str, ...]
    base_stake_cap: Optional[float]
    recommended_stake: Optional[float]


# =============================================================================
# Correlation Display
# =============================================================================


@dataclass(frozen=True)
class CorrelationDisplay:
    """Correlation pair for UI display."""
    a: UUID
    b: UUID
    type: str
    penalty: float


# =============================================================================
# Builder View (Main Contract)
# =============================================================================


@dataclass(frozen=True)
class BuilderView:
    """
    UI-focused response model for parlay builder.

    Contains everything the UI needs to display the builder state:
    - Parlay identification
    - Risk inductor (4-level)
    - Fragility meter values
    - DNA enforcement info
    - Per-block breakdowns with context deltas
    - Correlations between blocks
    - Optional alerts (for change notifications)
    - Optional suggestions

    Deterministic for same inputs.
    """
    parlay_id: UUID
    inductor: InductorDisplay
    meter: MeterValues
    dna: DNADisplay
    blocks: tuple[BlockBreakdown, ...]
    correlations: tuple[CorrelationDisplay, ...]
    alerts: Optional[tuple[Alert, ...]] = None
    suggestions: Optional[tuple[SuggestedBlock, ...]] = None


# =============================================================================
# Note Generation
# =============================================================================


def _generate_block_notes(
    block: BetBlock,
    correlations: Sequence[Correlation],
) -> tuple[str, ...]:
    """
    Generate factual notes for a block.

    Notes include:
    - Context impacts (e.g., "Weather +4")
    - Correlation involvement (e.g., "Same player correlation with block X")
    """
    notes: List[str] = []

    # Context notes
    mods = block.context_modifiers

    if mods.weather.applied and mods.weather.delta > 0:
        notes.append(f"Weather +{mods.weather.delta:.1f}")

    if mods.injury.applied and mods.injury.delta > 0:
        notes.append(f"Injury +{mods.injury.delta:.1f}")

    if mods.trade.applied and mods.trade.delta > 0:
        notes.append(f"Trade +{mods.trade.delta:.1f}")

    if mods.role.applied and mods.role.delta > 0:
        notes.append(f"Role instability +{mods.role.delta:.1f}")

    # Correlation notes
    for corr in correlations:
        if corr.block_a == block.block_id or corr.block_b == block.block_id:
            # Format correlation type for display
            corr_type = corr.type.replace("_", " ").title()
            notes.append(f"{corr_type} correlation (+{corr.penalty:.1f} penalty)")

    return tuple(notes)


def _generate_block_label(block: BetBlock) -> str:
    """Generate a short display label for a block."""
    # Use selection as the label, truncated if too long
    label = block.selection
    if len(label) > 50:
        label = label[:47] + "..."
    return label


# =============================================================================
# Block Breakdown Generation
# =============================================================================


def _create_block_breakdown(
    block: BetBlock,
    correlations: Sequence[Correlation],
) -> BlockBreakdown:
    """Create a block breakdown from a BetBlock."""
    mods = block.context_modifiers

    context_deltas = ContextDeltas(
        weather=mods.weather.delta if mods.weather.applied else 0.0,
        injury=mods.injury.delta if mods.injury.applied else 0.0,
        trade=mods.trade.delta if mods.trade.applied else 0.0,
        role=mods.role.delta if mods.role.applied else 0.0,
    )

    context_delta_total = (
        context_deltas.weather +
        context_deltas.injury +
        context_deltas.trade +
        context_deltas.role
    )

    notes = _generate_block_notes(block, correlations)

    return BlockBreakdown(
        block_id=block.block_id,
        label=_generate_block_label(block),
        bet_type=block.bet_type.value,
        base_fragility=block.base_fragility,
        context_deltas=context_deltas,
        context_delta_total=context_delta_total,
        effective_fragility=block.effective_fragility,
        notes=notes,
    )


# =============================================================================
# Derive Builder View
# =============================================================================


def derive_builder_view(
    response: EvaluationResponse,
    blocks: Sequence[BetBlock],
    prev_response: Optional[EvaluationResponse] = None,
    context_applied: Optional[dict] = None,
) -> BuilderView:
    """
    Derive a BuilderView from an EvaluationResponse and blocks.

    Args:
        response: The evaluation response
        blocks: The original blocks with context modifiers
        prev_response: Optional previous response for alert comparison
        context_applied: Optional dict with context signal impact info

    Returns:
        BuilderView with all UI-needed data
    """
    # Create block breakdowns
    block_breakdowns = tuple(
        _create_block_breakdown(block, response.correlations)
        for block in blocks
    )

    # Create correlation displays
    correlation_displays = tuple(
        CorrelationDisplay(
            a=corr.block_a,
            b=corr.block_b,
            type=corr.type,
            penalty=corr.penalty,
        )
        for corr in response.correlations
    )

    # Compute alerts if we have previous response
    alerts: Optional[tuple[Alert, ...]] = None
    if prev_response is not None or context_applied is not None:
        alert_list = compute_alerts(prev_response, response, context_applied)
        if alert_list:
            alerts = tuple(alert_list)

    return BuilderView(
        parlay_id=response.parlay_id,
        inductor=InductorDisplay(
            level=response.inductor.level.value,
            explanation=response.inductor.explanation,
        ),
        meter=MeterValues(
            final_fragility=response.metrics.final_fragility,
            raw_fragility=response.metrics.raw_fragility,
            leg_penalty=response.metrics.leg_penalty,
            correlation_penalty=response.metrics.correlation_penalty,
            correlation_multiplier=response.metrics.correlation_multiplier,
        ),
        dna=DNADisplay(
            violations=response.dna.violations,
            base_stake_cap=response.dna.base_stake_cap,
            recommended_stake=response.dna.recommended_stake,
        ),
        blocks=block_breakdowns,
        correlations=correlation_displays,
        alerts=alerts,
        suggestions=response.suggestions,
    )


# =============================================================================
# Convenience Function
# =============================================================================


def build_view_from_blocks(
    blocks: Sequence[BetBlock],
    dna_profile=None,
    bankroll: Optional[float] = None,
    candidates: Optional[Sequence[BetBlock]] = None,
    max_suggestions: int = 5,
    prev_response: Optional[EvaluationResponse] = None,
    context_applied: Optional[dict] = None,
) -> BuilderView:
    """
    Convenience function to build a complete BuilderView from blocks.

    Runs evaluation and derives the builder view.

    Args:
        blocks: The bet blocks to evaluate
        dna_profile: Optional DNA profile
        bankroll: Optional bankroll
        candidates: Optional candidate blocks for suggestions
        max_suggestions: Max suggestions to return
        prev_response: Optional previous response for alerts
        context_applied: Optional context signal impact info

    Returns:
        Complete BuilderView
    """
    from core.evaluation import evaluate_parlay

    response = evaluate_parlay(
        blocks=blocks,
        dna_profile=dna_profile,
        bankroll=bankroll,
        candidates=candidates,
        max_suggestions=max_suggestions,
    )

    return derive_builder_view(
        response=response,
        blocks=blocks,
        prev_response=prev_response,
        context_applied=context_applied,
    )
