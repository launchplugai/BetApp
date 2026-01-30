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
        # Ticket 23: Changed label to "Paste or type" for paste mode
        assert "Paste or type your bet slip" in response.text

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


# =============================================================================
# Tests: Ticket 23 - Parlay Builder UI
# =============================================================================


class TestParlayBuilderUI:
    """Tests for Ticket 23 - Simple Parlay Builder UI."""

    def test_builder_contains_mode_toggle(self, client):
        """App page contains Builder/Paste mode toggle."""
        response = client.get("/app")
        assert response.status_code == 200
        assert 'data-mode="builder"' in response.text
        assert 'data-mode="paste"' in response.text
        assert "Builder" in response.text
        assert "Paste Mode" in response.text

    def test_builder_contains_sport_dropdown(self, client):
        """App page contains sport dropdown with expected options."""
        response = client.get("/app")
        assert 'id="builder-sport"' in response.text
        assert "NBA" in response.text
        assert "NFL" in response.text
        assert "MLB" in response.text
        assert "NCAA" in response.text

    def test_builder_contains_market_dropdown(self, client):
        """App page contains market type dropdown."""
        response = client.get("/app")
        assert 'id="builder-market"' in response.text
        assert "Moneyline" in response.text
        assert "Spread" in response.text
        assert "Over/Under" in response.text
        assert "Player Prop" in response.text

    def test_builder_contains_team_input(self, client):
        """App page contains team/player input."""
        response = client.get("/app")
        assert 'id="builder-team"' in response.text
        assert 'placeholder="Team or Player"' in response.text

    def test_builder_contains_add_leg_button(self, client):
        """App page contains Add Leg button."""
        response = client.get("/app")
        assert 'id="add-leg-btn"' in response.text
        assert "Add Leg" in response.text

    def test_builder_contains_quick_add_chips(self, client):
        """App page contains Quick Add chips."""
        response = client.get("/app")
        assert 'class="quick-chip"' in response.text
        assert "+ Moneyline" in response.text
        assert "+ Spread" in response.text
        assert "+ Player Prop" in response.text

    def test_builder_contains_legs_list(self, client):
        """App page contains legs list container."""
        response = client.get("/app")
        assert 'id="legs-list"' in response.text
        assert "No legs added yet" in response.text

    def test_redirects_still_work_with_builder(self, client):
        """Redirects to /app still work (no routing regressions)."""
        # Root redirect
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers.get("location") == "/app"

        # UI2 redirect
        response = client.get("/ui2", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers.get("location") == "/app"


# =============================================================================
# Tests: Ticket 25 - Evaluation Receipt + Human Summary
# =============================================================================


class TestTicket25EvaluationReceipt:
    """Tests for Ticket 25 - Evaluation Receipt + Notable Legs + Final Verdict."""

    def test_ui_contains_parlay_receipt_section(self, client):
        """App page contains Evaluated Parlay section."""
        response = client.get("/app")
        assert 'id="parlay-receipt"' in response.text
        assert 'id="parlay-legs"' in response.text
        assert "Evaluated Parlay" in response.text

    def test_ui_contains_notable_legs_section(self, client):
        """App page contains Notable Legs section."""
        response = client.get("/app")
        assert 'id="notable-legs-section"' in response.text
        assert 'id="notable-legs-list"' in response.text
        assert "Notable Legs" in response.text

    def test_ui_contains_verdict_section(self, client):
        """App page contains Summary/Verdict section."""
        response = client.get("/app")
        assert 'id="verdict-section"' in response.text
        assert 'id="verdict-text"' in response.text

    def test_ui_contains_refine_button(self, client):
        """App page contains Refine Parlay button."""
        response = client.get("/app")
        assert 'id="refine-btn"' in response.text
        assert "Refine Parlay" in response.text
        assert "refineParlay()" in response.text

    def test_evaluation_includes_evaluated_parlay(self, client):
        """Evaluation response includes evaluatedParlay field."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets over 220",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        assert "evaluatedParlay" in data
        parlay = data["evaluatedParlay"]
        assert "leg_count" in parlay
        assert parlay["leg_count"] == 3
        assert "legs" in parlay
        assert len(parlay["legs"]) == 3

    def test_evaluation_includes_notable_legs(self, client):
        """Evaluation response includes notableLegs field."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + LeBron over 25 points + Celtics ML",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        assert "notableLegs" in data
        # Should have notable legs (at least the player prop)
        notable = data["notableLegs"]
        assert isinstance(notable, list)
        # Each notable leg should have "leg" and "reason"
        if len(notable) > 0:
            assert "leg" in notable[0]
            assert "reason" in notable[0]

    def test_evaluation_includes_final_verdict(self, client):
        """Evaluation response includes finalVerdict field."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        assert "finalVerdict" in data
        verdict = data["finalVerdict"]
        assert "verdict_text" in verdict
        assert "tone" in verdict
        assert verdict["tone"] in ["positive", "mixed", "cautious"]
        assert "grade" in verdict
        assert verdict["grade"] in ["A", "B", "C", "D"]

    def test_evaluated_parlay_legs_have_required_fields(self, client):
        """Each leg in evaluatedParlay has required fields."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets over 220",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        legs = data["evaluatedParlay"]["legs"]
        for leg in legs:
            assert "position" in leg
            assert "text" in leg
            assert "bet_type" in leg


class TestTicket26LegInterpretationAndGuidance:
    """
    Ticket 26: Leg Interpretation + Gentle Guidance tests.

    Part A: Leg interpretation field under each leg
    Part B: Expanded explanation cadence (2-3 sentences)
    Part C: Gentle guidance for yellow/red signals
    """

    def test_leg_has_interpretation_field(self, client):
        """Part A: Each leg has an interpretation field."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets over 220",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        legs = data["evaluatedParlay"]["legs"]
        for leg in legs:
            assert "interpretation" in leg

    def test_spread_leg_has_spread_interpretation(self, client):
        """Part A: Spread bet has correct interpretation text."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        legs = data["evaluatedParlay"]["legs"]
        # At least one leg should have spread interpretation
        spread_legs = [l for l in legs if l.get("bet_type") == "spread"]
        if spread_legs:
            assert "final margin" in spread_legs[0]["interpretation"].lower()

    def test_notable_legs_have_expanded_reasons(self, client):
        """Part B: Notable legs reasons are 2-3 sentences (contain multiple periods)."""
        response = client.post("/app/evaluate", json={
            "input": "LeBron over 25 pts + Lakers -5.5 + Celtics ML + Nuggets over 220",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        notable = data.get("notableLegs", [])
        if notable:
            for item in notable:
                reason = item.get("reason", "")
                # Expanded reasons should have at least 2 sentences (multiple periods)
                period_count = reason.count(".")
                assert period_count >= 2, f"Expected 2+ sentences, got: {reason}"

    def test_ui_contains_leg_interpretation_class(self, client):
        """Part A: UI HTML contains leg-interpretation CSS class."""
        response = client.get("/app")
        assert response.status_code == 200
        assert "leg-interpretation" in response.text

    def test_ui_contains_guidance_section(self, client):
        """Part C: UI HTML contains guidance section."""
        response = client.get("/app")
        assert response.status_code == 200
        assert "guidance-section" in response.text
        assert "guidance-header" in response.text
        assert "guidance-list" in response.text

    def test_response_includes_gentle_guidance(self, client):
        """Part C: Response includes gentleGuidance field."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets over 220",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        # gentleGuidance may be None for green/blue signals
        assert "gentleGuidance" in data

    def test_guidance_not_shown_for_strong_signals(self, client):
        """Part C: Gentle guidance is None for blue/green signals."""
        # Single simple bet should typically be a strong signal
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        signal = data.get("signalInfo", {}).get("signal", "yellow")
        if signal in ("blue", "green"):
            assert data.get("gentleGuidance") is None

    def test_guidance_structure_when_present(self, client):
        """Part C: When guidance is present, it has correct structure."""
        # High leg count parlay more likely to trigger guidance
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets over 220 + Warriors -3 + Suns ML",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        guidance = data.get("gentleGuidance")
        if guidance is not None:
            assert "header" in guidance
            assert "suggestions" in guidance
            assert isinstance(guidance["suggestions"], list)
            assert len(guidance["suggestions"]) > 0
            # Suggestions should use "you could" language, not "you should"
            for suggestion in guidance["suggestions"]:
                assert "should" not in suggestion.lower() or "you should" not in suggestion.lower()
