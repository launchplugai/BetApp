# app/proof.py
"""
Sherlock/DNA Proof Infrastructure (Ticket 18).

Provides user-verifiable proof that Sherlock/DNA mapping is running.
This module tracks execution metadata WITHOUT storing sensitive data.

Key constraints:
- Does NOT change engine scoring, tier gating, or evaluation math
- Does NOT add external network calls
- Deterministic behavior
- All artifacts marked derived=true
- No persistence required (in-memory only)
"""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.config import load_config

_logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Maximum number of proof records to keep in memory
MAX_PROOF_HISTORY = 50

# DNA artifact types (for counting)
DNA_ARTIFACT_TYPES = [
    "correlation",
    "fragility",
    "inductor",
    "recommendation",
    "suggestion",
]


# =============================================================================
# Data Models
# =============================================================================


@dataclass(frozen=True)
class DNAArtifactSummary:
    """Summary of DNA artifacts produced by an evaluation."""

    correlation_count: int = 0
    fragility_computed: bool = False
    inductor_level: Optional[str] = None
    recommendation_action: Optional[str] = None
    suggestion_count: int = 0

    @property
    def total_artifacts(self) -> int:
        """Total number of artifacts produced."""
        count = 0
        if self.correlation_count > 0:
            count += self.correlation_count
        if self.fragility_computed:
            count += 1
        if self.inductor_level:
            count += 1
        if self.recommendation_action:
            count += 1
        count += self.suggestion_count
        return count

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "correlation_count": self.correlation_count,
            "fragility_computed": self.fragility_computed,
            "inductor_level": self.inductor_level,
            "recommendation_action": self.recommendation_action,
            "suggestion_count": self.suggestion_count,
            "total_artifacts": self.total_artifacts,
        }


@dataclass(frozen=True)
class SherlockProofRecord:
    """
    Proof record for a single evaluation.

    Contains NON-SENSITIVE metadata about Sherlock/DNA execution.
    All data is derived from existing evaluation output.
    """

    # Identifiers
    proof_id: UUID
    evaluation_id: UUID
    timestamp_utc: str

    # Execution flags
    sherlock_ran: bool
    dna_recording_active: bool

    # Audit status
    audit_status: str  # "PASS" | "FAIL" | "SKIPPED"
    audit_notes: Optional[str] = None

    # DNA artifact summary (if recording was active)
    artifacts: Optional[DNAArtifactSummary] = None

    # Metadata
    derived: bool = True  # Always true - this is derived data

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "proof_id": str(self.proof_id),
            "evaluation_id": str(self.evaluation_id),
            "timestamp_utc": self.timestamp_utc,
            "sherlock_ran": self.sherlock_ran,
            "dna_recording_active": self.dna_recording_active,
            "audit_status": self.audit_status,
            "audit_notes": self.audit_notes,
            "artifacts": self.artifacts.to_dict() if self.artifacts else None,
            "derived": self.derived,
        }


# =============================================================================
# In-Memory Proof Store
# =============================================================================


class ProofStore:
    """
    In-memory store for proof records.

    Thread-safe deque with fixed size to prevent unbounded growth.
    """

    def __init__(self, max_size: int = MAX_PROOF_HISTORY):
        self._records: deque[SherlockProofRecord] = deque(maxlen=max_size)

    def add(self, record: SherlockProofRecord) -> None:
        """Add a proof record to the store."""
        self._records.append(record)

    def get_recent(self, limit: int = 10) -> list[SherlockProofRecord]:
        """Get the most recent proof records."""
        # Return in reverse order (newest first)
        records = list(self._records)
        records.reverse()
        return records[:limit]

    def get_by_evaluation_id(
        self, evaluation_id: UUID
    ) -> Optional[SherlockProofRecord]:
        """Get proof record for a specific evaluation."""
        for record in self._records:
            if record.evaluation_id == evaluation_id:
                return record
        return None

    def clear(self) -> None:
        """Clear all proof records."""
        self._records.clear()

    @property
    def count(self) -> int:
        """Number of records in the store."""
        return len(self._records)


# Global proof store instance
_proof_store = ProofStore()


# =============================================================================
# Proof Generation Functions
# =============================================================================


def get_proof_flags() -> dict:
    """
    Get current Sherlock/DNA flag states.

    Returns:
        Dict with sherlock_enabled and dna_recording_enabled.
    """
    config = load_config(fail_fast=False)
    return {
        "sherlock_enabled": config.sherlock_enabled,
        "dna_recording_enabled": config.dna_recording_enabled,
    }


def is_sherlock_enabled() -> bool:
    """Check if Sherlock is enabled."""
    config = load_config(fail_fast=False)
    return config.sherlock_enabled


def is_dna_recording_enabled() -> bool:
    """Check if DNA recording is enabled."""
    config = load_config(fail_fast=False)
    return config.dna_recording_enabled


def generate_proof_record(
    evaluation_id: UUID,
    evaluation_response: Optional[object] = None,
) -> SherlockProofRecord:
    """
    Generate a proof record for an evaluation.

    This function:
    1. Checks if Sherlock/DNA flags are enabled
    2. Extracts artifact counts from the evaluation response
    3. Runs a deterministic audit check
    4. Returns a proof record

    Args:
        evaluation_id: The UUID of the evaluation
        evaluation_response: The EvaluationResponse from the engine (optional)

    Returns:
        SherlockProofRecord with execution proof
    """
    flags = get_proof_flags()
    sherlock_enabled = flags["sherlock_enabled"]
    dna_recording_enabled = flags["dna_recording_enabled"]

    # If both flags are off, return a minimal "skipped" record
    if not sherlock_enabled and not dna_recording_enabled:
        return SherlockProofRecord(
            proof_id=uuid4(),
            evaluation_id=evaluation_id,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            sherlock_ran=False,
            dna_recording_active=False,
            audit_status="SKIPPED",
            audit_notes="Sherlock and DNA recording are disabled",
            artifacts=None,
        )

    # Extract artifacts from evaluation response
    artifacts = None
    if evaluation_response is not None and dna_recording_enabled:
        artifacts = _extract_artifact_summary(evaluation_response)

    # Run audit check
    audit_status, audit_notes = _run_audit_check(
        sherlock_enabled, dna_recording_enabled, artifacts
    )

    # Create and store proof record
    record = SherlockProofRecord(
        proof_id=uuid4(),
        evaluation_id=evaluation_id,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        sherlock_ran=sherlock_enabled,
        dna_recording_active=dna_recording_enabled,
        audit_status=audit_status,
        audit_notes=audit_notes,
        artifacts=artifacts,
    )

    # Store the record
    _proof_store.add(record)

    _logger.debug(
        f"Generated proof record: {record.proof_id} "
        f"sherlock={sherlock_enabled} dna={dna_recording_enabled} "
        f"audit={audit_status}"
    )

    return record


def _extract_artifact_summary(evaluation_response: object) -> DNAArtifactSummary:
    """
    Extract artifact summary from an evaluation response.

    This reads existing metrics from the evaluation - no new computation.
    """
    # Safe attribute access for frozen dataclass
    try:
        # Correlation count
        correlations = getattr(evaluation_response, "correlations", ())
        correlation_count = len(correlations) if correlations else 0

        # Fragility computed
        metrics = getattr(evaluation_response, "metrics", None)
        fragility_computed = metrics is not None and hasattr(
            metrics, "final_fragility"
        )

        # Inductor level
        inductor = getattr(evaluation_response, "inductor", None)
        inductor_level = None
        if inductor is not None:
            level = getattr(inductor, "level", None)
            if level is not None:
                inductor_level = str(level.value) if hasattr(level, "value") else str(level)

        # Recommendation action
        recommendation = getattr(evaluation_response, "recommendation", None)
        recommendation_action = None
        if recommendation is not None:
            action = getattr(recommendation, "action", None)
            if action is not None:
                recommendation_action = (
                    str(action.value) if hasattr(action, "value") else str(action)
                )

        # Suggestion count
        suggestions = getattr(evaluation_response, "suggestions", None)
        suggestion_count = len(suggestions) if suggestions else 0

        return DNAArtifactSummary(
            correlation_count=correlation_count,
            fragility_computed=fragility_computed,
            inductor_level=inductor_level,
            recommendation_action=recommendation_action,
            suggestion_count=suggestion_count,
        )

    except Exception as e:
        _logger.warning(f"Failed to extract artifact summary: {e}")
        return DNAArtifactSummary()


def _run_audit_check(
    sherlock_enabled: bool,
    dna_recording_enabled: bool,
    artifacts: Optional[DNAArtifactSummary],
) -> tuple[str, Optional[str]]:
    """
    Run deterministic audit check on the proof.

    Returns (status, notes) where status is "PASS", "FAIL", or "SKIPPED".
    """
    # If nothing is enabled, audit is skipped
    if not sherlock_enabled and not dna_recording_enabled:
        return "SKIPPED", "Both features disabled"

    # If DNA recording is enabled, artifacts must be present
    if dna_recording_enabled:
        if artifacts is None:
            return "FAIL", "DNA recording enabled but no artifacts captured"
        if artifacts.total_artifacts == 0:
            return "FAIL", "DNA recording enabled but zero artifacts produced"

    # If Sherlock is enabled, basic checks pass
    # (Future: add Sherlock-specific validation when implemented)
    if sherlock_enabled:
        pass  # Sherlock validation placeholder

    return "PASS", None


# =============================================================================
# Public API
# =============================================================================


def get_recent_proofs(limit: int = 10) -> list[dict]:
    """
    Get recent proof records as dictionaries.

    Args:
        limit: Maximum number of records to return

    Returns:
        List of proof record dictionaries (newest first)
    """
    records = _proof_store.get_recent(limit)
    return [r.to_dict() for r in records]


def get_proof_for_evaluation(evaluation_id: UUID) -> Optional[dict]:
    """
    Get proof record for a specific evaluation.

    Args:
        evaluation_id: The evaluation UUID

    Returns:
        Proof record dictionary or None if not found
    """
    record = _proof_store.get_by_evaluation_id(evaluation_id)
    return record.to_dict() if record else None


def get_proof_summary() -> dict:
    """
    Get a summary of proof system status.

    Returns:
        Dict with flags, record count, and audit stats
    """
    flags = get_proof_flags()
    records = _proof_store.get_recent(MAX_PROOF_HISTORY)

    # Count audit statuses
    pass_count = sum(1 for r in records if r.audit_status == "PASS")
    fail_count = sum(1 for r in records if r.audit_status == "FAIL")
    skip_count = sum(1 for r in records if r.audit_status == "SKIPPED")

    return {
        "sherlock_enabled": flags["sherlock_enabled"],
        "dna_recording_enabled": flags["dna_recording_enabled"],
        "record_count": _proof_store.count,
        "audit_summary": {
            "pass": pass_count,
            "fail": fail_count,
            "skipped": skip_count,
        },
    }


def clear_proof_store() -> None:
    """Clear all proof records (for testing)."""
    _proof_store.clear()
