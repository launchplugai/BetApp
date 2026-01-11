# app/routers/leading_light.py
"""
Leading Light API Router.

Exposes the evaluation pipeline via HTTP endpoints.
Feature-flagged via LEADING_LIGHT_ENABLED environment variable.
"""
from __future__ import annotations

import os
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.schemas.leading_light import (
    BetBlockSchema,
    ContextModifiersSchema,
    DNAProfileSchema,
    EvaluationRequestSchema,
    EvaluationResponseSchema,
    CorrelationSchema,
    DNAInfoSchema,
    InductorInfoSchema,
    MetricsInfoSchema,
    RecommendationSchema,
    ServiceDisabledResponseSchema,
    SuggestedBlockSchema,
)

# Import core types
from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextModifier,
    ContextModifiers,
)
from core.dna_enforcement import (
    BehaviorProfile,
    DNAProfile,
    RiskProfile,
)
from core.evaluation import (
    EvaluationResponse,
    evaluate_parlay,
)


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(
    prefix="/leading-light",
    tags=["Leading Light"],
)


# =============================================================================
# Feature Flag
# =============================================================================


def is_leading_light_enabled() -> bool:
    """Check if Leading Light feature is enabled."""
    return os.environ.get("LEADING_LIGHT_ENABLED", "false").lower() == "true"


# =============================================================================
# Conversion Functions
# =============================================================================


def _convert_bet_type(bet_type_str: str) -> BetType:
    """Convert string to BetType enum."""
    mapping = {
        "player_prop": BetType.PLAYER_PROP,
        "spread": BetType.SPREAD,
        "total": BetType.TOTAL,
        "ml": BetType.ML,
        "team_total": BetType.TEAM_TOTAL,
    }
    if bet_type_str.lower() not in mapping:
        raise ValueError(f"Invalid bet_type: {bet_type_str}")
    return mapping[bet_type_str.lower()]


def _convert_context_modifiers(
    modifiers: Optional[ContextModifiersSchema],
) -> ContextModifiers:
    """Convert schema to core ContextModifiers."""
    if modifiers is None:
        # Return default modifiers
        default_mod = ContextModifier(applied=False, delta=0.0, reason=None)
        return ContextModifiers(
            weather=default_mod,
            injury=default_mod,
            trade=default_mod,
            role=default_mod,
        )

    return ContextModifiers(
        weather=ContextModifier(
            applied=modifiers.weather.applied,
            delta=modifiers.weather.delta,
            reason=modifiers.weather.reason,
        ),
        injury=ContextModifier(
            applied=modifiers.injury.applied,
            delta=modifiers.injury.delta,
            reason=modifiers.injury.reason,
        ),
        trade=ContextModifier(
            applied=modifiers.trade.applied,
            delta=modifiers.trade.delta,
            reason=modifiers.trade.reason,
        ),
        role=ContextModifier(
            applied=modifiers.role.applied,
            delta=modifiers.role.delta,
            reason=modifiers.role.reason,
        ),
    )


def _convert_block(block_schema: BetBlockSchema) -> BetBlock:
    """Convert schema to core BetBlock."""
    modifiers = _convert_context_modifiers(block_schema.context_modifiers)
    base_fragility = block_schema.base_fragility
    effective_fragility = base_fragility + modifiers.total_delta()

    return BetBlock(
        block_id=block_schema.block_id or uuid4(),
        sport=block_schema.sport,
        game_id=block_schema.game_id,
        bet_type=_convert_bet_type(block_schema.bet_type),
        selection=block_schema.selection,
        base_fragility=base_fragility,
        context_modifiers=modifiers,
        correlation_tags=tuple(block_schema.correlation_tags),
        effective_fragility=effective_fragility,
        player_id=block_schema.player_id,
        team_id=block_schema.team_id,
    )


def _convert_dna_profile(profile_schema: Optional[DNAProfileSchema]) -> Optional[DNAProfile]:
    """Convert schema to core DNAProfile."""
    if profile_schema is None:
        return None

    return DNAProfile(
        risk=RiskProfile(
            tolerance=profile_schema.risk.tolerance,
            max_parlay_legs=profile_schema.risk.max_parlay_legs,
            max_stake_pct=profile_schema.risk.max_stake_pct,
            avoid_live_bets=profile_schema.risk.avoid_live_bets,
            avoid_props=profile_schema.risk.avoid_props,
        ),
        behavior=BehaviorProfile(
            discipline=profile_schema.behavior.discipline,
        ),
    )


def _convert_response(response: EvaluationResponse) -> EvaluationResponseSchema:
    """Convert core EvaluationResponse to schema."""
    # Convert correlations
    # Core Correlation uses: block_a, block_b, type
    # Schema uses: block_a_id, block_b_id, correlation_type
    correlations = [
        CorrelationSchema(
            block_a_id=c.block_a,
            block_b_id=c.block_b,
            correlation_type=c.type,
            penalty=c.penalty,
        )
        for c in response.correlations
    ]

    # Convert suggestions if present
    suggestions = None
    if response.suggestions is not None:
        suggestions = [
            SuggestedBlockSchema(
                candidate_block_id=s.candidate_block_id,
                delta_fragility=s.delta_fragility,
                added_correlation=s.added_correlation,
                dna_compatible=s.dna_compatible,
                label=s.label.value,
                reason=s.reason,
            )
            for s in response.suggestions
        ]

    return EvaluationResponseSchema(
        parlay_id=response.parlay_id,
        inductor=InductorInfoSchema(
            level=response.inductor.level.value,
            explanation=response.inductor.explanation,
        ),
        metrics=MetricsInfoSchema(
            raw_fragility=response.metrics.raw_fragility,
            final_fragility=response.metrics.final_fragility,
            leg_penalty=response.metrics.leg_penalty,
            correlation_penalty=response.metrics.correlation_penalty,
            correlation_multiplier=response.metrics.correlation_multiplier,
        ),
        correlations=correlations,
        dna=DNAInfoSchema(
            violations=list(response.dna.violations),
            base_stake_cap=response.dna.base_stake_cap,
            recommended_stake=response.dna.recommended_stake,
            max_legs=response.dna.max_legs,
            fragility_tolerance=response.dna.fragility_tolerance,
        ),
        recommendation=RecommendationSchema(
            action=response.recommendation.action.value,
            reason=response.recommendation.reason,
        ),
        suggestions=suggestions,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/evaluate",
    response_model=EvaluationResponseSchema,
    responses={
        200: {"description": "Successful evaluation"},
        400: {"description": "Invalid request"},
        503: {
            "description": "Service disabled",
            "model": ServiceDisabledResponseSchema,
        },
    },
    summary="Evaluate a parlay",
    description="Evaluate a parlay and return risk metrics, recommendations, and suggestions.",
)
async def evaluate(request: EvaluationRequestSchema) -> EvaluationResponseSchema:
    """
    Evaluate a parlay using the Leading Light engine.

    Returns risk metrics, DNA enforcement, recommendations, and optional suggestions.
    """
    # Check feature flag
    if not is_leading_light_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Leading Light disabled",
                "detail": "The Leading Light feature is currently disabled. Set LEADING_LIGHT_ENABLED=true to enable.",
                "code": "SERVICE_DISABLED",
            },
        )

    try:
        # Convert request to core types
        blocks = [_convert_block(b) for b in request.blocks]
        dna_profile = _convert_dna_profile(request.dna_profile)
        candidates = None
        if request.candidates:
            candidates = [_convert_block(c) for c in request.candidates]

        # Evaluate parlay
        response = evaluate_parlay(
            blocks=blocks,
            dna_profile=dna_profile,
            bankroll=request.bankroll,
            candidates=candidates,
            max_suggestions=request.max_suggestions,
        )

        # Convert response to schema
        return _convert_response(response)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid request",
                "detail": str(e),
                "code": "VALIDATION_ERROR",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal error",
                "detail": str(e),
                "code": "INTERNAL_ERROR",
            },
        )


@router.get(
    "/status",
    summary="Check Leading Light status",
    description="Check if the Leading Light feature is enabled.",
)
async def status_check():
    """Check if Leading Light is enabled."""
    return {
        "enabled": is_leading_light_enabled(),
        "service": "leading-light",
    }
