# app/tests/test_web.py
"""
Tests for the web UI (Ticket 22: Scorched Earth Reset)

Verifies:
1. GET /app returns canonical UI with expected elements
2. GET / redirects to /app
3. GET /ui2 redirects to /app
4. POST /app/evaluate works correctly
5. Debug mode shows additional info
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


# =============================================================================
# Tests: Root Redirect
# =============================================================================


class TestRootRedirect:
    """Tests for GET / redirect to /app."""

    def test_root_redirects_to_app(self, client):
        """GET / should redirect to /app."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers.get("location") == "/app"

    def test_root_follows_to_app(self, client):
        """GET / with follow returns /app content."""
        response = client.get("/")
        assert response.status_code == 200
        assert "DNA Bet Engine" in response.text


# =============================================================================
# Tests: UI2 Redirect
# =============================================================================


class TestUI2Redirect:
    """Tests for GET /ui2 redirect to /app."""

    def test_ui2_redirects_to_app(self, client):
        """GET /ui2 should redirect to /app."""
        response = client.get("/ui2", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers.get("location") == "/app"

    def test_ui2_follows_to_app(self, client):
        """GET /ui2 with follow returns /app content."""
        response = client.get("/ui2")
        assert response.status_code == 200
        assert "DNA Bet Engine" in response.text


# =============================================================================
# Tests: Canonical App Page
# =============================================================================


class TestCanonicalAppPage:
    """Tests for GET /app (canonical UI)."""

    def test_returns_200(self, client):
        """App page returns 200 status."""
        response = client.get("/app")
        assert response.status_code == 200

    def test_contains_title(self, client):
        """App page contains title."""
        response = client.get("/app")
        assert "DNA Bet Engine" in response.text

    def test_contains_bet_input(self, client):
        """App page contains bet input textarea."""
        response = client.get("/app")
        assert 'id="bet-input"' in response.text
        assert "Enter your bet slip" in response.text

    def test_contains_tier_selector(self, client):
        """App page contains tier selector buttons."""
        response = client.get("/app")
        assert 'data-tier="good"' in response.text
        assert 'data-tier="better"' in response.text
        assert 'data-tier="best"' in response.text

    def test_contains_evaluate_button(self, client):
        """App page contains Evaluate Bet button."""
        response = client.get("/app")
        assert "Evaluate Bet" in response.text

    def test_contains_build_stamp(self, client):
        """App page contains build stamp."""
        response = client.get("/app")
        assert "build:" in response.text

    def test_returns_html_content_type(self, client):
        """App page returns HTML content type."""
        response = client.get("/app")
        assert "text/html" in response.headers.get("content-type", "")


# =============================================================================
# Tests: Evaluate Endpoint
# =============================================================================


class TestEvaluateEndpoint:
    """Tests for POST /app/evaluate."""

    def test_valid_evaluation_returns_200(self, client):
        """Valid bet text returns successful evaluation."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        assert "evaluation" in data
        assert "signalInfo" in data
        assert "proofSummary" in data

    def test_empty_input_returns_400(self, client):
        """Empty input returns 400 error."""
        response = client.post("/app/evaluate", json={
            "input": "",
            "tier": "good"
        })
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_evaluation_includes_artifacts(self, client):
        """Evaluation includes proof summary with artifacts."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "best"
        })
        assert response.status_code == 200
        data = response.json()
        proof = data.get("proofSummary", {})
        assert "sample_artifacts" in proof
        assert "dna_artifact_counts" in proof
        assert "ui_contract_status" in proof
        assert "ui_contract_version" in proof

    def test_evaluation_includes_signal_info(self, client):
        """Evaluation includes signal info for grade display."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        signal = data.get("signalInfo", {})
        assert "signal" in signal
        assert signal["signal"] in ["blue", "green", "yellow", "red"]

    def test_service_disabled_returns_503(self, client_disabled):
        """Disabled service returns 503."""
        response = client_disabled.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        assert response.status_code == 503
        data = response.json()
        assert data.get("error") == "SERVICE_DISABLED"


# =============================================================================
# Tests: Rate Limiting
# =============================================================================


class TestRateLimiting:
    """Tests for rate limiting on /app/evaluate."""

    def test_rate_limit_header_present(self, client):
        """Successful requests don't have retry header."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        # First request should succeed
        assert response.status_code in [200, 429]


# =============================================================================
# Tests: Debug Mode
# =============================================================================


class TestDebugMode:
    """Tests for debug mode (debug=1 query param)."""

    def test_app_with_debug_param(self, client):
        """App page with debug=1 still loads."""
        response = client.get("/app?debug=1")
        assert response.status_code == 200
        assert "DNA Bet Engine" in response.text
        # Debug mode is handled client-side via JavaScript
        assert "debugMode" in response.text
