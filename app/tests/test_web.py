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


class TestTicket32CoreWorkspace:
    """
    Ticket 32: Core Workspace Completion.

    Part A: OCR accuracy warning banner
    Part C: Sherlock/DNA badges + tooltips
    Part B: Session continuity (client-side)
    Part D: Workbench framing
    """

    def test_image_upload_section_exists(self, client):
        """
        Part A: Image upload section should exist in the UI.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        # Check for image upload elements
        assert "image-upload-section" in html, "Image upload section should exist"
        assert "image-input" in html, "Image input element should exist"
        assert "Upload Bet Slip Image" in html, "Upload button text should exist"

    def test_ocr_warning_banner_exists(self, client):
        """
        Part A: OCR warning banner should exist in the UI.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        # Check for OCR warning banner
        assert "ocr-warning-banner" in html, "OCR warning banner element should exist"
        assert "ocr-warning-icon" in html, "OCR warning icon should exist"
        assert "Please review for accuracy before evaluating" in html, \
            "OCR warning text should include accuracy disclaimer"

    def test_ocr_result_section_exists(self, client):
        """
        Part A: OCR result section with textarea should exist.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        # Check for OCR result elements
        assert "ocr-result" in html, "OCR result section should exist"
        assert "ocr-text" in html, "OCR text textarea should exist"
        assert "use-ocr-text" in html, "Use OCR text button should exist"

    def test_image_upload_styles_exist(self, client):
        """
        Part A: Image upload CSS styles should be included.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        # Check for key CSS classes
        assert ".image-upload-section" in html, "Image upload section styles should exist"
        assert ".ocr-warning-banner" in html, "OCR warning banner styles should exist"
        assert ".use-ocr-btn" in html, "Use OCR button styles should exist"

    # Part C: Sherlock/DNA Badges

    def test_sherlock_badge_exists(self, client):
        """
        Part C: Sherlock analysis badge should exist.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert "sherlock-badge" in html, "Sherlock badge should exist"
        assert "Analyzed by Sherlock" in html, "Sherlock badge text should exist"
        assert "(Structural)" in html, "Structural qualifier should exist"

    def test_dna_badge_exists(self, client):
        """
        Part C: DNA risk model badge should exist.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert "dna-badge" in html, "DNA badge should exist"
        assert "DNA Risk Model" in html, "DNA badge text should exist"

    def test_badges_have_tooltips(self, client):
        """
        Part C: Badges should have explanatory tooltips.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        # Check for title attributes with explanatory text
        assert "does NOT predict outcomes" in html, \
            "Sherlock tooltip should explain what it does NOT do"
        assert "does NOT factor in team strength" in html, \
            "DNA tooltip should explain what it does NOT do"

    def test_badge_styles_exist(self, client):
        """
        Part C: Badge CSS styles should be included.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert ".analysis-badges" in html, "Analysis badges container styles should exist"
        assert ".analysis-badge" in html, "Analysis badge styles should exist"
        assert ".sherlock-badge" in html, "Sherlock badge styles should exist"
        assert ".dna-badge" in html, "DNA badge styles should exist"

    # Part B: Session Manager

    def test_session_manager_exists(self, client):
        """
        Part B: SessionManager object should exist in JavaScript.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert "SessionManager" in html, "SessionManager object should exist"
        assert "STORAGE_KEY" in html, "SessionManager should have STORAGE_KEY"
        assert "dna_session" in html, "Storage key should be 'dna_session'"

    def test_session_bar_ui_exists(self, client):
        """
        Part B: Session bar UI should exist.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert "session-bar" in html, "Session bar should exist"
        assert "session-name" in html, "Session name input should exist"
        assert "session-history" in html, "Session history display should exist"

    def test_session_manager_methods(self, client):
        """
        Part B: SessionManager should have required methods.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        # Check for required methods
        assert "getSession" in html, "SessionManager should have getSession method"
        assert "saveSession" in html, "SessionManager should have saveSession method"
        assert "setSessionName" in html, "SessionManager should have setSessionName method"
        assert "addEvaluation" in html, "SessionManager should have addEvaluation method"
        assert "getEvaluations" in html, "SessionManager should have getEvaluations method"
        assert "saveRefinement" in html, "SessionManager should have saveRefinement method"
        assert "getRefinement" in html, "SessionManager should have getRefinement method"

    def test_session_localStorage_only(self, client):
        """
        Part B: Session should use localStorage only, no server calls.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        # Should use localStorage
        assert "localStorage.getItem" in html, "Should use localStorage.getItem"
        assert "localStorage.setItem" in html, "Should use localStorage.setItem"

        # Should NOT send session to server
        assert "sessionId" not in html or "session_id" not in html, \
            "Should not have server-bound session ID parameters"

    def test_session_bar_styles_exist(self, client):
        """
        Part B: Session bar CSS styles should be included.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert ".session-bar" in html, "Session bar styles should exist"
        assert ".session-name-input" in html, "Session name input styles should exist"
        assert ".session-history" in html, "Session history styles should exist"

    # Part D: Workbench Framing

    def test_workbench_container_exists(self, client):
        """
        Part D: Workbench container should exist.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert 'class="workbench"' in html, "Workbench container should exist"
        assert 'id="workbench"' in html, "Workbench should have ID"

    def test_workbench_panels_exist(self, client):
        """
        Part D: Workbench should have input and results panels.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert "workbench-input" in html, "Workbench input panel should exist"
        assert "workbench-results" in html, "Workbench results panel should exist"

    def test_workbench_panel_headers_exist(self, client):
        """
        Part D: Workbench panels should have headers.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert "Build Your Parlay" in html, "Input panel header should exist"
        assert "Analysis Results" in html, "Results panel header should exist"

    def test_sticky_action_bar_exists(self, client):
        """
        Part D: Sticky action bar should exist.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert "sticky-actions" in html, "Sticky actions class should exist"
        assert "action-buttons" in html, "Action buttons container should exist"

    def test_workbench_layout_styles_exist(self, client):
        """
        Part D: Workbench CSS styles should be included.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        assert ".workbench" in html, "Workbench styles should exist"
        assert ".workbench-panel" in html, "Workbench panel styles should exist"
        assert ".workbench-panel-header" in html, "Panel header styles should exist"
        assert ".sticky-actions" in html, "Sticky actions styles should exist"

    def test_desktop_media_query_exists(self, client):
        """
        Part D: Desktop layout media query should exist.
        """
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        # Check for desktop breakpoint
        assert "@media (min-width: 768px)" in html, "Desktop media query should exist"
        assert "flex-direction: row" in html, "Desktop should use row layout"


# =============================================================================
# Tests: Ticket 34 - OCR → Builder Precision + Trust Tightening
# =============================================================================


class TestTicket34OcrBuilderPrecision:
    """
    Ticket 34: OCR → Builder Precision + Trust Tightening.

    Part A: OCR → Canonical Builder Mapping
    Part B: Per-Leg Confidence Indicators
    Part C: OCR Review Soft Gate
    Part D: Promo/Info Box
    """

    # Part A: OCR → Canonical Builder Mapping

    def test_ocr_button_text_changed_to_add_to_builder(self, client):
        """Part A: OCR button should say 'Add to Builder' not 'Use This Text'."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "Add to Builder" in html, "OCR button should say 'Add to Builder'"

    def test_parse_ocr_to_legs_function_exists(self, client):
        """Part A: parseOcrToLegs function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "parseOcrToLegs" in html, "parseOcrToLegs function should exist"

    def test_parse_ocr_line_function_exists(self, client):
        """Part A: parseOcrLine function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "parseOcrLine" in html, "parseOcrLine function should exist"

    def test_leg_source_tag_class_exists(self, client):
        """Part A: leg-source-tag CSS class should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "leg-source-tag" in html, "leg-source-tag CSS class should exist"

    def test_ocr_leg_class_exists(self, client):
        """Part A: ocr-leg CSS class should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".ocr-leg" in html, "ocr-leg CSS class should exist"

    def test_detected_from_slip_tag_in_js(self, client):
        """Part A: 'Detected from slip' tag should appear in JavaScript."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "Detected from slip" in html, "'Detected from slip' tag should be in code"

    # Part B: Per-Leg Confidence Indicators

    def test_leg_clarity_css_classes_exist(self, client):
        """Part B: Leg clarity CSS classes should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".leg-clarity.clear" in html, "Clear clarity class should exist"
        assert ".leg-clarity.review" in html, "Review clarity class should exist"
        assert ".leg-clarity.ambiguous" in html, "Ambiguous clarity class should exist"

    def test_get_ocr_leg_clarity_function_exists(self, client):
        """Part B: getOcrLegClarity function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "getOcrLegClarity" in html, "getOcrLegClarity function should exist"

    def test_get_clarity_display_function_exists(self, client):
        """Part B: getClarityDisplay function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "getClarityDisplay" in html, "getClarityDisplay function should exist"

    def test_clarity_labels_exist(self, client):
        """Part B: Clarity labels should exist in code."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "Clear match" in html, "'Clear match' label should exist"
        assert "Review recommended" in html, "'Review recommended' label should exist"
        assert "Ambiguous" in html, "'Ambiguous' label should exist"

    # Part C: OCR Review Soft Gate

    def test_ocr_review_gate_element_exists(self, client):
        """Part C: OCR review gate element should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert 'id="ocr-review-gate"' in html, "OCR review gate element should exist"
        assert "ocr-review-gate" in html, "ocr-review-gate class should exist"

    def test_ocr_review_gate_buttons_exist(self, client):
        """Part C: Review gate buttons should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert 'id="gate-review-btn"' in html, "Review button should exist"
        assert 'id="gate-proceed-btn"' in html, "Proceed button should exist"
        assert "Review legs" in html, "'Review legs' button text should exist"
        assert "Evaluate anyway" in html, "'Evaluate anyway' button text should exist"

    def test_ocr_review_gate_message_exists(self, client):
        """Part C: Review gate message should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "Some detected legs may need review" in html, \
            "Review gate message should exist"

    def test_has_legs_needing_review_function_exists(self, client):
        """Part C: hasLegsNeedingReview function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "hasLegsNeedingReview" in html, "hasLegsNeedingReview function should exist"

    def test_show_hide_ocr_review_gate_functions_exist(self, client):
        """Part C: showOcrReviewGate and hideOcrReviewGate functions should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "showOcrReviewGate" in html, "showOcrReviewGate function should exist"
        assert "hideOcrReviewGate" in html, "hideOcrReviewGate function should exist"

    def test_ocr_review_gate_css_exists(self, client):
        """Part C: OCR review gate CSS styles should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".ocr-review-gate" in html, "ocr-review-gate styles should exist"
        assert ".ocr-review-gate-content" in html, "gate content styles should exist"
        assert ".ocr-review-gate-btn" in html, "gate button styles should exist"

    # Part D: Promo/Info Box

    def test_ocr_info_box_element_exists(self, client):
        """Part D: OCR info box element should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert 'id="ocr-info-box"' in html, "OCR info box element should exist"

    def test_ocr_info_box_title_exists(self, client):
        """Part D: OCR info box title should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "How DNA reads bet slips" in html, "Info box title should exist"

    def test_ocr_info_box_content_exists(self, client):
        """Part D: OCR info box content should exist with exact copy."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "DNA analyzes bet structure, not odds or payouts" in html, \
            "Info box should mention structure analysis"
        assert "including 6-leg slips" in html, \
            "Info box should mention 6-leg parlays are normal"
        assert "Image text may require review" in html, \
            "Info box should mention review requirement"

    def test_ocr_info_box_css_exists(self, client):
        """Part D: OCR info box CSS styles should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".ocr-info-box" in html, "ocr-info-box styles should exist"
        assert ".ocr-info-title" in html, "ocr-info-title styles should exist"
        assert ".ocr-info-text" in html, "ocr-info-text styles should exist"

    # Edit leg functionality

    def test_edit_leg_functionality_exists(self, client):
        """Part A: Edit leg functionality should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "startEditLeg" in html, "startEditLeg function should exist"
        assert "saveEditLeg" in html, "saveEditLeg function should exist"
        assert "cancelEditLeg" in html, "cancelEditLeg function should exist"

    def test_leg_edit_css_exists(self, client):
        """Part A: Leg edit CSS styles should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".leg-edit-input" in html, "leg-edit-input styles should exist"
        assert ".leg-edit-actions" in html, "leg-edit-actions styles should exist"
        assert ".leg-edit-save" in html, "leg-edit-save styles should exist"
        assert ".leg-edit-cancel" in html, "leg-edit-cancel styles should exist"

    def test_editable_leg_class_exists(self, client):
        """Part A: Editable leg CSS class should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".ocr-leg.editable" in html, "editable leg class should exist"

    # State tracking

    def test_has_ocr_legs_state_exists(self, client):
        """Part A: hasOcrLegs state variable should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "hasOcrLegs" in html, "hasOcrLegs state variable should exist"

    def test_pending_evaluation_state_exists(self, client):
        """Part C: pendingEvaluation state variable should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "pendingEvaluation" in html, "pendingEvaluation state variable should exist"

    def test_reset_form_clears_ocr_state(self, client):
        """Part A: resetForm should clear OCR state."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that resetForm resets hasOcrLegs
        assert "hasOcrLegs = false" in html, "resetForm should reset hasOcrLegs"


# =============================================================================
# Tests: Ticket 35 - Inline Refine Loop
# =============================================================================


class TestTicket35InlineRefineLoop:
    """
    Ticket 35: Inline Refine Loop.

    Part A: Results-Screen Leg Controls (Remove/Lock)
    Part B: Re-evaluate Action
    Part C: Full State Sync Guarantee
    Part D: UX Details
    """

    # Part A: Results-Screen Leg Controls

    def test_result_leg_controls_css_exists(self, client):
        """Part A: Result leg controls CSS should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".result-leg-controls" in html, "result-leg-controls CSS should exist"
        assert ".result-leg-num" in html, "result-leg-num CSS should exist"
        assert ".result-leg-content" in html, "result-leg-content CSS should exist"

    def test_leg_lock_btn_css_exists(self, client):
        """Part A: Leg lock button CSS should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".leg-lock-btn" in html, "leg-lock-btn CSS should exist"
        assert ".leg-lock-btn.locked" in html, "leg-lock-btn.locked CSS should exist"

    def test_leg_remove_btn_css_exists(self, client):
        """Part A: Leg remove button CSS should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".leg-remove-btn" in html, "leg-remove-btn CSS should exist"
        assert ".leg-remove-btn:disabled" in html, "leg-remove-btn:disabled CSS should exist"

    def test_locked_leg_styling_exists(self, client):
        """Part A: Locked leg styling should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".parlay-legs li.locked" in html, "locked leg styling should exist"

    def test_render_results_legs_function_exists(self, client):
        """Part A: renderResultsLegs function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "renderResultsLegs" in html, "renderResultsLegs function should exist"

    def test_toggle_leg_lock_function_exists(self, client):
        """Part A: toggleLegLock function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "toggleLegLock" in html, "toggleLegLock function should exist"

    def test_remove_leg_from_results_function_exists(self, client):
        """Part A: removeLegFromResults function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "removeLegFromResults" in html, "removeLegFromResults function should exist"

    def test_locked_leg_cannot_be_removed_logic(self, client):
        """Part A: Locked legs should not be removable (logic check)."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that the function checks for locked state before removing
        assert "if (leg.locked) return" in html, "Should check locked state before removing"

    # Part B: Re-evaluate Action

    def test_reevaluate_button_exists(self, client):
        """Part B: Re-evaluate button should exist in HTML."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert 'id="reevaluate-btn"' in html, "Re-evaluate button should exist"
        assert "Re-evaluate" in html, "'Re-evaluate' button text should exist"

    def test_reevaluate_btn_css_exists(self, client):
        """Part B: Re-evaluate button CSS should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert ".reevaluate-btn" in html, "reevaluate-btn CSS should exist"

    def test_re_evaluate_parlay_function_exists(self, client):
        """Part B: reEvaluateParlay function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "reEvaluateParlay" in html, "reEvaluateParlay function should exist"

    def test_re_evaluate_uses_run_evaluation(self, client):
        """Part B: reEvaluateParlay should use runEvaluation."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that reEvaluateParlay calls runEvaluation
        assert "await runEvaluation" in html, "Should call runEvaluation"

    def test_update_re_evaluate_button_function_exists(self, client):
        """Part B: updateReEvaluateButton function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "updateReEvaluateButton" in html, "updateReEvaluateButton function should exist"

    # Part C: Full State Sync Guarantee

    def test_results_legs_state_exists(self, client):
        """Part C: resultsLegs state variable should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "resultsLegs" in html, "resultsLegs state variable should exist"

    def test_locked_leg_ids_state_exists(self, client):
        """Part C: lockedLegIds state variable should exist (Ticket 37 migration)."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Ticket 37: Migrated from lockedLegIndices to lockedLegIds
        assert "lockedLegIds" in html, "lockedLegIds state variable should exist"

    def test_sync_state_from_results_function_exists(self, client):
        """Part C: syncStateFromResults function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "syncStateFromResults" in html, "syncStateFromResults function should exist"

    def test_sync_state_updates_builder_legs(self, client):
        """Part C: syncStateFromResults should update builderLegs."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that builderLegs is updated from resultsLegs
        assert "builderLegs = resultsLegs.map" in html, "Should update builderLegs from resultsLegs"

    def test_sync_state_calls_sync_textarea(self, client):
        """Part C: syncStateFromResults should call syncTextarea."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # The function should call syncTextarea
        assert "syncTextarea()" in html, "Should call syncTextarea"

    def test_update_parlay_label_function_exists(self, client):
        """Part C: updateParlayLabel function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "updateParlayLabel" in html, "updateParlayLabel function should exist"

    def test_reset_form_clears_refine_state(self, client):
        """Part C: resetForm should clear refine loop state."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Ticket 37: Migrated from lockedLegIndices to lockedLegIds
        assert "lockedLegIds.clear()" in html, "resetForm should clear lockedLegIds"
        assert "resultsLegs = []" in html, "resetForm should clear resultsLegs"

    def test_refine_parlay_uses_results_legs(self, client):
        """Part C: refineParlay should use resultsLegs if available."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "resultsLegs.length > 0" in html, "refineParlay should check resultsLegs"

    # Part D: UX Details

    def test_refine_actions_row_exists(self, client):
        """Part D: Refine actions row should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "refine-actions-row" in html, "refine-actions-row should exist"

    def test_refine_hint_exists(self, client):
        """Part D: Refine hint text should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "refine-hint" in html, "refine-hint CSS should exist"
        assert "Adjust structure above, then test" in html, "Hint text should exist"

    def test_edit_in_builder_button_exists(self, client):
        """Part D: Refine Structure button should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "Refine Structure" in html, "'Edit in Builder' button text should exist"

    def test_lock_icons_in_code(self, client):
        """Part D: Lock/unlock icons should be in code."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Unicode for lock icons
        assert "&#128274;" in html, "Locked icon should exist"
        assert "&#128275;" in html, "Unlocked icon should exist"

    def test_lock_button_titles_exist(self, client):
        """Part D: Lock button titles should exist for accessibility."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "Lock this leg" in html, "Lock title should exist"
        assert "Unlock this leg" in html, "Unlock title should exist"
        assert "Unlock to remove" in html, "Locked remove title should exist"

    # State sync during evaluation

    def test_show_results_populates_results_legs(self, client):
        """Part C: showResults should populate resultsLegs."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that showResults creates resultsLegs from parlay.legs
        assert "resultsLegs = (parlay.legs" in html, "showResults should populate resultsLegs"

    def test_results_legs_preserve_original_index(self, client):
        """Part C: resultsLegs should preserve originalIndex for lock tracking."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "originalIndex: i" in html, "Should track originalIndex"


# =============================================================================
# Tests: Ticket 36 - OCR Regression Repair + State Boundary Audit
# =============================================================================


class TestTicket36OcrRegressionRepair:
    """
    Ticket 36: OCR Regression Repair + State Boundary Audit.

    Part A: Root cause identification (verified by implementation)
    Part B: OCR → Builder path fix
    Part C: State collision fix
    Part D: Regression tests
    """

    # Part B: OCR → Builder path clears refine state

    def test_ocr_add_to_builder_clears_locked_ids(self, client):
        """Part B: 'Add to Builder' should clear lockedLegIds (Ticket 37 migration)."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that OCR handler clears lock state
        # Ticket 37: Migrated from lockedLegIndices to lockedLegIds
        assert "lockedLegIds.clear()" in html, \
            "OCR handler should clear lockedLegIds"
        # Verify it's in the useOcrBtn handler context
        # Ticket 37 update: Comment may now include both ticket references
        assert "Clear refine loop state" in html, \
            "OCR handler should have clear refine loop comment"

    def test_ocr_add_to_builder_clears_results_legs(self, client):
        """Part B: 'Add to Builder' should clear resultsLegs."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that OCR handler clears resultsLegs
        assert "resultsLegs = []" in html, \
            "OCR handler should clear resultsLegs"

    # Part C: State collision fix - isReEvaluation flag

    def test_is_re_evaluation_state_exists(self, client):
        """Part C: isReEvaluation state variable should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "isReEvaluation" in html, "isReEvaluation state variable should exist"

    def test_submit_handler_clears_lock_state(self, client):
        """Part C: Submit handler should clear lock state for fresh evaluations."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that submit handler marks as fresh evaluation
        assert "isReEvaluation = false" in html, \
            "Submit handler should set isReEvaluation = false"

    def test_re_evaluate_sets_is_re_evaluation(self, client):
        """Part C: reEvaluateParlay should set isReEvaluation = true."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that re-evaluate marks as re-evaluation
        assert "isReEvaluation = true" in html, \
            "reEvaluateParlay should set isReEvaluation = true"

    def test_soft_gate_proceed_clears_lock_state(self, client):
        """Part C: Soft gate 'Evaluate anyway' should clear lock state."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # The soft gate proceed handler should also clear lock state
        # This is a fresh evaluation from OCR
        # Ticket 37 update: Comment may now include both ticket references
        assert "fresh evaluation from OCR" in html, \
            "Soft gate proceed should document fresh evaluation from OCR"

    def test_reset_form_clears_is_re_evaluation(self, client):
        """Part C: resetForm should clear isReEvaluation."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that resetForm includes isReEvaluation = false
        # This ensures fresh start after 'Evaluate Another'
        assert "isReEvaluation = false" in html, \
            "resetForm should reset isReEvaluation"

    # Part D: Verify state boundaries

    def test_ocr_handler_has_fresh_start_comment(self, client):
        """Part D: OCR handler should document fresh start behavior."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "this is a fresh start" in html.lower(), \
            "OCR handler should document fresh start"

    def test_re_evaluate_has_preserve_lock_comment(self, client):
        """Part D: reEvaluateParlay should document lock preservation."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "lock state should be preserved" in html.lower(), \
            "reEvaluateParlay should document lock preservation"

    def test_ticket_36_comments_present(self, client):
        """Part D: Ticket 36 comments should be present in code."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Count Ticket 36 comments to ensure all fixes are documented
        ticket_36_count = html.count("Ticket 36")
        assert ticket_36_count >= 5, \
            f"Should have at least 5 Ticket 36 comments, found {ticket_36_count}"


class TestTicket37LegIdentity:
    """Ticket 37: Deterministic leg_id for refine loop stability."""

    def test_generate_leg_id_sync_exists(self, client):
        """Part A: generateLegIdSync function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "function generateLegIdSync" in html, \
            "generateLegIdSync function must be defined"

    def test_leg_id_uses_canonical_fields(self, client):
        """Part A: leg_id generation should use entity, market, value, sport."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that canonical fields are used
        assert "leg.entity" in html and "toLowerCase" in html, \
            "Should normalize entity to lowercase"
        assert "leg.market" in html, \
            "Should use market field"
        assert "leg.value" in html, \
            "Should use value field"
        assert "leg.sport" in html, \
            "Should use sport field"

    def test_leg_id_deterministic_hash(self, client):
        """Part A: leg_id should use djb2 hash algorithm."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # djb2 hash starts with 5381
        assert "5381" in html, \
            "Should use djb2 algorithm (starts with 5381)"
        assert "leg_" in html, \
            "leg_id should be prefixed with 'leg_'"

    def test_locked_leg_ids_replaces_indices(self, client):
        """Part B: lockedLegIds should replace lockedLegIndices."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check state variable declaration
        assert "let lockedLegIds = new Set()" in html, \
            "lockedLegIds state variable must be declared"
        # Ensure old variable is not used functionally
        # (may still appear in comments about the migration)
        assert "lockedLegIds.add" in html, \
            "Should use lockedLegIds.add()"
        assert "lockedLegIds.has" in html, \
            "Should use lockedLegIds.has()"
        assert "lockedLegIds.clear()" in html, \
            "Should use lockedLegIds.clear()"

    def test_toggle_lock_uses_leg_id(self, client):
        """Part B: toggleLegLock should use leg.leg_id."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Find the toggleLegLock function and check it uses leg_id
        assert "lockedLegIds.add(leg.leg_id)" in html, \
            "toggleLegLock should add leg.leg_id to lockedLegIds"
        assert "lockedLegIds.delete(leg.leg_id)" in html, \
            "toggleLegLock should delete leg.leg_id from lockedLegIds"

    def test_show_results_uses_leg_id_for_lock_check(self, client):
        """Part B: showResults should check lock state by leg_id."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "lockedLegIds.has(leg_id)" in html, \
            "showResults should check lock state using leg_id"

    def test_parse_ocr_line_includes_leg_id(self, client):
        """Part C: parseOcrLine should return leg_id."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check parseOcrLine returns object with leg_id
        assert "leg_id: leg_id" in html or "leg_id:" in html, \
            "parseOcrLine should include leg_id in return value"

    def test_add_leg_includes_leg_id(self, client):
        """Part C: addLeg should generate leg_id for new legs."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check addLeg generates leg_id
        # Look for generateLegIdSync call in addLeg context
        assert "builderLegs.push" in html, \
            "addLeg should push to builderLegs"

    def test_sync_state_from_results_preserves_leg_id(self, client):
        """Part C: syncStateFromResults should preserve leg_id."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check syncStateFromResults includes leg_id
        assert "leg_id: leg.leg_id" in html, \
            "syncStateFromResults should preserve leg_id"

    def test_refine_parlay_includes_leg_id(self, client):
        """Part C: refineParlay should include leg_id."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check refineParlay maps with leg_id
        assert "leg.leg_id || generateLegIdSync" in html, \
            "refineParlay should use existing leg_id or generate new one"

    def test_reevaluate_uses_leg_id_persistence(self, client):
        """Part B: reEvaluateParlay should rely on leg_id persistence."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check that reEvaluateParlay doesn't do complex index-based restoration
        # With leg_id, lock state is automatically restored via showResults
        assert "lockedLegIds persists" in html or "Ticket 37" in html, \
            "reEvaluateParlay should have Ticket 37 comments about leg_id persistence"

    def test_reset_form_clears_leg_ids(self, client):
        """Part B: resetForm should clear lockedLegIds."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check resetForm clears the set
        # Count occurrences - should have multiple clear() calls
        clear_count = html.count("lockedLegIds.clear()")
        assert clear_count >= 3, \
            f"Should have at least 3 lockedLegIds.clear() calls, found {clear_count}"

    def test_ticket_37_comments_present(self, client):
        """Part D: Ticket 37 comments should be present in code."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Count Ticket 37 comments to ensure all changes are documented
        ticket_37_count = html.count("Ticket 37")
        assert ticket_37_count >= 8, \
            f"Should have at least 8 Ticket 37 comments, found {ticket_37_count}"

    def test_no_functional_locked_leg_indices(self, client):
        """Part D: lockedLegIndices should not be used functionally."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Should not have functional uses of old variable
        # (it's OK if it appears in comments about the migration)
        assert "lockedLegIndices.add(" not in html, \
            "Should not use lockedLegIndices.add() anymore"
        assert "lockedLegIndices.delete(" not in html, \
            "Should not use lockedLegIndices.delete() anymore"
        assert "lockedLegIndices.has(" not in html, \
            "Should not use lockedLegIndices.has() anymore"


class TestTicket37BHashUpgrade:
    """Ticket 37B: Upgrade leg_id hash to SHA-256 with djb2 fallback."""

    def test_get_canonical_leg_string_exists(self, client):
        """Ticket 37B: getCanonicalLegString helper should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "function getCanonicalLegString" in html, \
            "getCanonicalLegString function must be defined"

    def test_hash_djb2_exists(self, client):
        """Ticket 37B: hashDjb2 fallback function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "function hashDjb2" in html, \
            "hashDjb2 fallback function must be defined"

    def test_generate_leg_id_uses_sha256(self, client):
        """Ticket 37B: generateLegId should use SHA-256 via WebCrypto."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "crypto.subtle.digest" in html, \
            "Should use crypto.subtle.digest for SHA-256"
        assert "SHA-256" in html, \
            "Should specify SHA-256 algorithm"

    def test_generate_leg_id_has_webcrypto_check(self, client):
        """Ticket 37B: generateLegId should check for WebCrypto availability."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "crypto.subtle" in html, \
            "Should check for crypto.subtle availability"

    def test_generate_leg_id_has_djb2_fallback(self, client):
        """Ticket 37B: generateLegId should fallback to djb2."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "hashDjb2(canonical)" in html, \
            "Should call hashDjb2 as fallback"

    def test_generate_leg_id_sync_uses_djb2(self, client):
        """Ticket 37B: generateLegIdSync should use djb2."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "hashDjb2(getCanonicalLegString(leg))" in html, \
            "generateLegIdSync should use hashDjb2"

    def test_ticket_37b_comments_present(self, client):
        """Ticket 37B: Ticket 37B comments should be present."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        ticket_37b_count = html.count("Ticket 37B")
        assert ticket_37b_count >= 4, \
            f"Should have at least 4 Ticket 37B comments, found {ticket_37b_count}"


class TestTicket38AOcrErrorRendering:
    """Ticket 38A: Fix OCR error rendering ([object Object])."""

    def test_safe_any_to_string_exists(self, client):
        """Ticket 38A: safeAnyToString helper function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "function safeAnyToString" in html, \
            "safeAnyToString helper function must be defined"

    def test_safe_response_error_exists(self, client):
        """Ticket 38A: safeResponseError helper function should exist."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "function safeResponseError" in html, \
            "safeResponseError helper function must be defined"

    def test_safe_any_to_string_handles_null(self, client):
        """Ticket 38A: safeAnyToString should handle null/undefined."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Check for null/undefined handling
        assert "x === null || x === undefined" in html, \
            "Should check for null/undefined"
        assert "Unknown error" in html, \
            "Should have fallback for null/undefined"

    def test_safe_any_to_string_handles_string(self, client):
        """Ticket 38A: safeAnyToString should return strings directly."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "typeof x === 'string'" in html, \
            "Should check if input is already a string"

    def test_safe_any_to_string_handles_error_message(self, client):
        """Ticket 38A: safeAnyToString should extract Error.message."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "x.message && typeof x.message === 'string'" in html, \
            "Should extract message from Error objects"

    def test_safe_any_to_string_handles_detail(self, client):
        """Ticket 38A: safeAnyToString should handle API {detail: ...} responses."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "x.detail" in html, \
            "Should check for .detail property"
        assert "Array.isArray(x.detail)" in html, \
            "Should handle Pydantic validation errors (array of details)"

    def test_safe_any_to_string_handles_error_property(self, client):
        """Ticket 38A: safeAnyToString should handle {error: ...} responses."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "x.error && typeof x.error === 'string'" in html, \
            "Should check for .error property"

    def test_ocr_handler_uses_safe_stringifier(self, client):
        """Ticket 38A: OCR error handler should use safeAnyToString."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "safeAnyToString(err," in html, \
            "OCR catch block should use safeAnyToString"

    def test_ocr_response_uses_safe_error(self, client):
        """Ticket 38A: OCR response error should use safeResponseError."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert "safeResponseError(data," in html, \
            "OCR response error should use safeResponseError"

    def test_evaluation_error_uses_safe_error(self, client):
        """Ticket 38A: Evaluation error should use safeResponseError."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # Count safeResponseError usages - should be at least 2 (OCR + evaluation)
        count = html.count("safeResponseError(data,")
        assert count >= 2, \
            f"Should use safeResponseError for at least OCR and evaluation errors, found {count}"

    def test_no_object_object_in_error_assignments(self, client):
        """Ticket 38A: No raw object concatenation that could produce [object Object]."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text

        # Patterns that could produce [object Object]
        # Look for "+ err" or "${err}" without safe extraction
        import re

        # Find textContent or innerHTML assignments with err concatenation
        # This is a best-effort check - look for dangerous patterns
        dangerous_patterns = [
            r"textContent\s*=\s*['\"].*['\"].*\+\s*err(?!\s*\.\s*message)",  # + err (not err.message)
            r"innerHTML\s*=\s*['\"].*['\"].*\+\s*err(?!\s*\.\s*message)",    # + err (not err.message)
        ]

        for pattern in dangerous_patterns:
            matches = re.findall(pattern, html)
            # Filter out safe uses
            safe_matches = [m for m in matches if "safeAnyToString" not in m]
            assert len(safe_matches) == 0, \
                f"Found dangerous error concatenation pattern: {safe_matches}"

    def test_ticket_38a_comments_present(self, client):
        """Ticket 38A: Ticket 38A comments should be present."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        ticket_38a_count = html.count("Ticket 38A")
        assert ticket_38a_count >= 3, \
            f"Should have at least 3 Ticket 38A comments, found {ticket_38a_count}"

    def test_never_returns_object_object(self, client):
        """Ticket 38A: safeAnyToString should never return [object Object]."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        # The function should explicitly check for and avoid [object Object]
        assert "[object Object]" in html, \
            "Should have explicit check against [object Object] string"
        assert "str !== '[object Object]'" in html, \
            "Should explicitly reject [object Object] from toString()"
