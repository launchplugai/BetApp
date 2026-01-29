# app/proof_summary.py
"""
Proof Summary Helper (Ticket 18B)

Derives a compact proof summary from explainability blocks for UI display.
This is a read-only view - no persistence, no external calls.

Contracts referenced:
- docs/contracts/SCH_SDK_CONTRACT.md#section-4-finalreport-schema
"""
from __future__ import annotations

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

_logger = logging.getLogger(__name__)


# =============================================================================
# Proof Summary Schema
# =============================================================================


@dataclass(frozen=True)
class ProofSummary:
    """
    Compact proof summary for UI display.

    All fields are derived from explainability output.
    Marked as derived=true, persisted=false to emphasize read-only nature.
    """
    # Feature flags
    sherlock_enabled: bool
    dna_recording_enabled: bool

    # Execution status
    sherlock_ran: bool
    audit_status: str  # "PASS", "FAIL", "NOT_RUN"

    # DNA artifact counts (by primitive type)
    dna_artifact_counts: Dict[str, int]

    # Sample artifacts (tiny list, 3-5 max)
    sample_artifacts: List[Dict[str, Any]]

    # Metadata
    derived: bool = True
    persisted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "sherlock_enabled": self.sherlock_enabled,
            "dna_recording_enabled": self.dna_recording_enabled,
            "sherlock_ran": self.sherlock_ran,
            "audit_status": self.audit_status,
            "dna_artifact_counts": self.dna_artifact_counts,
            "sample_artifacts": self.sample_artifacts,
            "derived": self.derived,
            "persisted": self.persisted,
        }


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_dna_counts(dna_preview_block: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """Extract primitive counts from DNA preview block."""
    if not dna_preview_block:
        return {}

    content = dna_preview_block.get("content", {})
    return content.get("primitive_counts", {})


def _build_sample_artifacts(
    dna_artifact_counts: Dict[str, int],
    audit_status: str,
) -> List[Dict[str, Any]]:
    """
    Build a tiny list of sample artifacts (3-5 max).

    These are synthetic examples based on counts - not real IDs.
    Used to show what WOULD be persisted if persistence was enabled.
    """
    samples = []

    # Add one sample per primitive type that has non-zero count
    for ptype, count in dna_artifact_counts.items():
        if count > 0 and len(samples) < 5:
            samples.append({
                "type": ptype,
                "count": count,
                "example_id": f"{ptype[:3]}-sample-001",
                "derived": True,
                "persisted": False,
            })

    # If no primitives, add a placeholder showing system state
    if not samples:
        samples.append({
            "type": "status",
            "audit_status": audit_status,
            "derived": True,
            "persisted": False,
        })

    return samples


# =============================================================================
# Main Function
# =============================================================================


def derive_proof_summary(
    sherlock_enabled: bool,
    dna_recording_enabled: bool,
    explainability_output: Optional[Dict[str, Any]],
) -> ProofSummary:
    """
    Derive proof summary from explainability output.

    Args:
        sherlock_enabled: Whether SHERLOCK_ENABLED flag is true
        dna_recording_enabled: Whether DNA_RECORDING_ENABLED flag is true
        explainability_output: Dict from transform_sherlock_to_explainability().to_dict()

    Returns:
        ProofSummary with all derived fields
    """
    # Determine execution status
    if not explainability_output:
        # Explainability not generated (Sherlock disabled)
        return ProofSummary(
            sherlock_enabled=sherlock_enabled,
            dna_recording_enabled=dna_recording_enabled,
            sherlock_ran=False,
            audit_status="NOT_RUN",
            dna_artifact_counts={},
            sample_artifacts=[{
                "type": "status",
                "message": "sherlock_disabled",
                "derived": True,
                "persisted": False,
            }],
        )

    if not explainability_output.get("enabled", False):
        # Sherlock was disabled at runtime
        return ProofSummary(
            sherlock_enabled=sherlock_enabled,
            dna_recording_enabled=dna_recording_enabled,
            sherlock_ran=False,
            audit_status="NOT_RUN",
            dna_artifact_counts={},
            sample_artifacts=[{
                "type": "status",
                "message": "sherlock_disabled_at_runtime",
                "derived": True,
                "persisted": False,
            }],
        )

    # Sherlock ran - extract summary
    summary = explainability_output.get("summary", {})
    sherlock_ran = True
    audit_passed = summary.get("audit_passed", False)
    audit_status = "PASS" if audit_passed else "FAIL"

    # Extract DNA counts from blocks
    blocks = explainability_output.get("blocks", [])
    dna_preview_block = None
    for block in blocks:
        if block.get("block_type") == "dna_preview":
            dna_preview_block = block
            break

    dna_artifact_counts = _extract_dna_counts(dna_preview_block)

    # Build sample artifacts
    sample_artifacts = _build_sample_artifacts(dna_artifact_counts, audit_status)

    return ProofSummary(
        sherlock_enabled=sherlock_enabled,
        dna_recording_enabled=dna_recording_enabled,
        sherlock_ran=sherlock_ran,
        audit_status=audit_status,
        dna_artifact_counts=dna_artifact_counts,
        sample_artifacts=sample_artifacts,
    )


def should_show_proof_panel(tier: str, debug_param: bool) -> bool:
    """
    Determine if the proof panel should be visible.

    Args:
        tier: User's tier ("good", "better", "best")
        debug_param: Whether debug=1 query param is present

    Returns:
        True if proof panel should be shown
    """
    return tier.lower() == "best" or debug_param
