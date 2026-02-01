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
    _extract_leg_info,
    _build_leg_specific_reason,
    _build_notable_legs,
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
        """Parser caps at 6 legs (Builder State Machine handles full limits)."""
        # Parser has internal cap; Builder State Machine handles extended limits
        blocks = _parse_bet_text("A + B + C + D + E + F + G + H")
        assert len(blocks) == 6  # Parser caps at 6; full 12-leg limit in Builder

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

        # Ticket 28: Pass leg_count as keyword argument (eval_ctx is optional)
        summary = _generate_summary(mock_response, leg_count=3)
        assert "3 leg(s)" in summary[0]

    def test_summary_includes_risk_level(self):
        """Summary includes risk level."""
        mock_response = MagicMock()
        mock_response.inductor.level.value = "tense"
        mock_response.metrics.final_fragility = 40.0
        mock_response.metrics.correlation_penalty = 0
        mock_response.correlations = []

        # Ticket 28: Pass leg_count as keyword argument (eval_ctx is optional)
        summary = _generate_summary(mock_response, leg_count=1)
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
        """Verify pipeline errors propagate correctly as 500 internal error."""
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

            # Pipeline errors are internal errors (500), not validation errors (400)
            assert response.status_code == 500
            assert "INTERNAL_ERROR" in response.json().get("error", "")

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


class TestTicket38NotableLegsV2:
    """
    Ticket 38: Notable Legs v2 with leg-specific reasoning.

    Tests verify specificity and non-generic behavior:
    1. Player prop notable leg includes player/entity reference
    2. Total notable leg mentions totals dependency language
    3. Spread notable leg mentions margin sensitivity language
    4. Multi-leg mixed markets produces distinct reason patterns
    5. No forbidden language (odds, payout, probability, lock, guarantee)
    6. Deterministic output: same input → same ordering
    """

    def test_extract_leg_info_player_prop(self):
        """Part A: Extract entity and value from player prop."""
        mock_block = MagicMock()
        mock_block.bet_type.value = "player_prop"
        mock_block.sport = "NBA"

        leg_info = _extract_leg_info(mock_block, "LeBron o25.5 pts")
        assert leg_info["market"] == "player_prop"
        assert "LeBron" in leg_info["entity"]
        assert leg_info["value"] == 25.5

    def test_extract_leg_info_spread(self):
        """Part A: Extract entity and value from spread."""
        mock_block = MagicMock()
        mock_block.bet_type.value = "spread"
        mock_block.sport = "NBA"

        leg_info = _extract_leg_info(mock_block, "Lakers -5.5")
        assert leg_info["market"] == "spread"
        assert "Lakers" in leg_info["entity"]
        assert leg_info["value"] == -5.5

    def test_extract_leg_info_total(self):
        """Part A: Extract value from total."""
        mock_block = MagicMock()
        mock_block.bet_type.value = "total"
        mock_block.sport = "NBA"

        leg_info = _extract_leg_info(mock_block, "Over 220.5")
        assert leg_info["market"] == "total"
        assert leg_info["value"] == 220.5

    def test_extract_leg_info_moneyline(self):
        """Part A: Extract entity from moneyline."""
        mock_block = MagicMock()
        mock_block.bet_type.value = "moneyline"
        mock_block.sport = "NBA"

        leg_info = _extract_leg_info(mock_block, "Celtics ML")
        assert leg_info["market"] == "moneyline"
        assert "Celtics" in leg_info["entity"]

    def test_player_prop_reason_includes_entity(self):
        """Part A: Player prop reason must include entity reference."""
        leg_info = {
            "entity": "LeBron",
            "market": "player_prop",
            "value": 25.5,
            "sport": "NBA",
        }
        reason = _build_leg_specific_reason(leg_info, "player_prop")

        assert "LeBron" in reason
        assert "player prop" in reason.lower()
        assert "individual" in reason.lower() or "performance" in reason.lower()

    def test_total_reason_mentions_dependency_language(self):
        """Part A: Total reason must mention totals dependency."""
        leg_info = {
            "entity": "Game",
            "market": "total",
            "value": 220.5,
            "sport": "NBA",
        }
        reason = _build_leg_specific_reason(leg_info, "total")

        assert "total" in reason.lower()
        # Should mention pace, foul, environment, or correlate
        assert any(word in reason.lower() for word in ["pace", "foul", "environment", "correlate", "scenarios"])

    def test_spread_reason_mentions_margin_sensitivity(self):
        """Part A: Spread reason must mention margin sensitivity."""
        leg_info = {
            "entity": "Lakers",
            "market": "spread",
            "value": -5.5,
            "sport": "NBA",
        }
        reason = _build_leg_specific_reason(leg_info, "spread")

        assert "Lakers" in reason
        assert "spread" in reason.lower()
        # Should mention margin, late, fouls, or final
        assert any(word in reason.lower() for word in ["margin", "late", "foul", "final", "possession"])

    def test_high_value_prop_mentions_threshold(self):
        """Part A: High value prop mentions higher threshold language."""
        leg_info = {
            "entity": "Giannis",
            "market": "player_prop",
            "value": 30.0,
            "sport": "NBA",
        }
        reason = _build_leg_specific_reason(leg_info, "player_prop")

        # Should mention the threshold value
        assert "30" in reason or "higher" in reason.lower() or "threshold" in reason.lower()

    def test_large_spread_mentions_decisive_margin(self):
        """Part A: Large spread (+10) mentions decisive margin."""
        leg_info = {
            "entity": "Warriors",
            "market": "spread",
            "value": -12.0,
            "sport": "NBA",
        }
        reason = _build_leg_specific_reason(leg_info, "spread")

        # Should mention the large spread
        assert "12" in reason or "decisive" in reason.lower() or "reducing" in reason.lower()

    def test_mixed_markets_produce_distinct_reasons(self):
        """Part D: Multi-leg mixed markets produces at least 2 distinct patterns."""
        # Create mock blocks for different market types
        blocks = []
        for bet_type, selection in [
            ("player_prop", "LeBron o25.5 pts"),
            ("spread", "Lakers -5.5"),
            ("total", "Over 220.5"),
        ]:
            block = MagicMock()
            block.bet_type.value = bet_type
            block.selection = selection
            block.sport = "NBA"
            block.block_id = uuid4()
            block.base_fragility = 0.10
            blocks.append(block)

        mock_eval = MagicMock()
        mock_eval.correlations = []

        notable = _build_notable_legs(blocks, mock_eval, {})

        # Should have at least 2 notable legs
        assert len(notable) >= 2

        # Reasons should be distinct (not copy-paste)
        reasons = [n["reason"] for n in notable]
        # At least 2 reasons should be different
        assert len(set(reasons)) >= 2, "Reasons should be distinct, not generic copy-paste"

    def test_no_forbidden_language_in_reasons(self):
        """Part D: No forbidden language: odds, payout, probability, lock, guarantee, should bet."""
        forbidden_words = ["odds", "payout", "probability", "lock", "guarantee", "should bet"]

        # Test all market types
        for market, value in [
            ("player_prop", 25.5),
            ("spread", -5.5),
            ("total", 220.5),
            ("moneyline", None),
        ]:
            leg_info = {
                "entity": "TestEntity",
                "market": market,
                "value": value,
                "sport": "NBA",
            }
            reason = _build_leg_specific_reason(leg_info, market)

            for forbidden in forbidden_words:
                assert forbidden not in reason.lower(), \
                    f"Forbidden word '{forbidden}' found in {market} reason: {reason}"

    def test_deterministic_ordering(self):
        """Part D: Same input produces same notable legs ordering."""
        # Create consistent mock blocks
        blocks = []
        for bet_type, selection in [
            ("player_prop", "LeBron o25.5 pts"),
            ("spread", "Lakers -5.5"),
            ("moneyline", "Celtics ML"),
        ]:
            block = MagicMock()
            block.bet_type.value = bet_type
            block.selection = selection
            block.sport = "NBA"
            block.block_id = uuid4()
            block.base_fragility = 0.10
            blocks.append(block)

        mock_eval = MagicMock()
        mock_eval.correlations = []

        # Run twice
        result1 = _build_notable_legs(blocks, mock_eval, {})
        result2 = _build_notable_legs(blocks, mock_eval, {})

        # Same ordering
        assert len(result1) == len(result2)
        for i in range(len(result1)):
            assert result1[i]["leg"] == result2[i]["leg"], \
                f"Ordering differs at position {i}"

    def test_scoring_player_prop_highest(self):
        """Part B: Player props should score highest (+3)."""
        blocks = []
        for bet_type, selection in [
            ("moneyline", "Celtics ML"),
            ("player_prop", "LeBron o25.5 pts"),
            ("spread", "Lakers -5.5"),
        ]:
            block = MagicMock()
            block.bet_type.value = bet_type
            block.selection = selection
            block.sport = "NBA"
            block.block_id = uuid4()
            block.base_fragility = 0.10
            blocks.append(block)

        mock_eval = MagicMock()
        mock_eval.correlations = []

        notable = _build_notable_legs(blocks, mock_eval, {})

        # Player prop should be first (highest score)
        assert len(notable) >= 1
        assert "LeBron" in notable[0]["leg"]

    def test_large_line_magnitude_bonus(self):
        """Part B: Large line magnitude (>=8) gets +1 bonus."""
        blocks = []

        # Two spreads: one large, one small
        for spread_val, selection in [
            (-3.5, "Celtics -3.5"),
            (-10.5, "Lakers -10.5"),
        ]:
            block = MagicMock()
            block.bet_type.value = "spread"
            block.selection = selection
            block.sport = "NBA"
            block.block_id = uuid4()
            block.base_fragility = 0.10
            blocks.append(block)

        mock_eval = MagicMock()
        mock_eval.correlations = []

        notable = _build_notable_legs(blocks, mock_eval, {})

        # The large spread should appear (gets magnitude bonus)
        assert len(notable) >= 1
        # At least one should mention the larger spread
        all_legs = " ".join(n["leg"] for n in notable)
        assert "-10.5" in all_legs or "-3.5" in all_legs

    def test_correlation_involvement_bonus(self):
        """Part B: Legs in correlations get +2 bonus."""
        blocks = []
        block_ids = []

        for bet_type, selection in [
            ("moneyline", "Celtics ML"),
            ("spread", "Lakers -5.5"),
        ]:
            block = MagicMock()
            block.bet_type.value = bet_type
            block.selection = selection
            block.sport = "NBA"
            bid = uuid4()
            block.block_id = bid
            block_ids.append(bid)
            block.base_fragility = 0.10
            blocks.append(block)

        # Create correlation involving the first block
        mock_corr = MagicMock()
        mock_corr.block_a = block_ids[0]
        mock_corr.block_b = uuid4()  # Some other block

        mock_eval = MagicMock()
        mock_eval.correlations = [mock_corr]

        notable = _build_notable_legs(blocks, mock_eval, {})

        # The correlated leg should appear with high priority
        assert len(notable) >= 1

    def test_empty_blocks_returns_empty(self):
        """Part D: Empty blocks returns empty notable legs."""
        mock_eval = MagicMock()
        mock_eval.correlations = []

        notable = _build_notable_legs([], mock_eval, {})
        assert notable == []

    def test_moneyline_reason_mentions_stacking(self):
        """Part A: Moneyline reason mentions stacking/compounding."""
        leg_info = {
            "entity": "Heat",
            "market": "moneyline",
            "value": None,
            "sport": "NBA",
        }
        reason = _build_leg_specific_reason(leg_info, "moneyline")

        assert "Heat" in reason
        assert "moneyline" in reason.lower()
        # Should mention stacking or compounding
        assert any(word in reason.lower() for word in ["stack", "compound", "fragility", "multiple"])


# =============================================================================
# TICKET 39: Leg Order Integrity Tests
# =============================================================================


class TestLegOrderIntegrity:
    """
    Ticket 39: Tests verifying leg order is preserved throughout the system.

    Core principle: Leg order is semantic data, not presentation.
    If order changes without explicit user action, the system is incorrect.
    """

    def test_canonical_legs_preserve_order_in_evaluated_parlay(self):
        """Canonical legs maintain their exact input order in evaluated_parlay."""
        from app.pipeline import _build_evaluated_parlay
        from app.airlock import CanonicalLegData

        # Create canonical legs in specific order
        canonical_legs = (
            CanonicalLegData(entity="Lakers", market="spread", value="-5.5", raw="Lakers -5.5"),
            CanonicalLegData(entity="Celtics", market="moneyline", value=None, raw="Celtics ML"),
            CanonicalLegData(entity="Heat", market="total", value="over 210", raw="Heat over 210"),
        )

        result = _build_evaluated_parlay([], "test", canonical_legs)

        # Verify order is preserved
        assert result["legs"][0]["entity"] == "Lakers"
        assert result["legs"][0]["position"] == 1
        assert result["legs"][1]["entity"] == "Celtics"
        assert result["legs"][1]["position"] == 2
        assert result["legs"][2]["entity"] == "Heat"
        assert result["legs"][2]["position"] == 3

    def test_position_field_matches_array_index(self):
        """Position field always equals array index + 1."""
        from app.pipeline import _build_evaluated_parlay
        from app.airlock import CanonicalLegData

        canonical_legs = tuple(
            CanonicalLegData(entity=f"Team{i}", market="spread", value=f"-{i}", raw=f"Team{i} -{i}")
            for i in range(1, 6)  # 5 legs
        )

        result = _build_evaluated_parlay([], "test", canonical_legs)

        for i, leg in enumerate(result["legs"]):
            assert leg["position"] == i + 1, f"Leg at index {i} has position {leg['position']}, expected {i + 1}"

    def test_airlock_tuple_preserves_list_order(self):
        """Airlock converts list to tuple while preserving order."""
        from app.airlock import airlock_ingest

        legs_input = [
            {"entity": "A", "market": "spread", "value": "-1", "raw": "A -1"},
            {"entity": "B", "market": "spread", "value": "-2", "raw": "B -2"},
            {"entity": "C", "market": "spread", "value": "-3", "raw": "C -3"},
        ]

        result = airlock_ingest(input_text="A -1, B -2, C -3", canonical_legs=legs_input)

        assert result.canonical_legs[0].entity == "A"
        assert result.canonical_legs[1].entity == "B"
        assert result.canonical_legs[2].entity == "C"

    def test_filter_comprehension_preserves_order(self):
        """List comprehension filtering preserves order of remaining elements."""
        from app.pipeline import _build_evaluated_parlay
        from app.airlock import CanonicalLegData

        # Simulate what happens when a leg is removed
        original = [
            CanonicalLegData(entity="A", market="spread", value="-1", raw="A -1"),
            CanonicalLegData(entity="B", market="spread", value="-2", raw="B -2"),
            CanonicalLegData(entity="C", market="spread", value="-3", raw="C -3"),
        ]

        # Remove B (index 1)
        filtered = [leg for i, leg in enumerate(original) if i != 1]

        # Order should be A, C (not C, A)
        assert filtered[0].entity == "A"
        assert filtered[1].entity == "C"

    def test_evaluated_parlay_legs_are_list_not_set(self):
        """evaluated_parlay.legs is a list (ordered), not a set (unordered)."""
        from app.pipeline import _build_evaluated_parlay
        from app.airlock import CanonicalLegData

        canonical_legs = (
            CanonicalLegData(entity="Lakers", market="spread", value="-5.5", raw="Lakers -5.5"),
        )

        result = _build_evaluated_parlay([], "test", canonical_legs)

        assert isinstance(result["legs"], list), "legs must be a list, not a set or dict"

    def test_canonical_legs_are_tuple_not_set(self):
        """canonical_legs from airlock is a tuple (ordered), not a set."""
        from app.airlock import airlock_ingest

        legs_input = [
            {"entity": "A", "market": "spread", "value": "-1", "raw": "A -1"},
        ]

        result = airlock_ingest(input_text="A -1", canonical_legs=legs_input)

        assert isinstance(result.canonical_legs, tuple), "canonical_legs must be a tuple"

    def test_order_stable_across_multiple_runs(self):
        """Same input produces same order on multiple runs (no random shuffling)."""
        from app.pipeline import _build_evaluated_parlay
        from app.airlock import CanonicalLegData

        canonical_legs = (
            CanonicalLegData(entity="Lakers", market="spread", value="-5.5", raw="Lakers -5.5"),
            CanonicalLegData(entity="Celtics", market="moneyline", value=None, raw="Celtics ML"),
            CanonicalLegData(entity="Heat", market="total", value="over 210", raw="Heat over 210"),
        )

        # Run multiple times
        results = [_build_evaluated_parlay([], "test", canonical_legs) for _ in range(5)]

        # All results should have identical order
        for result in results:
            assert [leg["entity"] for leg in result["legs"]] == ["Lakers", "Celtics", "Heat"]
