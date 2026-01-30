# app/proof_summary.py
"""
Proof Summary Helper (Ticket 18B, updated Ticket 19, Ticket 21)

Derives a compact proof summary from explainability blocks for UI display.
This is a read-only view - no persistence, no external calls.

Ticket 19 additions:
- DNA contract validation status
- Contract version tracking
- Quarantine status for invalid artifacts

Ticket 21 additions:
- UI contract validation status
- UI contract version tracking
- Normalized artifacts safe for UI display

Contracts referenced:
- docs/contracts/SCH_SDK_CONTRACT.md#section-4-finalreport-schema
- contracts/dna_contract_v1.json
- app/dna/ui_contract_v1.py
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

    # Ticket 19: Contract validation status
    dna_contract_status: str = "NOT_VALIDATED"  # "PASS", "FAIL", "NOT_VALIDATED"
    dna_contract_version: str = "unknown"
    dna_quarantined: bool = False
    dna_contract_errors: List[str] = field(default_factory=list)

    # Ticket 21: UI contract validation status
    ui_contract_status: str = "PASS"  # "PASS", "FAIL"
    ui_contract_version: str = "unknown"

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
            # Ticket 19 fields
            "dna_contract_status": self.dna_contract_status,
            "dna_contract_version": self.dna_contract_version,
            "dna_quarantined": self.dna_quarantined,
            "dna_contract_errors": self.dna_contract_errors,
            # Ticket 21 fields
            "ui_contract_status": self.ui_contract_status,
            "ui_contract_version": self.ui_contract_version,
            # Metadata
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
    contract_validation: Optional[Dict[str, Any]] = None,
    dna_artifacts: Optional[List[Dict[str, Any]]] = None,
    dna_artifact_counts: Optional[Dict[str, int]] = None,
    ui_contract_status: str = "PASS",
    ui_contract_version: str = "unknown",
) -> ProofSummary:
    """
    Derive proof summary from explainability output and real DNA artifacts.

    Args:
        sherlock_enabled: Whether SHERLOCK_ENABLED flag is true
        dna_recording_enabled: Whether DNA_RECORDING_ENABLED flag is true
        explainability_output: Dict from transform_sherlock_to_explainability().to_dict()
        contract_validation: Optional dict from ValidationResult.to_dict() (Ticket 19)
        dna_artifacts: Optional list of real emitted DNA artifacts (Ticket 20)
        dna_artifact_counts: Optional dict of artifact counts by type (Ticket 20)
        ui_contract_status: UI contract validation status (Ticket 21)
        ui_contract_version: UI contract version (Ticket 21)

    Returns:
        ProofSummary with all derived fields
    """
    # Ticket 19: Extract contract validation status
    dna_contract_status = "NOT_VALIDATED"
    dna_contract_version = "unknown"
    dna_quarantined = False
    dna_contract_errors: List[str] = []

    if contract_validation:
        dna_contract_status = "PASS" if contract_validation.get("ok", False) else "FAIL"
        dna_contract_version = contract_validation.get("contract_version", "unknown")
        dna_quarantined = contract_validation.get("quarantined", False)
        dna_contract_errors = contract_validation.get("errors", [])[:10]  # Limit to 10

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
            dna_contract_status=dna_contract_status,
            dna_contract_version=dna_contract_version,
            dna_quarantined=dna_quarantined,
            dna_contract_errors=dna_contract_errors,
            ui_contract_status=ui_contract_status,
            ui_contract_version=ui_contract_version,
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
            dna_contract_status=dna_contract_status,
            dna_contract_version=dna_contract_version,
            dna_quarantined=dna_quarantined,
            dna_contract_errors=dna_contract_errors,
            ui_contract_status=ui_contract_status,
            ui_contract_version=ui_contract_version,
        )

    # Sherlock ran - extract summary
    summary = explainability_output.get("summary", {})
    sherlock_ran = True
    audit_passed = summary.get("audit_passed", False)
    audit_status = "PASS" if audit_passed else "FAIL"

    # Ticket 20: Use real artifacts if provided, otherwise fall back to extraction
    if dna_artifact_counts is not None:
        # Use real artifact counts from emitter
        final_artifact_counts = dna_artifact_counts
    else:
        # Fall back to extracting from explainability blocks
        blocks = explainability_output.get("blocks", [])
        dna_preview_block = None
        for block in blocks:
            if block.get("block_type") == "dna_preview":
                dna_preview_block = block
                break
        final_artifact_counts = _extract_dna_counts(dna_preview_block)

    # Ticket 20: Use real artifacts if provided, otherwise build synthetic samples
    if dna_artifacts is not None and len(dna_artifacts) > 0:
        # Use real artifacts (limit to 5 for display)
        sample_artifacts = dna_artifacts[:5]
    else:
        # Build synthetic sample artifacts
        sample_artifacts = _build_sample_artifacts(final_artifact_counts, audit_status)

    return ProofSummary(
        sherlock_enabled=sherlock_enabled,
        dna_recording_enabled=dna_recording_enabled,
        sherlock_ran=sherlock_ran,
        audit_status=audit_status,
        dna_artifact_counts=final_artifact_counts,
        sample_artifacts=sample_artifacts,
        dna_contract_status=dna_contract_status,
        dna_contract_version=dna_contract_version,
        dna_quarantined=dna_quarantined,
        dna_contract_errors=dna_contract_errors,
        ui_contract_status=ui_contract_status,
        ui_contract_version=ui_contract_version,
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
