"""
Frontend-facing contract schemas for the separation work.

These models codify the first stable API boundary the dedicated frontend can
build against while the backend continues to evolve additively.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class FrontendCanonicalLegSchema(BaseModel):
    """Canonical leg shape accepted by the frontend evaluation contract."""

    entity: str = Field(..., description="Team or player name")
    market: str = Field(..., description="Market type")
    value: Optional[str] = Field(default=None, description="Line value or selection value")
    raw: str = Field(..., description="Original text entered or reviewed by the user")


class WebEvaluateRequestSchema(BaseModel):
    """Frozen request shape for the dedicated frontend Evaluate flow."""

    input: str = Field(..., description="Bet text input")
    tier: Optional[str] = Field(default=None, description="Plan tier: GOOD, BETTER, or BEST")
    legs: Optional[List[FrontendCanonicalLegSchema]] = Field(
        default=None,
        description="Structured canonical legs from Builder or OCR review",
    )


class BuilderHandoffSchema(BaseModel):
    """Explicit Airlock-shaped handoff contract for Builder refinement."""

    evaluationId: Optional[str] = None
    inputText: str
    tier: str
    primaryFailure: Optional[Dict[str, Any]] = None
    fastestFix: Optional[Dict[str, Any]] = None
    deltaPreview: Optional[Dict[str, Any]] = None
    signalInfo: Optional[Dict[str, Any]] = None
    protocolContextNote: Optional[str] = None


class WebEvaluateResponseSchema(BaseModel):
    """
    Stable frontend response contract for Evaluate.

    Extra fields are allowed so the backend can keep returning additive data
    without breaking the dedicated frontend.
    """

    model_config = ConfigDict(extra="allow")

    evaluationId: Optional[str] = None
    input: Dict[str, Any] = Field(default_factory=dict)
    evaluation: Dict[str, Any] = Field(default_factory=dict)
    interpretation: Dict[str, Any] = Field(default_factory=dict)
    explain: Dict[str, Any] = Field(default_factory=dict)
    signalInfo: Optional[Dict[str, Any]] = None
    primaryFailure: Optional[Dict[str, Any]] = None
    deltaPreview: Optional[Dict[str, Any]] = None
    builderHandoff: Optional[BuilderHandoffSchema] = None
    evaluatedParlay: Optional[Dict[str, Any]] = None
    nextAction: Optional[Dict[str, Any]] = None
    triggeredProtocols: List[Dict[str, Any]] = Field(default_factory=list)
    dnaScoring: Optional[Dict[str, Any]] = None
    proofSummary: Optional[Dict[str, Any]] = None
    structure: Optional[Dict[str, Any]] = None


class OcrDetectedLegSchema(BaseModel):
    """Structured OCR review leg returned to the frontend."""

    legId: str
    entity: str
    market: str
    value: Optional[str] = None
    raw: str
    source: Literal["ocr"] = "ocr"
    clarity: Literal["clear", "review", "ambiguous"]
    sport: Optional[str] = None


class OcrReviewResponseSchema(BaseModel):
    """
    Frozen OCR review contract.

    This intentionally stops before evaluation so the frontend can own the
    trust gate UX.
    """

    model_config = ConfigDict(extra="allow")

    requestId: str
    source: Literal["image"] = "image"
    fileName: Optional[str] = None
    rawText: str
    detectedLegs: List[OcrDetectedLegSchema]
    confidence: float = Field(..., ge=0.0, le=1.0)
    requiresReview: bool
