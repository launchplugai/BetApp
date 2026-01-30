# app/tests/test_ui_contract.py
"""
Tests for UI Artifact Contract v1 (Ticket 21)

Verifies:
- UI contract accepts valid artifacts and normalizes defaults
- UI contract rejects missing required keys
- UI contract ignores extra keys
- Pipeline behavior when UI validation fails: returns safe fallback
- Proof panel rendering edge cases (via pipeline integration)
"""

import pytest
from app.dna.ui_contract_v1 import (
    UIValidationResult,
    validate_for_ui,
    get_ui_contract_version,
    UI_CONTRACT_VERSION,
    ALLOWED_UI_TYPES,
    _normalize_weight,
    _normalize_constraint,
    _normalize_audit_note,
    _normalize_unknown,
    _create_fallback_artifact,
)


# =============================================================================
# Tests: UI Contract Version
# =============================================================================


class TestUIContractVersion:
    """Tests for UI contract versioning."""

    def test_get_version(self):
        """get_ui_contract_version returns the correct version."""
        assert get_ui_contract_version() == UI_CONTRACT_VERSION
        assert get_ui_contract_version() == "ui_contract_v1"


# =============================================================================
# Tests: Weight Artifact Normalization
# =============================================================================


class TestNormalizeWeight:
    """Tests for weight artifact normalization."""

    def test_normalize_complete_weight(self):
        """Complete weight artifact normalizes correctly."""
        artifact = {
            "artifact_type": "weight",
            "key": "correlation_penalty",
            "value": 1.5,
            "unit": "multiplier",
            "rationale": "High correlation detected",
        }
        result = _normalize_weight(artifact)

        assert result["artifact_type"] == "weight"
        assert result["key"] == "correlation_penalty"
        assert result["value"] == 1.5
        assert result["unit"] == "multiplier"
        assert result["rationale"] == "High correlation detected"
        assert result["display_label"] == "Weight: correlation_penalty"
        assert result["display_text"] == "High correlation detected"
        assert result["ui_safe"] is True

    def test_normalize_weight_missing_optional_fields(self):
        """Weight with missing optional fields gets defaults."""
        artifact = {
            "artifact_type": "weight",
            "key": "test_key",
            "value": 2.0,
        }
        result = _normalize_weight(artifact)

        assert result["unit"] == ""
        assert result["rationale"] == ""
        assert result["display_text"] == "test_key = 2.0"
        assert result["ui_safe"] is True

    def test_normalize_weight_missing_required_fields_uses_defaults(self):
        """Weight with missing required fields uses defaults."""
        artifact = {"artifact_type": "weight"}
        result = _normalize_weight(artifact)

        assert result["key"] == "unknown"
        assert result["value"] == 0.0
        assert result["ui_safe"] is True


# =============================================================================
# Tests: Constraint Artifact Normalization
# =============================================================================


class TestNormalizeConstraint:
    """Tests for constraint artifact normalization."""

    def test_normalize_complete_constraint(self):
        """Complete constraint artifact normalizes correctly."""
        artifact = {
            "artifact_type": "constraint",
            "key": "high_fragility",
            "rule": "Fragility exceeds 60%",
            "severity": "warning",
        }
        result = _normalize_constraint(artifact)

        assert result["artifact_type"] == "constraint"
        assert result["key"] == "high_fragility"
        assert result["rule"] == "Fragility exceeds 60%"
        assert result["severity"] == "warning"
        assert result["display_label"] == "Constraint: high_fragility"
        assert result["display_text"] == "Fragility exceeds 60%"
        assert result["ui_safe"] is True

    def test_normalize_constraint_invalid_severity_defaults(self):
        """Constraint with invalid severity defaults to 'info'."""
        artifact = {
            "artifact_type": "constraint",
            "key": "test",
            "rule": "Test rule",
            "severity": "INVALID_SEVERITY",
        }
        result = _normalize_constraint(artifact)

        assert result["severity"] == "info"

    def test_normalize_constraint_all_valid_severities(self):
        """Constraint accepts all valid severity values."""
        for severity in ["info", "warning", "error", "critical"]:
            artifact = {
                "artifact_type": "constraint",
                "key": "test",
                "rule": "Test rule",
                "severity": severity,
            }
            result = _normalize_constraint(artifact)
            assert result["severity"] == severity


# =============================================================================
# Tests: Audit Note Artifact Normalization
# =============================================================================


class TestNormalizeAuditNote:
    """Tests for audit_note artifact normalization."""

    def test_normalize_complete_audit_note(self):
        """Complete audit_note artifact normalizes correctly."""
        artifact = {
            "artifact_type": "audit_note",
            "status": "PASS",
            "notes": ["Signal: green", "Fragility: 25%"],
        }
        result = _normalize_audit_note(artifact)

        assert result["artifact_type"] == "audit_note"
        assert result["status"] == "PASS"
        assert result["notes"] == ["Signal: green", "Fragility: 25%"]
        assert result["display_label"] == "Audit: PASS"
        assert result["display_text"] == "Signal: green; Fragility: 25%"
        assert result["ui_safe"] is True

    def test_normalize_audit_note_invalid_status_defaults(self):
        """Audit note with invalid status defaults to 'FAIL'."""
        artifact = {
            "artifact_type": "audit_note",
            "status": "INVALID",
            "notes": [],
        }
        result = _normalize_audit_note(artifact)

        assert result["status"] == "FAIL"

    def test_normalize_audit_note_notes_not_list(self):
        """Audit note with non-list notes gets converted."""
        artifact = {
            "artifact_type": "audit_note",
            "status": "PASS",
            "notes": "single note string",
        }
        result = _normalize_audit_note(artifact)

        assert result["notes"] == ["single note string"]

    def test_normalize_audit_note_empty_notes(self):
        """Audit note with empty notes shows status."""
        artifact = {
            "artifact_type": "audit_note",
            "status": "PASS",
            "notes": [],
        }
        result = _normalize_audit_note(artifact)

        assert result["display_text"] == "Audit status: PASS"


# =============================================================================
# Tests: Unknown Artifact Normalization
# =============================================================================


class TestNormalizeUnknown:
    """Tests for unknown artifact type normalization."""

    def test_normalize_unknown_type(self):
        """Unknown artifact type normalizes to safe display."""
        artifact = {
            "artifact_type": "future_type",
            "some_field": "some_value",
        }
        result = _normalize_unknown(artifact)

        assert result["artifact_type"] == "future_type"
        assert result["original_type"] == "future_type"
        assert result["display_label"] == "Unknown: future_type"
        assert result["display_text"] == "Artifact type not recognized for display"
        assert result["ui_safe"] is True
        assert result["unknown_type"] is True

    def test_normalize_missing_artifact_type(self):
        """Artifact without type gets 'unknown' type."""
        artifact = {"some_field": "some_value"}
        result = _normalize_unknown(artifact)

        assert result["artifact_type"] == "unknown"
        assert result["unknown_type"] is True


# =============================================================================
# Tests: Fallback Artifact Creation
# =============================================================================


class TestCreateFallbackArtifact:
    """Tests for fallback artifact creation."""

    def test_create_fallback_with_errors(self):
        """Fallback artifact includes error summary."""
        errors = ["Error 1", "Error 2", "Error 3"]
        result = _create_fallback_artifact(errors)

        assert result["artifact_type"] == "audit_note"
        assert result["status"] == "FAIL"
        assert result["is_fallback"] is True
        assert result["ui_safe"] is True
        assert "Error 1" in result["display_text"]

    def test_create_fallback_truncates_many_errors(self):
        """Fallback with many errors truncates."""
        errors = ["Error 1", "Error 2", "Error 3", "Error 4", "Error 5"]
        result = _create_fallback_artifact(errors)

        assert "(+2 more)" in result["display_text"]


# =============================================================================
# Tests: Main Validation Function
# =============================================================================


class TestValidateForUI:
    """Tests for the main validate_for_ui function."""

    def test_validate_none_artifacts(self):
        """None artifacts returns ok with empty list."""
        result = validate_for_ui(None)

        assert result.ok is True
        assert result.normalized_artifacts == []
        assert result.ui_contract_status == "PASS"
        assert result.ui_contract_version == UI_CONTRACT_VERSION

    def test_validate_empty_list(self):
        """Empty list returns ok with empty list."""
        result = validate_for_ui([])

        assert result.ok is True
        assert result.normalized_artifacts == []
        assert result.ui_contract_status == "PASS"

    def test_validate_not_a_list(self):
        """Non-list artifacts returns fail with fallback."""
        result = validate_for_ui("not a list")

        assert result.ok is False
        assert len(result.normalized_artifacts) == 1
        assert result.normalized_artifacts[0]["is_fallback"] is True
        assert result.ui_contract_status == "FAIL"

    def test_validate_valid_weight(self):
        """Valid weight artifact passes validation."""
        artifacts = [{
            "artifact_type": "weight",
            "key": "test_key",
            "value": 1.0,
        }]
        result = validate_for_ui(artifacts)

        assert result.ok is True
        assert len(result.normalized_artifacts) == 1
        assert result.normalized_artifacts[0]["artifact_type"] == "weight"
        assert result.normalized_artifacts[0]["ui_safe"] is True

    def test_validate_valid_constraint(self):
        """Valid constraint artifact passes validation."""
        artifacts = [{
            "artifact_type": "constraint",
            "key": "test_key",
            "rule": "Test rule",
            "severity": "warning",
        }]
        result = validate_for_ui(artifacts)

        assert result.ok is True
        assert len(result.normalized_artifacts) == 1
        assert result.normalized_artifacts[0]["artifact_type"] == "constraint"

    def test_validate_valid_audit_note(self):
        """Valid audit_note artifact passes validation."""
        artifacts = [{
            "artifact_type": "audit_note",
            "status": "PASS",
            "notes": ["Test note"],
        }]
        result = validate_for_ui(artifacts)

        assert result.ok is True
        assert len(result.normalized_artifacts) == 1
        assert result.normalized_artifacts[0]["artifact_type"] == "audit_note"

    def test_validate_unknown_type_handled_gracefully(self):
        """Unknown artifact type is handled gracefully."""
        artifacts = [{
            "artifact_type": "future_type",
            "some_field": "value",
        }]
        result = validate_for_ui(artifacts)

        assert result.ok is True  # Unknown types are not errors
        assert len(result.normalized_artifacts) == 1
        assert result.normalized_artifacts[0]["unknown_type"] is True

    def test_validate_missing_artifact_type(self):
        """Missing artifact_type returns fail."""
        artifacts = [{"key": "value"}]
        result = validate_for_ui(artifacts)

        assert result.ok is False
        assert "artifact_type" in result.errors[0].lower()
        assert result.ui_contract_status == "FAIL"

    def test_validate_missing_required_field_for_type(self):
        """Missing required field for type returns fail."""
        artifacts = [{
            "artifact_type": "weight",
            # Missing 'key' and 'value'
        }]
        result = validate_for_ui(artifacts)

        assert result.ok is False
        assert any("key" in e for e in result.errors)
        assert result.ui_contract_status == "FAIL"

    def test_validate_extra_fields_ignored(self):
        """Extra fields are ignored (not copied)."""
        artifacts = [{
            "artifact_type": "weight",
            "key": "test",
            "value": 1.0,
            "extra_field": "should be ignored",
            "another_extra": 123,
        }]
        result = validate_for_ui(artifacts)

        assert result.ok is True
        assert "extra_field" not in result.normalized_artifacts[0]
        assert "another_extra" not in result.normalized_artifacts[0]

    def test_validate_mixed_valid_and_unknown(self):
        """Mix of valid and unknown types all pass."""
        artifacts = [
            {"artifact_type": "weight", "key": "k", "value": 1.0},
            {"artifact_type": "unknown_future_type"},
        ]
        result = validate_for_ui(artifacts)

        assert result.ok is True
        assert len(result.normalized_artifacts) == 2

    def test_validate_malformed_artifact_in_list(self):
        """Malformed (non-dict) artifact in list fails."""
        artifacts = [
            {"artifact_type": "weight", "key": "k", "value": 1.0},
            "not a dict",
        ]
        result = validate_for_ui(artifacts)

        assert result.ok is False
        assert len(result.normalized_artifacts) >= 1  # First valid one kept

    def test_validate_multiple_valid_artifacts(self):
        """Multiple valid artifacts all normalize."""
        artifacts = [
            {"artifact_type": "weight", "key": "k1", "value": 1.0},
            {"artifact_type": "constraint", "key": "k2", "rule": "r", "severity": "info"},
            {"artifact_type": "audit_note", "status": "PASS", "notes": []},
        ]
        result = validate_for_ui(artifacts)

        assert result.ok is True
        assert len(result.normalized_artifacts) == 3


# =============================================================================
# Tests: UIValidationResult
# =============================================================================


class TestUIValidationResult:
    """Tests for UIValidationResult dataclass."""

    def test_to_dict(self):
        """to_dict produces correct structure."""
        result = UIValidationResult(
            ok=True,
            errors=[],
            normalized_artifacts=[{"type": "test"}],
            ui_contract_status="PASS",
            ui_contract_version="ui_contract_v1",
        )
        d = result.to_dict()

        assert d["ok"] is True
        assert d["errors"] == []
        assert d["normalized_artifacts"] == [{"type": "test"}]
        assert d["ui_contract_status"] == "PASS"
        assert d["ui_contract_version"] == "ui_contract_v1"


# =============================================================================
# Tests: Pipeline Integration
# =============================================================================


class TestPipelineUIContractIntegration:
    """Tests for UI contract integration in pipeline."""

    def test_pipeline_includes_ui_contract_status(self):
        """Pipeline response includes UI contract status."""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {
            "SHERLOCK_ENABLED": "true",
            "DNA_RECORDING_ENABLED": "true",
        }):
            import importlib
            import app.config
            importlib.reload(app.config)

            import app.pipeline
            importlib.reload(app.pipeline)

            from app.pipeline import run_evaluation
            from app.airlock import NormalizedInput, Tier

            test_input = NormalizedInput(
                input_text="Lakers -5.5",
                tier=Tier.BEST,
            )

            result = run_evaluation(test_input)

            # proof_summary should include UI contract fields
            assert result.proof_summary is not None
            assert "ui_contract_status" in result.proof_summary
            assert "ui_contract_version" in result.proof_summary
            assert result.proof_summary["ui_contract_status"] in ["PASS", "FAIL"]

    def test_pipeline_safe_artifacts_for_display(self):
        """Pipeline provides safe artifacts for display."""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {
            "SHERLOCK_ENABLED": "true",
            "DNA_RECORDING_ENABLED": "true",
        }):
            import importlib
            import app.config
            importlib.reload(app.config)

            import app.pipeline
            importlib.reload(app.pipeline)

            from app.pipeline import run_evaluation
            from app.airlock import NormalizedInput, Tier

            test_input = NormalizedInput(
                input_text="Lakers -5.5 + Celtics ML",
                tier=Tier.BEST,
            )

            result = run_evaluation(test_input)

            # Sample artifacts should be UI-safe
            artifacts = result.proof_summary.get("sample_artifacts", [])
            for artifact in artifacts:
                # All artifacts should have ui_safe or be synthetic
                if artifact.get("artifact_type") in ALLOWED_UI_TYPES:
                    assert artifact.get("ui_safe") is True


# =============================================================================
# Tests: Proof Panel Rendering Safety
# =============================================================================


class TestProofPanelRenderingSafety:
    """Tests for proof panel rendering safety."""

    def test_empty_artifacts_render_safely(self):
        """Empty artifacts should be handled."""
        result = validate_for_ui([])
        assert result.ok is True
        assert len(result.normalized_artifacts) == 0
        # UI code should handle empty list gracefully

    def test_unknown_type_has_display_fields(self):
        """Unknown type artifacts have required display fields."""
        artifacts = [{"artifact_type": "future_unknown_type"}]
        result = validate_for_ui(artifacts)

        norm = result.normalized_artifacts[0]
        assert "display_label" in norm
        assert "display_text" in norm
        assert norm["ui_safe"] is True

    def test_fallback_has_display_fields(self):
        """Fallback artifact has required display fields."""
        fallback = _create_fallback_artifact(["Test error"])

        assert "display_label" in fallback
        assert "display_text" in fallback
        assert "artifact_type" in fallback
        assert fallback["ui_safe"] is True

    def test_all_normalized_artifacts_have_display_fields(self):
        """All normalized artifacts have required display fields."""
        artifacts = [
            {"artifact_type": "weight", "key": "k", "value": 1.0},
            {"artifact_type": "constraint", "key": "k", "rule": "r", "severity": "info"},
            {"artifact_type": "audit_note", "status": "PASS", "notes": []},
            {"artifact_type": "unknown_type"},
        ]
        result = validate_for_ui(artifacts)

        for norm in result.normalized_artifacts:
            assert "artifact_type" in norm
            assert "display_label" in norm
            assert "display_text" in norm
            assert "ui_safe" in norm
