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
from pydantic import BaseModel, Field, field_validator

from app.schemas.leading_light import (
    BetBlockSchema,
    ContextModifiersSchema,
    ContextSignalInputSchema,
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
from core.context_adapters import adapt_and_apply_signals

# Import tiering
from app.tiering import (
    Plan,
    parse_plan,
    validate_context_signals,
    apply_tier_to_response,
    get_max_suggestions_for_plan,
    is_demo_allowed,
    ContextSignalNotAllowedError,
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
    Response is filtered based on plan tier (good, better, best).
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

    # Parse plan from request
    plan = parse_plan(request.plan)

    try:
        # Validate context signals against plan
        if request.context_signals:
            raw_signals = [
                signal.model_dump(exclude_none=True)
                for signal in request.context_signals
            ]
            validate_context_signals(raw_signals, plan)
        else:
            raw_signals = []

        # Convert request to core types
        blocks = [_convert_block(b) for b in request.blocks]
        dna_profile = _convert_dna_profile(request.dna_profile)
        candidates = None
        if request.candidates:
            candidates = [_convert_block(c) for c in request.candidates]

        # Apply context signals if provided
        if raw_signals:
            blocks = list(adapt_and_apply_signals(blocks, raw_signals))

        # Determine max suggestions based on plan
        max_suggestions = min(
            request.max_suggestions,
            get_max_suggestions_for_plan(plan),
        )

        # Evaluate parlay
        response = evaluate_parlay(
            blocks=blocks,
            dna_profile=dna_profile,
            bankroll=request.bankroll,
            candidates=candidates,
            max_suggestions=max_suggestions,
        )

        # Apply tier filtering to response
        filtered_response = apply_tier_to_response(plan, response)

        # Convert response to schema
        return _convert_response(filtered_response)

    except ContextSignalNotAllowedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Context signal not allowed",
                "detail": str(e),
                "code": "SIGNAL_NOT_ALLOWED",
            },
        )
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


# =============================================================================
# Demo Endpoints
# =============================================================================


def _is_demo_override_enabled() -> bool:
    """Check if demo override environment variable is set."""
    return os.environ.get("LEADING_LIGHT_DEMO_OVERRIDE", "false").lower() == "true"


def _check_demo_access(plan: Optional[str]) -> None:
    """
    Check if demo access is allowed for the given plan.

    Raises HTTPException if not allowed.

    Demo access requires:
    - plan=BEST, OR
    - LEADING_LIGHT_DEMO_OVERRIDE=true env var
    """
    parsed_plan = parse_plan(plan)
    env_override = _is_demo_override_enabled()

    if not is_demo_allowed(parsed_plan, env_override):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Demo access denied",
                "detail": f"Demo endpoints require plan='best' or LEADING_LIGHT_DEMO_OVERRIDE=true. Current plan: '{parsed_plan.value}'",
                "code": "DEMO_ACCESS_DENIED",
            },
        )


@router.get(
    "/demo",
    summary="List available demo cases",
    description="List all available demo scenarios for testing. Requires BEST plan or demo override.",
)
async def list_demos(plan: Optional[str] = None):
    """List all available demo cases."""
    _check_demo_access(plan)

    from app.demo.leading_light_demo_cases import list_demo_cases
    return {
        "cases": list_demo_cases(),
    }


@router.get(
    "/demo/{case_name}",
    summary="Get demo case request JSON",
    description="Get the request JSON payload for a specific demo case. Requires BEST plan or demo override.",
)
async def get_demo_request(case_name: str, plan: Optional[str] = None):
    """Get the request JSON for a demo case."""
    _check_demo_access(plan)

    from app.demo.leading_light_demo_cases import get_demo_case

    case = get_demo_case(case_name)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Demo case not found",
                "detail": f"No demo case named '{case_name}'. Use GET /leading-light/demo to list available cases.",
                "code": "NOT_FOUND",
            },
        )

    return {
        "name": case.name,
        "description": case.description,
        "expected_inductor": case.expected_inductor,
        "request": case.to_request_json(),
    }


@router.post(
    "/demo/{case_name}",
    response_model=EvaluationResponseSchema,
    responses={
        200: {"description": "Successful evaluation"},
        403: {"description": "Demo access denied"},
        404: {"description": "Demo case not found"},
        503: {"description": "Service disabled"},
    },
    summary="Run demo case",
    description="Execute a demo case and return the evaluation response. Requires BEST plan or demo override.",
)
async def run_demo(case_name: str, plan: Optional[str] = None) -> EvaluationResponseSchema:
    """
    Run a demo case and return the evaluation response.

    Executes the specified demo case through the full evaluation pipeline.
    Requires BEST plan or LEADING_LIGHT_DEMO_OVERRIDE=true.
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

    # Check demo access
    _check_demo_access(plan)

    from app.demo.leading_light_demo_cases import get_demo_case

    case = get_demo_case(case_name)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Demo case not found",
                "detail": f"No demo case named '{case_name}'. Use GET /leading-light/demo to list available cases.",
                "code": "NOT_FOUND",
            },
        )

    try:
        # Convert blocks
        blocks = []
        for b in case.blocks:
            block_schema = BetBlockSchema(**b)
            blocks.append(_convert_block(block_schema))

        # Convert DNA profile if present
        dna_profile = None
        if case.dna_profile:
            profile_schema = DNAProfileSchema(**case.dna_profile)
            dna_profile = _convert_dna_profile(profile_schema)

        # Convert candidates if present
        candidates = None
        if case.candidates:
            candidates = []
            for c in case.candidates:
                cand_schema = BetBlockSchema(**c)
                candidates.append(_convert_block(cand_schema))

        # Apply context signals if present
        if case.context_signals:
            blocks = list(adapt_and_apply_signals(blocks, case.context_signals))

        # Evaluate
        response = evaluate_parlay(
            blocks=blocks,
            dna_profile=dna_profile,
            bankroll=case.bankroll,
            candidates=candidates,
            max_suggestions=5,
        )

        return _convert_response(response)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Demo execution failed",
                "detail": str(e),
                "code": "INTERNAL_ERROR",
            },
        )


# =============================================================================
# Simple Text-Based Evaluate Endpoint (Entry Point)
# =============================================================================


class TextEvaluateRequest(BaseModel):
    """Request schema for text-based bet evaluation."""
    bet_text: str = Field(..., min_length=1, description="Bet description as plain text")
    plan: Optional[str] = Field(default="free", description="Subscription plan tier")
    session_id: Optional[str] = Field(default=None, description="Optional session identifier")

    @field_validator("bet_text")
    @classmethod
    def validate_bet_text(cls, v: str) -> str:
        """Validate bet_text is not empty or whitespace."""
        if not v or not v.strip():
            raise ValueError("bet_text cannot be empty or whitespace")
        return v.strip()


@router.post(
    "/evaluate/text",
    responses={
        200: {"description": "Evaluation with plain-English explanation"},
        400: {"description": "Invalid request"},
    },
    summary="Evaluate bet from text (simple entry point)",
    description="Accept a bet as plain text and return evaluation with plain-English explanation.",
)
async def evaluate_from_text(request: TextEvaluateRequest):
    """
    Evaluate a bet from plain text.

    Simple entry point that accepts bet text and returns deterministic evaluation
    with plain-English explanation wrapper.
    """
    # Simple complexity heuristics (deterministic)
    text_lower = request.bet_text.lower()
    leg_count = 0
    
    # Count potential legs
    for indicator in ['+', 'and', ',', 'parlay']:
        if indicator in text_lower:
            leg_count += text_lower.count(indicator)
    
    # Estimate legs (minimum 1)
    estimated_legs = max(1, min(leg_count, 5))
    
    # Detect risk indicators
    has_weather = any(word in text_lower for word in ['snow', 'wind', 'rain', 'weather'])
    has_injury = any(word in text_lower for word in ['injury', 'out', 'questionable', 'doubtful'])
    has_props = any(word in text_lower for word in ['yards', 'points', 'rebounds', 'assists', 'touchdowns'])
    
    # Calculate simple fragility (deterministic)
    base_fragility = estimated_legs * 0.15
    if has_props:
        base_fragility += 0.10
    if has_weather:
        base_fragility += 0.08
    if has_injury:
        base_fragility += 0.08
    
    fragility = min(base_fragility, 0.95)
    
    # Determine risk level
    if fragility < 0.25:
        risk_level = "STABLE"
        recommended_step = "This structure is within tolerance"
    elif fragility < 0.45:
        risk_level = "LOADED"
        recommended_step = "Monitor closely; consider reducing legs"
    elif fragility < 0.65:
        risk_level = "TENSE"
        recommended_step = "Simplify the bet; multiple risk factors present"
    else:
        risk_level = "CRITICAL"
        recommended_step = "Simplify the bet; high fragility detected"
    
    # Build plain-English summary
    summary = [
        f"Detected approximately {estimated_legs} leg(s) in this bet",
        f"Estimated fragility: {fragility:.2f} ({risk_level})",
    ]
    
    if has_props:
        summary.append("Player props detected - adds outcome variance")
    if has_weather:
        summary.append("Weather context mentioned - may affect performance")
    if has_injury:
        summary.append("Injury context mentioned - affects player availability")
    
    # Build response
    return {
        "input": {
            "bet_text": request.bet_text,
            "plan": request.plan,
            "session_id": request.session_id,
        },
        "evaluation": {
            "risk_level": risk_level,
            "fragility": round(fragility, 3),
            "estimated_legs": estimated_legs,
            "indicators": {
                "has_props": has_props,
                "has_weather": has_weather,
                "has_injury": has_injury,
            },
        },
        "explain": {
            "summary": summary,
            "alerts": [],
            "recommended_next_step": recommended_step,
        },
    }
