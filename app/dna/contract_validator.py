"""
DNA Contract Validator Module.

Validates DNA artifacts against the canonical contract (contracts/dna_contract_v1.json).
This is the enforcement layer - artifacts that fail validation are quarantined.

Invariants:
- No mutation of artifacts
- No persistence
- No network calls
- Deterministic behavior
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path


@dataclass
class ValidationResult:
    """
    Result of validating DNA artifacts against the contract.

    Attributes:
        ok: True if all artifacts pass validation
        errors: List of validation error messages
        contract_version: Version of contract used for validation
        artifact_count: Number of artifacts validated
        quarantined: True if artifacts should be quarantined (not attached to response)
    """
    ok: bool
    errors: list[str] = field(default_factory=list)
    contract_version: str = "unknown"
    artifact_count: int = 0
    quarantined: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "ok": self.ok,
            "errors": self.errors,
            "contract_version": self.contract_version,
            "artifact_count": self.artifact_count,
            "quarantined": self.quarantined,
        }


# Cache the contract to avoid repeated file reads
_contract_cache: Optional[dict] = None


def _get_contract_path() -> Path:
    """Get the path to the canonical contract file."""
    # Navigate from app/dna to contracts/
    base_dir = Path(__file__).parent.parent.parent
    return base_dir / "contracts" / "dna_contract_v1.json"


def load_contract() -> dict:
    """
    Load the canonical DNA contract.

    Returns cached version if already loaded.
    Raises FileNotFoundError if contract doesn't exist.
    """
    global _contract_cache

    if _contract_cache is not None:
        return _contract_cache

    contract_path = _get_contract_path()
    if not contract_path.exists():
        raise FileNotFoundError(f"DNA contract not found at {contract_path}")

    with open(contract_path, "r") as f:
        _contract_cache = json.load(f)

    return _contract_cache


def get_contract_version() -> str:
    """Get the version string from the contract."""
    try:
        contract = load_contract()
        return contract.get("contract_version", "unknown")
    except FileNotFoundError:
        return "unknown"


def _check_forbidden_fields(obj: Any, forbidden: list[str], path: str = "") -> list[str]:
    """
    Recursively check for forbidden fields in any object.

    Returns list of error messages for any forbidden fields found.
    """
    errors = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = key.lower()
            current_path = f"{path}.{key}" if path else key

            # Check if this key is forbidden
            for forbidden_field in forbidden:
                if forbidden_field.lower() in key_lower:
                    errors.append(f"Forbidden field '{forbidden_field}' found at '{current_path}'")

            # Recurse into value
            errors.extend(_check_forbidden_fields(value, forbidden, current_path))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            current_path = f"{path}[{i}]"
            errors.extend(_check_forbidden_fields(item, forbidden, current_path))

    return errors


def _validate_type(value: Any, expected_type: str, field_name: str) -> Optional[str]:
    """
    Validate that a value matches the expected type.

    Returns error message if validation fails, None if passes.
    """
    type_map = {
        "string": str,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    expected = type_map.get(expected_type)
    if expected is None:
        return None  # Unknown type, skip validation

    if not isinstance(value, expected):
        return f"Field '{field_name}' expected {expected_type}, got {type(value).__name__}"

    return None


def _validate_common_fields(artifact: dict, contract: dict) -> list[str]:
    """
    Validate that an artifact has all required common fields.

    Returns list of error messages.
    """
    errors = []
    required = contract.get("required_common_fields", {})

    for field_name, field_spec in required.items():
        if field_name not in artifact:
            errors.append(f"Missing required common field: '{field_name}'")
            continue

        value = artifact[field_name]

        # Check type
        expected_type = field_spec.get("type")
        if expected_type:
            type_error = _validate_type(value, expected_type, field_name)
            if type_error:
                errors.append(type_error)

        # Check required_value if specified
        required_value = field_spec.get("required_value")
        if required_value is not None and value != required_value:
            errors.append(
                f"Field '{field_name}' must be {required_value}, got {value}"
            )

        # Check nested required_keys for objects
        if field_spec.get("type") == "object" and "required_keys" in field_spec:
            if isinstance(value, dict):
                for key in field_spec["required_keys"]:
                    if key not in value:
                        errors.append(f"Field '{field_name}' missing required key: '{key}'")

    return errors


def _validate_per_type_fields(artifact: dict, contract: dict) -> list[str]:
    """
    Validate per-type required fields for an artifact.

    Returns list of error messages.
    """
    errors = []

    artifact_type = artifact.get("artifact_type")
    if not artifact_type:
        return errors  # Already caught by common field validation

    per_type = contract.get("per_type_required_fields", {})
    type_spec = per_type.get(artifact_type)

    if not type_spec:
        return errors  # No per-type requirements

    for field_name, field_spec in type_spec.items():
        # Skip optional fields
        if field_spec.get("optional"):
            continue

        if field_name not in artifact:
            errors.append(
                f"Artifact type '{artifact_type}' missing required field: '{field_name}'"
            )
            continue

        value = artifact[field_name]

        # Check type
        expected_type = field_spec.get("type")
        if expected_type:
            type_error = _validate_type(value, expected_type, field_name)
            if type_error:
                errors.append(type_error)

        # Check required_value if specified
        required_value = field_spec.get("required_value")
        if required_value is not None and value != required_value:
            errors.append(
                f"Field '{field_name}' must be {required_value}, got {value}"
            )

        # Check allowed_values if specified
        allowed = field_spec.get("allowed_values")
        if allowed and value not in allowed:
            errors.append(
                f"Field '{field_name}' must be one of {allowed}, got '{value}'"
            )

        # Check number bounds
        if expected_type == "number" and isinstance(value, (int, float)):
            min_val = field_spec.get("min")
            max_val = field_spec.get("max")
            if min_val is not None and value < min_val:
                errors.append(f"Field '{field_name}' value {value} below minimum {min_val}")
            if max_val is not None and value > max_val:
                errors.append(f"Field '{field_name}' value {value} above maximum {max_val}")

    return errors


def _validate_single_artifact(artifact: dict, contract: dict, index: int) -> list[str]:
    """
    Validate a single artifact against the contract.

    Returns list of error messages with artifact index prefix.
    """
    errors = []
    prefix = f"Artifact[{index}]: "

    if not isinstance(artifact, dict):
        return [f"{prefix}Expected dict, got {type(artifact).__name__}"]

    # Check artifact_type is allowed
    artifact_type = artifact.get("artifact_type")
    allowed_types = contract.get("allowed_artifact_types", [])
    if artifact_type is not None and artifact_type not in allowed_types:
        errors.append(f"{prefix}Unknown artifact_type '{artifact_type}'")

    # Check common fields
    common_errors = _validate_common_fields(artifact, contract)
    errors.extend(f"{prefix}{e}" for e in common_errors)

    # Check per-type fields
    type_errors = _validate_per_type_fields(artifact, contract)
    errors.extend(f"{prefix}{e}" for e in type_errors)

    # Check forbidden fields (deep scan)
    forbidden = contract.get("forbidden_fields", [])
    forbidden_errors = _check_forbidden_fields(artifact, forbidden)
    errors.extend(f"{prefix}{e}" for e in forbidden_errors)

    return errors


def validate_dna_artifacts(
    artifacts: Optional[list[dict]],
    contract: Optional[dict] = None,
) -> ValidationResult:
    """
    Validate a list of DNA artifacts against the canonical contract.

    Args:
        artifacts: List of artifact dictionaries to validate
        contract: Optional contract dict (loads default if not provided)

    Returns:
        ValidationResult with ok=True if all pass, ok=False with errors if any fail

    This function is:
    - Read-only (does not modify artifacts)
    - Side-effect free (no persistence, no network)
    - Deterministic (same input = same output)
    """
    # Handle None/empty artifacts
    if artifacts is None:
        return ValidationResult(
            ok=True,
            errors=[],
            contract_version=get_contract_version(),
            artifact_count=0,
            quarantined=False,
        )

    if not isinstance(artifacts, list):
        return ValidationResult(
            ok=False,
            errors=["Artifacts must be a list"],
            contract_version=get_contract_version(),
            artifact_count=0,
            quarantined=True,
        )

    if len(artifacts) == 0:
        return ValidationResult(
            ok=True,
            errors=[],
            contract_version=get_contract_version(),
            artifact_count=0,
            quarantined=False,
        )

    # Load contract if not provided
    if contract is None:
        try:
            contract = load_contract()
        except FileNotFoundError as e:
            return ValidationResult(
                ok=False,
                errors=[str(e)],
                contract_version="unknown",
                artifact_count=len(artifacts),
                quarantined=True,
            )

    contract_version = contract.get("contract_version", "unknown")

    # Validate each artifact
    all_errors = []
    for i, artifact in enumerate(artifacts):
        errors = _validate_single_artifact(artifact, contract, i)
        all_errors.extend(errors)

    # Build result
    ok = len(all_errors) == 0
    return ValidationResult(
        ok=ok,
        errors=all_errors,
        contract_version=contract_version,
        artifact_count=len(artifacts),
        quarantined=not ok,  # Quarantine if any errors
    )


def create_quarantine_summary(result: ValidationResult) -> dict:
    """
    Create a quarantine summary for failed validation.

    This is attached to the response when artifacts fail validation.
    """
    return {
        "dna_quarantined": True,
        "dna_contract_status": "FAIL",
        "dna_contract_version": result.contract_version,
        "dna_contract_errors": result.errors[:10],  # Limit to first 10 errors
        "dna_artifact_count": result.artifact_count,
    }


def create_pass_summary(result: ValidationResult) -> dict:
    """
    Create a pass summary for successful validation.

    This is attached alongside valid artifacts.
    """
    return {
        "dna_quarantined": False,
        "dna_contract_status": "PASS",
        "dna_contract_version": result.contract_version,
        "dna_artifact_count": result.artifact_count,
    }
