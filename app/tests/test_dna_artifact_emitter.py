# app/tests/test_dna_artifact_emitter.py
"""
Tests for DNA Artifact Emitter (Ticket 20)

Verifies:
- Artifacts are contract-compliant
- Emits 1-3 artifacts per evaluation
- Deterministic: same input = same output
- Invariants: derived=True, persisted=False, source="sherlock"
- No forbidden fields
"""

import pytest
from app.dna.artifact_emitter import (
    EmissionContext,
    emit_artifacts_from_evaluation,
    emit_weight_artifact,
    emit_constraint_artifact,
    emit_audit_note_artifact,
    get_artifact_counts,
)
from app.dna.contract_validator import validate_dna_artifacts


# =============================================================================
# EmissionContext Tests
# =============================================================================


class TestEmissionContext:
    """Tests for EmissionContext creation."""

    def test_create_with_request_id(self):
        """Context with request_id derives deterministic run_id and claim_id."""
        ctx = EmissionContext.create(request_id="test-request-123")

        assert ctx.request_id == "test-request-123"
        assert ctx.run_id.startswith("run-")
        assert ctx.claim_id.startswith("claim-")
        assert len(ctx.run_id) > 4  # Has hash suffix
        assert len(ctx.claim_id) > 6  # Has hash suffix

    def test_create_without_request_id(self):
        """Context without request_id generates a random request_id."""
        ctx = EmissionContext.create()

        assert ctx.request_id is not None
        assert len(ctx.request_id) > 0
        assert ctx.run_id.startswith("run-")
        assert ctx.claim_id.startswith("claim-")

    def test_determinism(self):
        """Same request_id produces same run_id and claim_id."""
        ctx1 = EmissionContext.create(request_id="determinism-test")
        ctx2 = EmissionContext.create(request_id="determinism-test")

        assert ctx1.run_id == ctx2.run_id
        assert ctx1.claim_id == ctx2.claim_id

    def test_different_request_ids_produce_different_hashes(self):
        """Different request_ids produce different derived IDs."""
        ctx1 = EmissionContext.create(request_id="request-A")
        ctx2 = EmissionContext.create(request_id="request-B")

        assert ctx1.run_id != ctx2.run_id
        assert ctx1.claim_id != ctx2.claim_id


# =============================================================================
# Weight Artifact Tests
# =============================================================================


class TestWeightArtifact:
    """Tests for weight artifact emission."""

    def test_emit_weight_basic(self):
        """Basic weight artifact has all required fields."""
        ctx = EmissionContext.create(request_id="weight-test")
        artifact = emit_weight_artifact(
            context=ctx,
            key="correlation_penalty",
            value=1.5,
        )

        assert artifact["artifact_type"] == "weight"
        assert artifact["key"] == "correlation_penalty"
        assert artifact["value"] == 1.5
        assert artifact["derived"] is True
        assert artifact["persisted"] is False
        assert artifact["source"] == "sherlock"
        assert "created_utc" in artifact
        assert "lineage" in artifact
        assert artifact["lineage"]["request_id"] == "weight-test"

    def test_emit_weight_with_optional_fields(self):
        """Weight artifact with optional unit and rationale."""
        ctx = EmissionContext.create(request_id="weight-optional")
        artifact = emit_weight_artifact(
            context=ctx,
            key="leg_penalty",
            value=10.5,
            unit="percent",
            rationale="Penalty for 4-leg parlay",
        )

        assert artifact["unit"] == "percent"
        assert artifact["rationale"] == "Penalty for 4-leg parlay"

    def test_weight_passes_validation(self):
        """Weight artifact passes contract validation."""
        ctx = EmissionContext.create(request_id="weight-validation")
        artifact = emit_weight_artifact(
            context=ctx,
            key="test_weight",
            value=42.0,
        )

        result = validate_dna_artifacts([artifact])
        assert result.ok, f"Validation failed: {result.errors}"


# =============================================================================
# Constraint Artifact Tests
# =============================================================================


class TestConstraintArtifact:
    """Tests for constraint artifact emission."""

    def test_emit_constraint_basic(self):
        """Basic constraint artifact has all required fields."""
        ctx = EmissionContext.create(request_id="constraint-test")
        artifact = emit_constraint_artifact(
            context=ctx,
            key="high_fragility",
            rule="Fragility exceeds safe threshold",
            severity="warning",
        )

        assert artifact["artifact_type"] == "constraint"
        assert artifact["key"] == "high_fragility"
        assert artifact["rule"] == "Fragility exceeds safe threshold"
        assert artifact["severity"] == "warning"
        assert artifact["derived"] is True
        assert artifact["persisted"] is False

    def test_emit_constraint_all_severities(self):
        """Constraint artifact accepts all valid severities."""
        ctx = EmissionContext.create(request_id="severity-test")

        for severity in ["info", "warning", "error", "critical"]:
            artifact = emit_constraint_artifact(
                context=ctx,
                key=f"test_{severity}",
                rule="Test rule",
                severity=severity,
            )
            assert artifact["severity"] == severity

    def test_emit_constraint_invalid_severity_defaults(self):
        """Invalid severity defaults to 'info'."""
        ctx = EmissionContext.create(request_id="invalid-severity")
        artifact = emit_constraint_artifact(
            context=ctx,
            key="test",
            rule="Test rule",
            severity="INVALID",
        )
        assert artifact["severity"] == "info"

    def test_constraint_passes_validation(self):
        """Constraint artifact passes contract validation."""
        ctx = EmissionContext.create(request_id="constraint-validation")
        artifact = emit_constraint_artifact(
            context=ctx,
            key="test_constraint",
            rule="Test rule description",
            severity="warning",
        )

        result = validate_dna_artifacts([artifact])
        assert result.ok, f"Validation failed: {result.errors}"


# =============================================================================
# Audit Note Artifact Tests
# =============================================================================


class TestAuditNoteArtifact:
    """Tests for audit_note artifact emission."""

    def test_emit_audit_note_pass(self):
        """Audit note with PASS status."""
        ctx = EmissionContext.create(request_id="audit-pass")
        artifact = emit_audit_note_artifact(
            context=ctx,
            status="PASS",
            notes=["Evaluation signal: green", "Final fragility: 25.0%"],
        )

        assert artifact["artifact_type"] == "audit_note"
        assert artifact["status"] == "PASS"
        assert len(artifact["notes"]) == 2
        assert artifact["derived"] is True
        assert artifact["persisted"] is False

    def test_emit_audit_note_fail(self):
        """Audit note with FAIL status."""
        ctx = EmissionContext.create(request_id="audit-fail")
        artifact = emit_audit_note_artifact(
            context=ctx,
            status="FAIL",
            notes=["Evaluation signal: red", "Fragility exceeds threshold"],
        )

        assert artifact["status"] == "FAIL"

    def test_emit_audit_note_invalid_status_defaults(self):
        """Invalid status defaults to 'FAIL'."""
        ctx = EmissionContext.create(request_id="invalid-status")
        artifact = emit_audit_note_artifact(
            context=ctx,
            status="INVALID",
            notes=["Test note"],
        )
        assert artifact["status"] == "FAIL"

    def test_audit_note_passes_validation(self):
        """Audit note artifact passes contract validation."""
        ctx = EmissionContext.create(request_id="audit-validation")
        artifact = emit_audit_note_artifact(
            context=ctx,
            status="PASS",
            notes=["Validation test"],
        )

        result = validate_dna_artifacts([artifact])
        assert result.ok, f"Validation failed: {result.errors}"


# =============================================================================
# Main Emission Function Tests
# =============================================================================


class TestEmitArtifactsFromEvaluation:
    """Tests for emit_artifacts_from_evaluation()."""

    def test_emit_low_fragility(self):
        """Low fragility evaluation emits 2 artifacts (weight + audit_note)."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 15.0,
                "correlation_penalty": 0.5,
                "leg_penalty": 5.0,
            },
            signal="green",
            leg_count=2,
            primary_failure_type=None,
            request_id="low-fragility-test",
        )

        assert len(artifacts) == 2  # weight + audit_note (no constraint)
        types = {a["artifact_type"] for a in artifacts}
        assert "weight" in types
        assert "audit_note" in types

    def test_emit_high_fragility(self):
        """High fragility evaluation emits 3 artifacts (weight + constraint + audit_note)."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 75.0,
                "correlation_penalty": 2.0,
                "leg_penalty": 20.0,
            },
            signal="yellow",
            leg_count=4,
            primary_failure_type="correlation",
            request_id="high-fragility-test",
        )

        assert len(artifacts) == 3
        types = {a["artifact_type"] for a in artifacts}
        assert "weight" in types
        assert "constraint" in types
        assert "audit_note" in types

    def test_emit_many_legs(self):
        """Many-leg parlay emits constraint for leg_count_warning."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 40.0,
                "correlation_penalty": 1.0,
                "leg_penalty": 15.0,
            },
            signal="yellow",
            leg_count=8,  # >6 legs
            primary_failure_type=None,
            request_id="many-legs-test",
        )

        constraint = next((a for a in artifacts if a["artifact_type"] == "constraint"), None)
        assert constraint is not None
        assert constraint["key"] == "leg_count_warning"
        assert "8 legs" in constraint["rule"]

    def test_emit_with_primary_failure(self):
        """Primary failure type emits constraint."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 35.0,
                "correlation_penalty": 0.5,
                "leg_penalty": 10.0,
            },
            signal="yellow",
            leg_count=3,
            primary_failure_type="volatility",
            request_id="primary-failure-test",
        )

        constraint = next((a for a in artifacts if a["artifact_type"] == "constraint"), None)
        assert constraint is not None
        assert constraint["key"] == "primary_failure"
        assert "volatility" in constraint["rule"]

    def test_emit_red_signal(self):
        """Red signal produces FAIL audit status."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 85.0,
                "correlation_penalty": 3.0,
                "leg_penalty": 25.0,
            },
            signal="red",
            leg_count=5,
            primary_failure_type="correlation",
            request_id="red-signal-test",
        )

        audit_note = next((a for a in artifacts if a["artifact_type"] == "audit_note"), None)
        assert audit_note is not None
        assert audit_note["status"] == "FAIL"

    def test_all_artifacts_pass_validation(self):
        """All emitted artifacts pass contract validation."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 65.0,
                "correlation_penalty": 1.5,
                "leg_penalty": 15.0,
            },
            signal="yellow",
            leg_count=4,
            primary_failure_type="leg_count",
            request_id="validation-test",
        )

        result = validate_dna_artifacts(artifacts)
        assert result.ok, f"Validation failed: {result.errors}"
        assert result.artifact_count == len(artifacts)

    def test_determinism(self):
        """Same input produces identical artifacts."""
        params = {
            "evaluation_metrics": {
                "final_fragility": 50.0,
                "correlation_penalty": 1.0,
                "leg_penalty": 12.0,
            },
            "signal": "yellow",
            "leg_count": 3,
            "primary_failure_type": "correlation",
            "request_id": "determinism-test-123",
        }

        artifacts1 = emit_artifacts_from_evaluation(**params)
        artifacts2 = emit_artifacts_from_evaluation(**params)

        # Compare types and values (excluding created_utc which varies)
        for a1, a2 in zip(artifacts1, artifacts2):
            assert a1["artifact_type"] == a2["artifact_type"]
            assert a1["lineage"] == a2["lineage"]
            assert a1["derived"] == a2["derived"]
            assert a1["persisted"] == a2["persisted"]

    def test_invariants_always_hold(self):
        """Invariants hold for all emitted artifacts."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 45.0,
                "correlation_penalty": 0.8,
                "leg_penalty": 10.0,
            },
            signal="green",
            leg_count=3,
            primary_failure_type=None,
            request_id="invariants-test",
        )

        for artifact in artifacts:
            assert artifact["derived"] is True, "derived must be True"
            assert artifact["persisted"] is False, "persisted must be False"
            assert artifact["source"] == "sherlock", "source must be sherlock"


# =============================================================================
# Artifact Counts Tests
# =============================================================================


class TestGetArtifactCounts:
    """Tests for get_artifact_counts()."""

    def test_count_by_type(self):
        """Counts artifacts by type."""
        artifacts = [
            {"artifact_type": "weight"},
            {"artifact_type": "weight"},
            {"artifact_type": "constraint"},
            {"artifact_type": "audit_note"},
        ]

        counts = get_artifact_counts(artifacts)

        assert counts["weight"] == 2
        assert counts["constraint"] == 1
        assert counts["audit_note"] == 1

    def test_empty_list(self):
        """Empty artifact list returns empty counts."""
        counts = get_artifact_counts([])
        assert counts == {}

    def test_unknown_type(self):
        """Unknown type is counted as 'unknown'."""
        artifacts = [
            {"artifact_type": "weight"},
            {},  # Missing artifact_type
        ]

        counts = get_artifact_counts(artifacts)

        assert counts["weight"] == 1
        assert counts["unknown"] == 1


# =============================================================================
# Integration Tests
# =============================================================================


class TestEmitterIntegration:
    """Integration tests for the artifact emission pipeline."""

    def test_full_pipeline_low_risk(self):
        """Full pipeline test for low-risk evaluation."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 12.0,
                "correlation_penalty": 0.0,
                "leg_penalty": 3.0,
            },
            signal="blue",
            leg_count=2,
            primary_failure_type=None,
            request_id="pipeline-low-risk",
        )

        # Validate
        result = validate_dna_artifacts(artifacts)
        assert result.ok

        # Check counts
        counts = get_artifact_counts(artifacts)
        assert counts.get("weight", 0) >= 1
        assert counts.get("audit_note", 0) >= 1

    def test_full_pipeline_high_risk(self):
        """Full pipeline test for high-risk evaluation."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 88.0,
                "correlation_penalty": 4.5,
                "leg_penalty": 30.0,
            },
            signal="red",
            leg_count=6,
            primary_failure_type="prop_density",
            request_id="pipeline-high-risk",
        )

        # Validate
        result = validate_dna_artifacts(artifacts)
        assert result.ok

        # Check counts
        counts = get_artifact_counts(artifacts)
        assert sum(counts.values()) >= 2  # At least weight + audit_note

    def test_artifacts_are_human_readable(self):
        """Artifacts contain human-readable content."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 55.0,
                "correlation_penalty": 1.2,
                "leg_penalty": 12.0,
            },
            signal="yellow",
            leg_count=3,
            primary_failure_type="correlation",
            request_id="human-readable-test",
        )

        # Weight should have human-readable rationale
        weight = next((a for a in artifacts if a["artifact_type"] == "weight"), None)
        assert weight is not None
        assert "rationale" in weight
        assert "parlay" in weight["rationale"].lower()

        # Audit note should have readable notes
        audit = next((a for a in artifacts if a["artifact_type"] == "audit_note"), None)
        assert audit is not None
        assert len(audit["notes"]) >= 1
        assert any("signal" in note.lower() for note in audit["notes"])


# =============================================================================
# Ticket 23: Sherlock Advisory Synthesis Tests
# =============================================================================


class TestSherlockAdvisorySynthesis:
    """Tests for Ticket 23 - Sherlock advisory synthesis."""

    def test_low_risk_2_leg_bet_has_nonempty_artifacts(self):
        """For a low-risk 2-leg bet, artifacts list is NON-empty (Ticket 23 DoD)."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 12.0,
                "correlation_penalty": 0.0,
                "leg_penalty": 3.0,
            },
            signal="blue",
            leg_count=2,
            primary_failure_type=None,
            request_id="ticket23-2leg-test",
        )

        # Must have at least 1 artifact
        assert len(artifacts) >= 1
        # Must have audit_note with meaningful content
        audit = next((a for a in artifacts if a["artifact_type"] == "audit_note"), None)
        assert audit is not None
        assert len(audit["notes"]) >= 1
        # First note should be the Sherlock advisory (contains structure check)
        assert "leg" in audit["notes"][0].lower()

    def test_low_risk_3_leg_bet_has_nonempty_artifacts(self):
        """For a normal 3-leg bet, UI shows at least 1 artifact (Ticket 23 DoD)."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 25.0,
                "correlation_penalty": 0.5,
                "leg_penalty": 8.0,
            },
            signal="green",
            leg_count=3,
            primary_failure_type=None,
            request_id="ticket23-3leg-test",
        )

        # Must have at least 1 artifact
        assert len(artifacts) >= 1
        # Must have audit_note
        audit = next((a for a in artifacts if a["artifact_type"] == "audit_note"), None)
        assert audit is not None

    def test_audit_note_contains_sherlock_advisory(self):
        """Audit note contains meaningful Sherlock advisory synthesis."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 30.0,
                "correlation_penalty": 1.0,
                "leg_penalty": 10.0,
            },
            signal="green",
            leg_count=3,
            primary_failure_type=None,
            request_id="sherlock-advisory-test",
        )

        audit = next((a for a in artifacts if a["artifact_type"] == "audit_note"), None)
        assert audit is not None

        # First note should be the Sherlock advisory
        advisory = audit["notes"][0]

        # Advisory should explain what was checked:
        # 1. Structure check
        assert "parlay" in advisory.lower() or "leg" in advisory.lower()
        # 2. Correlation check
        assert "correlation" in advisory.lower()
        # 3. Fragility assessment
        assert "fragility" in advisory.lower()
        # 4. Verdict
        assert "verdict" in advisory.lower()

    def test_sherlock_advisory_includes_primary_failure_explanation(self):
        """Sherlock advisory includes explanation when primary failure exists."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 45.0,
                "correlation_penalty": 2.0,
                "leg_penalty": 12.0,
            },
            signal="yellow",
            leg_count=4,
            primary_failure_type="correlation",
            request_id="primary-failure-advisory-test",
        )

        audit = next((a for a in artifacts if a["artifact_type"] == "audit_note"), None)
        advisory = audit["notes"][0]

        # Should mention primary concern for correlation
        assert "primary concern" in advisory.lower()
        assert "correlation" in advisory.lower() or "independence" in advisory.lower()

    def test_sherlock_advisory_truthful_not_inflated(self):
        """Sherlock advisory is truthful and does not inflate severity."""
        # Low-risk bet
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 10.0,
                "correlation_penalty": 0.0,
                "leg_penalty": 2.0,
            },
            signal="blue",
            leg_count=2,
            primary_failure_type=None,
            request_id="truthful-advisory-test",
        )

        audit = next((a for a in artifacts if a["artifact_type"] == "audit_note"), None)
        advisory = audit["notes"][0]

        # Should NOT contain alarm words for low-risk bet
        assert "high" not in advisory.lower() or "high — significant risk" not in advisory.lower()
        assert "critical" not in advisory.lower()
        # Should contain positive assessment
        assert "low" in advisory.lower() or "strong" in advisory.lower() or "sound" in advisory.lower()

    def test_all_artifacts_pass_contract_validation(self):
        """All artifacts including enhanced audit_note pass contract validation."""
        artifacts = emit_artifacts_from_evaluation(
            evaluation_metrics={
                "final_fragility": 35.0,
                "correlation_penalty": 1.5,
                "leg_penalty": 10.0,
            },
            signal="green",
            leg_count=3,
            primary_failure_type=None,
            request_id="contract-validation-test",
        )

        result = validate_dna_artifacts(artifacts)
        assert result.ok, f"Validation failed: {result.errors}"
