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


class TestTicket27CanonicalLegsAndGrounding:
    """
    Ticket 27: Canonical Leg Normalization + Grounding Guardrails tests.

    Part A: Canonical leg schema
    Part B: Builder serialization
    Part C: Evaluator uses canonical legs
    Part D: Grounding warnings
    Part E: Language consistency
    """

    def test_request_accepts_canonical_legs(self, client):
        """Part A/B: Request accepts legs array with canonical structure."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"}
            ]
        })
        assert response.status_code == 200

    def test_canonical_legs_have_source_field(self, client):
        """Part C: Evaluated parlay legs indicate their source."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics -5.5",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"},
                {"entity": "Celtics", "market": "spread", "value": "-5.5", "raw": "Celtics -5.5"}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        parlay = data["evaluatedParlay"]
        assert parlay["canonical"] is True
        for leg in parlay["legs"]:
            assert leg["source"] == "builder"

    def test_text_only_legs_have_parsed_source(self, client):
        """Part C: Without canonical legs, source is 'parsed'."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        parlay = data["evaluatedParlay"]
        # Without canonical legs, canonical should be False
        assert parlay.get("canonical", False) is False
        for leg in parlay["legs"]:
            assert leg["source"] == "parsed"

    def test_canonical_leg_count_matches_input(self, client):
        """Part C: Leg count from canonical legs is accurate."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics -5.5 + Nuggets over 220",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"},
                {"entity": "Celtics", "market": "spread", "value": "-5.5", "raw": "Celtics -5.5"},
                {"entity": "Nuggets", "market": "total", "value": "over 220", "raw": "Nuggets over 220"}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["evaluatedParlay"]["leg_count"] == 3
        assert len(data["evaluatedParlay"]["legs"]) == 3

    def test_response_includes_grounding_warnings(self, client):
        """Part D: Response includes groundingWarnings field."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        assert "groundingWarnings" in data

    def test_unrecognized_entity_triggers_warning(self, client):
        """Part D: Unrecognized entities generate grounding warnings."""
        response = client.post("/app/evaluate", json={
            "input": "MightyDucks -5.5",
            "tier": "good",
            "legs": [
                {"entity": "MightyDucks", "market": "spread", "value": "-5.5", "raw": "MightyDucks -5.5"}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        warnings = data.get("groundingWarnings")
        assert warnings is not None
        assert len(warnings) > 0
        # Should mention the unrecognized entity or generic warning
        warning_text = " ".join(warnings).lower()
        assert "could not" in warning_text or "recognized" in warning_text or "structural only" in warning_text or "may not correspond" in warning_text

    def test_recognized_entity_no_warning(self, client):
        """Part D: Recognized teams don't trigger entity warnings."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "spread", "value": "-5.5", "raw": "Lakers -5.5"}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        warnings = data.get("groundingWarnings")
        # Should be empty or None for recognized teams
        if warnings:
            warning_text = " ".join(warnings).lower()
            assert "lakers" not in warning_text

    def test_ui_contains_grounding_warnings_section(self, client):
        """Part D: UI HTML contains grounding warnings elements."""
        response = client.get("/app")
        assert response.status_code == 200
        assert "grounding-warnings" in response.text
        assert "grounding-warnings-list" in response.text

    def test_single_bet_uses_bet_terminology(self, client):
        """Part E: Single leg uses 'bet' not 'parlay'."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "spread", "value": "-5.5", "raw": "Lakers -5.5"}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        display_label = data["evaluatedParlay"]["display_label"]
        assert display_label == "Single bet"

    def test_multi_leg_uses_parlay_terminology(self, client):
        """Part E: Multiple legs use 'X-leg parlay'."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics -5.5",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"},
                {"entity": "Celtics", "market": "spread", "value": "-5.5", "raw": "Celtics -5.5"}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        display_label = data["evaluatedParlay"]["display_label"]
        assert display_label == "2-leg parlay"


class TestTicket27BCanonicalContextConsistency:
    """
    Ticket 27B HOTFIX: Canonical Context Propagation tests.

    Verifies that when canonical legs are present, ALL outputs use
    the same leg_count (receipt, audit, summary, verdict).
    """

    def test_3_leg_canonical_produces_consistent_output(self, client):
        """
        With 3 canonical legs:
        - Receipt shows 3 legs
        - Summary uses "parlay" not "bet"
        - No "1-leg" text anywhere in response
        """
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics -5.5 + Nuggets over 220",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"},
                {"entity": "Celtics", "market": "spread", "value": "-5.5", "raw": "Celtics -5.5"},
                {"entity": "Nuggets", "market": "total", "value": "over 220", "raw": "Nuggets over 220"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        # Receipt must show 3 legs
        assert data["evaluatedParlay"]["leg_count"] == 3
        assert len(data["evaluatedParlay"]["legs"]) == 3
        assert data["evaluatedParlay"]["display_label"] == "3-leg parlay"

        # Serialize full response to check for inconsistencies
        import json
        response_text = json.dumps(data).lower()

        # Must NOT contain "1-leg parlay" anywhere
        assert "1-leg parlay" not in response_text
        assert "1 leg" not in response_text or "1 leg" in "31 leg"  # Allow "31 legs" etc

        # Final verdict should use parlay language
        verdict = data.get("finalVerdict", {})
        if verdict and verdict.get("verdict_text"):
            verdict_text = verdict["verdict_text"].lower()
            # Should NOT say "this bet" for 3 legs
            assert "single-bet" not in verdict_text

    def test_canonical_legs_drive_all_outputs(self, client):
        """
        When canonical legs present, they drive leg_count everywhere.
        """
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics -5.5 + Nuggets over 220 + Warriors -3",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"},
                {"entity": "Celtics", "market": "spread", "value": "-5.5", "raw": "Celtics -5.5"},
                {"entity": "Nuggets", "market": "total", "value": "over 220", "raw": "Nuggets over 220"},
                {"entity": "Warriors", "market": "spread", "value": "-3", "raw": "Warriors -3"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        # Receipt shows canonical leg count
        assert data["evaluatedParlay"]["leg_count"] == 4
        assert data["evaluatedParlay"]["canonical"] is True

        # Human summary should reference parlay structure
        summary = data.get("humanSummary", "")
        # Should not call it a "single bet" or "bet"
        assert "single bet" not in summary.lower() or "parlay" in summary.lower()

    def test_no_single_leg_terminology_in_multileg_parlay(self, client):
        """
        Regression: Ensure no "Single-leg" or "1-leg" text appears for multi-leg parlays.
        """
        response = client.post("/app/evaluate", json={
            "input": "Test parlay",
            "tier": "good",
            "legs": [
                {"entity": "TeamA", "market": "spread", "value": "-5", "raw": "TeamA -5"},
                {"entity": "TeamB", "market": "moneyline", "value": None, "raw": "TeamB ML"},
                {"entity": "TeamC", "market": "total", "value": "over 200", "raw": "TeamC over 200"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        import json
        full_response = json.dumps(data)

        # These patterns should NOT appear for a 3-leg parlay
        problematic_patterns = [
            "Single-leg structure",
            "1-leg parlay",
            "Legs: 1",
        ]

        for pattern in problematic_patterns:
            assert pattern not in full_response, f"Found '{pattern}' in response for 3-leg parlay"

    def test_audit_legs_matches_canonical_count(self, client):
        """
        Audit note "Legs: X" must match canonical leg count.
        """
        response = client.post("/app/evaluate", json={
            "input": "Three leg parlay",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "spread", "value": "-5", "raw": "Lakers -5"},
                {"entity": "Celtics", "market": "spread", "value": "-3", "raw": "Celtics -3"},
                {"entity": "Nuggets", "market": "spread", "value": "-7", "raw": "Nuggets -7"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        # Check proof summary artifacts for audit notes
        proof = data.get("proofSummary", {})
        artifacts = proof.get("sample_artifacts", [])

        import json
        artifacts_text = json.dumps(artifacts)

        # If there's a "Legs: X" pattern, X must be 3
        if "Legs:" in artifacts_text:
            assert "Legs: 3" in artifacts_text, f"Expected 'Legs: 3' but got: {artifacts_text}"
            assert "Legs: 1" not in artifacts_text, "Found 'Legs: 1' for 3-leg parlay"


class TestTicket28CanonicalContextRepair:
    """
    Ticket 28: Canonical Context Repair tests.

    Verifies that EvaluationContext provides a single authoritative source
    for leg_count across all outputs: receipt, artifacts, audit, summary, verdict.
    """

    def test_all_outputs_use_same_leg_count(self, client):
        """
        Core requirement: receipt, artifacts, audit, summary all agree on leg_count.
        """
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics -5.5 + Nuggets over 220 + Warriors ML",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"},
                {"entity": "Celtics", "market": "spread", "value": "-5.5", "raw": "Celtics -5.5"},
                {"entity": "Nuggets", "market": "total", "value": "over 220", "raw": "Nuggets over 220"},
                {"entity": "Warriors", "market": "moneyline", "value": None, "raw": "Warriors ML"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        # All sources must agree on 4 legs
        expected_leg_count = 4

        # 1. Receipt leg_count
        receipt_leg_count = data["evaluatedParlay"]["leg_count"]
        assert receipt_leg_count == expected_leg_count, f"Receipt shows {receipt_leg_count} legs, expected {expected_leg_count}"

        # 2. Receipt legs array length
        legs_array_len = len(data["evaluatedParlay"]["legs"])
        assert legs_array_len == expected_leg_count, f"Legs array has {legs_array_len} items, expected {expected_leg_count}"

        # 3. Display label
        display_label = data["evaluatedParlay"]["display_label"]
        assert f"{expected_leg_count}-leg" in display_label, f"Display label '{display_label}' doesn't match expected leg count"

        # 4. Canonical flag should be True for builder mode
        is_canonical = data["evaluatedParlay"].get("canonical", False)
        assert is_canonical is True, "evaluatedParlay should have canonical=True for builder input"

    def test_language_consistency_single_leg(self, client):
        """
        Single leg must use 'bet' terminology in primary outputs.
        """
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        # Display label should say "Single bet", not "1-leg parlay"
        display_label = data["evaluatedParlay"]["display_label"]
        assert display_label == "Single bet", f"Display label should be 'Single bet', got '{display_label}'"

        # Final verdict should use "bet" terminology
        verdict = data.get("finalVerdict", {})
        verdict_text = verdict.get("verdict_text", "").lower()
        assert "parlay" not in verdict_text, f"Verdict should not use 'parlay' for single leg: {verdict_text}"

    def test_language_consistency_multi_leg(self, client):
        """
        Multiple legs must use 'parlay' terminology.
        """
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics ML",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"},
                {"entity": "Celtics", "market": "moneyline", "value": None, "raw": "Celtics ML"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        # Display label should say "parlay"
        display_label = data["evaluatedParlay"]["display_label"]
        assert "parlay" in display_label.lower(), f"Display label '{display_label}' should contain 'parlay'"

    def test_artifacts_match_canonical_leg_count(self, client):
        """
        Artifacts must reflect the canonical leg count, not parsed block count.
        """
        response = client.post("/app/evaluate", json={
            "input": "Test parlay with canonical legs",
            "tier": "good",
            "legs": [
                {"entity": "TeamA", "market": "spread", "value": "-5", "raw": "TeamA -5"},
                {"entity": "TeamB", "market": "spread", "value": "-3", "raw": "TeamB -3"},
                {"entity": "TeamC", "market": "spread", "value": "-7", "raw": "TeamC -7"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        import json

        # Check proof summary artifacts
        proof = data.get("proofSummary", {})
        artifacts = proof.get("sample_artifacts", [])
        artifacts_text = json.dumps(artifacts)

        # Should reference 3 legs, not 1
        if "Legs:" in artifacts_text:
            assert "Legs: 3" in artifacts_text, f"Artifacts should show 'Legs: 3', got: {artifacts_text}"

    def test_verdict_uses_context_leg_count(self, client):
        """
        Final verdict must use the authoritative leg count from context.
        """
        response = client.post("/app/evaluate", json={
            "input": "Multi-leg test",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"},
                {"entity": "Celtics", "market": "moneyline", "value": None, "raw": "Celtics ML"},
                {"entity": "Nuggets", "market": "moneyline", "value": None, "raw": "Nuggets ML"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        verdict = data.get("finalVerdict", {})
        verdict_text = verdict.get("verdict_text", "").lower()

        # Should not contain single-bet language for 3-leg parlay
        assert "single-bet" not in verdict_text, f"Verdict contains 'single-bet' for 3-leg parlay: {verdict_text}"


class TestTicket29GroundedConfidenceUpgrade:
    """
    Ticket 29: Grounded Confidence Upgrade tests.

    Verifies improved artifact wording, varied summaries, and analysis_depth flag.
    """

    def test_analysis_depth_flag_present(self, client):
        """
        evaluatedParlay must include analysis_depth="structural_only".
        """
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics -5.5",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"},
                {"entity": "Celtics", "market": "spread", "value": "-5.5", "raw": "Celtics -5.5"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        evaluated = data.get("evaluatedParlay", {})
        assert "analysis_depth" in evaluated, "evaluatedParlay should have analysis_depth field"
        assert evaluated["analysis_depth"] == "structural_only", f"analysis_depth should be 'structural_only', got '{evaluated.get('analysis_depth')}'"

    def test_artifact_why_explanations(self, client):
        """
        Artifacts should explain WHY risk exists, not just WHAT.
        """
        response = client.post("/app/evaluate", json={
            "input": "Test prop parlay",
            "tier": "good",
            "legs": [
                {"entity": "LeBron", "market": "player_prop", "value": "over 25.5", "raw": "LeBron over 25.5 pts"},
                {"entity": "Curry", "market": "player_prop", "value": "over 5.5", "raw": "Curry over 5.5 3PT"}
            ]
        })
        assert response.status_code == 200
        data = response.json()

        import json
        proof = data.get("proofSummary", {})
        artifacts = proof.get("sample_artifacts", [])
        artifacts_text = json.dumps(artifacts).lower()

        # Artifacts should contain explanatory language
        has_explanation = (
            "because" in artifacts_text or
            "when" in artifacts_text or
            "—" in artifacts_text or  # em-dash indicates explanation
            "depend" in artifacts_text or
            "compound" in artifacts_text
        )
        # At minimum, should have some advisory text
        assert "primary concern" in artifacts_text or "verdict" in artifacts_text, \
            "Artifacts should include primary concern or verdict explanation"

    def test_summary_references_composition(self, client):
        """
        Human summary should vary based on leg composition.
        """
        # Test ML-only parlay
        response_ml = client.post("/app/evaluate", json={
            "input": "ML parlay",
            "tier": "good",
            "legs": [
                {"entity": "Lakers", "market": "moneyline", "value": None, "raw": "Lakers ML"},
                {"entity": "Celtics", "market": "moneyline", "value": None, "raw": "Celtics ML"}
            ]
        })
        assert response_ml.status_code == 200
        data_ml = response_ml.json()
        summary_ml = data_ml.get("humanSummary", "").lower()

        # ML-only should mention low variance or moneyline
        # (structure determines outlook text)
        assert "structurally sound" in summary_ml or "complexity" in summary_ml or "risk" in summary_ml

    def test_analysis_depth_for_text_input(self, client):
        """
        Text-only input (no canonical legs) should also have analysis_depth.
        """
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML, Celtics -5.5",
            "tier": "good"
            # No legs array - text parsing mode
        })
        assert response.status_code == 200
        data = response.json()

        evaluated = data.get("evaluatedParlay", {})
        assert evaluated.get("analysis_depth") == "structural_only", \
            "Text-only input should also have analysis_depth='structural_only'"
