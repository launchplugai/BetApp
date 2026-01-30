"""
DNA Contract Validation and Artifact Emission Module.

Provides:
- Validation of DNA artifacts against the canonical contract
- Emission of contract-compliant artifacts from evaluation data
- UI contract validation and normalization for proof panel display

All artifacts must comply with contracts/dna_contract_v1.json.

This module is:
- Read-only (no mutations)
- Side-effect free (no persistence, no network)
- Deterministic (same input = same output)
"""

from app.dna.contract_validator import (
    ValidationResult,
    load_contract,
    validate_dna_artifacts,
    get_contract_version,
)

from app.dna.artifact_emitter import (
    EmissionContext,
    emit_artifacts_from_evaluation,
    emit_weight_artifact,
    emit_constraint_artifact,
    emit_audit_note_artifact,
    get_artifact_counts,
)

from app.dna.ui_contract_v1 import (
    UIValidationResult,
    validate_for_ui,
    get_ui_contract_version,
)

__all__ = [
    # Validator (Ticket 19)
    "ValidationResult",
    "load_contract",
    "validate_dna_artifacts",
    "get_contract_version",
    # Emitter (Ticket 20)
    "EmissionContext",
    "emit_artifacts_from_evaluation",
    "emit_weight_artifact",
    "emit_constraint_artifact",
    "emit_audit_note_artifact",
    "get_artifact_counts",
    # UI Contract (Ticket 21)
    "UIValidationResult",
    "validate_for_ui",
    "get_ui_contract_version",
]
