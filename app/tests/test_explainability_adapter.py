# app/tests/test_explainability_adapter.py
"""
Tests for Sherlock Explainability Adapter (Ticket 18)

Tests the transformation of Sherlock output into Explainability Blocks.
"""
import pytest
from datetime import datetime, timezone

from app.explainability_adapter import (
    BlockType,
    ExplainabilityBlock,
    ExplainabilityOutput,
    transform_sherlock_to_explainability,
    attach_explainability_to_debug,
    _build_investigation_summary_block,
    _build_claim_block,
    _build_verdict_block,
    _build_audit_block,
    _build_dna_preview_block,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def minimal_sherlock_result():
    """Minimal Sherlock result with required fields."""
    return {
        "enabled": True,
        "claim_text": "This 3-leg parlay is highly fragile",
        "iterations_completed": 2,
        "verdict": "likely_true",
        "confidence": 0.75,
        "audit_passed": True,
        "audit_score": 0.88,
        "dna_artifact": None,
    }


@pytest.fixture
def full_sherlock_result():
    """Full Sherlock result with DNA artifact."""
    return {
        "enabled": True,
        "claim_text": "This 4-leg parlay has moderate complexity because correlated outcomes amplify risk",
        "iterations_completed": 3,
        "verdict": "likely_true",
        "confidence": 0.78,
        "audit_passed": True,
        "audit_score": 0.91,
        "dna_artifact": {
            "created_at": "2026-01-29T10:00:00+00:00",
            "sherlock_report_id": "rpt-123",
            "audit_passed": True,
            "audit_score": 0.91,
            "quarantined": False,
            "primitives": {
                "weights": [{"id": "w1"}, {"id": "w2"}],
                "constraints": [{"id": "c1"}],
                "conflicts": [],
                "baseline": {"id": "b1"},
                "drifts": [],
                "tradeoffs": [{"id": "t1"}],
                "lineage": [{"id": "l1"}],
            },
        },
    }


@pytest.fixture
def failed_audit_sherlock_result():
    """Sherlock result with failed audit."""
    return {
        "enabled": True,
        "claim_text": "This parlay is structurally sound",
        "iterations_completed": 3,
        "verdict": "unclear",
        "confidence": 0.45,
        "audit_passed": False,
        "audit_score": 0.72,
        "dna_artifact": {
            "created_at": "2026-01-29T10:00:00+00:00",
            "sherlock_report_id": "rpt-456",
            "audit_passed": False,
            "audit_score": 0.72,
            "quarantined": True,
            "primitives": {
                "weights": [{"id": "w1"}],
                "constraints": [],
                "conflicts": [],
                "baseline": None,
                "drifts": [{"id": "d1"}],
                "tradeoffs": [],
                "lineage": [{"id": "l1"}],
            },
        },
    }


@pytest.fixture
def disabled_sherlock_result():
    """Sherlock result when Sherlock was disabled."""
    return {
        "enabled": False,
        "claim_text": "",
        "iterations_completed": 0,
        "verdict": "unknown",
        "confidence": 0.0,
        "audit_passed": False,
        "audit_score": 0.0,
        "dna_artifact": None,
    }


# =============================================================================
# Tests: transform_sherlock_to_explainability
# =============================================================================


class TestTransformSherlockToExplainability:
    """Tests for main transform function."""

    def test_none_input_returns_none(self):
        """When input is None, output should be None."""
        result = transform_sherlock_to_explainability(None)
        assert result is None

    def test_disabled_sherlock_returns_disabled_output(self, disabled_sherlock_result):
        """When Sherlock was disabled, returns output with enabled=False."""
        result = transform_sherlock_to_explainability(disabled_sherlock_result)

        assert result is not None
        assert result.enabled is False
        assert len(result.blocks) == 0
        assert result.summary["reason"] == "sherlock_disabled"
        assert result.generated_at is not None

    def test_minimal_result_produces_four_blocks(self, minimal_sherlock_result):
        """Minimal result without DNA produces 4 blocks."""
        result = transform_sherlock_to_explainability(minimal_sherlock_result)

        assert result is not None
        assert result.enabled is True
        assert len(result.blocks) == 4

        # Verify block types
        block_types = [b.block_type for b in result.blocks]
        assert BlockType.INVESTIGATION_SUMMARY in block_types
        assert BlockType.CLAIM in block_types
        assert BlockType.VERDICT in block_types
        assert BlockType.AUDIT in block_types
        assert BlockType.DNA_PREVIEW not in block_types

    def test_full_result_produces_five_blocks(self, full_sherlock_result):
        """Full result with DNA produces 5 blocks."""
        result = transform_sherlock_to_explainability(full_sherlock_result)

        assert result is not None
        assert result.enabled is True
        assert len(result.blocks) == 5

        # Verify DNA preview block is included
        block_types = [b.block_type for b in result.blocks]
        assert BlockType.DNA_PREVIEW in block_types

    def test_blocks_have_sequential_ordering(self, full_sherlock_result):
        """Blocks should have sequential sequence numbers."""
        result = transform_sherlock_to_explainability(full_sherlock_result)

        sequences = [b.sequence for b in result.blocks]
        assert sequences == [0, 1, 2, 3, 4]

    def test_summary_contains_key_fields(self, full_sherlock_result):
        """Summary should contain verdict, confidence, audit status."""
        result = transform_sherlock_to_explainability(full_sherlock_result)

        assert result.summary["verdict"] == "likely_true"
        assert result.summary["confidence"] == 0.78
        assert result.summary["audit_passed"] is True
        assert result.summary["iterations"] == 3
        assert result.summary["has_dna_preview"] is True

    def test_to_dict_serialization(self, minimal_sherlock_result):
        """ExplainabilityOutput.to_dict() should produce valid dict."""
        result = transform_sherlock_to_explainability(minimal_sherlock_result)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["enabled"] is True
        assert result_dict["block_count"] == 4
        assert isinstance(result_dict["blocks"], list)
        assert all(isinstance(b, dict) for b in result_dict["blocks"])


# =============================================================================
# Tests: Individual Block Builders
# =============================================================================


class TestInvestigationSummaryBlock:
    """Tests for investigation summary block builder."""

    def test_builds_correct_structure(self, minimal_sherlock_result):
        """Block should have correct type and content."""
        block = _build_investigation_summary_block(minimal_sherlock_result, 0)

        assert block.block_type == BlockType.INVESTIGATION_SUMMARY
        assert block.title == "Investigation Overview"
        assert block.content["claim_text"] == "This 3-leg parlay is highly fragile"
        assert block.content["iterations_completed"] == 2
        assert block.content["verdict"] == "likely_true"
        assert block.content["confidence"] == 0.75
        assert block.content["audit_passed"] is True

    def test_metadata_contains_audit_score(self, minimal_sherlock_result):
        """Metadata should contain audit score."""
        block = _build_investigation_summary_block(minimal_sherlock_result, 0)

        assert block.metadata["audit_score"] == 0.88


class TestClaimBlock:
    """Tests for claim block builder."""

    def test_builds_correct_structure(self, minimal_sherlock_result):
        """Block should have correct type and content."""
        block = _build_claim_block(minimal_sherlock_result, 1)

        assert block.block_type == BlockType.CLAIM
        assert block.title == "Investigated Claim"
        assert block.content["claim_text"] == "This 3-leg parlay is highly fragile"
        assert '"This 3-leg parlay is highly fragile"' in block.content["formatted"]

    def test_empty_claim_produces_fallback(self):
        """Empty claim should produce fallback text."""
        result = {"claim_text": ""}
        block = _build_claim_block(result, 1)

        assert block.content["formatted"] == "(no claim)"


class TestVerdictBlock:
    """Tests for verdict block builder."""

    def test_builds_correct_structure(self, minimal_sherlock_result):
        """Block should have correct type and content."""
        block = _build_verdict_block(minimal_sherlock_result, 2)

        assert block.block_type == BlockType.VERDICT
        assert block.title == "Investigation Verdict"
        assert block.content["verdict"] == "likely_true"
        assert block.content["verdict_label"] == "Likely True"
        assert block.content["confidence"] == 0.75
        assert block.content["confidence_percent"] == "75%"

    def test_color_hints_for_verdicts(self):
        """Different verdicts should have appropriate color hints."""
        verdict_colors = {
            "true": "green",
            "likely_true": "light_green",
            "unclear": "yellow",
            "likely_false": "orange",
            "false": "red",
            "non_falsifiable": "gray",
            "error": "red",
        }

        for verdict, expected_color in verdict_colors.items():
            result = {"verdict": verdict, "confidence": 0.5}
            block = _build_verdict_block(result, 0)
            assert block.metadata["color_hint"] == expected_color, f"Failed for verdict: {verdict}"


class TestAuditBlock:
    """Tests for audit block builder."""

    def test_passed_audit_structure(self, minimal_sherlock_result):
        """Passed audit should have correct structure and color hint."""
        block = _build_audit_block(minimal_sherlock_result, 3)

        assert block.block_type == BlockType.AUDIT
        assert block.title == "Logic Audit"
        assert block.content["passed"] is True
        assert block.content["passed_label"] == "Passed"
        assert block.content["weighted_score"] == 0.88
        assert block.content["score_percent"] == "88%"
        assert block.metadata["color_hint"] == "green"

    def test_failed_audit_structure(self, failed_audit_sherlock_result):
        """Failed audit should have correct structure and color hint."""
        block = _build_audit_block(failed_audit_sherlock_result, 3)

        assert block.content["passed"] is False
        assert block.content["passed_label"] == "Failed"
        assert block.metadata["color_hint"] == "red"


class TestDNAPreviewBlock:
    """Tests for DNA preview block builder."""

    def test_active_dna_structure(self, full_sherlock_result):
        """Active DNA (audit passed) should have correct structure."""
        dna_artifact = full_sherlock_result["dna_artifact"]
        block = _build_dna_preview_block(dna_artifact, 4)

        assert block.block_type == BlockType.DNA_PREVIEW
        assert block.title == "DNA Matrix Preview"
        assert block.content["quarantined"] is False
        assert block.content["quarantine_label"] == "Active"
        assert block.content["audit_passed"] is True

        # Verify primitive counts
        counts = block.content["primitive_counts"]
        assert counts["weights"] == 2
        assert counts["constraints"] == 1
        assert counts["conflicts"] == 0
        assert counts["baseline"] == 1
        assert counts["drifts"] == 0
        assert counts["tradeoffs"] == 1
        assert counts["lineage"] == 1
        assert block.content["total_primitives"] == 6

    def test_quarantined_dna_structure(self, failed_audit_sherlock_result):
        """Quarantined DNA (audit failed) should have correct structure."""
        dna_artifact = failed_audit_sherlock_result["dna_artifact"]
        block = _build_dna_preview_block(dna_artifact, 4)

        assert block.content["quarantined"] is True
        assert block.content["quarantine_label"] == "Quarantined"
        assert block.content["audit_passed"] is False

        # Verify baseline is 0 (not created for failed audit)
        counts = block.content["primitive_counts"]
        assert counts["baseline"] == 0
        assert counts["drifts"] == 1

    def test_metadata_contains_report_id(self, full_sherlock_result):
        """Metadata should contain sherlock_report_id and preview flag."""
        dna_artifact = full_sherlock_result["dna_artifact"]
        block = _build_dna_preview_block(dna_artifact, 4)

        assert block.metadata["sherlock_report_id"] == "rpt-123"
        assert block.metadata["preview_only"] is True


# =============================================================================
# Tests: ExplainabilityBlock Dataclass
# =============================================================================


class TestExplainabilityBlock:
    """Tests for ExplainabilityBlock dataclass."""

    def test_to_dict_serialization(self):
        """Block.to_dict() should produce correct dict structure."""
        block = ExplainabilityBlock(
            block_type=BlockType.CLAIM,
            title="Test Title",
            content={"key": "value"},
            metadata={"meta_key": "meta_value"},
            sequence=5,
        )
        result = block.to_dict()

        assert result["block_type"] == "claim"
        assert result["title"] == "Test Title"
        assert result["content"] == {"key": "value"}
        assert result["metadata"] == {"meta_key": "meta_value"}
        assert result["sequence"] == 5

    def test_frozen_immutability(self):
        """Block should be immutable (frozen dataclass)."""
        block = ExplainabilityBlock(
            block_type=BlockType.CLAIM,
            title="Test",
            content={},
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            block.title = "Modified"


# =============================================================================
# Tests: Helper Functions
# =============================================================================


class TestAttachExplainabilityToDebug:
    """Tests for attach_explainability_to_debug helper."""

    def test_attaches_explainability_to_debug_dict(self, minimal_sherlock_result):
        """Should add explainability key to debug dict."""
        debug_dict = {"existing_key": "existing_value"}
        result = attach_explainability_to_debug(debug_dict, minimal_sherlock_result)

        assert "explainability" in result
        assert result["existing_key"] == "existing_value"
        assert result["explainability"]["enabled"] is True

    def test_handles_none_sherlock_result(self):
        """Should handle None sherlock result gracefully."""
        debug_dict = {"key": "value"}
        result = attach_explainability_to_debug(debug_dict, None)

        assert result["explainability"] is None

    def test_returns_same_dict_object(self, minimal_sherlock_result):
        """Should modify and return the same dict object."""
        debug_dict = {"key": "value"}
        result = attach_explainability_to_debug(debug_dict, minimal_sherlock_result)

        assert result is debug_dict


# =============================================================================
# Tests: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_missing_fields_use_defaults(self):
        """Missing fields should use sensible defaults."""
        incomplete_result = {
            "enabled": True,
            # Missing all other fields
        }
        result = transform_sherlock_to_explainability(incomplete_result)

        assert result is not None
        assert result.enabled is True

        # Verify blocks handle missing data
        summary_block = result.blocks[0]
        assert summary_block.content["claim_text"] == ""
        assert summary_block.content["iterations_completed"] == 0
        assert summary_block.content["verdict"] == "unknown"

    def test_unknown_verdict_produces_fallback_display(self):
        """Unknown verdict type should produce reasonable fallback."""
        result = {"verdict": "some_new_verdict", "confidence": 0.5}
        block = _build_verdict_block(result, 0)

        assert block.content["verdict_label"] == "Some_New_Verdict"
        assert block.metadata["color_hint"] == "gray"

    def test_empty_dna_primitives(self):
        """Empty primitives dict should produce zero counts."""
        dna_artifact = {
            "quarantined": True,
            "audit_passed": False,
            "audit_score": 0.5,
            "sherlock_report_id": "rpt-empty",
            "created_at": "2026-01-29T10:00:00+00:00",
            "primitives": {},
        }
        block = _build_dna_preview_block(dna_artifact, 0)

        assert block.content["total_primitives"] == 0
        assert all(v == 0 for v in block.content["primitive_counts"].values())
