# app/tests/test_proof.py
"""
Tests for Sherlock/DNA Proof Infrastructure (Ticket 18).
"""
import os
import pytest
from uuid import uuid4


class TestProofFlags:
    """Test proof flag detection."""

    def test_get_proof_flags_when_disabled(self, monkeypatch):
        """Proof flags should default to disabled."""
        # Clear any existing env vars
        monkeypatch.delenv("SHERLOCK_ENABLED", raising=False)
        monkeypatch.delenv("DNA_RECORDING_ENABLED", raising=False)

        from app.proof import get_proof_flags

        flags = get_proof_flags()
        assert flags["sherlock_enabled"] is False
        assert flags["dna_recording_enabled"] is False

    def test_get_proof_flags_when_enabled(self, monkeypatch):
        """Proof flags should reflect environment."""
        monkeypatch.setenv("SHERLOCK_ENABLED", "true")
        monkeypatch.setenv("DNA_RECORDING_ENABLED", "true")

        from app.proof import get_proof_flags

        flags = get_proof_flags()
        assert flags["sherlock_enabled"] is True
        assert flags["dna_recording_enabled"] is True


class TestProofRecord:
    """Test proof record generation."""

    def test_generate_proof_record_when_disabled(self, monkeypatch):
        """Should return minimal record when both flags disabled."""
        monkeypatch.delenv("SHERLOCK_ENABLED", raising=False)
        monkeypatch.delenv("DNA_RECORDING_ENABLED", raising=False)

        from app.proof import generate_proof_record

        record = generate_proof_record(evaluation_id=uuid4())

        assert record.sherlock_ran is False
        assert record.dna_recording_active is False
        assert record.audit_status == "SKIPPED"
        assert record.artifacts is None

    def test_generate_proof_record_when_sherlock_enabled(self, monkeypatch):
        """Should mark sherlock_ran=True when enabled."""
        monkeypatch.setenv("SHERLOCK_ENABLED", "true")
        monkeypatch.delenv("DNA_RECORDING_ENABLED", raising=False)

        from app.proof import generate_proof_record, clear_proof_store

        clear_proof_store()
        record = generate_proof_record(evaluation_id=uuid4())

        assert record.sherlock_ran is True
        assert record.dna_recording_active is False
        # With no evaluation response, artifacts should be None
        assert record.artifacts is None


class TestProofStore:
    """Test in-memory proof store."""

    def test_store_and_retrieve(self, monkeypatch):
        """Should store and retrieve proof records."""
        monkeypatch.setenv("SHERLOCK_ENABLED", "true")

        from app.proof import (
            generate_proof_record,
            get_recent_proofs,
            clear_proof_store,
        )

        clear_proof_store()

        # Generate some records
        eval_id_1 = uuid4()
        eval_id_2 = uuid4()
        generate_proof_record(evaluation_id=eval_id_1)
        generate_proof_record(evaluation_id=eval_id_2)

        # Retrieve recent
        recent = get_recent_proofs(limit=10)
        assert len(recent) == 2
        # Newest first
        assert recent[0]["evaluation_id"] == str(eval_id_2)
        assert recent[1]["evaluation_id"] == str(eval_id_1)

    def test_proof_summary(self, monkeypatch):
        """Should return summary statistics."""
        monkeypatch.setenv("SHERLOCK_ENABLED", "true")

        from app.proof import (
            generate_proof_record,
            get_proof_summary,
            clear_proof_store,
        )

        clear_proof_store()

        # Generate a record
        generate_proof_record(evaluation_id=uuid4())

        summary = get_proof_summary()
        assert summary["sherlock_enabled"] is True
        assert summary["record_count"] == 1


class TestDNAArtifactSummary:
    """Test DNA artifact extraction."""

    def test_artifact_summary_from_mock_evaluation(self, monkeypatch):
        """Should extract artifacts from evaluation response."""
        monkeypatch.setenv("DNA_RECORDING_ENABLED", "true")

        from app.proof import DNAArtifactSummary

        # Create a mock evaluation response
        class MockInductor:
            level = type("Level", (), {"value": "stable"})()

        class MockRecommendation:
            action = type("Action", (), {"value": "accept"})()

        class MockMetrics:
            final_fragility = 25.0

        class MockEvaluation:
            parlay_id = uuid4()
            correlations = []
            inductor = MockInductor()
            recommendation = MockRecommendation()
            metrics = MockMetrics()
            suggestions = None

        from app.proof import _extract_artifact_summary

        summary = _extract_artifact_summary(MockEvaluation())

        assert summary.correlation_count == 0
        assert summary.fragility_computed is True
        assert summary.inductor_level == "stable"
        assert summary.recommendation_action == "accept"
        assert summary.suggestion_count == 0
        assert summary.total_artifacts == 3  # fragility + inductor + recommendation


class TestProofDerived:
    """Test that all proof records are marked as derived."""

    def test_record_is_derived(self, monkeypatch):
        """All proof records should have derived=True."""
        monkeypatch.setenv("SHERLOCK_ENABLED", "true")

        from app.proof import generate_proof_record

        record = generate_proof_record(evaluation_id=uuid4())
        assert record.derived is True


class TestProofToDict:
    """Test proof record serialization."""

    def test_record_to_dict(self, monkeypatch):
        """Record should serialize to dict correctly."""
        monkeypatch.setenv("SHERLOCK_ENABLED", "true")

        from app.proof import generate_proof_record

        record = generate_proof_record(evaluation_id=uuid4())
        d = record.to_dict()

        assert "proof_id" in d
        assert "evaluation_id" in d
        assert "timestamp_utc" in d
        assert "sherlock_ran" in d
        assert "audit_status" in d
        assert "derived" in d
        assert d["derived"] is True
