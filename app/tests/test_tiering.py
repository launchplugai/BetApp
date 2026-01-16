# app/tests/test_tiering.py
"""
Tests for Tier Gating System.

Required test vectors:
- Test A: GOOD strips suggestions and alerts
- Test B: BETTER allows suggestions + alerts
- Test C: Context restrictions per plan
- Test D: BEST allows demo endpoints
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tiering import (
    Plan,
    TierPolicy,
    parse_plan,
    get_policy,
    get_allowed_signals,
    validate_context_signals,
    apply_tier_to_response,
    apply_tier_to_builder_view,
    get_max_suggestions_for_plan,
    is_demo_allowed,
    ContextSignalNotAllowedError,
    GOOD_POLICY,
    BETTER_POLICY,
    BEST_POLICY,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# =============================================================================
# Test Vector A: GOOD strips suggestions and alerts
# =============================================================================


class TestVectorA_GoodStripsSuggestionsAndAlerts:
    """Test that GOOD plan strips suggestions and alerts."""

    def test_good_strips_suggestions_from_response(self, client):
        """GOOD plan request with candidates returns no suggestions."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-1",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 10.0,
                            "correlation_tags": [],
                        },
                    ],
                    "candidates": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-2",
                            "bet_type": "spread",
                            "selection": "Team B -7.5",
                            "base_fragility": 8.0,
                            "correlation_tags": [],
                        },
                    ],
                    "plan": "good",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # GOOD plan: suggestions should be null/empty
            assert data["suggestions"] is None or data["suggestions"] == []

    def test_good_policy_disallows_suggestions(self):
        """GOOD policy has suggestions_allowed=False."""
        assert GOOD_POLICY.suggestions_allowed is False
        assert GOOD_POLICY.max_suggestions == 0

    def test_good_policy_disallows_alerts(self):
        """GOOD policy has alerts_allowed=False."""
        assert GOOD_POLICY.alerts_allowed is False


# =============================================================================
# Test Vector B: BETTER allows suggestions + alerts
# =============================================================================


class TestVectorB_BetterAllowsSuggestionsAndAlerts:
    """Test that BETTER plan allows suggestions and alerts."""

    def test_better_returns_suggestions(self, client):
        """BETTER plan request with candidates returns suggestions."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-1",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 10.0,
                            "correlation_tags": [],
                        },
                    ],
                    "candidates": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-2",
                            "bet_type": "spread",
                            "selection": "Team B -7.5",
                            "base_fragility": 8.0,
                            "correlation_tags": [],
                        },
                    ],
                    "plan": "better",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # BETTER plan: suggestions should be present
            assert data["suggestions"] is not None
            assert len(data["suggestions"]) > 0

    def test_better_suggestions_limited_to_5(self, client):
        """BETTER plan limits suggestions to max 5."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            # Request many candidates
            candidates = [
                {
                    "sport": "NFL",
                    "game_id": f"test-game-{i}",
                    "bet_type": "spread",
                    "selection": f"Team {i} -3.5",
                    "base_fragility": 8.0,
                    "correlation_tags": [],
                }
                for i in range(10)
            ]

            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-0",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 10.0,
                            "correlation_tags": [],
                        },
                    ],
                    "candidates": candidates,
                    "max_suggestions": 10,  # Request 10
                    "plan": "better",
                },
            )

            assert response.status_code == 200
            data = response.json()

            # BETTER plan: max 5 suggestions
            if data["suggestions"]:
                assert len(data["suggestions"]) <= 5

    def test_better_policy_allows_suggestions(self):
        """BETTER policy has suggestions_allowed=True with max 5."""
        assert BETTER_POLICY.suggestions_allowed is True
        assert BETTER_POLICY.max_suggestions == 5

    def test_better_policy_allows_alerts(self):
        """BETTER policy has alerts_allowed=True."""
        assert BETTER_POLICY.alerts_allowed is True


# =============================================================================
# Test Vector C: Context restrictions
# =============================================================================


class TestVectorC_ContextRestrictions:
    """Test context signal restrictions per plan."""

    def test_good_allows_weather_only(self):
        """GOOD plan allows only weather signals."""
        allowed = get_allowed_signals(Plan.GOOD)
        assert allowed == {"weather"}

    def test_good_rejects_injury_signal(self, client):
        """GOOD plan + injury signal => rejected with 400."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-1",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 10.0,
                            "correlation_tags": [],
                        },
                    ],
                    "context_signals": [
                        {
                            "type": "injury",
                            "player_id": "player-1",
                            "player_name": "Test Player",
                            "status": "QUESTIONABLE",
                        },
                    ],
                    "plan": "good",
                },
            )

            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["code"] == "SIGNAL_NOT_ALLOWED"
            assert "injury" in data["detail"]["detail"].lower()

    def test_better_allows_weather_and_injury(self):
        """BETTER plan allows weather and injury signals."""
        allowed = get_allowed_signals(Plan.BETTER)
        assert allowed == {"weather", "injury"}

    def test_better_rejects_trade_signal(self, client):
        """BETTER plan + trade signal => rejected with 400."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-1",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 10.0,
                            "correlation_tags": [],
                        },
                    ],
                    "context_signals": [
                        {
                            "type": "trade",
                            "player_id": "player-1",
                            "player_name": "Traded Player",
                            "from_team_id": "team-a",
                            "to_team_id": "team-b",
                        },
                    ],
                    "plan": "better",
                },
            )

            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["code"] == "SIGNAL_NOT_ALLOWED"
            assert "trade" in data["detail"]["detail"].lower()

    def test_best_accepts_all_signals(self, client):
        """BEST plan accepts all signal types."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-1",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 10.0,
                            "correlation_tags": [],
                        },
                    ],
                    "context_signals": [
                        {
                            "type": "weather",
                            "game_id": "test-game-1",
                            "wind_mph": 20,
                            "precip": True,
                        },
                        {
                            "type": "injury",
                            "player_id": "player-1",
                            "player_name": "Test Player",
                            "status": "QUESTIONABLE",
                        },
                        {
                            "type": "trade",
                            "player_id": "player-2",
                            "player_name": "Traded Player",
                            "from_team_id": "team-a",
                            "to_team_id": "team-b",
                        },
                    ],
                    "plan": "best",
                },
            )

            assert response.status_code == 200

    def test_best_allows_all_signal_types(self):
        """BEST plan allows weather, injury, and trade signals."""
        allowed = get_allowed_signals(Plan.BEST)
        assert allowed == {"weather", "injury", "trade"}

    def test_validate_context_signals_raises_for_disallowed(self):
        """validate_context_signals raises ContextSignalNotAllowedError."""
        signals = [{"type": "trade"}]

        with pytest.raises(ContextSignalNotAllowedError) as exc_info:
            validate_context_signals(signals, Plan.GOOD)

        assert exc_info.value.signal_type == "trade"
        assert exc_info.value.plan == Plan.GOOD


# =============================================================================
# Test Vector D: BEST allows demo endpoints
# =============================================================================


class TestVectorD_BestAllowsDemoEndpoints:
    """Test that demo endpoints require BEST plan or override."""

    def test_demo_denied_for_good_plan(self, client):
        """GET /leading-light/demo denied for GOOD plan."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.get("/leading-light/demo?plan=good")

            assert response.status_code == 403
            data = response.json()
            assert data["detail"]["code"] == "DEMO_ACCESS_DENIED"

    def test_demo_denied_for_better_plan(self, client):
        """GET /leading-light/demo denied for BETTER plan."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.get("/leading-light/demo?plan=better")

            assert response.status_code == 403
            data = response.json()
            assert data["detail"]["code"] == "DEMO_ACCESS_DENIED"

    def test_demo_allowed_for_best_plan(self, client):
        """GET /leading-light/demo allowed for BEST plan."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.get("/leading-light/demo?plan=best")

            assert response.status_code == 200
            data = response.json()
            assert "cases" in data

    def test_demo_allowed_with_override(self, client):
        """GET /leading-light/demo allowed with env override even for GOOD plan."""
        with patch.dict(
            os.environ,
            {"LEADING_LIGHT_ENABLED": "true", "LEADING_LIGHT_DEMO_OVERRIDE": "true"},
        ):
            response = client.get("/leading-light/demo?plan=good")

            assert response.status_code == 200
            data = response.json()
            assert "cases" in data

    def test_run_demo_denied_for_good_plan(self, client):
        """POST /leading-light/demo/{case} denied for GOOD plan."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/stable?plan=good")

            assert response.status_code == 403
            data = response.json()
            assert data["detail"]["code"] == "DEMO_ACCESS_DENIED"

    def test_run_demo_allowed_for_best_plan(self, client):
        """POST /leading-light/demo/{case} allowed for BEST plan."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/stable?plan=best")

            assert response.status_code == 200
            data = response.json()
            assert data["inductor"]["level"] == "stable"

    def test_is_demo_allowed_function(self):
        """is_demo_allowed returns correct values."""
        # GOOD: not allowed
        assert is_demo_allowed(Plan.GOOD) is False
        # BETTER: not allowed
        assert is_demo_allowed(Plan.BETTER) is False
        # BEST: allowed
        assert is_demo_allowed(Plan.BEST) is True
        # Override: always allowed
        assert is_demo_allowed(Plan.GOOD, env_override=True) is True


# =============================================================================
# Additional Unit Tests
# =============================================================================


class TestParsePlan:
    """Tests for parse_plan function."""

    def test_parse_good(self):
        """Parse 'good' returns Plan.GOOD."""
        assert parse_plan("good") == Plan.GOOD
        assert parse_plan("GOOD") == Plan.GOOD
        assert parse_plan("Good") == Plan.GOOD

    def test_parse_better(self):
        """Parse 'better' returns Plan.BETTER."""
        assert parse_plan("better") == Plan.BETTER
        assert parse_plan("BETTER") == Plan.BETTER

    def test_parse_best(self):
        """Parse 'best' returns Plan.BEST."""
        assert parse_plan("best") == Plan.BEST
        assert parse_plan("BEST") == Plan.BEST

    def test_parse_none_defaults_to_good(self):
        """Parse None defaults to Plan.GOOD."""
        assert parse_plan(None) == Plan.GOOD

    def test_parse_invalid_defaults_to_good(self):
        """Parse invalid string defaults to Plan.GOOD."""
        assert parse_plan("invalid") == Plan.GOOD
        assert parse_plan("premium") == Plan.GOOD


class TestGetPolicy:
    """Tests for get_policy function."""

    def test_get_good_policy(self):
        """Get GOOD policy."""
        policy = get_policy(Plan.GOOD)
        assert policy.plan == Plan.GOOD
        assert policy.suggestions_allowed is False
        assert policy.alerts_allowed is False

    def test_get_better_policy(self):
        """Get BETTER policy."""
        policy = get_policy(Plan.BETTER)
        assert policy.plan == Plan.BETTER
        assert policy.suggestions_allowed is True
        assert policy.max_suggestions == 5
        assert policy.alerts_allowed is True

    def test_get_best_policy(self):
        """Get BEST policy."""
        policy = get_policy(Plan.BEST)
        assert policy.plan == Plan.BEST
        assert policy.suggestions_allowed is True
        assert policy.max_suggestions == 10
        assert policy.alerts_allowed is True
        assert policy.demo_endpoints_allowed is True


class TestGetMaxSuggestions:
    """Tests for get_max_suggestions_for_plan function."""

    def test_good_max_suggestions(self):
        """GOOD plan has 0 max suggestions."""
        assert get_max_suggestions_for_plan(Plan.GOOD) == 0

    def test_better_max_suggestions(self):
        """BETTER plan has 5 max suggestions."""
        assert get_max_suggestions_for_plan(Plan.BETTER) == 5

    def test_best_max_suggestions(self):
        """BEST plan has 10 max suggestions."""
        assert get_max_suggestions_for_plan(Plan.BEST) == 10


class TestApplyTierToResponse:
    """Tests for apply_tier_to_response function."""

    def test_good_strips_suggestions(self):
        """GOOD plan strips suggestions from response."""
        from uuid import uuid4
        from core.evaluation import (
            EvaluationResponse,
            InductorInfo,
            MetricsInfo,
            DNAInfo,
            Recommendation,
            RecommendationAction,
        )
        from core.risk_inductor import RiskInductor
        from core.models.leading_light import SuggestedBlock, SuggestedBlockLabel

        # Create response with suggestions
        response = EvaluationResponse(
            parlay_id=uuid4(),
            inductor=InductorInfo(
                level=RiskInductor.STABLE,
                explanation="Test",
            ),
            metrics=MetricsInfo(
                raw_fragility=20.0,
                final_fragility=20.0,
                leg_penalty=8.0,
                correlation_penalty=0.0,
                correlation_multiplier=1.0,
            ),
            correlations=(),
            dna=DNAInfo(
                violations=(),
                base_stake_cap=None,
                recommended_stake=None,
                max_legs=None,
                fragility_tolerance=None,
            ),
            recommendation=Recommendation(
                action=RecommendationAction.ACCEPT,
                reason="Test",
            ),
            suggestions=(
                SuggestedBlock(
                    candidate_block_id=uuid4(),
                    delta_fragility=5.0,
                    added_correlation=0.0,
                    dna_compatible=True,
                    label=SuggestedBlockLabel.LOWEST_ADDED_RISK,
                    reason="Test",
                ),
            ),
        )

        # Apply GOOD tier
        filtered = apply_tier_to_response(Plan.GOOD, response)

        # Suggestions should be stripped
        assert filtered.suggestions is None

    def test_better_keeps_suggestions_limited(self):
        """BETTER plan keeps suggestions but limits to 5."""
        from uuid import uuid4
        from core.evaluation import (
            EvaluationResponse,
            InductorInfo,
            MetricsInfo,
            DNAInfo,
            Recommendation,
            RecommendationAction,
        )
        from core.risk_inductor import RiskInductor
        from core.models.leading_light import SuggestedBlock, SuggestedBlockLabel

        # Create response with 10 suggestions
        suggestions = tuple(
            SuggestedBlock(
                candidate_block_id=uuid4(),
                delta_fragility=5.0 + i,
                added_correlation=0.0,
                dna_compatible=True,
                label=SuggestedBlockLabel.LOWEST_ADDED_RISK,
                reason=f"Test {i}",
            )
            for i in range(10)
        )

        response = EvaluationResponse(
            parlay_id=uuid4(),
            inductor=InductorInfo(
                level=RiskInductor.STABLE,
                explanation="Test",
            ),
            metrics=MetricsInfo(
                raw_fragility=20.0,
                final_fragility=20.0,
                leg_penalty=8.0,
                correlation_penalty=0.0,
                correlation_multiplier=1.0,
            ),
            correlations=(),
            dna=DNAInfo(
                violations=(),
                base_stake_cap=None,
                recommended_stake=None,
                max_legs=None,
                fragility_tolerance=None,
            ),
            recommendation=Recommendation(
                action=RecommendationAction.ACCEPT,
                reason="Test",
            ),
            suggestions=suggestions,
        )

        # Apply BETTER tier
        filtered = apply_tier_to_response(Plan.BETTER, response)

        # Suggestions should be limited to 5
        assert filtered.suggestions is not None
        assert len(filtered.suggestions) == 5


class TestPlanInRequest:
    """Tests for plan parameter in API request."""

    def test_default_plan_is_good(self, client):
        """Default plan is GOOD when not specified."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            # Request without plan - should default to GOOD
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-1",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 10.0,
                            "correlation_tags": [],
                        },
                    ],
                    "candidates": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-2",
                            "bet_type": "spread",
                            "selection": "Team B -7.5",
                            "base_fragility": 8.0,
                            "correlation_tags": [],
                        },
                    ],
                    # No plan specified
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Should behave like GOOD plan - no suggestions
            assert data["suggestions"] is None or data["suggestions"] == []

    def test_invalid_plan_rejected(self, client):
        """Invalid plan value is rejected with 422."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "test-game-1",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 10.0,
                            "correlation_tags": [],
                        },
                    ],
                    "plan": "premium",  # Invalid
                },
            )

            assert response.status_code == 422  # Validation error
