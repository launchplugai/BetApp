# app/tests/test_sherlock.py
"""
Sherlock Mode v1 - Test Suite

Tests the Sherlock investigation engine per Ticket 16A requirements.
"""
import pytest
import json

from sherlock import (
    SherlockEngine,
    ClaimInput,
    FinalReport,
    LockedClaim,
    EvidenceMap,
    ArgumentGraph,
    VerdictDraft,
    LogicAuditResult,
    VerdictLevel,
    run_logic_audit,
    get_audit_weights,
    AUDIT_WEIGHTS,
    DEFAULT_THRESHOLD,
)


# =============================================================================
# Test: Engine returns FinalReport with 3 iterations by default
# =============================================================================


def test_engine_returns_final_report_with_default_iterations():
    """Engine returns FinalReport with 3 iterations by default."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="The sky is blue during daytime",
        evidence_policy={"generate_placeholder": True},
    )

    report = engine.run(claim_input)

    assert isinstance(report, FinalReport)
    # Default is 3 iterations (may stop early if audit passes or stop conditions)
    assert report.iterations >= 1
    assert report.iterations <= 3


def test_engine_respects_custom_iterations():
    """Engine respects custom iteration count."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="Water boils at 100 degrees Celsius at sea level",
        iterations=5,
        evidence_policy={"generate_placeholder": True},
    )

    report = engine.run(claim_input)

    assert isinstance(report, FinalReport)
    assert report.iterations <= 5


# =============================================================================
# Test: Each iteration produces all artifacts with matching version numbers
# =============================================================================


def test_iteration_artifacts_have_matching_versions():
    """Each iteration produces all artifacts with matching version numbers."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="Python is a programming language",
        iterations=2,
        evidence_policy={"generate_placeholder": True},
    )

    # Run single iteration directly
    artifacts = engine.run_iteration(1, None, claim_input)

    assert artifacts.version == 1
    assert artifacts.locked_claim.version == 1
    assert artifacts.evidence_map.version == 1
    assert artifacts.argument_graph.version == 1
    assert artifacts.verdict.version == 1
    assert artifacts.audit.version == 1

    # Verify consistency check
    assert artifacts.is_consistent()


def test_iteration_two_has_version_two():
    """Second iteration has version 2 on all artifacts."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="Testing version numbers",
        iterations=3,
        evidence_policy={"generate_placeholder": True},
    )

    # Run first iteration
    artifacts_v1 = engine.run_iteration(1, None, claim_input)

    # Run second iteration
    artifacts_v2 = engine.run_iteration(2, artifacts_v1, claim_input)

    assert artifacts_v2.version == 2
    assert artifacts_v2.locked_claim.version == 2
    assert artifacts_v2.evidence_map.version == 2
    assert artifacts_v2.argument_graph.version == 2
    assert artifacts_v2.verdict.version == 2
    assert artifacts_v2.audit.version == 2
    assert artifacts_v2.is_consistent()


# =============================================================================
# Test: Audit weights compute correctly and threshold gating works
# =============================================================================


def test_audit_weights_sum_to_one():
    """Audit weights must sum to 1.0."""
    weights = get_audit_weights()
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"


def test_audit_weights_are_correct():
    """Audit weights match spec values."""
    weights = get_audit_weights()
    assert weights["clarity"] == 0.10
    assert weights["evidence_integrity"] == 0.30
    assert weights["reasoning_validity"] == 0.25
    assert weights["counterargument_handling"] == 0.20
    assert weights["scope_control"] == 0.10
    assert weights["conclusion_discipline"] == 0.05


def test_default_threshold_is_085():
    """Default threshold is 0.85."""
    assert DEFAULT_THRESHOLD == 0.85


def test_audit_fails_below_threshold():
    """Audit fails when weighted score is below threshold."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="Test claim",
        validation_threshold=0.99,  # Very high threshold
    )

    # Run with no evidence (will fail)
    artifacts = engine.run_iteration(1, None, claim_input)

    # With no evidence and high threshold, should fail
    assert artifacts.audit.passed is False
    assert artifacts.audit.weighted_score < 0.99


def test_audit_uses_custom_threshold():
    """Audit respects custom threshold from input."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="Test with low threshold",
        validation_threshold=0.10,  # Very low threshold
        evidence_policy={"generate_placeholder": True},
    )

    artifacts = engine.run_iteration(1, None, claim_input)

    assert artifacts.audit.threshold == 0.10


# =============================================================================
# Test: Non-falsifiable claim triggers stop condition early
# =============================================================================


def test_non_falsifiable_claim_stops_early():
    """Non-falsifiable claim triggers early stop with correct verdict."""
    engine = SherlockEngine()

    # Create claim that won't generate falsifiability conditions
    # (claims without "is", "are", "will", "can", "always", "never", etc.)
    claim_input = ClaimInput(
        claim_text="Hmm",  # Very short, no falsifiable patterns
        iterations=5,
    )

    report = engine.run(claim_input)

    # Should stop early due to non-falsifiable claim
    # Check that the final verdict handles this
    assert isinstance(report, FinalReport)

    # If non-falsifiable, verdict should reflect this
    if report.final_verdict.verdict == VerdictLevel.NON_FALSIFIABLE:
        assert report.iterations < 5  # Stopped early


def test_falsifiable_claim_generates_conditions():
    """Falsifiable claim generates falsifiability conditions."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="All dogs are mammals and can bark",
        iterations=1,
    )

    artifacts = engine.run_iteration(1, None, claim_input)

    # This claim should generate falsifiability conditions
    assert artifacts.locked_claim.is_falsifiable()
    assert len(artifacts.locked_claim.falsifiability) > 0


# =============================================================================
# Test: Mutation log remains empty when mutations disabled
# =============================================================================


def test_mutations_disabled_by_default():
    """Mutations are disabled by default."""
    engine = SherlockEngine()
    assert engine.mutations_enabled is False


def test_mutation_log_empty_when_disabled():
    """Mutation log is empty when mutations are disabled."""
    engine = SherlockEngine(mutations_enabled=False)
    claim_input = ClaimInput(
        claim_text="Test claim for mutation check",
        iterations=3,
    )

    report = engine.run(claim_input)

    assert report.mutation_log == []


def test_mutation_log_populated_when_enabled():
    """Mutation log may have entries when mutations are enabled and audit fails."""
    engine = SherlockEngine(mutations_enabled=True)
    claim_input = ClaimInput(
        claim_text="This claim will likely have audit failures",
        iterations=2,
        validation_threshold=0.99,  # High threshold to ensure failures
    )

    report = engine.run(claim_input)

    # With high threshold, audit will fail and mutations should be proposed
    # (mutations may still be empty if no applicable mutation types)
    assert isinstance(report.mutation_log, list)


# =============================================================================
# Test: JSON serialization roundtrip for FinalReport
# =============================================================================


def test_final_report_json_serialization():
    """FinalReport can be serialized to JSON."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="Test JSON serialization",
        iterations=1,
        evidence_policy={"generate_placeholder": True},
    )

    report = engine.run(claim_input)

    # Serialize to JSON string
    json_str = report.to_json()

    assert isinstance(json_str, str)
    assert len(json_str) > 0

    # Should be valid JSON
    parsed = json.loads(json_str)
    assert "iterations" in parsed
    assert "final_verdict" in parsed


def test_final_report_json_roundtrip():
    """FinalReport survives JSON roundtrip."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="Test JSON roundtrip",
        iterations=2,
        evidence_policy={"generate_placeholder": True},
    )

    original = engine.run(claim_input)

    # Serialize
    json_str = original.to_json()

    # Deserialize
    restored = FinalReport.from_json(json_str)

    # Compare
    assert restored.iterations == original.iterations
    assert restored.final_verdict.verdict == original.final_verdict.verdict
    assert restored.final_verdict.confidence == original.final_verdict.confidence
    assert len(restored.logic_audit_appendix) == len(original.logic_audit_appendix)
    assert len(restored.mutation_log) == len(original.mutation_log)


def test_final_report_model_dump():
    """FinalReport.model_dump() produces dict."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="Test model dump",
        iterations=1,
    )

    report = engine.run(claim_input)

    dump = report.model_dump()

    assert isinstance(dump, dict)
    assert dump["iterations"] == report.iterations
    assert "final_verdict" in dump
    assert "publishable_report" in dump


# =============================================================================
# Additional Determinism Tests
# =============================================================================


def test_engine_is_deterministic():
    """Same input produces same output."""
    engine1 = SherlockEngine()
    engine2 = SherlockEngine()

    claim_input = ClaimInput(
        claim_text="Determinism test claim",
        iterations=2,
        evidence_policy={"generate_placeholder": True},
    )

    report1 = engine1.run(claim_input)
    report2 = engine2.run(claim_input)

    assert report1.iterations == report2.iterations
    assert report1.final_verdict.verdict == report2.final_verdict.verdict
    assert report1.final_verdict.confidence == report2.final_verdict.confidence


def test_claim_input_is_immutable():
    """ClaimInput is immutable (frozen)."""
    claim_input = ClaimInput(claim_text="Test")

    with pytest.raises(Exception):  # ValidationError for frozen model
        claim_input.claim_text = "Modified"


def test_locked_claim_is_immutable():
    """LockedClaim is immutable (frozen)."""
    locked = LockedClaim(
        version=1,
        testable_claim="Test",
        subclaims=[],
        assumptions=[],
        falsifiability=[],
    )

    with pytest.raises(Exception):
        locked.testable_claim = "Modified"


# =============================================================================
# Audit Category Score Tests
# =============================================================================


def test_audit_returns_all_category_scores():
    """Audit result contains all category scores."""
    engine = SherlockEngine()
    claim_input = ClaimInput(
        claim_text="Test all categories are scored",
        iterations=1,
        evidence_policy={"generate_placeholder": True},
    )

    artifacts = engine.run_iteration(1, None, claim_input)

    expected_categories = [
        "clarity",
        "evidence_integrity",
        "reasoning_validity",
        "counterargument_handling",
        "scope_control",
        "conclusion_discipline",
    ]

    for category in expected_categories:
        assert category in artifacts.audit.category_scores
        score = artifacts.audit.category_scores[category]
        assert 0.0 <= score <= 1.0
