# app/tests/test_web.py
"""
Tests for the web UI boundary layer.

These tests verify:
1. Landing page returns 200 with expected markers
2. App page returns 200
3. Evaluation proxy validates input
4. Tier enforcement works correctly
"""
import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with Leading Light enabled."""
    os.environ["LEADING_LIGHT_ENABLED"] = "true"
    from app.main import app
    return TestClient(app)


@pytest.fixture
def client_disabled():
    """Create test client with Leading Light disabled."""
    os.environ["LEADING_LIGHT_ENABLED"] = "false"
    from app.main import app
    return TestClient(app)


class TestLandingPage:
    """Tests for GET / endpoint."""

    def test_returns_200(self, client):
        """Landing page returns 200 status."""
        response = client.get("/")
        assert response.status_code == 200

    def test_contains_service_name(self, client):
        """Landing page contains service name marker."""
        response = client.get("/")
        assert "DNA Matrix" in response.text

    def test_contains_leading_light(self, client):
        """Landing page contains Leading Light marker."""
        response = client.get("/")
        assert "Leading Light" in response.text

    def test_contains_app_link(self, client):
        """Landing page contains link to /app."""
        response = client.get("/")
        assert "/app" in response.text

    def test_contains_health_link(self, client):
        """Landing page contains link to /health."""
        response = client.get("/")
        assert "/health" in response.text

    def test_returns_html_content_type(self, client):
        """Landing page returns HTML content type."""
        response = client.get("/")
        assert "text/html" in response.headers.get("content-type", "")


class TestAppPage:
    """Tests for GET /app endpoint."""

    def test_returns_200(self, client):
        """App page returns 200 status."""
        response = client.get("/app")
        assert response.status_code == 200

    def test_contains_form_elements(self, client):
        """App page contains expected form elements."""
        response = client.get("/app")
        # Check for textarea
        assert "bet-input" in response.text
        # Check for tier selector
        assert "tier-good" in response.text
        assert "tier-better" in response.text
        assert "tier-best" in response.text
        # Check for submit button
        assert "Evaluate" in response.text

    def test_returns_html_content_type(self, client):
        """App page returns HTML content type."""
        response = client.get("/app")
        assert "text/html" in response.headers.get("content-type", "")


class TestEvaluateProxy:
    """Tests for POST /app/evaluate endpoint."""

    def test_empty_input_returns_422(self, client):
        """Empty input returns 422 validation error."""
        response = client.post(
            "/app/evaluate",
            json={"input": "", "tier": "good"}
        )
        assert response.status_code == 422

    def test_whitespace_input_returns_422(self, client):
        """Whitespace-only input returns 422 validation error."""
        response = client.post(
            "/app/evaluate",
            json={"input": "   ", "tier": "good"}
        )
        assert response.status_code == 422

    def test_missing_input_returns_422(self, client):
        """Missing input field returns 422 validation error."""
        response = client.post(
            "/app/evaluate",
            json={"tier": "good"}
        )
        assert response.status_code == 422

    def test_invalid_tier_returns_422(self, client):
        """Invalid tier returns 422 validation error."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "invalid"}
        )
        assert response.status_code == 422

    def test_missing_tier_returns_422(self, client):
        """Missing tier returns 422 validation error."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5"}
        )
        assert response.status_code == 422

    def test_valid_request_returns_200(self, client):
        """Valid request returns 200 with evaluation data."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "evaluation" in data
        assert "interpretation" in data
        assert "explain" in data

    def test_service_disabled_returns_503(self, client_disabled):
        """Returns 503 when Leading Light is disabled."""
        response = client_disabled.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"}
        )
        assert response.status_code == 503


class TestTierEnforcement:
    """Tests for tier-based explain filtering."""

    def test_tier_good_returns_empty_explain(self, client):
        """GOOD tier returns empty explain dict."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"}
        )
        assert response.status_code == 200
        data = response.json()
        # GOOD tier should have empty explain
        assert data["explain"] == {}

    def test_tier_better_returns_summary_only(self, client):
        """BETTER tier returns explain with summary only."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "better"}
        )
        assert response.status_code == 200
        data = response.json()
        explain = data["explain"]
        # BETTER should have summary
        assert "summary" in explain
        # BETTER should NOT have alerts or recommended_next_step
        assert "alerts" not in explain
        assert "recommended_next_step" not in explain

    def test_tier_best_returns_full_explain(self, client):
        """BEST tier returns full explain with all fields."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "best"}
        )
        assert response.status_code == 200
        data = response.json()
        explain = data["explain"]
        # BEST should have all fields
        assert "summary" in explain
        assert "alerts" in explain
        assert "recommended_next_step" in explain

    def test_tier_case_insensitive(self, client):
        """Tier values are case-insensitive."""
        for tier in ["GOOD", "Good", "good", "BETTER", "Better", "BEST", "Best"]:
            response = client.post(
                "/app/evaluate",
                json={"input": "Lakers -5.5", "tier": tier}
            )
            assert response.status_code == 200, f"Failed for tier: {tier}"

    def test_evaluation_always_present(self, client):
        """Evaluation data is always present regardless of tier."""
        for tier in ["good", "better", "best"]:
            response = client.post(
                "/app/evaluate",
                json={"input": "Lakers -5.5 parlay", "tier": tier}
            )
            assert response.status_code == 200
            data = response.json()
            # Evaluation should always be present
            assert "evaluation" in data
            assert "parlay_id" in data["evaluation"]
            assert "inductor" in data["evaluation"]
            assert "metrics" in data["evaluation"]
            assert "recommendation" in data["evaluation"]
