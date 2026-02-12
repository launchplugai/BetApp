"""
Sherlock Audit Layer - S-INT-2

Entry point for turning Incentive Intelligence into auditable claims.
Ahistorical model without impacting projections.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict
from app.intelligence import IncentiveIntelligence


class ClaimStatus(str, Enum):
    """Claim validation status."""
    SUPPORTED = "supported"
    CONTESTED = "contested"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class Claim:
    """
    Single auditable claim with evidence.
    Immutable. Confidence bounded [0, 1].
    """
    id: str
    claim: str
    confidence: float  # 0.0 - 1.0
    falsifier: str  # What would disprove this claim
    recommended_action: str
    support: List[str] = field(default_factory=list)
    counter: List[str] = field(default_factory=list)
    status: ClaimStatus = ClaimStatus.SUPPORTED

    def __post_init__(self):
        """Validate bounds at construction."""
        object.__setattr__(self, 'confidence', round(max(0.0, min(1.0, self.confidence)), 4))

    def to_dict(self) -> Dict[str, any]:
        """Serialize to audit payload format."""
        return {
            "id": self.id,
            "claim": self.claim,
            "confidence": self.confidence,
            "support": self.support,
            "counter": self.counter,
            "falsifier": self.falsifier,
            "recommended_action": self.recommended_action,
            "status": self.status.value
        }


@dataclass(frozen=True)
class IncentiveAudit:
    """
    Complete audit of incentive intelligence.
    Contains all claims with their evidence.
    """
    claims: List[Claim] = field(default_factory=list)
    audit_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, any]:
        """Serialize full audit payload."""
        return {
            "claims": [claim.to_dict() for claim in self.claims],
            "audit_version": self.audit_version,
            "claim_count": len(self.claims)
        }


def empty_audit() -> IncentiveAudit:
    """Return empty audit (neutral, no claims)."""
    return IncentiveAudit(claims=[], audit_version="1.0.0")


def create_initial_audit(intel: IncentiveIntelligence) -> IncentiveAudit:
    """
    Run initial claims based on the incentive intelligence.
    """
    claims = []
    # Start building claims based on intel
    return IncentiveAudit(claims=claims, audit_version="1.0.0")


def run_incentive_audit(intel: IncentiveIntelligence, context: Dict = None) -> IncentiveAudit:
    """
    Main entry point for incentive auditing.
    Returns audit with all claims evaluated.
    """
    from app.sherlock.claims import (
        evaluate_team_tanking,
        evaluate_minutes_suppression,
        evaluate_effort_decay_pace
    )
    
    claims = [
        evaluate_team_tanking(intel),
        evaluate_minutes_suppression(intel),
        evaluate_effort_decay_pace(intel)
    ]
    
    return IncentiveAudit(claims=claims, audit_version="1.0.0")
