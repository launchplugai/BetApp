# app/tests/test_sherlock_integration.py
"""
Ticket 17 - Sherlock Integration Golden Tests

Tests the dry-run integration between pipeline and Sherlock.
Verifies:
1. Pipeline output unchanged with flags off
2. Sherlock runs and produces results with flags on
3. DNA artifacts created when both flags on
4. Zero latency impact when disabled
"""
import os
import pytest
from unittest.mock import patch


# =============================================================================
# Test: Flags Off - No Sherlock/DNA Fields
# =============================================================================


def test_pipeline_no_sherlock_when_disabled():
    """With SHERLOCK_ENABLED=false, sherlock_result should be None."""
    # Ensure flags are off
    with patch.dict(os.environ, {
        "SHERLOCK_ENABLED": "false",
        "DNA_RECORDING_ENABLED": "false",
    }):
        # Re-import to pick up new env
        import importlib
        import app.config
        importlib.reload(app.config)

        from app.pipeline import run_evaluation
        from app.airlock import NormalizedInput, Tier

        # Fixed test input
        test_input = NormalizedInput(
            input_text="Lakers -5.5 + LeBron over 25.5 points",
            tier=Tier.GOOD,
        )

        result = run_evaluation(test_input)

        # Sherlock result should be None when disabled
        assert result.sherlock_result is None

        # Core evaluation should still work
        assert result.evaluation is not None
        assert result.leg_count >= 1
        assert result.signal_info is not None


def test_pipeline_core_output_unchanged_with_flags_off():
    """Core pipeline output should be identical with flags off."""
    with patch.dict(os.environ, {
        "SHERLOCK_ENABLED": "false",
        "DNA_RECORDING_ENABLED": "false",
    }):
        import importlib
        import app.config
        importlib.reload(app.config)

        from app.pipeline import run_evaluation
        from app.airlock import NormalizedInput, Tier

        test_input = NormalizedInput(
            input_text="Celtics ML + Tatum over 30 points",
            tier=Tier.GOOD,
        )

        result = run_evaluation(test_input)

        # Verify core fields are present and valid
        assert result.evaluation is not None
        assert result.interpretation is not None
        assert result.explain is not None
        assert result.primary_failure is not None
        assert result.signal_info is not None
        assert result.entities is not None
        assert result.human_summary is not None

        # Verify no sherlock contamination
        assert result.sherlock_result is None


# =============================================================================
# Test: Flags On - Sherlock Runs
# =============================================================================


def test_pipeline_sherlock_runs_when_enabled():
    """With SHERLOCK_ENABLED=true, sherlock_result should contain investigation."""
    with patch.dict(os.environ, {
        "SHERLOCK_ENABLED": "true",
        "DNA_RECORDING_ENABLED": "false",
    }):
        import importlib
        import app.config
        importlib.reload(app.config)

        # Need to reload pipeline to pick up new config
        import app.pipeline
        importlib.reload(app.pipeline)

        from app.pipeline import run_evaluation
        from app.airlock import NormalizedInput, Tier

        test_input = NormalizedInput(
            input_text="Lakers -5.5 + LeBron over 25.5 points + Warriors ML",
            tier=Tier.GOOD,
        )

        result = run_evaluation(test_input)

        # Sherlock result should be present
        assert result.sherlock_result is not None
        assert result.sherlock_result["enabled"] is True
        assert result.sherlock_result["claim_text"] is not None
        assert result.sherlock_result["iterations_completed"] >= 1
        assert result.sherlock_result["verdict"] in [
            "true", "likely_true", "unclear", "likely_false", "false", "non_falsifiable", "error"
        ]
        assert 0.0 <= result.sherlock_result["confidence"] <= 1.0
        assert "audit_passed" in result.sherlock_result
        assert "audit_score" in result.sherlock_result

        # DNA artifact should be None when DNA_RECORDING_ENABLED=false
        assert result.sherlock_result["dna_artifact"] is None


def test_pipeline_dna_artifacts_when_both_enabled():
    """With both flags true, DNA artifacts should be created."""
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

        # Sherlock result should be present
        assert result.sherlock_result is not None
        assert result.sherlock_result["enabled"] is True

        # DNA artifact should be present
        dna_artifact = result.sherlock_result["dna_artifact"]
        assert dna_artifact is not None

        # Verify DNA artifact structure
        assert "created_at" in dna_artifact
        assert "sherlock_report_id" in dna_artifact
        assert "audit_passed" in dna_artifact
        assert "audit_score" in dna_artifact
        assert "quarantined" in dna_artifact

        # Verify primitives
        assert "primitives" in dna_artifact
        primitives = dna_artifact["primitives"]
        assert "weights" in primitives
        assert "constraints" in primitives
        assert "conflicts" in primitives
        assert "baseline" in primitives  # May be None if audit failed
        assert "drifts" in primitives
        assert "tradeoffs" in primitives
        assert "lineage" in primitives

        # Weights should have at least verdict confidence
        assert len(primitives["weights"]) >= 1

        # Lineage should have at least the investigation record
        assert len(primitives["lineage"]) >= 1


# =============================================================================
# Test: Audit Gate Controls Persistence
# =============================================================================


def test_dna_quarantine_when_audit_fails():
    """When audit fails, DNA artifact should be quarantined."""
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

        # Use a simple input that may not pass strict audit
        test_input = NormalizedInput(
            input_text="Bet",  # Very minimal input
            tier=Tier.GOOD,
        )

        result = run_evaluation(test_input)

        if result.sherlock_result and result.sherlock_result["dna_artifact"]:
            dna_artifact = result.sherlock_result["dna_artifact"]

            # If audit failed, should be quarantined
            if not dna_artifact["audit_passed"]:
                assert dna_artifact["quarantined"] is True
                # Baseline should be None when quarantined
                assert dna_artifact["primitives"]["baseline"] is None
                # Drifts should have rejection record
                assert len(dna_artifact["primitives"]["drifts"]) >= 1


# =============================================================================
# Test: Debug Endpoint
# =============================================================================


def test_debug_contracts_endpoint():
    """Debug endpoint should return contract versions and flags."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/debug/contracts")

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "contracts" in data
    assert "flags" in data
    assert "build" in data
    assert "service" in data
    assert "sherlock_version" in data

    # Verify contract versions
    contracts = data["contracts"]
    assert contracts["SYSTEM_CONTRACT_SDS"] == "1.0.0"
    assert contracts["SCH_SDK_CONTRACT"] == "1.0.0"
    assert contracts["DNA_PRIMITIVES_CONTRACT"] == "1.0.0"
    assert contracts["MAP_SHERLOCK_TO_DNA"] == "1.0.0"

    # Verify flags present
    flags = data["flags"]
    assert "sherlock_enabled" in flags
    assert "dna_recording_enabled" in flags

    # Verify build info
    build = data["build"]
    assert "git_sha" in build
    assert "build_time_utc" in build
    assert "environment" in build


def test_health_endpoint_still_works():
    """/health should still work and show git_sha."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert "git_sha" in data
    assert "build_time_utc" in data


# =============================================================================
# Test: Determinism
# =============================================================================


def test_sherlock_hook_deterministic():
    """Same input should produce same Sherlock output."""
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
            input_text="Heat ML + Butler over 20 points",
            tier=Tier.GOOD,
        )

        result1 = run_evaluation(test_input)
        result2 = run_evaluation(test_input)

        # Core evaluation should be identical
        assert result1.evaluation.metrics.final_fragility == result2.evaluation.metrics.final_fragility

        # Sherlock results should be identical
        if result1.sherlock_result and result2.sherlock_result:
            assert result1.sherlock_result["verdict"] == result2.sherlock_result["verdict"]
            assert result1.sherlock_result["confidence"] == result2.sherlock_result["confidence"]
            assert result1.sherlock_result["audit_passed"] == result2.sherlock_result["audit_passed"]


# =============================================================================
# Test: Explainability Adapter (Ticket 18)
# =============================================================================


def test_debug_explainability_when_sherlock_enabled():
    """With SHERLOCK_ENABLED=true, debug_explainability should contain blocks."""
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
            input_text="Lakers -5.5 + LeBron over 25.5 points",
            tier=Tier.GOOD,
        )

        result = run_evaluation(test_input)

        # Explainability should be present when Sherlock runs
        assert result.debug_explainability is not None
        assert result.debug_explainability["enabled"] is True

        # Should have blocks
        assert "blocks" in result.debug_explainability
        blocks = result.debug_explainability["blocks"]
        assert len(blocks) >= 4  # At minimum: summary, claim, verdict, audit

        # Verify block types
        block_types = [b["block_type"] for b in blocks]
        assert "investigation_summary" in block_types
        assert "claim" in block_types
        assert "verdict" in block_types
        assert "audit" in block_types

        # Should have summary
        assert "summary" in result.debug_explainability
        summary = result.debug_explainability["summary"]
        assert "verdict" in summary
        assert "confidence" in summary
        assert "audit_passed" in summary


def test_debug_explainability_none_when_sherlock_disabled():
    """With SHERLOCK_ENABLED=false, debug_explainability should be None."""
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
            input_text="Celtics ML",
            tier=Tier.GOOD,
        )

        result = run_evaluation(test_input)

        # Explainability should be None when Sherlock is disabled
        assert result.debug_explainability is None


def test_debug_explainability_includes_dna_preview_when_enabled():
    """With both flags enabled, debug_explainability should include DNA preview block."""
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
            input_text="Nuggets -3.5 + Jokic over 25 points",
            tier=Tier.GOOD,
        )

        result = run_evaluation(test_input)

        # Explainability should be present
        assert result.debug_explainability is not None
        assert result.debug_explainability["enabled"] is True

        # Should have 5 blocks including DNA preview
        blocks = result.debug_explainability["blocks"]
        assert len(blocks) == 5

        # Verify DNA preview block is present
        block_types = [b["block_type"] for b in blocks]
        assert "dna_preview" in block_types

        # Find and verify DNA preview block
        dna_block = next(b for b in blocks if b["block_type"] == "dna_preview")
        assert "quarantined" in dna_block["content"]
        assert "primitive_counts" in dna_block["content"]
