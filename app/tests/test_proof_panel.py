# app/tests/test_proof_panel.py
"""
Tests for Ticket 18B - System Proof Panel + Proof Summary

Tests:
1. Proof summary is always present in pipeline response
2. With flags OFF => proof shows disabled status
3. With SHERLOCK_ENABLED=1 => proof shows ran=true and audit status
4. If audit fails => proof shows FAIL and still no downstream effects
5. Panel visibility logic (BEST tier OR debug=1)
"""
import os
import pytest
from unittest.mock import patch

from app.proof_summary import (
    ProofSummary,
    derive_proof_summary,
    should_show_proof_panel,
)


# =============================================================================
# Tests: ProofSummary Schema
# =============================================================================


class TestProofSummarySchema:
    """Tests for ProofSummary dataclass."""

    def test_to_dict_serialization(self):
        """ProofSummary.to_dict() should produce correct dict structure."""
        summary = ProofSummary(
            sherlock_enabled=True,
            dna_recording_enabled=False,
            sherlock_ran=True,
            audit_status="PASS",
            dna_artifact_counts={"weights": 2, "constraints": 1},
            sample_artifacts=[{"type": "weights", "count": 2}],
        )
        result = summary.to_dict()

        assert result["sherlock_enabled"] is True
        assert result["dna_recording_enabled"] is False
        assert result["sherlock_ran"] is True
        assert result["audit_status"] == "PASS"
        assert result["dna_artifact_counts"] == {"weights": 2, "constraints": 1}
        assert result["derived"] is True
        assert result["persisted"] is False


# =============================================================================
# Tests: derive_proof_summary
# =============================================================================


class TestDeriveProofSummary:
    """Tests for derive_proof_summary function."""

    def test_flags_off_returns_not_run(self):
        """With both flags off and no explainability output, returns NOT_RUN."""
        result = derive_proof_summary(
            sherlock_enabled=False,
            dna_recording_enabled=False,
            explainability_output=None,
        )

        assert result.sherlock_enabled is False
        assert result.dna_recording_enabled is False
        assert result.sherlock_ran is False
        assert result.audit_status == "NOT_RUN"
        assert result.derived is True
        assert result.persisted is False

    def test_sherlock_disabled_at_runtime(self):
        """When explainability output has enabled=false, returns NOT_RUN."""
        result = derive_proof_summary(
            sherlock_enabled=False,
            dna_recording_enabled=False,
            explainability_output={"enabled": False},
        )

        assert result.sherlock_ran is False
        assert result.audit_status == "NOT_RUN"

    def test_sherlock_enabled_and_ran(self):
        """When Sherlock ran, returns correct status and audit."""
        explainability = {
            "enabled": True,
            "blocks": [],
            "summary": {
                "verdict": "likely_true",
                "confidence": 0.78,
                "audit_passed": True,
            },
        }

        result = derive_proof_summary(
            sherlock_enabled=True,
            dna_recording_enabled=False,
            explainability_output=explainability,
        )

        assert result.sherlock_enabled is True
        assert result.sherlock_ran is True
        assert result.audit_status == "PASS"

    def test_audit_failed_shows_fail(self):
        """When audit fails, returns FAIL status."""
        explainability = {
            "enabled": True,
            "blocks": [],
            "summary": {
                "verdict": "unclear",
                "confidence": 0.45,
                "audit_passed": False,
            },
        }

        result = derive_proof_summary(
            sherlock_enabled=True,
            dna_recording_enabled=True,
            explainability_output=explainability,
        )

        assert result.sherlock_ran is True
        assert result.audit_status == "FAIL"

    def test_dna_counts_extracted_from_preview_block(self):
        """DNA artifact counts should be extracted from dna_preview block."""
        explainability = {
            "enabled": True,
            "blocks": [
                {
                    "block_type": "dna_preview",
                    "content": {
                        "primitive_counts": {
                            "weights": 3,
                            "constraints": 1,
                            "conflicts": 0,
                            "baseline": 1,
                            "drifts": 0,
                            "tradeoffs": 1,
                            "lineage": 2,
                        },
                    },
                },
            ],
            "summary": {"audit_passed": True},
        }

        result = derive_proof_summary(
            sherlock_enabled=True,
            dna_recording_enabled=True,
            explainability_output=explainability,
        )

        assert result.dna_artifact_counts["weights"] == 3
        assert result.dna_artifact_counts["constraints"] == 1
        assert result.dna_artifact_counts["lineage"] == 2

    def test_sample_artifacts_limited_to_five(self):
        """Sample artifacts should be limited to 5 max."""
        explainability = {
            "enabled": True,
            "blocks": [
                {
                    "block_type": "dna_preview",
                    "content": {
                        "primitive_counts": {
                            "weights": 10,
                            "constraints": 5,
                            "conflicts": 3,
                            "baseline": 1,
                            "drifts": 2,
                            "tradeoffs": 4,
                            "lineage": 8,
                        },
                    },
                },
            ],
            "summary": {"audit_passed": True},
        }

        result = derive_proof_summary(
            sherlock_enabled=True,
            dna_recording_enabled=True,
            explainability_output=explainability,
        )

        # Should have at most 5 sample artifacts
        assert len(result.sample_artifacts) <= 5


# =============================================================================
# Tests: should_show_proof_panel
# =============================================================================


class TestShouldShowProofPanel:
    """Tests for panel visibility logic."""

    def test_best_tier_shows_panel(self):
        """BEST tier should show proof panel."""
        assert should_show_proof_panel(tier="best", debug_param=False) is True
        assert should_show_proof_panel(tier="BEST", debug_param=False) is True

    def test_debug_param_shows_panel(self):
        """debug=1 param should show proof panel regardless of tier."""
        assert should_show_proof_panel(tier="good", debug_param=True) is True
        assert should_show_proof_panel(tier="better", debug_param=True) is True
        assert should_show_proof_panel(tier="best", debug_param=True) is True

    def test_good_tier_without_debug_hides_panel(self):
        """GOOD tier without debug should hide proof panel."""
        assert should_show_proof_panel(tier="good", debug_param=False) is False

    def test_better_tier_without_debug_hides_panel(self):
        """BETTER tier without debug should hide proof panel."""
        assert should_show_proof_panel(tier="better", debug_param=False) is False


# =============================================================================
# Tests: Pipeline Integration
# =============================================================================


class TestPipelineProofIntegration:
    """Tests for proof_summary in pipeline response."""

    def test_proof_summary_always_present_flags_off(self):
        """proof_summary should be present even with flags off."""
        with patch.dict(os.environ, {
            "SHERLOCK_ENABLED": "false",
            "DNA_RECORDING_ENABLED": "false",
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
                tier=Tier.GOOD,
            )

            result = run_evaluation(test_input)

            # proof_summary should be present
            assert result.proof_summary is not None
            assert result.proof_summary["sherlock_enabled"] is False
            assert result.proof_summary["sherlock_ran"] is False
            assert result.proof_summary["audit_status"] == "NOT_RUN"
            assert result.proof_summary["derived"] is True
            assert result.proof_summary["persisted"] is False

    def test_proof_summary_shows_ran_when_enabled(self):
        """With SHERLOCK_ENABLED=true, proof shows ran=true."""
        with patch.dict(os.environ, {
            "SHERLOCK_ENABLED": "true",
            "DNA_RECORDING_ENABLED": "false",
        }):
            import importlib
            import app.config
            importlib.reload(app.config)

            import app.pipeline
            importlib.reload(app.pipeline)

            from app.pipeline import run_evaluation
            from app.airlock import NormalizedInput, Tier

            test_input = NormalizedInput(
                input_text="Lakers -5.5 + LeBron over 25 points",
                tier=Tier.GOOD,
            )

            result = run_evaluation(test_input)

            # proof_summary should show Sherlock ran
            assert result.proof_summary is not None
            assert result.proof_summary["sherlock_enabled"] is True
            assert result.proof_summary["sherlock_ran"] is True
            assert result.proof_summary["audit_status"] in ["PASS", "FAIL"]

    def test_proof_summary_shows_dna_counts_when_both_enabled(self):
        """With both flags enabled, proof shows DNA artifact counts."""
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
                input_text="Nuggets -3.5 + Jokic triple-double",
                tier=Tier.GOOD,
            )

            result = run_evaluation(test_input)

            # proof_summary should have DNA counts
            assert result.proof_summary is not None
            assert result.proof_summary["dna_recording_enabled"] is True
            # Counts may be empty if no DNA preview block, but should be present
            assert "dna_artifact_counts" in result.proof_summary

    def test_audit_fail_no_downstream_effects(self):
        """If audit fails, core evaluation should be unaffected."""
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

            # Use minimal input likely to cause lower audit confidence
            test_input = NormalizedInput(
                input_text="Bet",
                tier=Tier.GOOD,
            )

            result = run_evaluation(test_input)

            # Core evaluation should still work
            assert result.evaluation is not None
            assert result.evaluation.metrics is not None
            assert result.signal_info is not None

            # Proof summary should be present regardless of audit status
            assert result.proof_summary is not None
            assert result.proof_summary["audit_status"] in ["PASS", "FAIL", "NOT_RUN"]


# =============================================================================
# Tests: Web Route Response
# =============================================================================


class TestWebRouteProofResponse:
    """Tests for proofSummary in web route JSON response."""

    def test_proof_summary_in_evaluate_response(self):
        """proofSummary should be included in /app/evaluate response."""
        with patch.dict(os.environ, {
            "LEADING_LIGHT_ENABLED": "true",
        }):
            # Need to reload the routers module to pick up the env change
            import importlib
            import app.routers.leading_light
            importlib.reload(app.routers.leading_light)

            from fastapi.testclient import TestClient
            from app.main import app

            client = TestClient(app)

            # Make evaluation request
            response = client.post("/app/evaluate", json={
                "input": "Lakers -5.5",
                "tier": "good",
            })

            assert response.status_code == 200
            data = response.json()

            # proofSummary should be present
            assert "proofSummary" in data
            proof = data["proofSummary"]
            assert "sherlock_enabled" in proof
            assert "dna_recording_enabled" in proof
            assert "sherlock_ran" in proof
            assert "audit_status" in proof
            assert "derived" in proof
            assert proof["derived"] is True
            assert proof["persisted"] is False
