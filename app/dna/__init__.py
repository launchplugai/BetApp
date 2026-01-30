"""
DNA Contract Validation Module.

Provides validation of DNA artifacts against the canonical contract.
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

__all__ = [
    "ValidationResult",
    "load_contract",
    "validate_dna_artifacts",
    "get_contract_version",
]
