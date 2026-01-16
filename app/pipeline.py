# app/pipeline.py
"""
Pipeline Facade - Single entry point for all evaluation requests.

This is the ONLY place where core evaluation is called.
All routes MUST go through this facade:

    Airlock (validation) → Pipeline (evaluation) → Route (HTTP response)

The pipeline:
1. Parses text input into BetBlocks
2. Calls the canonical evaluate_parlay()
3. Wraps response with plain-English explanations
4. Applies tier-based filtering

Routes should NOT:
- Import core.evaluation directly
- Reimplement parsing/summary logic
- Call evaluate_parlay() themselves
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from app.airlock import NormalizedInput, Tier

# Core evaluation - the ONLY direct import of core.evaluation in app/
from core.evaluation import EvaluationResponse, evaluate_parlay
from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextModifier,
    ContextModifiers,
)


# =============================================================================
# Pipeline Response
# =============================================================================


@dataclass(frozen=True)
class PipelineResponse:
    """
    Unified response from the evaluation pipeline.

    Contains:
    - Raw evaluation response from core engine
    - Plain-English interpretation
    - Tier-filtered explain content
    - Metadata for logging
    """
    # Core evaluation result
    evaluation: EvaluationResponse

    # Plain-English interpretation (always included)
    interpretation: dict

    # Explain content (tier-filtered)
    explain: dict

    # Metadata
    leg_count: int
    tier: str


# =============================================================================
# Text Parsing (moved from leading_light.py)
# =============================================================================


def _parse_bet_text(bet_text: str) -> list[BetBlock]:
    """
    Parse bet_text into BetBlock objects.

    Minimal parser that creates simple bet blocks from text.
    Does NOT implement scoring logic - just format conversion.
    """
    # Count legs based on delimiters
    leg_count = 1
    for delimiter in ['+', ',', 'and ', ' parlay']:
        if delimiter in bet_text.lower():
            leg_count = bet_text.lower().count(delimiter) + 1
            break

    # Cap at reasonable limit
    leg_count = min(leg_count, 5)

    # Detect bet types from text
    text_lower = bet_text.lower()
    is_prop = any(word in text_lower for word in ['yards', 'points', 'rebounds', 'assists', 'touchdowns', 'td'])
    is_total = any(word in text_lower for word in ['over', 'under', 'o/', 'u/'])
    is_spread = any(word in text_lower for word in ['-', '+']) and not is_total

    # Determine bet type
    if is_prop:
        bet_type = BetType.PLAYER_PROP
        base_fragility = 0.20  # Props are inherently more fragile
    elif is_total:
        bet_type = BetType.TOTAL
        base_fragility = 0.12
    elif is_spread:
        bet_type = BetType.SPREAD
        base_fragility = 0.10
    else:
        bet_type = BetType.ML
        base_fragility = 0.08

    # Create bet blocks (one per leg)
    blocks = []
    default_mod = ContextModifier(applied=False, delta=0.0, reason=None)
    modifiers = ContextModifiers(
        weather=default_mod,
        injury=default_mod,
        trade=default_mod,
        role=default_mod,
    )

    for i in range(leg_count):
        block = BetBlock(
            block_id=uuid4(),
            sport="generic",
            game_id=f"game_{i+1}",
            bet_type=bet_type,
            selection=f"Leg {i+1}",
            base_fragility=base_fragility,
            context_modifiers=modifiers,
            correlation_tags=(),
            effective_fragility=base_fragility,
            player_id=None,
            team_id=None,
        )
        blocks.append(block)

    return blocks


# =============================================================================
# Summary Generation (moved from leading_light.py)
# =============================================================================


def _generate_summary(response: EvaluationResponse, leg_count: int) -> list[str]:
    """Generate plain-English summary bullets from evaluation response."""
    summary = [
        f"Detected {leg_count} leg(s) in this bet",
        f"Risk level: {response.inductor.level.value.upper()}",
        f"Final fragility: {response.metrics.final_fragility:.2f}",
    ]

    if response.metrics.correlation_penalty > 0:
        summary.append(f"Correlation penalty applied: +{response.metrics.correlation_penalty:.2f}")

    if len(response.correlations) > 0:
        summary.append(f"Found {len(response.correlations)} correlation(s) between legs")

    return summary


def _generate_alerts(response: EvaluationResponse) -> list[str]:
    """Generate alerts from evaluation response."""
    alerts = []

    # Check for DNA violations
    if response.dna.violations:
        for violation in response.dna.violations:
            alerts.append(violation)

    # Check for high correlation
    if response.metrics.correlation_multiplier >= 1.5:
        alerts.append("High correlation detected between selections")

    # Check for critical risk
    if response.inductor.level.value == "critical":
        alerts.append("Critical risk level - structure exceeds safe thresholds")

    return alerts


def _interpret_fragility(final_fragility: float) -> dict:
    """
    Generate user-friendly interpretation of fragility score.

    Maps 0-100 scale to buckets with plain-English meaning and actionable advice.
    Does NOT modify engine metrics - interpretation layer only.
    """
    # Clamp for display (engine can produce values outside 0-100)
    display_value = max(0.0, min(100.0, final_fragility))

    # Determine bucket
    if final_fragility <= 15:
        bucket = "low"
        meaning = "Few dependencies; most paths lead to success."
        what_to_do = "Structure is solid; proceed with confidence."
    elif final_fragility <= 35:
        bucket = "medium"
        meaning = "Moderate complexity; several things must align."
        what_to_do = "Review each leg independently before committing."
    elif final_fragility <= 60:
        bucket = "high"
        meaning = "Many things must go right; one miss breaks the ticket."
        what_to_do = "Reduce legs or remove correlated/prop legs to lower failure points."
    else:  # > 60
        bucket = "critical"
        meaning = "Extreme fragility; compounding failure paths."
        what_to_do = "Simplify significantly or avoid this structure entirely."

    return {
        "scale": "0-100",
        "value": final_fragility,
        "display_value": display_value,
        "bucket": bucket,
        "meaning": meaning,
        "what_to_do": what_to_do,
    }


# =============================================================================
# Tier Filtering (moved from leading_light.py)
# =============================================================================


def _apply_tier_filtering(tier: Tier, explain: dict) -> dict:
    """
    Apply tier-based filtering to explain content.

    Tier rules:
    - GOOD: Empty explain (interpretation only)
    - BETTER: summary only
    - BEST: summary + alerts + recommended_next_step
    """
    if tier == Tier.GOOD:
        return {}
    elif tier == Tier.BETTER:
        return {"summary": explain.get("summary", [])}
    else:  # BEST
        return explain


# =============================================================================
# Main Pipeline Function
# =============================================================================


def run_evaluation(normalized: NormalizedInput) -> PipelineResponse:
    """
    Run the canonical evaluation pipeline.

    This is the ONLY entry point for evaluation. All routes call this.

    Args:
        normalized: Validated input from Airlock

    Returns:
        PipelineResponse with evaluation, interpretation, and explain

    Flow:
        1. Parse text → BetBlocks
        2. Call evaluate_parlay() (the canonical core function)
        3. Generate plain-English interpretation
        4. Apply tier filtering to explain
        5. Return unified response
    """
    # Step 1: Parse text into BetBlocks
    blocks = _parse_bet_text(normalized.input_text)
    leg_count = len(blocks)

    # Step 2: Call canonical evaluation engine
    evaluation = evaluate_parlay(
        blocks=blocks,
        dna_profile=None,
        bankroll=None,
        candidates=None,
        max_suggestions=0,
    )

    # Step 3: Generate plain-English interpretation
    interpretation = {
        "fragility": _interpret_fragility(evaluation.metrics.final_fragility),
    }

    # Step 4: Build full explain wrapper
    explain_full = {
        "summary": _generate_summary(evaluation, leg_count),
        "alerts": _generate_alerts(evaluation),
        "recommended_next_step": evaluation.recommendation.reason,
    }

    # Step 5: Apply tier filtering
    explain_filtered = _apply_tier_filtering(normalized.tier, explain_full)

    return PipelineResponse(
        evaluation=evaluation,
        interpretation=interpretation,
        explain=explain_filtered,
        leg_count=leg_count,
        tier=normalized.tier.value,
    )
