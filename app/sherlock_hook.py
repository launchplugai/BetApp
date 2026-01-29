# app/sherlock_hook.py
"""
Sherlock Integration Hook (Ticket 17)

Dry-run integration between the evaluation pipeline and Sherlock.
Feature-flagged, no external calls, deterministic.

When enabled:
- Derives a claim from the evaluation result
- Runs Sherlock investigation
- Translates artifacts to DNA primitives (in-memory only)
- Returns structured result for debugging

When disabled:
- Returns None immediately (zero latency impact)

Contracts referenced:
- docs/contracts/SYSTEM_CONTRACT_SDS.md
- docs/contracts/SCH_SDK_CONTRACT.md
- docs/mappings/MAP_SHERLOCK_TO_DNA.md
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import uuid4

_logger = logging.getLogger(__name__)


# =============================================================================
# DNA Artifact (In-Memory Only)
# =============================================================================


@dataclass(frozen=True)
class DNAArtifact:
    """
    In-memory representation of DNA primitives produced from Sherlock.

    NOT persisted. For dry-run debugging only.

    Fields match docs/contracts/DNA_PRIMITIVES_CONTRACT.md
    """
    # Metadata
    created_at: str  # ISO 8601
    sherlock_report_id: str
    audit_passed: bool
    audit_score: float

    # Primitives (in-memory representations)
    weights: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]
    baseline: Optional[Dict[str, Any]]
    drifts: List[Dict[str, Any]]
    tradeoffs: List[Dict[str, Any]]
    lineage: List[Dict[str, Any]]

    # Quarantine status (per oversight decision)
    quarantined: bool  # True if audit failed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "created_at": self.created_at,
            "sherlock_report_id": self.sherlock_report_id,
            "audit_passed": self.audit_passed,
            "audit_score": self.audit_score,
            "quarantined": self.quarantined,
            "primitives": {
                "weights": self.weights,
                "constraints": self.constraints,
                "conflicts": self.conflicts,
                "baseline": self.baseline,
                "drifts": self.drifts,
                "tradeoffs": self.tradeoffs,
                "lineage": self.lineage,
            },
        }


# =============================================================================
# Sherlock Hook Result
# =============================================================================


@dataclass(frozen=True)
class SherlockHookResult:
    """
    Result from Sherlock hook execution.

    Contains Sherlock report summary and DNA artifacts.
    """
    enabled: bool
    claim_text: str
    iterations_completed: int
    verdict: str
    confidence: float
    audit_passed: bool
    audit_score: float
    dna_artifact: Optional[DNAArtifact]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "enabled": self.enabled,
            "claim_text": self.claim_text,
            "iterations_completed": self.iterations_completed,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "audit_passed": self.audit_passed,
            "audit_score": self.audit_score,
            "dna_artifact": self.dna_artifact.to_dict() if self.dna_artifact else None,
        }


# =============================================================================
# Claim Derivation
# =============================================================================


def _derive_claim_from_evaluation(
    evaluation_metrics: Dict[str, Any],
    signal: str,
    primary_failure_type: str,
    leg_count: int,
) -> str:
    """
    Derive a structured claim from the evaluation result.

    The claim is a statement about the parlay that Sherlock will investigate.
    Example: "This parlay is fragile because correlation penalty is high"
    """
    fragility = evaluation_metrics.get("final_fragility", 0)

    # Build claim based on primary failure
    claim_parts = [f"This {leg_count}-leg parlay"]

    if signal == "blue":
        claim_parts.append("is structurally sound")
    elif signal == "green":
        claim_parts.append("has moderate complexity")
    elif signal == "yellow":
        claim_parts.append("carries elevated risk")
    else:  # red
        claim_parts.append("is highly fragile")

    # Add reason from primary failure
    failure_reasons = {
        "correlation": "correlated outcomes amplify risk",
        "leg_count": "too many legs compound failure probability",
        "volatility": "high-variance selections increase uncertainty",
        "dependency": "dependent outcomes create hidden risk",
        "prop_density": "prop-heavy structure has elevated variance",
        "same_game_dependency": "same-game legs are not independent",
        "market_conflict": "overlapping markets create correlation",
        "weak_clarity": "input lacks sufficient detail for analysis",
    }

    reason = failure_reasons.get(primary_failure_type, "structural factors")
    claim_parts.append(f"because {reason}")

    return " ".join(claim_parts)


# =============================================================================
# Artifact Translation (MAP_SHERLOCK_TO_DNA.md)
# =============================================================================


def _translate_to_dna_artifacts(
    report: Any,  # FinalReport from Sherlock
    claim_text: str,
) -> DNAArtifact:
    """
    Translate Sherlock FinalReport to DNA primitives.

    Follows docs/mappings/MAP_SHERLOCK_TO_DNA.md exactly.
    """
    now = datetime.now(timezone.utc).isoformat()
    report_id = str(uuid4())

    # Get final audit result
    final_audit = report.logic_audit_appendix[-1] if report.logic_audit_appendix else None
    audit_passed = final_audit.passed if final_audit else False
    audit_score = final_audit.weighted_score if final_audit else 0.0

    # Per oversight decision: if audit fails, quarantine but still record
    quarantined = not audit_passed

    # --- Weights ---
    weights = []

    # Weight from verdict confidence
    weights.append({
        "id": str(uuid4()),
        "version": 1,
        "created_at": now,
        "target_type": "verdict",
        "target_id": report_id,
        "value": report.final_verdict.confidence,
        "source": "sherlock",
        "metadata": {"verdict": report.final_verdict.verdict.value},
    })

    # Weight from audit score
    if final_audit:
        weights.append({
            "id": str(uuid4()),
            "version": 1,
            "created_at": now,
            "target_type": "audit",
            "target_id": report_id,
            "value": audit_score,
            "source": "sherlock",
            "metadata": {"threshold": final_audit.threshold},
        })

    # --- Constraints (from assumptions) ---
    constraints = []

    # Get locked claim from last iteration
    if report.logic_audit_appendix:
        # We need to access iteration artifacts - for now use publishable_report
        pass

    # Add constraint from the claim itself
    constraints.append({
        "id": str(uuid4()),
        "version": 1,
        "created_at": now,
        "constraint_type": "assumption",
        "expression": f"Investigation assumes: {claim_text[:100]}",
        "scope": "sherlock_investigation",
        "source_claim_id": report_id,
        "is_violated": False,
        "violation_details": None,
    })

    # --- Conflicts (from argument graph attack relationships) ---
    conflicts = []
    # In skeleton, we don't have access to raw iteration artifacts in FinalReport
    # This would be populated in full implementation

    # --- Baseline (only if audit passed) ---
    baseline = None
    if audit_passed:
        baseline = {
            "id": str(uuid4()),
            "version": 1,
            "created_at": now,
            "entity_type": "verdict",
            "entity_id": report_id,
            "snapshot": report.publishable_report,
            "snapshot_hash": "",  # Would be SHA-256 in production
            "reason": "Sherlock investigation passed audit",
        }

    # --- Drifts (logged if audit failed) ---
    drifts = []
    if not audit_passed:
        drifts.append({
            "id": str(uuid4()),
            "version": 1,
            "created_at": now,
            "baseline_id": None,  # No prior baseline
            "drift_type": "modification",
            "delta": {"rejected_verdict": report.final_verdict.verdict.value},
            "magnitude": 0.0,
            "cause": f"Sherlock audit failed (score={audit_score:.2f}, threshold={final_audit.threshold if final_audit else 0.85:.2f})",
            "sherlock_report_id": report_id,
        })

    # --- Tradeoffs (required for verdict decisions) ---
    tradeoffs = []
    if audit_passed:
        tradeoffs.append({
            "id": str(uuid4()),
            "version": 1,
            "created_at": now,
            "decision": f"Accept verdict: {report.final_verdict.verdict.value}",
            "benefits": report.final_verdict.rationale_bullets,
            "costs": ["May invalidate prior assumptions"],
            "alternatives_considered": ["Reject investigation", "Request more iterations"],
            "accepted_by": "sherlock",
            "resolves_conflict_id": None,
            "sherlock_report_id": report_id,
        })

    # --- Lineage ---
    lineage = [{
        "id": str(uuid4()),
        "version": 1,
        "created_at": now,
        "entity_type": "sherlock_investigation",
        "entity_id": report_id,
        "parent_id": None,
        "operation": "create",
        "source_ids": [],
        "actor": "sherlock",
        "sherlock_report_id": report_id,
    }]

    return DNAArtifact(
        created_at=now,
        sherlock_report_id=report_id,
        audit_passed=audit_passed,
        audit_score=audit_score,
        weights=weights,
        constraints=constraints,
        conflicts=conflicts,
        baseline=baseline,
        drifts=drifts,
        tradeoffs=tradeoffs,
        lineage=lineage,
        quarantined=quarantined,
    )


# =============================================================================
# Main Hook
# =============================================================================


def run_sherlock_hook(
    sherlock_enabled: bool,
    dna_recording_enabled: bool,
    evaluation_metrics: Dict[str, Any],
    signal: str,
    primary_failure_type: str,
    leg_count: int,
) -> Optional[SherlockHookResult]:
    """
    Run Sherlock integration hook.

    Args:
        sherlock_enabled: SHERLOCK_ENABLED flag
        dna_recording_enabled: DNA_RECORDING_ENABLED flag
        evaluation_metrics: Metrics from core evaluation
        signal: Signal color (blue/green/yellow/red)
        primary_failure_type: Primary failure type string
        leg_count: Number of legs in parlay

    Returns:
        SherlockHookResult if enabled, None if disabled

    Contracts referenced:
        - docs/contracts/SYSTEM_CONTRACT_SDS.md#section-2-dataflow
        - docs/contracts/SCH_SDK_CONTRACT.md#section-7-usage
        - docs/mappings/MAP_SHERLOCK_TO_DNA.md#section-2-mapping-table
    """
    # Early exit if disabled (zero latency)
    if not sherlock_enabled:
        return None

    _logger.info("[SHERLOCK_HOOK] Running Sherlock integration (dry-run)")

    # Step 1: Derive claim from evaluation
    claim_text = _derive_claim_from_evaluation(
        evaluation_metrics=evaluation_metrics,
        signal=signal,
        primary_failure_type=primary_failure_type,
        leg_count=leg_count,
    )
    _logger.debug(f"[SHERLOCK_HOOK] Derived claim: {claim_text}")

    # Step 2: Import and run Sherlock
    try:
        from sherlock import SherlockEngine, ClaimInput

        engine = SherlockEngine(mutations_enabled=False)
        claim_input = ClaimInput(
            claim_text=claim_text,
            iterations=3,
            validation_threshold=0.85,
            evidence_policy={"generate_placeholder": True},
        )

        report = engine.run(claim_input)
        _logger.info(
            f"[SHERLOCK_HOOK] Investigation complete: "
            f"iterations={report.iterations}, "
            f"verdict={report.final_verdict.verdict.value}"
        )

    except Exception as e:
        _logger.error(f"[SHERLOCK_HOOK] Sherlock execution failed: {e}")
        return SherlockHookResult(
            enabled=True,
            claim_text=claim_text,
            iterations_completed=0,
            verdict="error",
            confidence=0.0,
            audit_passed=False,
            audit_score=0.0,
            dna_artifact=None,
        )

    # Step 3: Get audit result
    final_audit = report.logic_audit_appendix[-1] if report.logic_audit_appendix else None
    audit_passed = final_audit.passed if final_audit else False
    audit_score = final_audit.weighted_score if final_audit else 0.0

    # Step 4: Translate to DNA artifacts (if DNA recording enabled)
    dna_artifact = None
    if dna_recording_enabled:
        _logger.debug("[SHERLOCK_HOOK] Translating to DNA artifacts")
        dna_artifact = _translate_to_dna_artifacts(report, claim_text)
        _logger.info(
            f"[SHERLOCK_HOOK] DNA artifact created: "
            f"quarantined={dna_artifact.quarantined}, "
            f"weights={len(dna_artifact.weights)}, "
            f"constraints={len(dna_artifact.constraints)}"
        )

    return SherlockHookResult(
        enabled=True,
        claim_text=claim_text,
        iterations_completed=report.iterations,
        verdict=report.final_verdict.verdict.value,
        confidence=report.final_verdict.confidence,
        audit_passed=audit_passed,
        audit_score=audit_score,
        dna_artifact=dna_artifact,
    )
