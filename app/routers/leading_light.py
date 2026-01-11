# app/routers/leading_light.py
"""
Leading Light API Router.

Exposes the evaluation pipeline via HTTP endpoints.
Feature-flagged via LEADING_LIGHT_ENABLED environment variable.
"""
from __future__ import annotations

import base64
import os
import time
from collections import defaultdict
from typing import List, Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
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
# Image Upload Guardrails
# =============================================================================

# Max file size: 5MB
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024

# Rate limiting: in-memory sliding window
# Format: {ip_address: [(timestamp1, timestamp2, ...)]}
_image_upload_requests: dict[str, list[float]] = defaultdict(list)
IMAGE_RATE_LIMIT = 10  # requests
IMAGE_RATE_WINDOW = 600  # seconds (10 minutes)


def _check_rate_limit(client_ip: str) -> None:
    """
    Check if client IP has exceeded rate limit for image uploads.

    Raises:
        HTTPException: If rate limit exceeded
    """
    now = time.time()

    # Get request timestamps for this IP
    timestamps = _image_upload_requests[client_ip]

    # Remove timestamps outside the window
    timestamps[:] = [ts for ts in timestamps if now - ts < IMAGE_RATE_WINDOW]

    # Check if limit exceeded
    if len(timestamps) >= IMAGE_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limited",
                "detail": "Too many image uploads. Try again later.",
                "code": "RATE_LIMITED",
            },
        )

    # Add current request
    timestamps.append(now)


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

@router.post(
    "/evaluate/text",
    responses={
        200: {"description": "Evaluation with plain-English explanation"},
        400: {"description": "Invalid request"},
        503: {"description": "Service disabled"},
    },
    summary="Evaluate bet from text (simple entry point)",
    description="Accept a bet as plain text and return evaluation with plain-English explanation.",
)
async def evaluate_from_text(request: TextEvaluateRequest):
    """
    Evaluate a bet from plain text using the canonical evaluation engine.

    Parses bet_text into BetBlock(s), calls evaluate_parlay, and wraps
    the response with plain-English explanations.
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
        # Parse bet_text into BetBlock(s)
        blocks = _parse_bet_text(request.bet_text)

        # Call the canonical evaluation engine
        response = evaluate_parlay(
            blocks=blocks,
            dna_profile=None,
            bankroll=None,
            candidates=None,
            max_suggestions=0,
        )

        # Build plain-English explain wrapper
        summary = _generate_summary(response, len(blocks))
        alerts = _generate_alerts(response)
        recommended_step = response.recommendation.reason

        # Build fragility interpretation
        fragility_interpretation = _interpret_fragility(response.metrics.final_fragility)

        # Build response
        return {
            "input": {
                "bet_text": request.bet_text,
                "plan": request.plan,
                "session_id": request.session_id,
            },
            "evaluation": {
                "parlay_id": str(response.parlay_id),
                "inductor": {
                    "level": response.inductor.level.value,
                    "explanation": response.inductor.explanation,
                },
                "metrics": {
                    "raw_fragility": response.metrics.raw_fragility,
                    "final_fragility": response.metrics.final_fragility,
                    "leg_penalty": response.metrics.leg_penalty,
                    "correlation_penalty": response.metrics.correlation_penalty,
                    "correlation_multiplier": response.metrics.correlation_multiplier,
                },
                "correlations": [
                    {
                        "block_a": str(c.block_a),
                        "block_b": str(c.block_b),
                        "type": c.type,
                        "penalty": c.penalty,
                    }
                    for c in response.correlations
                ],
                "recommendation": {
                    "action": response.recommendation.action.value,
                    "reason": response.recommendation.reason,
                },
            },
            "interpretation": {
                "fragility": fragility_interpretation,
            },
            "explain": {
                "summary": summary,
                "alerts": alerts,
                "recommended_next_step": recommended_step,
            },
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid bet text",
                "detail": str(e),
                "code": "PARSE_ERROR",
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


# =============================================================================
# Image Vision Parsing Helper
# =============================================================================


async def _parse_bet_slip_image(image_bytes: bytes) -> str:
    """Parse bet slip image to extract bet text using OpenAI Vision API."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Image parsing not configured",
                "detail": "OPENAI_API_KEY environment variable is not set",
                "code": "IMAGE_PARSE_NOT_CONFIGURED",
            },
        )

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract the bet information from this betting slip image. "
                            "Return ONLY the bet legs in plain text format, one per line. "
                            "Format each leg as: Team/Player + Bet Type + Line. "
                            "If this is not a betting slip, respond with: NOT_A_BET_SLIP"
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}",
                        },
                    },
                ],
            }
        ],
        "max_tokens": 300,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )

    if response.status_code != 200:
        error_detail = response.text
        try:
            error_json = response.json()
            error_detail = error_json.get("error", {}).get("message", response.text)
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Vision API error",
                "detail": error_detail,
                "code": "VISION_API_ERROR",
            },
        )

    try:
        result = response.json()
        extracted_text = result["choices"][0]["message"]["content"].strip()

        if "NOT_A_BET_SLIP" in extracted_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Not a bet slip",
                    "detail": "The uploaded image does not appear to be a betting slip",
                    "code": "NOT_A_BET_SLIP",
                },
            )

        return extracted_text

    except (KeyError, IndexError) as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Failed to parse vision response",
                "detail": str(e),
                "code": "VISION_PARSE_ERROR",
            },
        )


@router.post("/evaluate/image")
async def evaluate_from_image(
    request: Request,
    image: UploadFile = File(...),
    plan: str = Form("free"),
    session_id: Optional[str] = Form(None),
):
    """Evaluate bet slip from uploaded image."""
    if not is_leading_light_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "enabled": False,
                "message": "Leading Light feature is currently disabled",
                "code": "FEATURE_DISABLED",
            },
        )

    # Guardrail 1: Check rate limit
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    # Guardrail 2: Validate content type
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid file type",
                "detail": "Only images are supported",
                "code": "INVALID_FILE_TYPE",
            },
        )

    try:
        # Read image bytes
        image_bytes = await image.read()

        # Guardrail 3: Check file size
        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": "File too large",
                    "detail": f"Maximum file size is {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB",
                    "code": "FILE_TOO_LARGE",
                },
            )
        bet_text = await _parse_bet_slip_image(image_bytes)
        blocks = _parse_bet_text(bet_text)

        response = evaluate_parlay(
            blocks=blocks,
            dna_profile=None,
            bankroll=None,
            candidates=None,
            max_suggestions=0,
        )

        summary = _generate_summary(response, len(blocks))
        alerts = _generate_alerts(response)
        recommended_step = response.recommendation.reason
        fragility_interpretation = _interpret_fragility(response.metrics.final_fragility)

        return {
            "input": {
                "image_filename": image.filename,
                "extracted_bet_text": bet_text,
                "plan": plan,
                "session_id": session_id,
            },
            "evaluation": {
                "parlay_id": str(response.parlay_id),
                "inductor": {
                    "level": response.inductor.level.value,
                    "explanation": response.inductor.explanation,
                },
                "metrics": {
                    "raw_fragility": response.metrics.raw_fragility,
                    "final_fragility": response.metrics.final_fragility,
                    "leg_penalty": response.metrics.leg_penalty,
                    "correlation_penalty": response.metrics.correlation_penalty,
                    "multiplier": response.metrics.multiplier,
                },
                "correlations": [
                    {
                        "tag": c.tag,
                        "description": c.description,
                        "weight": c.weight,
                    }
                    for c in response.correlations
                ],
                "recommendation": {
                    "action": response.recommendation.action.value,
                    "reason": response.recommendation.reason,
                },
            },
            "interpretation": {
                "fragility": fragility_interpretation,
            },
            "explain": {
                "summary": summary,
                "alerts": alerts,
                "recommended_next_step": recommended_step,
            },
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid bet text extracted from image",
                "detail": str(e),
                "code": "PARSE_ERROR",
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
