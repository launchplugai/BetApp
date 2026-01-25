# app/tests/test_pipeline.py
"""
Tests for the Pipeline Facade - unified evaluation entry point.

These tests verify:
1. Pipeline is the single entry point (routes don't call core.evaluation directly)
2. Pipeline produces consistent results
3. Tier filtering works correctly through pipeline
4. Errors propagate correctly
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.airlock import airlock_ingest, NormalizedInput, Tier
from app.pipeline import (
    run_evaluation,
    PipelineResponse,
    _parse_bet_text,
    _generate_summary,
    _generate_alerts,
    _interpret_fragility,
    _apply_tier_filtering,
)


class TestParseBetText:
    """Tests for bet text parsing."""

    def test_single_leg_detected(self):
        """Single bet creates one block."""
        blocks = _parse_bet_text("Lakers -5.5")
        assert len(blocks) == 1

    def test_parlay_detected(self):
        """Parlay with + delimiter creates multiple blocks."""
        blocks = _parse_bet_text("Lakers -5.5 + Celtics ML")
        assert len(blocks) == 2

    def test_comma_delimiter_detected(self):
        """Comma delimiter creates multiple blocks."""
        blocks = _parse_bet_text("Lakers -5.5, Celtics ML, Heat ML")
        assert len(blocks) == 3

    def test_max_legs_capped(self):
        """Leg count capped at 5."""
        blocks = _parse_bet_text("A + B + C + D + E + F + G + H")
        assert len(blocks) == 5

    def test_prop_bet_detected(self):
        """Player prop keywords detected."""
        blocks = _parse_bet_text("LeBron over 25 points")
        assert blocks[0].bet_type.value == "player_prop"

    def test_total_bet_detected(self):
        """Over/under keywords detected."""
        blocks = _parse_bet_text("Lakers vs Celtics over 220")
        assert blocks[0].bet_type.value == "total"


class TestGenerateSummary:
    """Tests for summary generation."""

    def test_summary_includes_leg_count(self):
        """Summary includes leg count."""
        mock_response = MagicMock()
        mock_response.inductor.level.value = "stable"
        mock_response.metrics.final_fragility = 10.0
        mock_response.metrics.correlation_penalty = 0
        mock_response.correlations = []

        summary = _generate_summary(mock_response, 3)
        assert "3 leg(s)" in summary[0]

    def test_summary_includes_risk_level(self):
        """Summary includes risk level."""
        mock_response = MagicMock()
        mock_response.inductor.level.value = "tense"
        mock_response.metrics.final_fragility = 40.0
        mock_response.metrics.correlation_penalty = 0
        mock_response.correlations = []

        summary = _generate_summary(mock_response, 1)
        assert any("TENSE" in s for s in summary)


class TestGenerateAlerts:
    """Tests for alert generation."""

    def test_dna_violations_become_alerts(self):
        """DNA violations added to alerts."""
        mock_response = MagicMock()
        mock_response.dna.violations = ["Max legs exceeded", "High fragility"]
        mock_response.metrics.correlation_multiplier = 1.0
        mock_response.inductor.level.value = "stable"

        alerts = _generate_alerts(mock_response)
        assert "Max legs exceeded" in alerts
        assert "High fragility" in alerts

    def test_high_correlation_alert(self):
        """High correlation triggers alert."""
        mock_response = MagicMock()
        mock_response.dna.violations = []
        mock_response.metrics.correlation_multiplier = 1.5
        mock_response.inductor.level.value = "stable"

        alerts = _generate_alerts(mock_response)
        assert any("correlation" in a.lower() for a in alerts)


class TestInterpretFragility:
    """Tests for fragility interpretation."""

    def test_low_fragility(self):
        """Low fragility (<=15) returns low bucket."""
        result = _interpret_fragility(10.0)
        assert result["bucket"] == "low"

    def test_medium_fragility(self):
        """Medium fragility (16-35) returns medium bucket."""
        result = _interpret_fragility(25.0)
        assert result["bucket"] == "medium"

    def test_high_fragility(self):
        """High fragility (36-60) returns high bucket."""
        result = _interpret_fragility(50.0)
        assert result["bucket"] == "high"

    def test_critical_fragility(self):
        """Critical fragility (>60) returns critical bucket."""
        result = _interpret_fragility(75.0)
        assert result["bucket"] == "critical"


class TestTierFiltering:
    """Tests for tier-based filtering."""

    def test_good_tier_empty_explain(self):
        """GOOD tier returns empty explain."""
        explain = {
            "summary": ["Test summary"],
            "alerts": ["Test alert"],
            "recommended_next_step": "Test step",
        }
        result = _apply_tier_filtering(Tier.GOOD, explain)
        assert result == {}

    def test_better_tier_summary_only(self):
        """BETTER tier returns summary only."""
        explain = {
            "summary": ["Test summary"],
            "alerts": ["Test alert"],
            "recommended_next_step": "Test step",
        }
        result = _apply_tier_filtering(Tier.BETTER, explain)
        assert "summary" in result
        assert "alerts" not in result
        assert "recommended_next_step" not in result

    def test_best_tier_all_fields(self):
        """BEST tier returns all fields."""
        explain = {
            "summary": ["Test summary"],
            "alerts": ["Test alert"],
            "recommended_next_step": "Test step",
        }
        result = _apply_tier_filtering(Tier.BEST, explain)
        assert "summary" in result
        assert "alerts" in result
        assert "recommended_next_step" in result


class TestRunEvaluation:
    """Tests for main pipeline function."""

    def test_returns_pipeline_response(self):
        """run_evaluation returns PipelineResponse."""
        normalized = airlock_ingest("Lakers -5.5", tier="good")
        result = run_evaluation(normalized)
        assert isinstance(result, PipelineResponse)

    def test_evaluation_included(self):
        """Response includes evaluation from core engine."""
        normalized = airlock_ingest("Lakers -5.5", tier="good")
        result = run_evaluation(normalized)
        assert result.evaluation is not None
        assert result.evaluation.parlay_id is not None

    def test_interpretation_included(self):
        """Response includes interpretation."""
        normalized = airlock_ingest("Lakers -5.5", tier="good")
        result = run_evaluation(normalized)
        assert "fragility" in result.interpretation

    def test_tier_reflected_in_response(self):
        """Tier from input reflected in response."""
        normalized = airlock_ingest("Lakers -5.5", tier="better")
        result = run_evaluation(normalized)
        assert result.tier == "better"

    def test_good_tier_structured_explain(self):
        """GOOD tier returns structured explain in pipeline response (Ticket 3)."""
        normalized = airlock_ingest("Lakers -5.5", tier="good")
        result = run_evaluation(normalized)
        # Ticket 3: GOOD tier now returns structured output
        assert "overallSignal" in result.explain
        assert "grade" in result.explain
        assert "fragilityScore" in result.explain
        # GOOD tier should NOT have BETTER/BEST fields
        assert "summary" not in result.explain
        assert "alerts" not in result.explain

    def test_best_tier_full_explain(self):
        """BEST tier returns full explain in pipeline response."""
        normalized = airlock_ingest("Lakers -5.5", tier="best")
        result = run_evaluation(normalized)
        assert "summary" in result.explain
        assert "alerts" in result.explain


class TestRouteIntegration:
    """Integration tests to verify routes use the same pipeline."""

    @pytest.fixture
    def client(self):
        """Create test client with Leading Light enabled."""
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        from app.rate_limiter import set_rate_limiter, RateLimiter
        set_rate_limiter(RateLimiter(requests_per_minute=100, burst_size=100))
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_app_evaluate_uses_pipeline(self):
        """Verify /app/evaluate goes through pipeline."""
        with patch("app.pipeline.run_evaluation") as mock_pipeline:
            # Setup mock return
            mock_response = MagicMock()
            mock_response.evaluation.parlay_id = uuid4()
            mock_response.evaluation.inductor.level.value = "stable"
            mock_response.evaluation.inductor.explanation = "test"
            mock_response.evaluation.metrics.raw_fragility = 10.0
            mock_response.evaluation.metrics.final_fragility = 10.0
            mock_response.evaluation.metrics.leg_penalty = 0.0
            mock_response.evaluation.metrics.correlation_penalty = 0.0
            mock_response.evaluation.metrics.correlation_multiplier = 1.0
            mock_response.evaluation.correlations = []
            mock_response.evaluation.recommendation.action.value = "accept"
            mock_response.evaluation.recommendation.reason = "test"
            mock_response.interpretation = {"fragility": {"bucket": "low"}}
            mock_response.explain = {}
            mock_response.tier = "good"
            mock_pipeline.return_value = mock_response

            os.environ["LEADING_LIGHT_ENABLED"] = "true"
            from app.rate_limiter import set_rate_limiter, RateLimiter
            set_rate_limiter(RateLimiter(requests_per_minute=100, burst_size=100))
            from app.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)

            response = client.post(
                "/app/evaluate",
                json={"input": "Lakers -5.5", "tier": "good"},
            )

            # Verify pipeline was called
            assert mock_pipeline.called

    def test_pipeline_failure_propagates(self):
        """Verify pipeline errors propagate correctly."""
        with patch("app.pipeline.run_evaluation") as mock_pipeline:
            mock_pipeline.side_effect = ValueError("Pipeline error")

            os.environ["LEADING_LIGHT_ENABLED"] = "true"
            from app.rate_limiter import set_rate_limiter, RateLimiter
            set_rate_limiter(RateLimiter(requests_per_minute=100, burst_size=100))
            from app.main import app
            from fastapi.testclient import TestClient
            client = TestClient(app)

            response = client.post(
                "/app/evaluate",
                json={"input": "Lakers -5.5", "tier": "good"},
            )

            assert response.status_code == 400
            assert "VALIDATION_ERROR" in response.json().get("code", "")

    def test_consistent_tier_filtering_via_pipeline(self):
        """Verify tier filtering works the same way through pipeline."""
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        from app.rate_limiter import set_rate_limiter, RateLimiter
        set_rate_limiter(RateLimiter(requests_per_minute=100, burst_size=100))
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # GOOD tier should have structured explain (Ticket 3)
        response_good = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        assert response_good.status_code == 200
        good_explain = response_good.json()["explain"]
        assert "overallSignal" in good_explain
        assert "grade" in good_explain
        # GOOD should NOT have BETTER/BEST fields
        assert "summary" not in good_explain

        # BEST tier should have full explain
        response_best = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "best"},
        )
        assert response_best.status_code == 200
        explain = response_best.json()["explain"]
        assert "summary" in explain
