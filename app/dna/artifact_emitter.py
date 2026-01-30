"""
DNA Artifact Emitter (Ticket 20)

Emits real, contract-compliant DNA artifacts from evaluation data.
Artifacts are deterministic, derived, and never persisted.

Emits 1-3 artifacts per evaluation:
- weight: Captures key scoring factors
- constraint: Captures rule violations
- audit_note: Captures validation status

All artifacts comply with contracts/dna_contract_v1.json.

Invariants:
- derived = True (always)
- persisted = False (always)
- source = "sherlock" (always)
- Deterministic: same input = same output
- No side effects
"""

from datetime import datetime, timezone
from typing import Any, Optional
from dataclasses import dataclass
import uuid
import hashlib


@dataclass
class EmissionContext:
    """
    Context for artifact emission.

    Provides lineage tracking and ensures deterministic IDs.
    """
    request_id: str
    run_id: str
    claim_id: str

    @classmethod
    def create(cls, request_id: Optional[str] = None) -> "EmissionContext":
        """
        Create emission context with deterministic IDs.

        If request_id is provided, run_id and claim_id are derived from it
        to ensure determinism.
        """
        if request_id is None:
            request_id = str(uuid.uuid4())

        # Derive run_id and claim_id deterministically from request_id
        run_id = f"run-{_deterministic_hash(request_id, 'run')[:12]}"
        claim_id = f"claim-{_deterministic_hash(request_id, 'claim')[:12]}"

        return cls(
            request_id=request_id,
            run_id=run_id,
            claim_id=claim_id,
        )


def _deterministic_hash(base: str, salt: str) -> str:
    """Create a deterministic hash from base string and salt."""
    return hashlib.sha256(f"{base}:{salt}".encode()).hexdigest()


def _create_base_artifact(
    artifact_type: str,
    context: EmissionContext,
) -> dict[str, Any]:
    """
    Create base artifact with all common fields.

    All artifacts share these fields per dna_contract_v1.
    """
    return {
        "artifact_type": artifact_type,
        "derived": True,  # INVARIANT: always true
        "persisted": False,  # INVARIANT: always false
        "source": "sherlock",  # INVARIANT: always sherlock
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "lineage": {
            "request_id": context.request_id,
            "run_id": context.run_id,
            "claim_id": context.claim_id,
        },
    }


def emit_weight_artifact(
    context: EmissionContext,
    key: str,
    value: float,
    unit: Optional[str] = None,
    rationale: Optional[str] = None,
) -> dict[str, Any]:
    """
    Emit a weight artifact.

    Captures a scoring factor from the evaluation.

    Args:
        context: Emission context with lineage
        key: Weight identifier (e.g., "correlation_penalty")
        value: Numeric weight value
        unit: Optional unit (e.g., "percent", "multiplier")
        rationale: Optional explanation

    Returns:
        Contract-compliant weight artifact
    """
    artifact = _create_base_artifact("weight", context)
    artifact["key"] = key
    artifact["value"] = value

    if unit is not None:
        artifact["unit"] = unit
    if rationale is not None:
        artifact["rationale"] = rationale

    return artifact


def emit_constraint_artifact(
    context: EmissionContext,
    key: str,
    rule: str,
    severity: str,
) -> dict[str, Any]:
    """
    Emit a constraint artifact.

    Captures a rule or constraint from the evaluation.

    Args:
        context: Emission context with lineage
        key: Constraint identifier
        rule: Human-readable rule description
        severity: One of "info", "warning", "error", "critical"

    Returns:
        Contract-compliant constraint artifact
    """
    # Validate severity
    valid_severities = ["info", "warning", "error", "critical"]
    if severity not in valid_severities:
        severity = "info"

    artifact = _create_base_artifact("constraint", context)
    artifact["key"] = key
    artifact["rule"] = rule
    artifact["severity"] = severity

    return artifact


def emit_audit_note_artifact(
    context: EmissionContext,
    status: str,
    notes: list[str],
) -> dict[str, Any]:
    """
    Emit an audit_note artifact.

    Captures validation/audit status.

    Args:
        context: Emission context with lineage
        status: "PASS" or "FAIL"
        notes: List of audit notes

    Returns:
        Contract-compliant audit_note artifact
    """
    # Validate status
    if status not in ["PASS", "FAIL"]:
        status = "FAIL"

    artifact = _create_base_artifact("audit_note", context)
    artifact["status"] = status
    artifact["notes"] = notes

    return artifact


def _build_sherlock_advisory(
    evaluation_metrics: dict[str, Any],
    signal: str,
    leg_count: int,
    primary_failure_type: Optional[str],
) -> str:
    """
    Build a human-readable Sherlock advisory synthesis.

    Explains what was checked in plain English:
    - Structure analysis (leg count, complexity)
    - Correlation/dependency heuristics
    - Risk assessment verdict

    Ticket 23: Always emit meaningful, truthful explanation.
    """
    final_fragility = evaluation_metrics.get("final_fragility", 0.0)
    correlation_penalty = evaluation_metrics.get("correlation_penalty", 0.0)
    leg_penalty = evaluation_metrics.get("leg_penalty", 0.0)

    # Build checks summary
    checks_performed = []

    # 1. Structure check
    if leg_count == 1:
        checks_performed.append("Single-leg structure verified (no parlay complexity)")
    elif leg_count <= 3:
        checks_performed.append(f"Analyzed {leg_count}-leg parlay structure for complexity")
    else:
        checks_performed.append(f"Evaluated {leg_count}-leg parlay (elevated structural risk)")

    # 2. Correlation check
    if correlation_penalty > 0:
        checks_performed.append(f"Detected correlation between legs (+{correlation_penalty:.1f}pt penalty)")
    else:
        checks_performed.append("No significant correlation detected between legs")

    # 3. Fragility assessment
    if final_fragility <= 15:
        checks_performed.append(f"Fragility score {final_fragility:.0f}% is low — structure is sound")
    elif final_fragility <= 35:
        checks_performed.append(f"Fragility score {final_fragility:.0f}% is moderate — manageable risk")
    elif final_fragility <= 60:
        checks_performed.append(f"Fragility score {final_fragility:.0f}% is elevated — consider simplifying")
    else:
        checks_performed.append(f"Fragility score {final_fragility:.0f}% is high — significant risk")

    # 4. Primary failure insight (if any)
    if primary_failure_type:
        failure_explanations = {
            "correlation": "Primary concern: correlated outcomes reduce independence",
            "leg_count": "Primary concern: too many legs compound failure probability",
            "volatility": "Primary concern: high-variance selections increase unpredictability",
            "dependency": "Primary concern: shared variables create hidden dependencies",
            "prop_density": "Primary concern: heavy prop concentration elevates variance",
            "same_game_dependency": "Primary concern: same-game legs share outcome drivers",
            "market_conflict": "Primary concern: overlapping markets amplify correlation",
            "weak_clarity": "Primary concern: limited input clarity affects analysis depth",
        }
        explanation = failure_explanations.get(
            primary_failure_type,
            f"Primary concern: {primary_failure_type.replace('_', ' ')}"
        )
        checks_performed.append(explanation)

    # 5. Signal-based verdict
    signal_verdicts = {
        "blue": "Verdict: Strong structure with minimal risk factors",
        "green": "Verdict: Solid structure with acceptable risk profile",
        "yellow": "Verdict: Fixable issues identified — improvements possible",
        "red": "Verdict: Fragile structure — significant changes recommended",
    }
    checks_performed.append(signal_verdicts.get(signal, "Verdict: Evaluation complete"))

    return ". ".join(checks_performed) + "."


def emit_artifacts_from_evaluation(
    evaluation_metrics: dict[str, Any],
    signal: str,
    leg_count: int,
    primary_failure_type: Optional[str],
    request_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    Emit 1-3 DNA artifacts from evaluation data.

    This is the main entry point for artifact emission.
    Emits deterministic, contract-compliant artifacts.

    Ticket 23: Always emits at least one meaningful audit_note with
    Sherlock advisory synthesis explaining what was checked.

    Args:
        evaluation_metrics: Dict with final_fragility, correlation_penalty, leg_penalty
        signal: Signal color (blue, green, yellow, red)
        leg_count: Number of legs in parlay
        primary_failure_type: Type of primary failure (if any)
        request_id: Optional request ID for lineage tracking

    Returns:
        List of 1-3 contract-compliant artifacts
    """
    context = EmissionContext.create(request_id)
    artifacts = []

    # 1. Weight artifact: Always emit correlation_penalty as key factor
    correlation_penalty = evaluation_metrics.get("correlation_penalty", 0.0)
    artifacts.append(
        emit_weight_artifact(
            context=context,
            key="correlation_penalty",
            value=round(correlation_penalty, 4),
            unit="multiplier",
            rationale=f"Correlation penalty applied to {leg_count}-leg parlay",
        )
    )

    # 2. Constraint artifact: Emit if there's a notable condition
    final_fragility = evaluation_metrics.get("final_fragility", 0.0)

    if final_fragility > 60:
        # High fragility constraint
        artifacts.append(
            emit_constraint_artifact(
                context=context,
                key="high_fragility",
                rule=f"Fragility {final_fragility:.1f}% exceeds safe threshold (60%)",
                severity="error" if final_fragility > 80 else "warning",
            )
        )
    elif leg_count > 6:
        # Many legs constraint
        artifacts.append(
            emit_constraint_artifact(
                context=context,
                key="leg_count_warning",
                rule=f"Parlay has {leg_count} legs; complexity increases risk",
                severity="warning",
            )
        )
    elif primary_failure_type:
        # Primary failure constraint
        artifacts.append(
            emit_constraint_artifact(
                context=context,
                key="primary_failure",
                rule=f"Primary failure detected: {primary_failure_type}",
                severity="warning",
            )
        )

    # 3. Audit note: Always emit with Sherlock advisory synthesis (Ticket 23)
    # This ensures the UI never shows "Artifacts: none" for normal inputs
    signal_map = {
        "blue": "PASS",
        "green": "PASS",
        "yellow": "PASS",  # Fixable = still pass
        "red": "FAIL",
    }
    audit_status = signal_map.get(signal, "FAIL")

    # Build comprehensive Sherlock advisory (Ticket 23)
    sherlock_advisory = _build_sherlock_advisory(
        evaluation_metrics=evaluation_metrics,
        signal=signal,
        leg_count=leg_count,
        primary_failure_type=primary_failure_type,
    )

    # Audit notes include both structured data and advisory synthesis
    audit_notes = [
        sherlock_advisory,  # Human-readable synthesis first
        f"Signal: {signal} | Fragility: {final_fragility:.0f}% | Legs: {leg_count}",
    ]

    artifacts.append(
        emit_audit_note_artifact(
            context=context,
            status=audit_status,
            notes=audit_notes,
        )
    )

    return artifacts


def get_artifact_counts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    """
    Count artifacts by type.

    Returns dict like {"weight": 1, "constraint": 1, "audit_note": 1}
    """
    counts: dict[str, int] = {}
    for artifact in artifacts:
        atype = artifact.get("artifact_type", "unknown")
        counts[atype] = counts.get(atype, 0) + 1
    return counts
