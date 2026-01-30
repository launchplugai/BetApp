"""
UI Artifact Contract v1 (Ticket 21)

Validates and normalizes DNA artifacts for UI consumption.
This is the final safety layer before artifacts reach the proof panel.

Design principles:
- Strict on missing required fields (validation fail)
- Tolerant on extra fields (ignored)
- Safe fallback for unknown types (render with generic display)
- Normalize all artifacts to stable UI-safe shape
- No mutation of source artifacts (creates copies)
- No persistence, no network, no side effects

UI Contract defines:
- Required display fields: artifact_type, a display label, a message/text
- Type-specific display fields (severity, status, value, etc.)
- Safe defaults for missing optional fields
"""

from dataclasses import dataclass, field
from typing import Any, Optional


# =============================================================================
# UI Contract Constants
# =============================================================================

# Allowed artifact types for UI display
ALLOWED_UI_TYPES = {"weight", "constraint", "audit_note"}

# Type-specific required fields for display
REQUIRED_DISPLAY_FIELDS = {
    "weight": ["key", "value"],
    "constraint": ["key", "rule", "severity"],
    "audit_note": ["status", "notes"],
}

# Valid severity values
VALID_SEVERITIES = {"info", "warning", "error", "critical"}

# Valid audit status values
VALID_AUDIT_STATUSES = {"PASS", "FAIL"}

# Default values for optional/missing fields
DEFAULT_VALUES = {
    "severity": "info",
    "status": "FAIL",
    "unit": "",
    "rationale": "",
    "notes": [],
    "value": 0.0,
    "key": "unknown",
    "rule": "No rule specified",
}

# UI contract version
UI_CONTRACT_VERSION = "ui_contract_v1"


# =============================================================================
# Validation Result
# =============================================================================


@dataclass
class UIValidationResult:
    """
    Result of UI contract validation.

    Attributes:
        ok: True if all artifacts passed UI validation
        errors: List of validation error messages
        normalized_artifacts: List of normalized artifacts safe for UI
        ui_contract_status: "PASS", "FAIL", or "FALLBACK"
        ui_contract_version: Version of the UI contract used
    """
    ok: bool
    errors: list[str] = field(default_factory=list)
    normalized_artifacts: list[dict[str, Any]] = field(default_factory=list)
    ui_contract_status: str = "PASS"
    ui_contract_version: str = UI_CONTRACT_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "ok": self.ok,
            "errors": self.errors,
            "normalized_artifacts": self.normalized_artifacts,
            "ui_contract_status": self.ui_contract_status,
            "ui_contract_version": self.ui_contract_version,
        }


# =============================================================================
# Normalization Functions
# =============================================================================


def _normalize_weight(artifact: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a weight artifact for UI display.

    Creates a UI-safe copy with stable keys and defaults.
    """
    key = artifact.get("key", DEFAULT_VALUES["key"])
    value = artifact.get("value", DEFAULT_VALUES["value"])
    unit = artifact.get("unit", DEFAULT_VALUES["unit"])
    rationale = artifact.get("rationale", DEFAULT_VALUES["rationale"])

    return {
        "artifact_type": "weight",
        "display_label": f"Weight: {key}",
        "display_text": rationale if rationale else f"{key} = {value}",
        "key": key,
        "value": value,
        "unit": unit,
        "rationale": rationale,
        "ui_safe": True,
    }


def _normalize_constraint(artifact: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a constraint artifact for UI display.

    Creates a UI-safe copy with stable keys and defaults.
    """
    key = artifact.get("key", DEFAULT_VALUES["key"])
    rule = artifact.get("rule", DEFAULT_VALUES["rule"])
    severity = artifact.get("severity", DEFAULT_VALUES["severity"])

    # Validate severity, default if invalid
    if severity not in VALID_SEVERITIES:
        severity = DEFAULT_VALUES["severity"]

    return {
        "artifact_type": "constraint",
        "display_label": f"Constraint: {key}",
        "display_text": rule,
        "key": key,
        "rule": rule,
        "severity": severity,
        "ui_safe": True,
    }


def _normalize_audit_note(artifact: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize an audit_note artifact for UI display.

    Creates a UI-safe copy with stable keys and defaults.
    """
    status = artifact.get("status", DEFAULT_VALUES["status"])
    notes = artifact.get("notes", DEFAULT_VALUES["notes"])

    # Validate status, default if invalid
    if status not in VALID_AUDIT_STATUSES:
        status = DEFAULT_VALUES["status"]

    # Ensure notes is a list
    if not isinstance(notes, list):
        notes = [str(notes)] if notes else []

    # Build display text from notes
    display_text = "; ".join(notes) if notes else f"Audit status: {status}"

    return {
        "artifact_type": "audit_note",
        "display_label": f"Audit: {status}",
        "display_text": display_text,
        "status": status,
        "notes": notes,
        "ui_safe": True,
    }


def _normalize_unknown(artifact: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize an unknown artifact type for safe UI display.

    Creates a generic UI-safe representation that won't crash rendering.
    """
    artifact_type = artifact.get("artifact_type", "unknown")

    return {
        "artifact_type": artifact_type,
        "display_label": f"Unknown: {artifact_type}",
        "display_text": "Artifact type not recognized for display",
        "original_type": artifact_type,
        "ui_safe": True,
        "unknown_type": True,
    }


def _create_fallback_artifact(errors: list[str]) -> dict[str, Any]:
    """
    Create a safe fallback artifact when UI validation fails.

    This ensures the UI always has something safe to display.
    """
    error_summary = "; ".join(errors[:3])  # Limit to first 3 errors
    if len(errors) > 3:
        error_summary += f" (+{len(errors) - 3} more)"

    return {
        "artifact_type": "audit_note",
        "display_label": "Audit: FAIL",
        "display_text": f"UI validation failed: {error_summary}",
        "status": "FAIL",
        "notes": ["UI contract validation failed"],
        "ui_safe": True,
        "is_fallback": True,
    }


# =============================================================================
# Validation Functions
# =============================================================================


def _validate_single_artifact(artifact: Any, index: int) -> tuple[list[str], Optional[dict[str, Any]]]:
    """
    Validate a single artifact against the UI contract.

    Returns:
        Tuple of (errors, normalized_artifact)
        If errors is non-empty, normalized_artifact may be None or a fallback.
    """
    errors: list[str] = []
    prefix = f"Artifact[{index}]: "

    # Must be a dict
    if not isinstance(artifact, dict):
        errors.append(f"{prefix}Expected dict, got {type(artifact).__name__}")
        return errors, None

    # Must have artifact_type
    artifact_type = artifact.get("artifact_type")
    if not artifact_type:
        errors.append(f"{prefix}Missing required field 'artifact_type'")
        return errors, None

    if not isinstance(artifact_type, str):
        errors.append(f"{prefix}Field 'artifact_type' must be string")
        return errors, None

    # Check if known type
    if artifact_type not in ALLOWED_UI_TYPES:
        # Unknown type - normalize as unknown (not an error, just a warning path)
        return [], _normalize_unknown(artifact)

    # Check type-specific required fields
    required_fields = REQUIRED_DISPLAY_FIELDS.get(artifact_type, [])
    for field_name in required_fields:
        if field_name not in artifact:
            errors.append(f"{prefix}Type '{artifact_type}' missing required field '{field_name}'")

    # If any required fields missing, still return errors but try to normalize
    # This allows the UI to show something even with partial data
    if errors:
        return errors, None

    # Normalize based on type
    if artifact_type == "weight":
        return [], _normalize_weight(artifact)
    elif artifact_type == "constraint":
        return [], _normalize_constraint(artifact)
    elif artifact_type == "audit_note":
        return [], _normalize_audit_note(artifact)
    else:
        # Should not reach here due to type check above
        return [], _normalize_unknown(artifact)


# =============================================================================
# Main Validation Function
# =============================================================================


def validate_for_ui(
    artifacts: Optional[list[dict[str, Any]]],
) -> UIValidationResult:
    """
    Validate and normalize artifacts for UI consumption.

    This is the main entry point for UI contract validation.

    Args:
        artifacts: List of DNA artifacts to validate

    Returns:
        UIValidationResult with normalized artifacts safe for UI display

    Behavior:
    - Empty/None artifacts: Returns ok=True with empty list
    - All valid: Returns ok=True with normalized artifacts
    - Any invalid: Returns ok=False with errors, plus a safe fallback artifact
    - Unknown types: Handled gracefully with generic display

    Guarantees:
    - normalized_artifacts is always a valid list (may be empty or contain fallback)
    - UI can always render the result without crashing
    - Extra fields are ignored (not copied to normalized output)
    """
    # Handle None/empty
    if artifacts is None or len(artifacts) == 0:
        return UIValidationResult(
            ok=True,
            errors=[],
            normalized_artifacts=[],
            ui_contract_status="PASS",
        )

    # Validate it's a list
    if not isinstance(artifacts, list):
        return UIValidationResult(
            ok=False,
            errors=["Artifacts must be a list"],
            normalized_artifacts=[_create_fallback_artifact(["Artifacts must be a list"])],
            ui_contract_status="FAIL",
        )

    all_errors: list[str] = []
    normalized: list[dict[str, Any]] = []

    for i, artifact in enumerate(artifacts):
        errors, norm = _validate_single_artifact(artifact, i)
        all_errors.extend(errors)
        if norm is not None:
            normalized.append(norm)

    # Determine result
    if all_errors:
        # Some validation failed - include fallback artifact
        if not normalized:
            normalized = [_create_fallback_artifact(all_errors)]
        return UIValidationResult(
            ok=False,
            errors=all_errors,
            normalized_artifacts=normalized,
            ui_contract_status="FAIL",
        )

    return UIValidationResult(
        ok=True,
        errors=[],
        normalized_artifacts=normalized,
        ui_contract_status="PASS",
    )


def get_ui_contract_version() -> str:
    """Get the UI contract version string."""
    return UI_CONTRACT_VERSION
