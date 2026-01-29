# sherlock/models.py
"""
Sherlock Mode v1 - Data Models

All models are JSON-serializable Pydantic models.
Each model represents a structured artifact in the Sherlock investigation loop.

Constraints:
- All models MUST be immutable after creation (frozen=True where applicable).
- All models MUST support JSON serialization via model_dump().
- Version fields track iteration provenance.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================


class EvidenceTier(str, Enum):
    """Evidence reliability tiers."""
    TIER_1 = "tier_1"  # Primary sources, peer-reviewed
    TIER_2 = "tier_2"  # Secondary sources, reputable
    TIER_3 = "tier_3"  # Tertiary, aggregated, or lower reliability


class ArgumentSide(str, Enum):
    """Side of an argument node."""
    PRO = "pro"
    CON = "con"


class VerdictLevel(str, Enum):
    """Possible verdict outcomes."""
    TRUE = "true"
    LIKELY_TRUE = "likely_true"
    UNCLEAR = "unclear"
    LIKELY_FALSE = "likely_false"
    FALSE = "false"
    NON_FALSIFIABLE = "non_falsifiable"


# =============================================================================
# Input Models
# =============================================================================


class ClaimInput(BaseModel):
    """
    Input for Sherlock investigation.

    This is the entry point for all investigations.
    MUST contain the claim text and investigation parameters.
    """
    claim_text: str = Field(..., min_length=1, description="The claim to investigate")
    iterations: int = Field(default=3, ge=1, le=10, description="Max investigation iterations")
    validation_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="Logic audit pass threshold")
    scope: Dict[str, Any] = Field(default_factory=dict, description="Investigation scope constraints")
    evidence_policy: Dict[str, Any] = Field(default_factory=dict, description="Evidence gathering policy")
    tone: Optional[str] = Field(default=None, description="Output tone preference")
    time_bounds: Optional[Dict[str, Any]] = Field(default=None, description="Temporal constraints")
    prior_assumptions: List[str] = Field(default_factory=list, description="Explicit prior assumptions")

    class Config:
        frozen = True


# =============================================================================
# Step 1: Claim Lock
# =============================================================================


class LockedClaim(BaseModel):
    """
    A claim that has been locked for investigation.

    MUST contain:
    - A testable, unambiguous claim statement
    - Decomposed subclaims
    - Explicit assumptions
    - Falsifiability conditions

    If falsifiability is empty, the claim is non-falsifiable and investigation stops.
    """
    version: int = Field(..., ge=1, description="Iteration version")
    testable_claim: str = Field(..., min_length=1, description="The locked, testable claim")
    subclaims: List[str] = Field(default_factory=list, description="Decomposed subclaims")
    assumptions: List[str] = Field(default_factory=list, description="Explicit assumptions")
    falsifiability: List[str] = Field(default_factory=list, description="Conditions that would falsify the claim")

    class Config:
        frozen = True

    def is_falsifiable(self) -> bool:
        """Returns True if claim has falsifiability conditions."""
        return len(self.falsifiability) > 0


# =============================================================================
# Step 2: Evidence Map
# =============================================================================


class EvidenceItem(BaseModel):
    """
    A single piece of evidence.

    MUST have tier, source, and reliability score.
    Reliability is 0.0-1.0 where 1.0 is perfectly reliable.
    """
    tier: EvidenceTier = Field(..., description="Evidence tier (1=best, 3=lowest)")
    source_type: str = Field(..., description="Type of source (e.g., 'primary', 'study', 'expert')")
    citation: str = Field(..., description="Citation or reference")
    summary: str = Field(..., description="Brief summary of evidence")
    reliability: float = Field(..., ge=0.0, le=1.0, description="Reliability score")

    class Config:
        frozen = True


class EvidenceMap(BaseModel):
    """
    Collection of evidence for an investigation iteration.

    MUST track version and contain list of evidence items.
    Empty evidence map is valid (no evidence found).
    """
    version: int = Field(..., ge=1, description="Iteration version")
    items: List[EvidenceItem] = Field(default_factory=list, description="Evidence items")

    class Config:
        frozen = True

    def total_reliability(self) -> float:
        """Compute average reliability across all items."""
        if not self.items:
            return 0.0
        return sum(item.reliability for item in self.items) / len(self.items)

    def has_evidence(self) -> bool:
        """Returns True if any evidence exists."""
        return len(self.items) > 0


# =============================================================================
# Step 3: Argument Graph
# =============================================================================


class ArgumentNode(BaseModel):
    """
    A node in the argument graph.

    MUST have unique id, side (pro/con), and claim.
    Supports/attacks reference other node ids.
    """
    id: str = Field(..., description="Unique node identifier")
    side: ArgumentSide = Field(..., description="Pro or con the main claim")
    claim: str = Field(..., description="The argument claim")
    supports: List[str] = Field(default_factory=list, description="IDs of nodes this supports")
    attacks: List[str] = Field(default_factory=list, description="IDs of nodes this attacks")

    class Config:
        frozen = True


class ArgumentGraph(BaseModel):
    """
    Directed graph of arguments.

    MUST contain nodes representing pro and con arguments.
    Graph structure tracks support/attack relationships.
    """
    version: int = Field(..., ge=1, description="Iteration version")
    nodes: List[ArgumentNode] = Field(default_factory=list, description="Argument nodes")

    class Config:
        frozen = True

    def pro_count(self) -> int:
        """Count of pro arguments."""
        return sum(1 for n in self.nodes if n.side == ArgumentSide.PRO)

    def con_count(self) -> int:
        """Count of con arguments."""
        return sum(1 for n in self.nodes if n.side == ArgumentSide.CON)


# =============================================================================
# Step 4: Scoring / Verdict
# =============================================================================


class VerdictDraft(BaseModel):
    """
    A verdict draft with confidence and rationale.

    MUST include verdict, confidence, score breakdown, and rationale.
    """
    version: int = Field(..., ge=1, description="Iteration version")
    verdict: VerdictLevel = Field(..., description="The verdict")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in verdict")
    score_breakdown: Dict[str, float] = Field(default_factory=dict, description="Component scores")
    rationale_bullets: List[str] = Field(default_factory=list, description="Rationale points")

    class Config:
        frozen = True


# =============================================================================
# Step 5: Logic Audit
# =============================================================================


class LogicAuditResult(BaseModel):
    """
    Result of the logic audit gate.

    MUST include pass/fail, threshold, category scores, and failures.
    Weighted score is computed from category scores.
    """
    version: int = Field(..., ge=1, description="Iteration version")
    passed: bool = Field(..., description="Whether audit passed")
    threshold: float = Field(..., ge=0.0, le=1.0, description="Pass threshold used")
    category_scores: Dict[str, float] = Field(default_factory=dict, description="Scores by category")
    weighted_score: float = Field(..., ge=0.0, le=1.0, description="Final weighted score")
    failures: List[str] = Field(default_factory=list, description="List of failures/issues")

    class Config:
        frozen = True


# =============================================================================
# Step 6: Mutation System
# =============================================================================


class MutationEvent(BaseModel):
    """
    A mutation event that could modify the investigation.

    Mutations are OFF by default. This logs proposed changes.
    """
    version: int = Field(..., ge=1, description="Iteration version when proposed")
    trigger: str = Field(..., description="What triggered the mutation proposal")
    change: str = Field(..., description="Proposed change description")
    risk: str = Field(..., description="Risk assessment of the change")
    expected_benefit: str = Field(..., description="Expected benefit")
    observed_outcome: Optional[str] = Field(default=None, description="Outcome if applied")

    class Config:
        frozen = True


# =============================================================================
# Composite Artifacts
# =============================================================================


class IterationArtifacts(BaseModel):
    """
    All artifacts from a single investigation iteration.

    MUST contain all step outputs with matching version numbers.
    Mutations list may be empty if mutations are disabled.
    """
    version: int = Field(..., ge=1, description="Iteration number")
    locked_claim: LockedClaim = Field(..., description="Step 1: Locked claim")
    evidence_map: EvidenceMap = Field(..., description="Step 2: Evidence map")
    argument_graph: ArgumentGraph = Field(..., description="Step 3: Argument graph")
    verdict: VerdictDraft = Field(..., description="Step 4: Verdict draft")
    audit: LogicAuditResult = Field(..., description="Step 5: Logic audit result")
    mutations: List[MutationEvent] = Field(default_factory=list, description="Proposed mutations")

    class Config:
        frozen = True

    def is_consistent(self) -> bool:
        """Check if all artifacts have matching version numbers."""
        return (
            self.locked_claim.version == self.version
            and self.evidence_map.version == self.version
            and self.argument_graph.version == self.version
            and self.verdict.version == self.version
            and self.audit.version == self.version
        )


class FinalReport(BaseModel):
    """
    Final investigation report.

    MUST contain:
    - Number of iterations completed
    - Final verdict
    - Publishable report (structured)
    - Algorithm evolution report
    - Logic audit appendix
    - Mutation log
    """
    iterations: int = Field(..., ge=1, description="Number of iterations completed")
    final_verdict: VerdictDraft = Field(..., description="Final verdict")
    publishable_report: Dict[str, Any] = Field(default_factory=dict, description="Structured report for output")
    algorithm_evolution_report: Dict[str, Any] = Field(default_factory=dict, description="How investigation evolved")
    logic_audit_appendix: List[LogicAuditResult] = Field(default_factory=list, description="All audit results")
    mutation_log: List[MutationEvent] = Field(default_factory=list, description="All mutation events")

    class Config:
        frozen = True

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "FinalReport":
        """Deserialize from JSON string."""
        return cls.model_validate_json(json_str)
