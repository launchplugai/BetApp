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
        # Check for builder elements (leg-based inputs)
        assert "legs-container" in response.text
        assert "add-leg-btn" in response.text
        # Check for tier selector
        assert "tier-good" in response.text
        assert "tier-better" in response.text
        assert "tier-best" in response.text
        # Check for submit button
        assert "Evaluate" in response.text
        # Check for navigation tabs
        assert "nav-tab" in response.text
        assert "tab-builder" in response.text

    def test_returns_html_content_type(self, client):
        """App page returns HTML content type."""
        response = client.get("/app")
        assert "text/html" in response.headers.get("content-type", "")

    def test_contains_orientation_banner(self, client):
        """App page contains orientation banner for first-time users."""
        response = client.get("/app")
        # Check for orientation banner content
        assert "orientation-banner" in response.text
        assert "Build a parlay or paste a bet" in response.text
        assert "risk, correlation, and fragility" in response.text

    def test_anonymous_user_sees_login_hint(self, client):
        """Anonymous users see login hint in orientation banner."""
        response = client.get("/app")
        # Check for login hint (anonymous users)
        assert "Log in to save history" in response.text

    def test_tier_selector_in_step_lane(self, client):
        """Tier selector is in step 2 of the evaluation lane."""
        response = client.get("/app")
        assert "tier-selector" in response.text
        assert "Choose depth" in response.text

    def test_image_upload_panel_exists(self, client):
        """Image upload panel exists with upload UI."""
        response = client.get("/app")
        # Check for image upload area
        assert "file-upload-area" in response.text
        assert "file-input" in response.text
        assert "image-input-panel" in response.text


class TestUIFlowLock:
    """Ticket 1: UI Flow Lock verification tests."""

    # --- Cold Load (new user, no state) ---

    def test_cold_load_lands_on_evaluate(self, client):
        """Default tab is Evaluate, not Builder."""
        response = client.get("/app")
        assert response.status_code == 200
        # Evaluate tab should have 'active' class
        assert 'id="tab-evaluate"' in response.text
        # The evaluate tab content div should be active
        text = response.text
        # Find tab-evaluate and check it has active class
        import re
        eval_tab = re.search(r'<div class="tab-content[^"]*"[^>]*id="tab-evaluate"', text)
        assert eval_tab is not None

    def test_cold_load_evaluate_is_active_tab(self, client):
        """Evaluate nav tab has active class by default."""
        response = client.get("/app")
        assert 'class="nav-tab active" data-tab="evaluate"' in response.text

    def test_cold_load_builder_not_active(self, client):
        """Builder tab is NOT active on cold load."""
        response = client.get("/app")
        assert 'class="nav-tab active" data-tab="builder"' not in response.text

    def test_discover_tab_has_cta_to_evaluate(self, client):
        """Discover tab exists with CTA that routes to Evaluate."""
        response = client.get("/app?tab=discover")
        assert response.status_code == 200
        assert "tab-discover" in response.text
        assert "Start Evaluating" in response.text
        assert "switchToTab(&#x27;evaluate&#x27;)" in response.text or "switchToTab('evaluate')" in response.text

    # --- Evaluate Flow ---

    def test_evaluate_has_text_input(self, client):
        """Evaluate tab has Text input option."""
        response = client.get("/app")
        assert 'data-input="text"' in response.text
        assert "text-input-panel" in response.text

    def test_evaluate_has_image_input(self, client):
        """Evaluate tab has Image input option."""
        response = client.get("/app")
        assert 'data-input="image"' in response.text
        assert "image-input-panel" in response.text

    def test_evaluate_has_bundle_input(self, client):
        """Evaluate tab has Bundle input option."""
        response = client.get("/app")
        assert 'data-input="bundle"' in response.text
        assert "bundle-input-panel" in response.text

    def test_bundle_routes_to_builder(self, client):
        """Bundle panel contains action to switch to Builder."""
        response = client.get("/app")
        assert "Go to Builder" in response.text
        assert "switchToTab(&#x27;builder&#x27;)" in response.text or "switchToTab('builder')" in response.text

    def test_evaluate_has_step_lane(self, client):
        """Evaluate tab has step lane (1→2→3)."""
        response = client.get("/app")
        assert "eval-step-number" in response.text
        assert "Provide bet" in response.text
        assert "Choose depth" in response.text
        assert "Analyze" in response.text

    # --- Post-Evaluation State ---

    def test_builder_cta_disabled_by_default(self, client):
        """Builder CTA button is disabled until evaluation completes."""
        response = client.get("/app")
        # Check that the builder CTA is present and disabled
        assert "builder-cta-btn" in response.text
        assert 'id="builder-cta-btn" disabled' in response.text
        assert "Evaluate a bet first" in response.text

    def test_builder_cta_has_enable_logic(self, client):
        """JavaScript enables Builder CTA after showEvalResults."""
        response = client.get("/app")
        # Verify the JS logic to enable the button is present
        assert "builderCtaBtn.disabled = false" in response.text
        assert "builderCtaBtn.classList.remove" in response.text

    # --- Tier Selector ---

    def test_tier_label_no_pricing(self, client):
        """Tier selector step label uses neutral language, not pricing."""
        response = client.get("/app")
        assert "Choose depth" in response.text
        # Must NOT contain pricing language in main app flow
        assert "$19.99" not in response.text

    def test_no_unlock_with_price(self, client):
        """No 'Unlock' CTA with price anchoring in main app."""
        response = client.get("/app")
        assert "Unlock BEST" not in response.text
        assert "Unlock Full Analysis" not in response.text

    def test_upgrade_cta_no_billing_implication(self, client):
        """Upgrade CTA exists but without pricing."""
        response = client.get("/app")
        # The upgrade nudge should say "Upgrade to BEST" without price
        assert "Upgrade to BEST" in response.text
        assert "/mo)" not in response.text

    # --- Regression: All tabs load ---

    def test_all_four_tabs_present(self, client):
        """All four tabs render in correct order."""
        response = client.get("/app")
        text = response.text
        assert 'data-tab="discover"' in text
        assert 'data-tab="evaluate"' in text
        assert 'data-tab="builder"' in text
        assert 'data-tab="history"' in text

    def test_navigation_order_locked(self, client):
        """Tabs appear in order: Discover, Evaluate, Builder, History."""
        response = client.get("/app")
        text = response.text
        discover_pos = text.find('data-tab="discover"')
        evaluate_pos = text.find('data-tab="evaluate"')
        builder_pos = text.find('data-tab="builder"')
        history_pos = text.find('data-tab="history"')
        assert discover_pos < evaluate_pos < builder_pos < history_pos

    def test_tab_content_containers_exist(self, client):
        """All tab content containers are in the DOM."""
        response = client.get("/app")
        assert 'id="tab-discover"' in response.text
        assert 'id="tab-evaluate"' in response.text
        assert 'id="tab-builder"' in response.text
        assert 'id="tab-history"' in response.text

    def test_builder_tab_still_functional(self, client):
        """Builder tab content still has form elements."""
        response = client.get("/app?tab=builder")
        assert response.status_code == 200
        assert "Parlay Builder" in response.text
        assert "add-leg-btn" in response.text
        assert "submit-btn" in response.text

    def test_history_tab_still_functional(self, client):
        """History tab content still loads."""
        response = client.get("/app?tab=history")
        assert response.status_code == 200
        assert "tab-history" in response.text

    def test_no_coming_soon_text(self, client):
        """No placeholder 'coming soon' text anywhere."""
        response = client.get("/app")
        assert "coming soon" not in response.text.lower()


class TestCoreLoopReinforcement:
    """Ticket 2: Core Loop Reinforcement tests."""

    # --- Signal System ---

    def test_signal_display_exists(self, client):
        """Signal badge and score elements are in the DOM."""
        response = client.get("/app")
        assert "eval-signal-badge" in response.text
        assert "eval-signal-score" in response.text
        assert "signal-display" in response.text

    def test_signal_map_in_javascript(self, client):
        """Signal map has all four signals: blue, green, yellow, red."""
        response = client.get("/app")
        assert "signal-blue" in response.text
        assert "signal-green" in response.text
        assert "signal-yellow" in response.text
        assert "signal-red" in response.text

    def test_signal_labels_correct(self, client):
        """Signal labels: Strong, Solid, Fixable, Fragile."""
        response = client.get("/app")
        # These are in the JS signalMap
        assert "'Strong'" in response.text or "Strong" in response.text
        assert "'Solid'" in response.text or "Solid" in response.text
        assert "'Fixable'" in response.text or "Fixable" in response.text
        assert "'Fragile'" in response.text or "Fragile" in response.text

    # --- Metrics Grid (GOOD+) ---

    def test_metrics_grid_exists(self, client):
        """Metrics grid with leg penalty, correlation, raw, final."""
        response = client.get("/app")
        assert "eval-metrics-grid" in response.text
        assert "eval-metric-leg" in response.text
        assert "eval-metric-corr" in response.text
        assert "eval-metric-raw" in response.text
        assert "eval-metric-final" in response.text

    # --- Improvement Tips (GOOD+) ---

    def test_tips_panel_exists(self, client):
        """Tips panel exists with 'How to Improve' heading."""
        response = client.get("/app")
        assert "eval-tips-panel" in response.text
        assert "How to Improve" in response.text

    # --- Tier Differentiation ---

    def test_correlations_panel_exists(self, client):
        """Correlations panel exists for BETTER+ tier rendering."""
        response = client.get("/app")
        assert "eval-correlations-panel" in response.text
        assert "Correlations Found" in response.text

    def test_summary_panel_exists(self, client):
        """Summary panel exists for BETTER+ tier rendering."""
        response = client.get("/app")
        assert "eval-summary-panel" in response.text
        assert "Deeper Insights" in response.text

    def test_alerts_panel_exists(self, client):
        """Alerts panel exists for BEST tier rendering."""
        response = client.get("/app")
        assert "eval-alerts-panel" in response.text

    def test_correlations_hidden_by_default(self, client):
        """Correlations panel is hidden in initial render."""
        response = client.get("/app")
        assert 'correlations-panel hidden' in response.text

    def test_summary_hidden_by_default(self, client):
        """Summary panel is hidden in initial render."""
        response = client.get("/app")
        assert 'summary-panel hidden' in response.text

    def test_alerts_hidden_by_default(self, client):
        """Alerts panel is hidden in initial render."""
        response = client.get("/app")
        assert 'alerts-detail-panel hidden' in response.text

    def test_tier_gating_logic_in_js(self, client):
        """JavaScript gates correlations/summary to BETTER+, alerts to BEST."""
        response = client.get("/app")
        # BETTER+ check for correlations
        assert "tier === 'better' || tier === 'best'" in response.text
        # BEST-only check for alerts
        assert "tier === 'best'" in response.text

    # --- Post-Result Actions ---

    def test_post_actions_exist(self, client):
        """Post-result action buttons exist: Improve, Re-Evaluate, Save."""
        response = client.get("/app")
        assert "eval-action-improve" in response.text
        assert "eval-action-reeval" in response.text
        assert "eval-action-save" in response.text

    def test_improve_routes_to_builder(self, client):
        """Improve button switches to Builder tab."""
        response = client.get("/app")
        assert "Improve This Bet" in response.text
        assert "switchToTab(&#x27;builder&#x27;)" in response.text or "switchToTab('builder')" in response.text

    def test_reeval_button_text(self, client):
        """Re-Evaluate button is present."""
        response = client.get("/app")
        assert "Re-Evaluate" in response.text

    def test_save_button_text(self, client):
        """Save button is present."""
        response = client.get("/app")
        assert ">Save<" in response.text

    # --- Verdict Bar ---

    def test_verdict_bar_exists(self, client):
        """Verdict bar with action and reason elements exists."""
        response = client.get("/app")
        assert "eval-verdict-bar" in response.text
        assert "eval-verdict-action" in response.text
        assert "eval-verdict-reason" in response.text

    # --- Tab Content Active Class ---

    def test_evaluate_tab_content_active_by_default(self, client):
        """Evaluate tab content has 'active' class on default load."""
        response = client.get("/app")
        # Check the tab-evaluate div has the active class
        import re
        match = re.search(r'<div class="tab-content\s+active"\s+id="tab-evaluate"', response.text)
        assert match is not None

    # --- API Tier Differentiation (end-to-end) ---

    def test_good_tier_returns_metrics(self, client):
        """GOOD tier response includes metrics for rendering."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML parlay", "tier": "good"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data["evaluation"]
        assert "final_fragility" in data["evaluation"]["metrics"]
        assert "leg_penalty" in data["evaluation"]["metrics"]

    def test_good_tier_has_interpretation(self, client):
        """GOOD tier has fragility interpretation with what_to_do."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML parlay", "tier": "good"}
        )
        data = response.json()
        assert "interpretation" in data
        assert "fragility" in data["interpretation"]
        frag = data["interpretation"]["fragility"]
        assert "bucket" in frag
        assert "what_to_do" in frag
        assert "meaning" in frag

    def test_better_tier_has_summary(self, client):
        """BETTER tier includes explain.summary list."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML parlay", "tier": "better"}
        )
        data = response.json()
        assert "explain" in data
        assert "summary" in data["explain"]
        assert isinstance(data["explain"]["summary"], list)

    def test_best_tier_has_alerts(self, client):
        """BEST tier includes explain.alerts and recommended_next_step."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML parlay", "tier": "best"}
        )
        data = response.json()
        assert "explain" in data
        assert "alerts" in data["explain"]
        assert "recommended_next_step" in data["explain"]

    def test_good_vs_better_output_differs(self, client):
        """GOOD and BETTER tier outputs are structurally different."""
        good = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML parlay", "tier": "good"}
        ).json()
        better = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML parlay", "tier": "better"}
        ).json()
        # GOOD has structured output, BETTER has summary
        assert "overallSignal" in good["explain"]
        assert "summary" not in good["explain"]
        assert "summary" in better["explain"]
        assert "overallSignal" not in better["explain"]


class TestEvaluateProxy:
    """Tests for POST /app/evaluate endpoint."""

    def test_empty_input_returns_400(self, client):
        """Empty input returns 400 validation error (Airlock)."""
        response = client.post(
            "/app/evaluate",
            json={"input": "", "tier": "good"}
        )
        assert response.status_code == 400

    def test_whitespace_input_returns_400(self, client):
        """Whitespace-only input returns 400 validation error (Airlock)."""
        response = client.post(
            "/app/evaluate",
            json={"input": "   ", "tier": "good"}
        )
        assert response.status_code == 400

    def test_missing_input_returns_422(self, client):
        """Missing input field returns 422 validation error."""
        response = client.post(
            "/app/evaluate",
            json={"tier": "good"}
        )
        assert response.status_code == 422

    def test_invalid_tier_returns_400(self, client):
        """Invalid tier returns 400 validation error (Airlock)."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "invalid"}
        )
        assert response.status_code == 400

    def test_missing_tier_defaults_to_good(self, client):
        """Missing tier defaults to 'good' and returns 200."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5"}
        )
        assert response.status_code == 200

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

    def test_tier_good_returns_structured_output(self, client):
        """GOOD tier returns structured explain with exact schema."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"}
        )
        assert response.status_code == 200
        data = response.json()
        explain = data["explain"]
        # GOOD tier should have structured output
        assert "overallSignal" in explain
        assert "grade" in explain
        assert "fragilityScore" in explain
        assert "contributors" in explain
        assert "warnings" in explain
        assert "tips" in explain
        assert "removalSuggestions" in explain

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


class TestImageEvaluateEndpoint:
    """Tests for POST /app/evaluate/image endpoint."""

    @pytest.fixture
    def image_client(self):
        """Create test client with image evaluation enabled."""
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        os.environ["IMAGE_EVAL_ENABLED"] = "true"
        # Note: OPENAI_API_KEY is not set intentionally for most tests
        from app.main import app
        return TestClient(app)

    @pytest.fixture
    def image_client_disabled(self):
        """Create test client with image evaluation disabled."""
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        os.environ["IMAGE_EVAL_ENABLED"] = "false"
        from app.main import app
        return TestClient(app)

    def test_image_endpoint_exists(self, image_client):
        """Image evaluation endpoint exists and accepts POST."""
        # Without OpenAI key, should return 503 (not configured)
        # This verifies the endpoint exists and routing works
        response = image_client.post(
            "/app/evaluate/image",
            files={"file": ("test.png", b"fake image data", "image/png")}
        )
        # Should return 503 because OPENAI_API_KEY is not configured
        assert response.status_code == 503
        data = response.json()
        assert data["code"] == "NOT_CONFIGURED"

    def test_rejects_invalid_file_type(self, image_client):
        """Rejects non-image file types."""
        from unittest.mock import patch, MagicMock
        os.environ["OPENAI_API_KEY"] = "test-key"  # Set temporarily

        # Mock rate limiter to always allow
        mock_limiter = MagicMock()
        mock_limiter.check.return_value = (True, 0)

        with patch("app.routers.web.get_rate_limiter", return_value=mock_limiter):
            from app.main import app
            client = TestClient(app)
            try:
                response = client.post(
                    "/app/evaluate/image",
                    files={"file": ("test.pdf", b"fake pdf data", "application/pdf")}
                )
                assert response.status_code == 400
                data = response.json()
                assert data["code"] == "INVALID_FILE_TYPE"
            finally:
                del os.environ["OPENAI_API_KEY"]

    def test_rejects_invalid_extension(self, image_client):
        """Rejects files with invalid extension."""
        from unittest.mock import patch, MagicMock
        os.environ["OPENAI_API_KEY"] = "test-key"  # Set temporarily

        # Mock rate limiter to always allow
        mock_limiter = MagicMock()
        mock_limiter.check.return_value = (True, 0)

        with patch("app.routers.web.get_rate_limiter", return_value=mock_limiter):
            from app.main import app
            client = TestClient(app)
            try:
                response = client.post(
                    "/app/evaluate/image",
                    files={"file": ("test.gif", b"fake gif data", "image/gif")}
                )
                # Should fail either on content type or extension
                assert response.status_code in [400, 503]
            finally:
                del os.environ["OPENAI_API_KEY"]

    def test_disabled_returns_503(self, image_client_disabled):
        """Returns 503 when image evaluation is disabled."""
        response = image_client_disabled.post(
            "/app/evaluate/image",
            files={"file": ("test.png", b"fake image data", "image/png")}
        )
        assert response.status_code == 503
        data = response.json()
        assert data["code"] == "FEATURE_DISABLED"

    def test_missing_file_returns_422(self, image_client):
        """Returns 422 when file is missing from request."""
        response = image_client.post("/app/evaluate/image")
        assert response.status_code == 422

    def test_response_includes_request_id(self, image_client):
        """All responses include request_id for tracing."""
        response = image_client.post(
            "/app/evaluate/image",
            files={"file": ("test.png", b"fake image data", "image/png")}
        )
        data = response.json()
        assert "request_id" in data


class TestImageEvalConfig:
    """Tests for image evaluation configuration."""

    def test_image_eval_enabled_default(self):
        """IMAGE_EVAL_ENABLED defaults to true."""
        # Clear the env var to test default
        old_val = os.environ.pop("IMAGE_EVAL_ENABLED", None)
        try:
            from app.image_eval.config import is_image_eval_enabled
            # Module may be cached, reimport to get fresh value
            import importlib
            import app.image_eval.config as config_mod
            importlib.reload(config_mod)
            assert config_mod.is_image_eval_enabled() is True
        finally:
            if old_val is not None:
                os.environ["IMAGE_EVAL_ENABLED"] = old_val

    def test_image_eval_enabled_false(self):
        """IMAGE_EVAL_ENABLED=false disables feature."""
        os.environ["IMAGE_EVAL_ENABLED"] = "false"
        try:
            import importlib
            import app.image_eval.config as config_mod
            importlib.reload(config_mod)
            assert config_mod.is_image_eval_enabled() is False
        finally:
            os.environ["IMAGE_EVAL_ENABLED"] = "true"

    def test_allowed_image_types(self):
        """ALLOWED_IMAGE_TYPES contains expected values."""
        from app.image_eval.config import ALLOWED_IMAGE_TYPES
        assert "image/png" in ALLOWED_IMAGE_TYPES
        assert "image/jpeg" in ALLOWED_IMAGE_TYPES
        assert "image/webp" in ALLOWED_IMAGE_TYPES

    def test_max_image_size(self):
        """MAX_IMAGE_SIZE is 5MB."""
        from app.image_eval.config import MAX_IMAGE_SIZE
        assert MAX_IMAGE_SIZE == 5 * 1024 * 1024


class TestImageEvaluateMocked:
    """Tests for image evaluation with mocked OpenAI response."""

    def test_successful_image_evaluation_mocked(self):
        """Test successful image evaluation with mocked OpenAI Vision API."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.image_eval.extractor import ImageParseResult

        # Set up environment
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        os.environ["IMAGE_EVAL_ENABLED"] = "true"
        os.environ["OPENAI_API_KEY"] = "test-key-mocked"

        # Create mock parse result
        mock_parse_result = ImageParseResult(
            bet_text="Lakers -5.5 (-110) + Celtics ML (-150)",
            confidence=0.92,
            notes=["2-leg parlay", "NBA basketball"],
            missing=[],
        )

        # Mock rate limiter to always allow
        mock_limiter = MagicMock()
        mock_limiter.check.return_value = (True, 0)

        # Mock the extraction function (imported inside the endpoint)
        with patch(
            "app.image_eval.extract_bet_text_from_image",
            new_callable=AsyncMock,
            return_value=mock_parse_result,
        ), patch(
            "app.routers.web.get_rate_limiter",
            return_value=mock_limiter,
        ):
            from app.main import app
            from fastapi.testclient import TestClient

            client = TestClient(app)

            # Create a minimal valid PNG (1x1 transparent pixel)
            png_bytes = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
                b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )

            response = client.post(
                "/app/evaluate/image",
                files={"file": ("betslip.png", png_bytes, "image/png")},
            )

            # Should succeed with evaluation results
            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert data["success"] is True
            assert "request_id" in data
            assert "evaluation" in data
            assert "image_parse" in data
            assert "interpretation" in data
            assert "explain" in data

            # Verify image_parse metadata
            assert data["image_parse"]["confidence"] == 0.92
            assert "2-leg parlay" in data["image_parse"]["notes"]

            # Verify input shows source as image
            assert data["input"]["source"] == "image"
            assert data["input"]["filename"] == "betslip.png"

            # Verify evaluation structure matches text endpoint
            assert "parlay_id" in data["evaluation"]
            assert "inductor" in data["evaluation"]
            assert "metrics" in data["evaluation"]
            assert "recommendation" in data["evaluation"]

        # Cleanup
        del os.environ["OPENAI_API_KEY"]

    def test_low_confidence_extraction_proceeds(self):
        """Test that low confidence (but above 0.3) extraction still proceeds."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.image_eval.extractor import ImageParseResult

        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        os.environ["IMAGE_EVAL_ENABLED"] = "true"
        os.environ["OPENAI_API_KEY"] = "test-key-mocked"

        # Create mock with low confidence but valid bet text
        mock_parse_result = ImageParseResult(
            bet_text="Warriors +3.5",
            confidence=0.45,  # Low but above 0.3 threshold
            notes=["Partial visibility"],
            missing=["odds"],
        )

        # Mock rate limiter to always allow
        mock_limiter = MagicMock()
        mock_limiter.check.return_value = (True, 0)

        with patch(
            "app.image_eval.extract_bet_text_from_image",
            new_callable=AsyncMock,
            return_value=mock_parse_result,
        ), patch(
            "app.routers.web.get_rate_limiter",
            return_value=mock_limiter,
        ):
            from app.main import app
            from fastapi.testclient import TestClient

            client = TestClient(app)

            png_bytes = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
                b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )

            response = client.post(
                "/app/evaluate/image",
                files={"file": ("betslip.png", png_bytes, "image/png")},
            )

            # Should still succeed
            assert response.status_code == 200
            data = response.json()
            assert data["image_parse"]["confidence"] == 0.45
            assert "odds" in data["image_parse"]["missing"]

        del os.environ["OPENAI_API_KEY"]

    def test_very_low_confidence_returns_422(self):
        """Test that very low confidence (<0.3) returns 422 error."""
        from unittest.mock import patch, AsyncMock, MagicMock
        from app.image_eval.extractor import ImageParseResult

        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        os.environ["IMAGE_EVAL_ENABLED"] = "true"
        os.environ["OPENAI_API_KEY"] = "test-key-mocked"

        # Create mock with very low confidence
        mock_parse_result = ImageParseResult(
            bet_text="unclear",
            confidence=0.15,  # Below 0.3 threshold
            notes=["Image too blurry"],
            missing=["all bet details"],
        )

        # Mock rate limiter to always allow
        mock_limiter = MagicMock()
        mock_limiter.check.return_value = (True, 0)

        with patch(
            "app.image_eval.extract_bet_text_from_image",
            new_callable=AsyncMock,
            return_value=mock_parse_result,
        ), patch(
            "app.routers.web.get_rate_limiter",
            return_value=mock_limiter,
        ):
            from app.main import app
            from fastapi.testclient import TestClient

            client = TestClient(app)

            png_bytes = (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
                b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )

            response = client.post(
                "/app/evaluate/image",
                files={"file": ("blurry.png", png_bytes, "image/png")},
            )

            # Should return 422 for low confidence
            assert response.status_code == 422
            data = response.json()
            assert data["code"] == "LOW_CONFIDENCE"
            assert "image_parse" in data

        del os.environ["OPENAI_API_KEY"]


class TestGoodTierStructuredOutput:
    """Tests for Ticket 3: GOOD tier structured evaluation output.

    Verifies:
    - GOOD tier returns exact schema (overallSignal, grade, fragilityScore,
      contributors, warnings, tips, removalSuggestions)
    - GOOD tier does NOT return summary/alerts/recommended_next_step
    - GOOD output differs structurally from BETTER and BEST
    - Signal/grade mapping is correct
    - Red signal is rare (only for critical fragility)
    - Contributors are typed and impact-rated
    """

    def test_good_returns_exact_schema_keys(self, client):
        """GOOD tier explain contains all required keys."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"}
        )
        assert response.status_code == 200
        explain = response.json()["explain"]
        required_keys = {"overallSignal", "grade", "fragilityScore",
                         "contributors", "warnings", "tips", "removalSuggestions"}
        assert required_keys == set(explain.keys())

    def test_good_does_not_return_summary(self, client):
        """GOOD tier must NOT include summary."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert "summary" not in explain

    def test_good_does_not_return_alerts(self, client):
        """GOOD tier must NOT include alerts."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert "alerts" not in explain

    def test_good_does_not_return_recommended_next_step(self, client):
        """GOOD tier must NOT include recommended_next_step."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert "recommended_next_step" not in explain

    def test_good_signal_is_valid_enum(self, client):
        """overallSignal must be one of blue/green/yellow/red."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert explain["overallSignal"] in ("blue", "green", "yellow", "red")

    def test_good_grade_is_valid_enum(self, client):
        """grade must be one of A/B/C/D."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert explain["grade"] in ("A", "B", "C", "D")

    def test_good_grade_maps_to_signal(self, client):
        """Grade must correspond to signal: A=blue, B=green, C=yellow, D=red."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML + Nuggets over 210", "tier": "good"}
        )
        explain = response.json()["explain"]
        grade_signal_map = {"A": "blue", "B": "green", "C": "yellow", "D": "red"}
        expected_signal = grade_signal_map[explain["grade"]]
        assert explain["overallSignal"] == expected_signal

    def test_good_fragility_score_is_numeric(self, client):
        """fragilityScore must be a number."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert isinstance(explain["fragilityScore"], (int, float))

    def test_good_fragility_score_uses_existing_scale(self, client):
        """fragilityScore must be on the 0-100 scale."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert 0 <= explain["fragilityScore"] <= 100

    def test_good_contributors_are_typed(self, client):
        """Each contributor must have type and impact fields."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML + Nuggets over", "tier": "good"}
        )
        explain = response.json()["explain"]
        for contrib in explain["contributors"]:
            assert "type" in contrib
            assert "impact" in contrib

    def test_good_contributor_types_are_valid(self, client):
        """Contributor type must be one of: correlation, volatility, leg_count, dependency."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML + Nuggets over", "tier": "good"}
        )
        explain = response.json()["explain"]
        valid_types = {"correlation", "volatility", "leg_count", "dependency"}
        for contrib in explain["contributors"]:
            assert contrib["type"] in valid_types

    def test_good_contributor_impacts_are_valid(self, client):
        """Contributor impact must be one of: low, medium, high."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML + Nuggets over", "tier": "good"}
        )
        explain = response.json()["explain"]
        valid_impacts = {"low", "medium", "high"}
        for contrib in explain["contributors"]:
            assert contrib["impact"] in valid_impacts

    def test_good_warnings_are_strings(self, client):
        """Warnings must be a list of strings."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert isinstance(explain["warnings"], list)
        for w in explain["warnings"]:
            assert isinstance(w, str)

    def test_good_tips_are_strings(self, client):
        """Tips must be a list of strings."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert isinstance(explain["tips"], list)
        for t in explain["tips"]:
            assert isinstance(t, str)

    def test_good_removal_suggestions_are_strings(self, client):
        """removalSuggestions must be a list of strings (leg_ids)."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert isinstance(explain["removalSuggestions"], list)
        for r in explain["removalSuggestions"]:
            assert isinstance(r, str)

    def test_good_differs_from_better(self, client):
        """GOOD output must be structurally different from BETTER."""
        good_resp = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"}
        )
        better_resp = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "better"}
        )
        good_explain = good_resp.json()["explain"]
        better_explain = better_resp.json()["explain"]
        # GOOD has overallSignal, BETTER has summary
        assert "overallSignal" in good_explain
        assert "overallSignal" not in better_explain
        assert "summary" in better_explain
        assert "summary" not in good_explain

    def test_good_differs_from_best(self, client):
        """GOOD output must be structurally different from BEST."""
        good_resp = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"}
        )
        best_resp = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "best"}
        )
        good_explain = good_resp.json()["explain"]
        best_explain = best_resp.json()["explain"]
        # GOOD has structured fields, BEST has prose fields
        assert "grade" in good_explain
        assert "grade" not in best_explain
        assert "alerts" in best_explain
        assert "alerts" not in good_explain

    def test_red_signal_only_for_critical(self, client):
        """Red signal only appears when fragility is critical (>60)."""
        # Simple input -> low fragility -> not red
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers ML", "tier": "good"}
        )
        explain = response.json()["explain"]
        if explain["fragilityScore"] <= 60:
            assert explain["overallSignal"] != "red"

    def test_yellow_is_common_for_multi_leg(self, client):
        """Multi-leg parlays typically produce yellow signal."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML + Nuggets over 210.5 + Bucks -3", "tier": "good"}
        )
        explain = response.json()["explain"]
        # 4-leg parlay should produce yellow or higher
        assert explain["overallSignal"] in ("yellow", "red")
        assert explain["grade"] in ("C", "D")

    def test_good_has_leg_count_contributor_for_multi_leg(self, client):
        """Multi-leg parlay should have leg_count as contributor."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML + Nuggets over 210.5", "tier": "good"}
        )
        explain = response.json()["explain"]
        contrib_types = [c["type"] for c in explain["contributors"]]
        assert "leg_count" in contrib_types

    def test_good_has_tips_for_high_fragility(self, client):
        """High fragility should produce tips."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lebron 25 points + AD 10 rebounds + Tatum 30 points + Jokic 12 assists", "tier": "good"}
        )
        explain = response.json()["explain"]
        assert len(explain["tips"]) > 0

    def test_good_deterministic(self, client):
        """Same input produces same GOOD output (deterministic)."""
        input_data = {"input": "Lakers -5.5 + Celtics ML", "tier": "good"}
        resp1 = client.post("/app/evaluate", json=input_data)
        resp2 = client.post("/app/evaluate", json=input_data)
        explain1 = resp1.json()["explain"]
        explain2 = resp2.json()["explain"]
        assert explain1["overallSignal"] == explain2["overallSignal"]
        assert explain1["grade"] == explain2["grade"]
        assert explain1["fragilityScore"] == explain2["fragilityScore"]
        assert explain1["contributors"] == explain2["contributors"]

    def test_better_unchanged(self, client):
        """BETTER tier response is not affected by GOOD changes."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "better"}
        )
        explain = response.json()["explain"]
        assert "summary" in explain
        assert isinstance(explain["summary"], list)
        assert "overallSignal" not in explain
        assert "grade" not in explain

    def test_best_unchanged(self, client):
        """BEST tier response is not affected by GOOD changes."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5 + Celtics ML", "tier": "best"}
        )
        explain = response.json()["explain"]
        assert "summary" in explain
        assert "alerts" in explain
        assert "recommended_next_step" in explain
        assert "overallSignal" not in explain

    def test_good_output_html_container_exists(self, client):
        """Frontend has dedicated GOOD tier output container."""
        response = client.get("/app")
        html = response.text
        assert 'id="eval-good-output"' in html
        assert 'class="good-output hidden"' in html

    def test_good_output_has_all_sections(self, client):
        """Frontend GOOD output has all required section elements."""
        response = client.get("/app")
        html = response.text
        assert 'id="good-signal-grade"' in html
        assert 'id="good-fragility"' in html
        assert 'id="good-contributors-section"' in html
        assert 'id="good-warnings-section"' in html
        assert 'id="good-tips-section"' in html
        assert 'id="good-removals-section"' in html

    def test_good_output_does_not_reuse_better_best_ids(self, client):
        """GOOD output uses its own IDs, not shared tier panel IDs."""
        response = client.get("/app")
        html = response.text
        # GOOD container should not reference the shared panel IDs
        good_section = html[html.find('id="eval-good-output"'):html.find('<!-- Shared tier panels')]
        assert 'eval-correlations-panel' not in good_section
        assert 'eval-summary-panel' not in good_section
        assert 'eval-alerts-panel' not in good_section


class TestPrimaryFailureAndDeltaPreview:
    """Ticket 4: primaryFailure + deltaPreview tests."""

    BANNED_PHRASES = [
        "too risky", "too fragile", "exceeds safe",
        "structure exceeds", "high fragility thresholds",
    ]

    # --- primaryFailure presence for all tiers ---

    def test_primary_failure_exists_good(self, client):
        """primaryFailure present in GOOD tier response."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        assert resp.status_code == 200
        data = resp.json()
        assert "primaryFailure" in data
        assert data["primaryFailure"] is not None

    def test_primary_failure_exists_better(self, client):
        """primaryFailure present in BETTER tier response."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "better"})
        assert resp.status_code == 200
        assert "primaryFailure" in resp.json()
        assert resp.json()["primaryFailure"] is not None

    def test_primary_failure_exists_best(self, client):
        """primaryFailure present in BEST tier response."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "best"})
        assert resp.status_code == 200
        assert "primaryFailure" in resp.json()
        assert resp.json()["primaryFailure"] is not None

    # --- primaryFailure schema ---

    def test_primary_failure_has_required_keys(self, client):
        """primaryFailure has type, severity, description, affectedLegIds, fastestFix."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML + Nuggets ML", "tier": "good"})
        pf = resp.json()["primaryFailure"]
        assert "type" in pf
        assert "severity" in pf
        assert "description" in pf
        assert "affectedLegIds" in pf
        assert "fastestFix" in pf

    def test_primary_failure_type_is_valid_enum(self, client):
        """primaryFailure.type is one of the allowed types."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        pf = resp.json()["primaryFailure"]
        assert pf["type"] in ("correlation", "leg_count", "dependency", "volatility")

    def test_primary_failure_severity_is_valid_enum(self, client):
        """primaryFailure.severity is low/medium/high."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        pf = resp.json()["primaryFailure"]
        assert pf["severity"] in ("low", "medium", "high")

    def test_primary_failure_affected_leg_ids_is_list(self, client):
        """affectedLegIds is always a list."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "good"})
        pf = resp.json()["primaryFailure"]
        assert isinstance(pf["affectedLegIds"], list)

    def test_fastest_fix_has_required_keys(self, client):
        """fastestFix has action, description, candidateLegIds."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML + Nuggets ML", "tier": "good"})
        fix = resp.json()["primaryFailure"]["fastestFix"]
        assert "action" in fix
        assert "description" in fix
        assert "candidateLegIds" in fix

    def test_fastest_fix_action_is_valid_enum(self, client):
        """fastestFix.action is one of the allowed actions."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        fix = resp.json()["primaryFailure"]["fastestFix"]
        valid_actions = ("remove_leg", "swap_leg", "split_parlay", "reduce_same_game", "reduce_props")
        assert fix["action"] in valid_actions

    # --- No banned phrases ---

    def test_primary_failure_no_banned_phrases(self, client):
        """primaryFailure.description must not contain banned generic phrases."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML + Nuggets ML + Bucks -3", "tier": "good"})
        pf = resp.json()["primaryFailure"]
        desc_lower = pf["description"].lower()
        for phrase in self.BANNED_PHRASES:
            assert phrase not in desc_lower, f"Banned phrase '{phrase}' found in: {pf['description']}"

    def test_fastest_fix_no_banned_phrases(self, client):
        """fastestFix.description must not contain generic phrases."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML + Nuggets ML", "tier": "good"})
        fix = resp.json()["primaryFailure"]["fastestFix"]
        desc_lower = fix["description"].lower()
        for phrase in self.BANNED_PHRASES:
            assert phrase not in desc_lower

    def test_good_warnings_no_banned_phrases(self, client):
        """GOOD tier warnings must not contain banned phrases."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML + Nuggets ML + Bucks -3", "tier": "good"})
        warnings = resp.json()["explain"].get("warnings", [])
        for w in warnings:
            w_lower = w.lower()
            for phrase in self.BANNED_PHRASES:
                assert phrase not in w_lower, f"Banned phrase '{phrase}' in warning: {w}"

    # --- deltaPreview ---

    def test_delta_preview_exists_all_tiers(self, client):
        """deltaPreview present in response for all tiers."""
        for tier in ("good", "better", "best"):
            resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": tier})
            assert "deltaPreview" in resp.json(), f"deltaPreview missing for tier={tier}"

    def test_delta_preview_has_before(self, client):
        """deltaPreview.before is always present with signal/grade/fragilityScore."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        dp = resp.json()["deltaPreview"]
        assert dp["before"] is not None
        assert "signal" in dp["before"]
        assert "grade" in dp["before"]
        assert "fragilityScore" in dp["before"]

    def test_delta_preview_before_signal_valid(self, client):
        """deltaPreview.before.signal is a valid color."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        dp = resp.json()["deltaPreview"]
        assert dp["before"]["signal"] in ("blue", "green", "yellow", "red")

    def test_delta_preview_multi_leg_has_after(self, client):
        """Multi-leg parlay with remove_leg action produces non-null after."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets ML + Bucks -3",
            "tier": "good"
        })
        data = resp.json()
        pf = data["primaryFailure"]
        dp = data["deltaPreview"]
        # If action is remove_leg with candidates, after should exist
        if pf["fastestFix"]["action"] == "remove_leg" and pf["fastestFix"]["candidateLegIds"]:
            assert dp["after"] is not None
            assert dp["change"] is not None

    def test_delta_preview_after_fragility_improves(self, client):
        """When deltaPreview.after exists, fragility should decrease (fix improves bet)."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets ML + Bucks -3",
            "tier": "good"
        })
        dp = resp.json()["deltaPreview"]
        if dp["after"] is not None:
            assert dp["after"]["fragilityScore"] <= dp["before"]["fragilityScore"]

    def test_delta_preview_single_leg_no_after(self, client):
        """Single-leg bet cannot simulate remove_leg, so after=null."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "good"})
        dp = resp.json()["deltaPreview"]
        # Single leg cannot remove, so after should be null
        assert dp["after"] is None
        assert dp["change"] is None

    def test_delta_preview_deterministic(self, client):
        """Same input produces same deltaPreview."""
        input_data = {"input": "Lakers -5.5 + Celtics ML + Nuggets ML", "tier": "good"}
        dp1 = client.post("/app/evaluate", json=input_data).json()["deltaPreview"]
        dp2 = client.post("/app/evaluate", json=input_data).json()["deltaPreview"]
        assert dp1["before"]["fragilityScore"] == dp2["before"]["fragilityScore"]
        if dp1["after"]:
            assert dp1["after"]["fragilityScore"] == dp2["after"]["fragilityScore"]

    def test_delta_preview_change_directions(self, client):
        """change.signal and change.fragility use valid direction values."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets ML",
            "tier": "good"
        })
        dp = resp.json()["deltaPreview"]
        if dp["change"] is not None:
            assert dp["change"]["signal"] in ("up", "down", "same")
            assert dp["change"]["fragility"] in ("up", "down", "same")

    # --- Tier separation ---

    def test_good_does_not_include_best_keys(self, client):
        """GOOD tier explain does not contain BEST-only keys."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        explain = resp.json()["explain"]
        assert "alerts" not in explain
        assert "recommended_next_step" not in explain
        assert "summary" not in explain

    def test_better_does_not_include_best_keys(self, client):
        """BETTER tier explain does not contain BEST-only keys."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "better"})
        explain = resp.json()["explain"]
        assert "alerts" not in explain
        assert "recommended_next_step" not in explain

    def test_primary_failure_same_across_tiers(self, client):
        """primaryFailure is the same regardless of tier (core truth)."""
        input_text = "Lakers -5.5 + Celtics ML + Nuggets ML"
        good = client.post("/app/evaluate", json={"input": input_text, "tier": "good"}).json()
        better = client.post("/app/evaluate", json={"input": input_text, "tier": "better"}).json()
        best = client.post("/app/evaluate", json={"input": input_text, "tier": "best"}).json()
        assert good["primaryFailure"]["type"] == better["primaryFailure"]["type"]
        assert good["primaryFailure"]["type"] == best["primaryFailure"]["type"]
        assert good["primaryFailure"]["severity"] == better["primaryFailure"]["severity"]

    # --- Frontend HTML ---

    def test_primary_failure_card_exists_in_html(self, client):
        """Primary failure card element exists in the app HTML."""
        resp = client.get("/app")
        html = resp.text
        assert 'id="eval-primary-failure"' in html
        assert 'id="pf-badge"' in html
        assert 'id="pf-description"' in html
        assert 'id="pf-fix-desc"' in html

    def test_delta_preview_elements_exist_in_html(self, client):
        """Delta preview elements exist in app HTML."""
        resp = client.get("/app")
        html = resp.text
        assert 'id="pf-delta"' in html
        assert 'id="pf-delta-before"' in html
        assert 'id="pf-delta-after"' in html

    def test_primary_failure_card_above_tips(self, client):
        """Primary failure card appears before tips panel in DOM order."""
        resp = client.get("/app")
        html = resp.text
        pf_pos = html.find('id="eval-primary-failure"')
        tips_pos = html.find('id="eval-tips-panel"')
        assert pf_pos < tips_pos, "Primary failure card must be above tips panel"

    # --- Description specificity ---

    def test_primary_failure_description_not_empty(self, client):
        """primaryFailure.description is never empty."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        pf = resp.json()["primaryFailure"]
        assert len(pf["description"]) > 10

    def test_primary_failure_description_references_cause(self, client):
        """Description references numeric data (penalty, count, etc)."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets ML + Bucks -3",
            "tier": "good"
        })
        pf = resp.json()["primaryFailure"]
        # Must contain at least one number (penalty value, count, etc.)
        import re
        assert re.search(r'\d', pf["description"]), f"Description has no numeric data: {pf['description']}"

    def test_fastest_fix_description_is_actionable(self, client):
        """fastestFix.description starts with an action verb."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML + Nuggets ML", "tier": "good"})
        fix = resp.json()["primaryFailure"]["fastestFix"]
        action_verbs = ("remove", "split", "replace", "reduce", "move", "simplify")
        assert any(fix["description"].lower().startswith(v) for v in action_verbs), \
            f"Fix description not actionable: {fix['description']}"
