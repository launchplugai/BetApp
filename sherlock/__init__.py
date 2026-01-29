# sherlock/__init__.py
"""
Sherlock Mode v1 - Investigation Engine

A structured investigation framework that produces auditable, deterministic
analysis of claims through a 6-step canonical loop.

Usage:
    from sherlock import SherlockEngine, ClaimInput

    engine = SherlockEngine()
    input = ClaimInput(claim_text="The claim to investigate")
    report = engine.run(input)

Constraints:
- MUST NOT mutate application state or persistence.
- MUST NOT call external network/web.
- MUST be deterministic: same input => same output.
- Mutations are OFF by default.
"""

from sherlock.models import (
    # Input
    ClaimInput,
    # Step artifacts
    LockedClaim,
    EvidenceItem,
    EvidenceMap,
    EvidenceTier,
    ArgumentNode,
    ArgumentGraph,
    ArgumentSide,
    VerdictDraft,
    VerdictLevel,
    LogicAuditResult,
    MutationEvent,
    # Composite
    IterationArtifacts,
    FinalReport,
)

from sherlock.engine import SherlockEngine
from sherlock.audit import run_logic_audit, get_audit_weights, AUDIT_WEIGHTS, DEFAULT_THRESHOLD
from sherlock.mutation import propose_mutations

__all__ = [
    # Engine
    "SherlockEngine",
    # Input
    "ClaimInput",
    # Models
    "LockedClaim",
    "EvidenceItem",
    "EvidenceMap",
    "EvidenceTier",
    "ArgumentNode",
    "ArgumentGraph",
    "ArgumentSide",
    "VerdictDraft",
    "VerdictLevel",
    "LogicAuditResult",
    "MutationEvent",
    "IterationArtifacts",
    "FinalReport",
    # Audit
    "run_logic_audit",
    "get_audit_weights",
    "AUDIT_WEIGHTS",
    "DEFAULT_THRESHOLD",
    # Mutation
    "propose_mutations",
]

__version__ = "1.0.0"
