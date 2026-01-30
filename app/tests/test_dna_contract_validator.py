"""
DNA Contract Validator Drift Tests.

These tests enforce the DNA contract and will FAIL LOUDLY if:
- Schema changes without explicit approval
- Required fields are missing
- Invariants are violated (derived=true, persisted=false)
- Forbidden fields appear at any depth
- Type mismatches occur

This is a guardrail to prevent drift in DNA artifact structure.
"""

import pytest
from datetime import datetime, timezone

from app.dna.contract_validator import (
    ValidationResult,
    load_contract,
    validate_dna_artifacts,
    get_contract_version,
    create_quarantine_summary,
    create_pass_summary,
    _check_forbidden_fields,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def contract():
    """Load the canonical contract."""
    return load_contract()


@pytest.fixture
def valid_lineage():
    """Valid lineage object for artifacts."""
    return {
        "request_id": "req-123",
        "run_id": "run-456",
        "claim_id": "claim-789",
    }


@pytest.fixture
def valid_weight_artifact(valid_lineage):
    """A minimal valid weight artifact."""
    return {
        "artifact_type": "weight",
        "derived": True,
        "persisted": False,
        "source": "sherlock",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "lineage": valid_lineage,
        "key": "correlation_penalty",
        "value": 0.15,
    }


@pytest.fixture
def valid_constraint_artifact(valid_lineage):
    """A minimal valid constraint artifact."""
    return {
        "artifact_type": "constraint",
        "derived": True,
        "persisted": False,
        "source": "sherlock",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "lineage": valid_lineage,
        "key": "max_legs",
        "rule": "Parlays must have <= 10 legs",
        "severity": "error",
    }


@pytest.fixture
def valid_evidence_artifact(valid_lineage):
    """A minimal valid evidence artifact."""
    return {
        "artifact_type": "evidence",
        "derived": True,
        "persisted": False,
        "source": "sherlock",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "lineage": valid_lineage,
        "summary": "High correlation detected between Lakers and Celtics legs",
        "confidence": 0.85,
        "internal_only": True,
    }


@pytest.fixture
def valid_audit_note_artifact(valid_lineage):
    """A minimal valid audit_note artifact."""
    return {
        "artifact_type": "audit_note",
        "derived": True,
        "persisted": False,
        "source": "sherlock",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "lineage": valid_lineage,
        "status": "PASS",
        "notes": ["All validations passed", "No drift detected"],
    }


@pytest.fixture
def valid_lineage_artifact(valid_lineage):
    """A minimal valid lineage artifact."""
    return {
        "artifact_type": "lineage",
        "derived": True,
        "persisted": False,
        "source": "sherlock",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "lineage": valid_lineage,
        "parent_ids": ["artifact-001", "artifact-002"],
    }


# =============================================================================
# Contract Loading Tests
# =============================================================================


class TestContractLoading:
    """Tests for contract loading and caching."""

    def test_contract_exists(self):
        """Contract file must exist."""
        contract = load_contract()
        assert contract is not None

    def test_contract_has_version(self, contract):
        """Contract must have a version string."""
        assert "contract_version" in contract
        assert contract["contract_version"] == "dna_contract_v1"

    def test_contract_has_allowed_types(self, contract):
        """Contract must define allowed artifact types."""
        assert "allowed_artifact_types" in contract
        types = contract["allowed_artifact_types"]
        assert "weight" in types
        assert "constraint" in types
        assert "lineage" in types
        assert "evidence" in types
        assert "audit_note" in types

    def test_contract_has_required_common_fields(self, contract):
        """Contract must define required common fields."""
        assert "required_common_fields" in contract
        common = contract["required_common_fields"]
        assert "artifact_type" in common
        assert "derived" in common
        assert "persisted" in common
        assert "source" in common
        assert "created_utc" in common
        assert "lineage" in common

    def test_contract_has_forbidden_fields(self, contract):
        """Contract must define forbidden fields."""
        assert "forbidden_fields" in contract
        forbidden = contract["forbidden_fields"]
        assert "pii" in forbidden
        assert "user_email" in forbidden
        assert "ip_address" in forbidden
        assert "raw_prompt" in forbidden

    def test_get_contract_version(self):
        """get_contract_version returns correct version."""
        version = get_contract_version()
        assert version == "dna_contract_v1"


# =============================================================================
# PASS Case Tests
# =============================================================================


class TestPassCases:
    """Tests for valid artifacts that should PASS."""

    def test_valid_weight_artifact_passes(self, valid_weight_artifact):
        """Valid weight artifact passes validation."""
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is True
        assert result.errors == []
        assert result.quarantined is False
        assert result.artifact_count == 1

    def test_valid_constraint_artifact_passes(self, valid_constraint_artifact):
        """Valid constraint artifact passes validation."""
        result = validate_dna_artifacts([valid_constraint_artifact])
        assert result.ok is True
        assert result.errors == []

    def test_valid_evidence_artifact_passes(self, valid_evidence_artifact):
        """Valid evidence artifact passes validation."""
        result = validate_dna_artifacts([valid_evidence_artifact])
        assert result.ok is True
        assert result.errors == []

    def test_valid_audit_note_artifact_passes(self, valid_audit_note_artifact):
        """Valid audit_note artifact passes validation."""
        result = validate_dna_artifacts([valid_audit_note_artifact])
        assert result.ok is True
        assert result.errors == []

    def test_valid_lineage_artifact_passes(self, valid_lineage_artifact):
        """Valid lineage artifact passes validation."""
        result = validate_dna_artifacts([valid_lineage_artifact])
        assert result.ok is True
        assert result.errors == []

    def test_multiple_valid_artifacts_pass(
        self,
        valid_weight_artifact,
        valid_constraint_artifact,
        valid_evidence_artifact,
    ):
        """Multiple valid artifacts all pass."""
        artifacts = [
            valid_weight_artifact,
            valid_constraint_artifact,
            valid_evidence_artifact,
        ]
        result = validate_dna_artifacts(artifacts)
        assert result.ok is True
        assert result.artifact_count == 3

    def test_empty_list_passes(self):
        """Empty artifact list passes validation."""
        result = validate_dna_artifacts([])
        assert result.ok is True
        assert result.artifact_count == 0

    def test_none_passes(self):
        """None artifacts passes validation."""
        result = validate_dna_artifacts(None)
        assert result.ok is True
        assert result.artifact_count == 0

    def test_optional_fields_allowed(self, valid_weight_artifact):
        """Optional fields (unit, rationale) are allowed."""
        valid_weight_artifact["unit"] = "multiplier"
        valid_weight_artifact["rationale"] = "Based on same-game dependency"
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is True


# =============================================================================
# FAIL Case: Missing Required Fields
# =============================================================================


class TestFailMissingFields:
    """Tests that FAIL when required fields are missing."""

    def test_fail_missing_artifact_type(self, valid_weight_artifact):
        """FAIL if artifact_type is missing."""
        del valid_weight_artifact["artifact_type"]
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert result.quarantined is True
        assert any("artifact_type" in e for e in result.errors)

    def test_fail_missing_derived(self, valid_weight_artifact):
        """FAIL if derived is missing."""
        del valid_weight_artifact["derived"]
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("derived" in e for e in result.errors)

    def test_fail_missing_persisted(self, valid_weight_artifact):
        """FAIL if persisted is missing."""
        del valid_weight_artifact["persisted"]
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("persisted" in e for e in result.errors)

    def test_fail_missing_source(self, valid_weight_artifact):
        """FAIL if source is missing."""
        del valid_weight_artifact["source"]
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("source" in e for e in result.errors)

    def test_fail_missing_created_utc(self, valid_weight_artifact):
        """FAIL if created_utc is missing."""
        del valid_weight_artifact["created_utc"]
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("created_utc" in e for e in result.errors)

    def test_fail_missing_lineage(self, valid_weight_artifact):
        """FAIL if lineage is missing."""
        del valid_weight_artifact["lineage"]
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("lineage" in e for e in result.errors)

    def test_fail_missing_lineage_request_id(self, valid_weight_artifact):
        """FAIL if lineage.request_id is missing."""
        del valid_weight_artifact["lineage"]["request_id"]
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("request_id" in e for e in result.errors)

    def test_fail_missing_weight_key(self, valid_weight_artifact):
        """FAIL if weight artifact missing key."""
        del valid_weight_artifact["key"]
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("key" in e for e in result.errors)

    def test_fail_missing_weight_value(self, valid_weight_artifact):
        """FAIL if weight artifact missing value."""
        del valid_weight_artifact["value"]
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("value" in e for e in result.errors)


# =============================================================================
# FAIL Case: Invariant Violations
# =============================================================================


class TestFailInvariantViolations:
    """Tests that FAIL when invariants are violated."""

    def test_fail_derived_not_true(self, valid_weight_artifact):
        """FAIL if derived != true."""
        valid_weight_artifact["derived"] = False
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("derived" in e and "True" in e for e in result.errors)

    def test_fail_persisted_not_false(self, valid_weight_artifact):
        """FAIL if persisted != false."""
        valid_weight_artifact["persisted"] = True
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("persisted" in e and "False" in e for e in result.errors)

    def test_fail_source_not_sherlock(self, valid_weight_artifact):
        """FAIL if source != 'sherlock'."""
        valid_weight_artifact["source"] = "user"
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("source" in e and "sherlock" in e for e in result.errors)

    def test_fail_evidence_internal_only_not_true(self, valid_evidence_artifact):
        """FAIL if evidence.internal_only != true."""
        valid_evidence_artifact["internal_only"] = False
        result = validate_dna_artifacts([valid_evidence_artifact])
        assert result.ok is False
        assert any("internal_only" in e for e in result.errors)


# =============================================================================
# FAIL Case: Unknown Artifact Type
# =============================================================================


class TestFailUnknownType:
    """Tests that FAIL for unknown artifact types."""

    def test_fail_unknown_artifact_type(self, valid_weight_artifact):
        """FAIL if artifact_type is unknown."""
        valid_weight_artifact["artifact_type"] = "super_secret_type"
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("Unknown artifact_type" in e for e in result.errors)

    def test_fail_empty_artifact_type(self, valid_weight_artifact):
        """FAIL if artifact_type is empty string."""
        valid_weight_artifact["artifact_type"] = ""
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False


# =============================================================================
# FAIL Case: Forbidden Fields
# =============================================================================


class TestFailForbiddenFields:
    """Tests that FAIL when forbidden fields are present."""

    def test_fail_forbidden_pii_field(self, valid_weight_artifact):
        """FAIL if 'pii' field is present."""
        valid_weight_artifact["pii"] = "sensitive data"
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("pii" in e.lower() for e in result.errors)

    def test_fail_forbidden_user_email(self, valid_weight_artifact):
        """FAIL if 'user_email' field is present."""
        valid_weight_artifact["user_email"] = "test@example.com"
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("user_email" in e.lower() for e in result.errors)

    def test_fail_forbidden_ip_address(self, valid_weight_artifact):
        """FAIL if 'ip_address' field is present."""
        valid_weight_artifact["ip_address"] = "192.168.1.1"
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("ip_address" in e.lower() for e in result.errors)

    def test_fail_forbidden_raw_prompt(self, valid_weight_artifact):
        """FAIL if 'raw_prompt' field is present."""
        valid_weight_artifact["raw_prompt"] = "User asked about..."
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("raw_prompt" in e.lower() for e in result.errors)

    def test_fail_forbidden_nested_deep(self, valid_weight_artifact):
        """FAIL if forbidden field appears deeply nested."""
        valid_weight_artifact["metadata"] = {
            "level1": {
                "level2": {
                    "user_email": "hidden@example.com"
                }
            }
        }
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("user_email" in e.lower() for e in result.errors)

    def test_fail_forbidden_in_list(self, valid_weight_artifact):
        """FAIL if forbidden field appears in nested list."""
        valid_weight_artifact["items"] = [
            {"name": "item1"},
            {"raw_prompt": "secret"},
        ]
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("raw_prompt" in e.lower() for e in result.errors)

    def test_fail_forbidden_api_key(self, valid_weight_artifact):
        """FAIL if 'api_key' field is present."""
        valid_weight_artifact["api_key"] = "sk-1234"
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("api_key" in e.lower() for e in result.errors)


# =============================================================================
# FAIL Case: Type Mismatches
# =============================================================================


class TestFailTypeMismatches:
    """Tests that FAIL when types don't match."""

    def test_fail_weight_value_not_number(self, valid_weight_artifact):
        """FAIL if weight.value is not a number."""
        valid_weight_artifact["value"] = "not a number"
        result = validate_dna_artifacts([valid_weight_artifact])
        assert result.ok is False
        assert any("number" in e.lower() for e in result.errors)

    def test_fail_evidence_confidence_not_number(self, valid_evidence_artifact):
        """FAIL if evidence.confidence is not a number."""
        valid_evidence_artifact["confidence"] = "high"
        result = validate_dna_artifacts([valid_evidence_artifact])
        assert result.ok is False
        assert any("number" in e.lower() for e in result.errors)

    def test_fail_evidence_confidence_out_of_range_high(self, valid_evidence_artifact):
        """FAIL if evidence.confidence > 1."""
        valid_evidence_artifact["confidence"] = 1.5
        result = validate_dna_artifacts([valid_evidence_artifact])
        assert result.ok is False
        assert any("maximum" in e.lower() for e in result.errors)

    def test_fail_evidence_confidence_out_of_range_low(self, valid_evidence_artifact):
        """FAIL if evidence.confidence < 0."""
        valid_evidence_artifact["confidence"] = -0.1
        result = validate_dna_artifacts([valid_evidence_artifact])
        assert result.ok is False
        assert any("minimum" in e.lower() for e in result.errors)

    def test_fail_audit_status_invalid(self, valid_audit_note_artifact):
        """FAIL if audit_note.status is not PASS or FAIL."""
        valid_audit_note_artifact["status"] = "MAYBE"
        result = validate_dna_artifacts([valid_audit_note_artifact])
        assert result.ok is False
        assert any("PASS" in e or "FAIL" in e for e in result.errors)

    def test_fail_constraint_severity_invalid(self, valid_constraint_artifact):
        """FAIL if constraint.severity is invalid."""
        valid_constraint_artifact["severity"] = "catastrophic"
        result = validate_dna_artifacts([valid_constraint_artifact])
        assert result.ok is False

    def test_fail_lineage_parent_ids_not_array(self, valid_lineage_artifact):
        """FAIL if lineage.parent_ids is not an array."""
        valid_lineage_artifact["parent_ids"] = "not-an-array"
        result = validate_dna_artifacts([valid_lineage_artifact])
        assert result.ok is False
        assert any("array" in e.lower() for e in result.errors)

    def test_fail_artifacts_not_list(self):
        """FAIL if artifacts is not a list."""
        result = validate_dna_artifacts({"not": "a list"})
        assert result.ok is False
        assert any("list" in e.lower() for e in result.errors)


# =============================================================================
# Summary Generation Tests
# =============================================================================


class TestSummaryGeneration:
    """Tests for quarantine and pass summary generation."""

    def test_quarantine_summary_structure(self, valid_weight_artifact):
        """Quarantine summary has correct structure."""
        valid_weight_artifact["derived"] = False  # Make it fail
        result = validate_dna_artifacts([valid_weight_artifact])
        summary = create_quarantine_summary(result)

        assert summary["dna_quarantined"] is True
        assert summary["dna_contract_status"] == "FAIL"
        assert "dna_contract_version" in summary
        assert "dna_contract_errors" in summary
        assert isinstance(summary["dna_contract_errors"], list)

    def test_pass_summary_structure(self, valid_weight_artifact):
        """Pass summary has correct structure."""
        result = validate_dna_artifacts([valid_weight_artifact])
        summary = create_pass_summary(result)

        assert summary["dna_quarantined"] is False
        assert summary["dna_contract_status"] == "PASS"
        assert summary["dna_contract_version"] == "dna_contract_v1"
        assert summary["dna_artifact_count"] == 1

    def test_validation_result_to_dict(self, valid_weight_artifact):
        """ValidationResult.to_dict() works correctly."""
        result = validate_dna_artifacts([valid_weight_artifact])
        d = result.to_dict()

        assert d["ok"] is True
        assert d["errors"] == []
        assert d["contract_version"] == "dna_contract_v1"
        assert d["artifact_count"] == 1
        assert d["quarantined"] is False


# =============================================================================
# Forbidden Field Deep Scan Tests
# =============================================================================


class TestForbiddenFieldDeepScan:
    """Tests for the forbidden field deep scan utility."""

    def test_no_forbidden_fields_found(self):
        """No errors when no forbidden fields."""
        obj = {"name": "test", "value": 123}
        errors = _check_forbidden_fields(obj, ["pii", "secret"])
        assert errors == []

    def test_forbidden_field_at_root(self):
        """Finds forbidden field at root level."""
        obj = {"name": "test", "pii": "sensitive"}
        errors = _check_forbidden_fields(obj, ["pii"])
        assert len(errors) == 1
        assert "pii" in errors[0].lower()

    def test_forbidden_field_nested(self):
        """Finds forbidden field when nested."""
        obj = {"level1": {"level2": {"user_email": "test@test.com"}}}
        errors = _check_forbidden_fields(obj, ["user_email"])
        assert len(errors) == 1
        assert "user_email" in errors[0].lower()

    def test_forbidden_field_in_list(self):
        """Finds forbidden field in list items."""
        obj = {"items": [{"ok": True}, {"password": "secret"}]}
        errors = _check_forbidden_fields(obj, ["password"])
        assert len(errors) == 1
        assert "password" in errors[0].lower()

    def test_partial_match_forbidden(self):
        """Finds partial match of forbidden field."""
        obj = {"my_api_key_here": "sk-123"}
        errors = _check_forbidden_fields(obj, ["api_key"])
        assert len(errors) == 1


# =============================================================================
# Contract Drift Detection Tests
# =============================================================================


class TestContractDriftDetection:
    """
    Tests that will FAIL if the contract schema drifts.

    These are intentionally brittle - they should break if someone
    changes the contract without updating these tests.
    """

    def test_contract_version_is_v1(self):
        """Contract version must be exactly 'dna_contract_v1'."""
        version = get_contract_version()
        assert version == "dna_contract_v1", (
            f"Contract version changed from 'dna_contract_v1' to '{version}'. "
            "This requires explicit approval and test updates."
        )

    def test_exactly_five_artifact_types(self, contract):
        """Contract must have exactly 5 artifact types."""
        types = contract["allowed_artifact_types"]
        assert len(types) == 5, (
            f"Artifact types changed from 5 to {len(types)}. "
            "Adding/removing types requires explicit approval."
        )

    def test_common_fields_count(self, contract):
        """Contract must have exactly 6 common fields."""
        common = contract["required_common_fields"]
        assert len(common) == 6, (
            f"Common fields changed from 6 to {len(common)}. "
            "This requires explicit approval."
        )

    def test_invariant_derived_true(self, contract):
        """Derived field must require True."""
        derived_spec = contract["required_common_fields"]["derived"]
        assert derived_spec["required_value"] is True, (
            "The 'derived' invariant changed. This is NON-NEGOTIABLE."
        )

    def test_invariant_persisted_false(self, contract):
        """Persisted field must require False."""
        persisted_spec = contract["required_common_fields"]["persisted"]
        assert persisted_spec["required_value"] is False, (
            "The 'persisted' invariant changed. This is NON-NEGOTIABLE."
        )

    def test_invariant_source_sherlock(self, contract):
        """Source field must require 'sherlock'."""
        source_spec = contract["required_common_fields"]["source"]
        assert source_spec["required_value"] == "sherlock", (
            "The 'source' invariant changed. This is NON-NEGOTIABLE."
        )
