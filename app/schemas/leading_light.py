# app/schemas/leading_light.py
"""
Pydantic schemas for Leading Light API.

Handles JSON serialization for EvaluationRequest and EvaluationResponse.
Uses snake_case to match existing API conventions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Request Schemas
# =============================================================================


class ContextModifierSchema(BaseModel):
    """Context modifier for a bet block."""
    applied: bool = False
    delta: float = 0.0
    reason: Optional[str] = None


class ContextModifiersSchema(BaseModel):
    """All context modifiers for a bet block."""
    weather: ContextModifierSchema = Field(default_factory=ContextModifierSchema)
    injury: ContextModifierSchema = Field(default_factory=ContextModifierSchema)
    trade: ContextModifierSchema = Field(default_factory=ContextModifierSchema)
    role: ContextModifierSchema = Field(default_factory=ContextModifierSchema)


class BetBlockSchema(BaseModel):
    """Bet block input schema."""
    block_id: Optional[UUID] = None
    sport: str
    game_id: str
    bet_type: str  # player_prop, spread, total, ml, team_total
    selection: str
    base_fragility: float
    context_modifiers: Optional[ContextModifiersSchema] = None
    correlation_tags: List[str] = Field(default_factory=list)
    player_id: Optional[str] = None
    team_id: Optional[str] = None


class RiskProfileSchema(BaseModel):
    """Risk profile settings."""
    tolerance: float = Field(ge=0, le=100)
    max_parlay_legs: int = Field(ge=1)
    max_stake_pct: float = Field(ge=0.01, le=0.25)
    avoid_live_bets: bool = False
    avoid_props: bool = False


class BehaviorProfileSchema(BaseModel):
    """Behavior profile settings."""
    discipline: float = Field(ge=0.0, le=1.0)


class DNAProfileSchema(BaseModel):
    """DNA profile input schema."""
    risk: RiskProfileSchema
    behavior: BehaviorProfileSchema


class EvaluationRequestSchema(BaseModel):
    """
    Request schema for parlay evaluation.

    Matches CANON REQUEST JSON:
    {
      "blocks": [ ... BetBlock JSON ... ],
      "dna_profile": { ... optional ... },
      "bankroll": 1000.0,
      "candidates": [ ... optional BetBlock JSON ... ]
    }
    """
    blocks: List[BetBlockSchema]
    dna_profile: Optional[DNAProfileSchema] = None
    bankroll: Optional[float] = Field(default=None, ge=0)
    candidates: Optional[List[BetBlockSchema]] = None
    max_suggestions: int = Field(default=5, ge=1, le=20)


# =============================================================================
# Response Schemas
# =============================================================================


class InductorInfoSchema(BaseModel):
    """Risk inductor information."""
    level: str  # stable, loaded, tense, critical
    explanation: str


class MetricsInfoSchema(BaseModel):
    """Parlay metrics."""
    raw_fragility: float
    final_fragility: float
    leg_penalty: float
    correlation_penalty: float
    correlation_multiplier: float


class CorrelationSchema(BaseModel):
    """Correlation between blocks."""
    block_a_id: UUID
    block_b_id: UUID
    correlation_type: str
    penalty: float


class DNAInfoSchema(BaseModel):
    """DNA enforcement information."""
    violations: List[str]
    base_stake_cap: Optional[float] = None
    recommended_stake: Optional[float] = None
    max_legs: Optional[int] = None
    fragility_tolerance: Optional[float] = None


class RecommendationSchema(BaseModel):
    """Recommendation for the parlay."""
    action: str  # accept, reduce, avoid
    reason: str


class SuggestedBlockSchema(BaseModel):
    """Suggested block to add."""
    candidate_block_id: UUID
    delta_fragility: float
    added_correlation: float
    dna_compatible: bool
    label: str  # Lowest added risk, Balanced, Aggressive but within limits
    reason: str


class EvaluationResponseSchema(BaseModel):
    """
    Response schema for parlay evaluation.

    Matches CANON RESPONSE JSON with snake_case fields.
    """
    parlay_id: UUID
    inductor: InductorInfoSchema
    metrics: MetricsInfoSchema
    correlations: List[CorrelationSchema]
    dna: DNAInfoSchema
    recommendation: RecommendationSchema
    suggestions: Optional[List[SuggestedBlockSchema]] = None


# =============================================================================
# Error Response
# =============================================================================


class ErrorResponseSchema(BaseModel):
    """Error response schema."""
    error: str
    detail: Optional[str] = None
    code: str


class ServiceDisabledResponseSchema(BaseModel):
    """Response when service is disabled."""
    error: str = "Leading Light disabled"
    detail: str = "The Leading Light feature is currently disabled. Set LEADING_LIGHT_ENABLED=true to enable."
    code: str = "SERVICE_DISABLED"
