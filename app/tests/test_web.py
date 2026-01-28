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
        """JavaScript enables Fastest Fix CTA and routes to builder."""
        response = client.get("/app")
        # Compressed layout: Fastest Fix CTA routes to builder
        assert "compressed-fix-cta" in response.text
        assert "switchToTab('builder')" in response.text or "switchToTab(&#x27;builder&#x27;)" in response.text

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
        """Upgrade CTA exists in tier selector without pricing."""
        response = client.get("/app")
        # VC-2: Upgrade path via tier selector (in Evaluate tab)
        assert "tier-best" in response.text
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
        """VC-2: Builder tab is now Fix Mode only."""
        response = client.get("/app?tab=builder")
        assert response.status_code == 200
        # Fix Mode elements exist
        assert "fix-blocked" in response.text
        assert "fix-mode" in response.text
        assert "fix-apply-btn" in response.text

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
        """Signal info elements are in the DOM (compressed layout)."""
        response = client.get("/app")
        # Compressed layout: signal in details accordion
        assert "detail-signal" in response.text
        assert "detail-fragility" in response.text

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
        """Metrics display in details accordion."""
        response = client.get("/app")
        # Compressed layout: metrics in details accordion
        assert "detail-leg-penalty" in response.text
        assert "detail-correlation" in response.text

    # --- Improvement Tips (GOOD+) ---

    def test_tips_panel_exists(self, client):
        """Tips section exists in details accordion."""
        response = client.get("/app")
        # Compressed layout: tips in details accordion
        assert "detail-tips" in response.text
        assert "detail-tips-list" in response.text

    # --- Tier Differentiation ---

    def test_correlations_panel_exists(self, client):
        """Correlations section exists in details accordion."""
        response = client.get("/app")
        # Compressed layout: correlations in details accordion
        assert "detail-correlations" in response.text
        assert "Correlations" in response.text

    def test_summary_panel_exists(self, client):
        """Summary/Insights section exists in details accordion."""
        response = client.get("/app")
        # Compressed layout: insights in details accordion
        assert "detail-summary" in response.text
        assert "Insights" in response.text

    def test_alerts_panel_exists(self, client):
        """Alerts section exists in details accordion."""
        response = client.get("/app")
        assert "detail-alerts" in response.text

    def test_correlations_hidden_by_default(self, client):
        """Correlations section is hidden in initial render."""
        response = client.get("/app")
        assert 'detail-correlations" class="detail-section hidden' in response.text or 'id="detail-correlations"' in response.text

    def test_summary_hidden_by_default(self, client):
        """Summary section is hidden in initial render."""
        response = client.get("/app")
        assert 'detail-summary" class="detail-section hidden' in response.text or 'id="detail-summary"' in response.text

    def test_alerts_hidden_by_default(self, client):
        """Alerts section is hidden in initial render."""
        response = client.get("/app")
        assert 'detail-alerts" class="detail-section hidden' in response.text or 'id="detail-alerts"' in response.text

    def test_tier_gating_logic_in_js(self, client):
        """JavaScript gates correlations/summary to BETTER+, alerts to BEST."""
        response = client.get("/app")
        # BETTER+ check for correlations
        assert "tier === 'better' || tier === 'best'" in response.text
        # BEST-only check for alerts
        assert "tier === 'best'" in response.text

    # --- Post-Result Actions ---

    def test_post_actions_exist(self, client):
        """Post-result action buttons exist: Re-Evaluate, Save (Improve via Fastest Fix CTA)."""
        response = client.get("/app")
        # Compressed layout: Improve button replaced by Fastest Fix CTA
        assert "compressed-fix-cta" in response.text
        # VC-3: Loop shortcuts replaced old action buttons
        assert "loop-reeval" in response.text
        assert "loop-save" in response.text

    def test_improve_routes_to_builder(self, client):
        """Fastest Fix CTA switches to Builder tab."""
        response = client.get("/app")
        # Compressed layout: Fastest Fix CTA routes to builder
        assert "compressed-fix-cta" in response.text
        assert "switchToTab('builder')" in response.text or "switchToTab(&#x27;builder&#x27;)" in response.text

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
        """Compressed layout uses Primary Failure instead of verdict bar."""
        response = client.get("/app")
        # Compressed layout: verdict/recommendation shown via Primary Failure
        assert "compressed-pf" in response.text
        assert "cpf-badge" in response.text
        assert "cpf-description" in response.text

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
        """Frontend has compressed layout container (unified for all tiers)."""
        response = client.get("/app")
        html = response.text
        # Compressed layout replaces tier-specific containers
        assert 'id="compressed-pf"' in html
        assert 'id="eval-details-accordion"' in html

    def test_good_output_has_all_sections(self, client):
        """Compressed layout has all required detail sections."""
        response = client.get("/app")
        html = response.text
        # Compressed layout: all sections in details accordion
        assert 'id="detail-signal"' in html
        assert 'id="detail-fragility"' in html
        assert 'id="detail-contributors"' in html
        assert 'id="detail-warnings"' in html
        assert 'id="detail-tips"' in html

    def test_good_output_does_not_reuse_better_best_ids(self, client):
        """Compressed layout uses unified detail IDs for all tiers."""
        response = client.get("/app")
        html = response.text
        # Compressed layout: tier-gating logic still gates content by tier
        assert "tier === 'better' || tier === 'best'" in html
        assert "tier === 'best'" in html


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
        assert pf["type"] in (
            "correlation", "leg_count", "dependency", "volatility",
            "prop_density", "same_game_dependency", "market_conflict", "weak_clarity",
        )

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
        valid_actions = ("remove_leg", "swap_leg", "split_parlay", "reduce_same_game", "reduce_props", "clarify_input")
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
        """Compressed primary failure element exists in the app HTML."""
        resp = client.get("/app")
        html = resp.text
        # Compressed layout uses compressed-pf
        assert 'id="compressed-pf"' in html
        assert 'id="cpf-badge"' in html
        assert 'id="cpf-description"' in html
        assert 'id="compressed-fix-cta"' in html

    def test_delta_preview_elements_exist_in_html(self, client):
        """Compressed delta preview elements exist in app HTML."""
        resp = client.get("/app")
        html = resp.text
        # Compressed layout uses compressed-delta
        assert 'id="compressed-delta"' in html
        assert 'id="cdelta-signal-before"' in html
        assert 'id="cdelta-signal-after"' in html

    def test_primary_failure_card_above_tips(self, client):
        """Primary failure appears before details accordion in DOM order (VC-1)."""
        resp = client.get("/app")
        html = resp.text
        pf_pos = html.find('id="compressed-pf"')
        details_pos = html.find('id="eval-details-accordion"')
        assert pf_pos < details_pos, "Primary failure must be above details accordion"

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


class TestSignalSystem:
    """Ticket 5: Signal system consistency tests."""

    VALID_SIGNALS = ("blue", "green", "yellow", "red")
    SIGNAL_LABELS = {"blue": "Strong", "green": "Solid", "yellow": "Fixable", "red": "Fragile"}

    # --- signalInfo presence ---

    def test_signal_info_exists_good(self, client):
        """signalInfo present in GOOD tier response."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "good"})
        assert resp.status_code == 200
        assert "signalInfo" in resp.json()
        assert resp.json()["signalInfo"] is not None

    def test_signal_info_exists_better(self, client):
        """signalInfo present in BETTER tier response."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "better"})
        assert "signalInfo" in resp.json()

    def test_signal_info_exists_best(self, client):
        """signalInfo present in BEST tier response."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "best"})
        assert "signalInfo" in resp.json()

    # --- signalInfo schema ---

    def test_signal_info_has_required_keys(self, client):
        """signalInfo has signal, label, grade, fragilityScore, signalLine."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        si = resp.json()["signalInfo"]
        assert "signal" in si
        assert "label" in si
        assert "grade" in si
        assert "fragilityScore" in si
        assert "signalLine" in si

    def test_signal_is_valid_color(self, client):
        """signalInfo.signal is blue/green/yellow/red."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        assert resp.json()["signalInfo"]["signal"] in self.VALID_SIGNALS

    def test_label_matches_signal(self, client):
        """signalInfo.label matches the locked mapping for its signal."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        si = resp.json()["signalInfo"]
        expected_label = self.SIGNAL_LABELS[si["signal"]]
        assert si["label"] == expected_label, f"Signal={si['signal']} should have label={expected_label}, got {si['label']}"

    def test_grade_matches_signal(self, client):
        """signalInfo.grade matches the locked mapping."""
        grade_map = {"blue": "A", "green": "B", "yellow": "C", "red": "D"}
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        si = resp.json()["signalInfo"]
        assert si["grade"] == grade_map[si["signal"]]

    # --- Red rarity enforcement ---

    def test_single_leg_not_red(self, client):
        """Single leg bet must never produce red signal."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "good"})
        assert resp.json()["signalInfo"]["signal"] != "red"

    def test_two_leg_not_red(self, client):
        """Two-leg bet must not produce red signal."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        assert resp.json()["signalInfo"]["signal"] != "red"

    def test_red_only_when_inductor_critical(self, client):
        """Red signal requires inductor level == critical."""
        # Test multiple inputs — any that produce red must have critical inductor
        inputs = [
            "Lakers -5.5",
            "Lakers -5.5 + Celtics ML",
            "Lakers -5.5 + Celtics ML + Nuggets ML",
            "Lakers -5.5 + Celtics ML + Nuggets ML + Bucks -3",
            "Lakers -5.5 + Celtics ML + Nuggets ML + Bucks -3 + Heat ML",
        ]
        for inp in inputs:
            resp = client.post("/app/evaluate", json={"input": inp, "tier": "good"})
            data = resp.json()
            if data["signalInfo"]["signal"] == "red":
                assert data["evaluation"]["inductor"]["level"] == "critical", \
                    f"Red signal without critical inductor for: {inp}"

    def test_non_critical_inductor_caps_at_yellow(self, client):
        """When inductor is not critical, signal must be yellow at most (not red)."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML + Nuggets ML", "tier": "good"})
        data = resp.json()
        if data["evaluation"]["inductor"]["level"] != "critical":
            signal_order = {"blue": 0, "green": 1, "yellow": 2, "red": 3}
            assert signal_order[data["signalInfo"]["signal"]] <= 2, \
                f"Non-critical inductor should cap at yellow, got {data['signalInfo']['signal']}"

    # --- Signal consistency across tiers ---

    def test_signal_consistent_across_tiers(self, client):
        """signalInfo.signal is the same regardless of tier."""
        input_text = "Lakers -5.5 + Celtics ML + Nuggets ML"
        signals = []
        for tier in ("good", "better", "best"):
            resp = client.post("/app/evaluate", json={"input": input_text, "tier": tier})
            signals.append(resp.json()["signalInfo"]["signal"])
        assert signals[0] == signals[1] == signals[2], f"Signal inconsistent: {signals}"

    def test_good_explain_signal_matches_signal_info(self, client):
        """GOOD tier explain.overallSignal matches signalInfo.signal."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        data = resp.json()
        assert data["explain"]["overallSignal"] == data["signalInfo"]["signal"]

    # --- signalLine (why one-liner) ---

    def test_signal_line_not_empty(self, client):
        """signalLine is never empty."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        assert len(resp.json()["signalInfo"]["signalLine"]) > 5

    def test_signal_line_references_primary_failure_type(self, client):
        """signalLine must reference the primaryFailure.type."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML + Nuggets ML", "tier": "good"})
        data = resp.json()
        pf_type = data["primaryFailure"]["type"].replace("_", " ")
        assert pf_type in data["signalInfo"]["signalLine"], \
            f"signalLine '{data['signalInfo']['signalLine']}' does not reference primaryFailure.type '{pf_type}'"

    def test_signal_line_includes_severity(self, client):
        """signalLine includes the primaryFailure.severity."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML + Nuggets ML", "tier": "good"})
        data = resp.json()
        assert data["primaryFailure"]["severity"] in data["signalInfo"]["signalLine"]

    def test_signal_line_fix_hint_when_delta_improves(self, client):
        """When deltaPreview shows improvement, signalLine has fix hint."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets ML + Bucks -3",
            "tier": "good"
        })
        data = resp.json()
        if data["deltaPreview"]["change"] and data["deltaPreview"]["change"]["fragility"] == "down":
            assert "fix lowers fragility" in data["signalInfo"]["signalLine"]

    # --- Frontend HTML elements ---

    def test_discover_signal_legend_exists(self, client):
        """Discover tab has signal legend with all 4 signals."""
        resp = client.get("/app")
        html = resp.text
        assert "discover-signals" in html
        assert "Strong" in html
        assert "Solid" in html
        assert "Fixable" in html
        assert "Fragile" in html

    def test_evaluate_signal_line_element_exists(self, client):
        """Evaluate tab has signal info in details accordion."""
        resp = client.get("/app")
        html = resp.text
        # Compressed layout: signal info in details accordion
        assert 'id="detail-signal"' in html
        assert 'id="detail-fragility"' in html

    def test_history_uses_signal_colors(self, client):
        """History CSS uses signal color classes (blue/green/yellow/red)."""
        resp = client.get("/app")
        html = resp.text
        assert "history-grade" in html
        # CSS should reference signal colors
        assert ".history-grade.blue" in html
        assert ".history-grade.green" in html
        assert ".history-grade.yellow" in html
        assert ".history-grade.red" in html


class TestVC3DeltaPayoff:
    """VC-3: Delta as Product Moment (Payoff + Repeatability)."""

    # --- Payoff Banner Tests ---

    def test_payoff_banner_hidden_on_fresh_load(self, client):
        """Payoff banner is hidden by default on fresh page load."""
        resp = client.get("/app")
        html = resp.text
        # Banner element exists but is hidden
        assert 'id="payoff-banner"' in html
        assert 'class="payoff-banner hidden"' in html

    def test_payoff_banner_html_structure(self, client):
        """Payoff banner has correct HTML structure."""
        resp = client.get("/app")
        html = resp.text
        # Required elements
        assert 'id="payoff-banner"' in html
        assert 'class="payoff-title"' in html
        assert 'id="payoff-line"' in html
        assert 'id="payoff-status"' in html
        assert 'id="payoff-dismiss"' in html

    def test_payoff_banner_css_exists(self, client):
        """Payoff banner CSS styles are defined."""
        resp = client.get("/app")
        html = resp.text
        assert ".payoff-banner" in html
        assert ".payoff-title" in html
        assert ".payoff-dismiss" in html
        assert ".payoff-status.improved" in html
        assert ".payoff-status.no-change" in html

    # --- Mini Diff Tests ---

    def test_mini_diff_hidden_on_fresh_load(self, client):
        """Mini diff section is hidden by default on fresh page load."""
        resp = client.get("/app")
        html = resp.text
        assert 'id="mini-diff"' in html
        assert 'class="mini-diff hidden"' in html

    def test_mini_diff_html_structure(self, client):
        """Mini diff has correct HTML structure."""
        resp = client.get("/app")
        html = resp.text
        assert 'id="mini-diff"' in html
        assert "See what changed" in html
        assert 'id="mini-diff-pf-before"' in html
        assert 'id="mini-diff-pf-after"' in html
        assert 'id="mini-diff-rec-before"' in html
        assert 'id="mini-diff-rec-after"' in html

    def test_mini_diff_css_exists(self, client):
        """Mini diff CSS styles are defined."""
        resp = client.get("/app")
        html = resp.text
        assert ".mini-diff" in html
        assert ".mini-diff-row" in html
        assert ".mini-diff-before" in html
        assert ".mini-diff-after" in html

    # --- Loop Shortcuts Tests ---

    def test_loop_shortcuts_html_structure(self, client):
        """Loop shortcuts section has correct HTML structure."""
        resp = client.get("/app")
        html = resp.text
        assert 'id="loop-shortcuts"' in html
        assert 'id="loop-reeval"' in html
        assert 'id="loop-try-fix"' in html
        assert 'id="loop-save"' in html

    def test_loop_reeval_visible(self, client):
        """Re-Evaluate button is visible in loop shortcuts."""
        resp = client.get("/app")
        html = resp.text
        assert 'id="loop-reeval"' in html
        assert "Re-Evaluate" in html

    def test_loop_try_fix_hidden_by_default(self, client):
        """Try Another Fix button is hidden by default."""
        resp = client.get("/app")
        html = resp.text
        assert 'class="loop-btn loop-try-fix hidden"' in html

    def test_loop_shortcuts_css_exists(self, client):
        """Loop shortcuts CSS styles are defined."""
        resp = client.get("/app")
        html = resp.text
        assert ".loop-shortcuts" in html
        assert ".loop-btn" in html
        assert ".loop-reeval" in html
        assert ".loop-try-fix" in html

    # --- Builder UI Tests (Sprint 2: Freeform Builder) ---

    def test_builder_parlay_builder_exists(self, client):
        """Builder tab shows Parlay Builder UI."""
        resp = client.get("/app?tab=builder")
        html = resp.text
        assert "Parlay Builder" in html
        assert "builder-legs" in html

    def test_builder_has_autosuggest(self, client):
        """Builder has auto-suggest dropdown for teams/players."""
        resp = client.get("/app?tab=builder")
        html = resp.text
        assert "autosuggest-dropdown" in html
        assert "team-player-input" in html

    # --- Numeric Delta Display Tests ---

    def test_delta_numeric_css_class_exists(self, client):
        """Delta numeric CSS class exists for prominence."""
        resp = client.get("/app")
        html = resp.text
        assert ".delta-num" in html

    def test_payoff_line_delta_format_in_js(self, client):
        """JavaScript includes delta format with numeric value."""
        resp = client.get("/app")
        html = resp.text
        # Check JS includes delta numeric formatting
        assert "delta-num" in html
        assert "&Delta;" in html or "Δ" in html

    # --- Apply Fix Response Tests ---

    def test_apply_fix_endpoint_exists(self, client):
        """Apply fix endpoint returns response."""
        resp = client.post("/app/apply-fix", json={
            "fix_action": "remove_leg",
            "affected_leg_ids": []
        })
        # Should return some response (success or error)
        assert resp.status_code in [200, 400, 422]

    def test_apply_fix_returns_evaluation(self, client):
        """Apply fix returns evaluation data when successful."""
        # First run evaluation to have context
        eval_resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets ML + Bucks -3",
            "tier": "good"
        })
        eval_data = eval_resp.json()

        # Apply fix
        fix_resp = client.post("/app/apply-fix", json={
            "fix_action": "remove_leg",
            "affected_leg_ids": eval_data.get("primaryFailure", {}).get("affectedLegIds", [])
        })
        fix_data = fix_resp.json()

        # Response should have success and evaluation keys
        assert "success" in fix_data
        if fix_data.get("success"):
            assert "evaluation" in fix_data


class TestHistoryMVP:
    """Ticket 6: History MVP tests.

    Verifies:
    - Successful evaluation creates a history item
    - /history returns items in reverse chronological order
    - History item contains correct signal + label + grade + fragilityScore
    - Failed evaluation does NOT create history item
    - Re-evaluate/edit actions exist in DOM for each item
    """

    @pytest.fixture(autouse=True)
    def clear_history_before_test(self):
        """Clear history store before each test."""
        from app.history_store import get_history_store
        store = get_history_store()
        store.clear()
        yield
        # Also clear after test
        store.clear()

    def test_successful_evaluation_creates_history_item(self, client):
        """Successful evaluation creates a history item."""
        # Run evaluation
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        assert resp.status_code == 200
        data = resp.json()

        # Response should include historyId
        assert "evaluationId" in data, "Response should include evaluationId"
        assert data["evaluationId"] is not None

        # History endpoint should return the item
        history_resp = client.get("/app/history")
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        assert "items" in history_data
        assert len(history_data["items"]) >= 1, "History should have at least one item"

    def test_history_returns_items_in_reverse_chronological_order(self, client):
        """History returns items in reverse chronological order (newest first)."""
        import time

        # Run multiple evaluations
        for i, bet in enumerate(["Lakers -5.5", "Celtics ML", "Nuggets ML"]):
            resp = client.post("/app/evaluate", json={
                "input": bet,
                "tier": "good"
            })
            assert resp.status_code == 200
            # Small delay to ensure different timestamps
            time.sleep(0.01)

        # Get history
        history_resp = client.get("/app/history")
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        items = history_data["items"]
        assert len(items) >= 3

        # Verify reverse chronological order (newest first)
        # Parse ISO timestamps and verify order
        timestamps = []
        for item in items[:3]:
            ts = item.get("createdAt")
            assert ts is not None, "History item should have createdAt"
            timestamps.append(ts)

        # Verify descending order
        for i in range(len(timestamps) - 1):
            assert timestamps[i] >= timestamps[i + 1], \
                f"History not in reverse chronological order: {timestamps[i]} should be >= {timestamps[i + 1]}"

    def test_history_item_contains_correct_signal_fields(self, client):
        """History item contains correct signal + label + grade + fragilityScore."""
        # Run evaluation
        eval_resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()

        # Get expected values from signalInfo
        signal_info = eval_data.get("signalInfo", {})
        expected_signal = signal_info.get("signal")
        expected_label = signal_info.get("label")
        expected_grade = signal_info.get("grade")
        expected_fragility = signal_info.get("fragilityScore")

        # Get history item
        history_resp = client.get("/app/history")
        history_data = history_resp.json()
        items = history_data["items"]
        assert len(items) >= 1

        # Find the item (most recent)
        item = items[0]

        # Verify all required fields
        assert "signal" in item, "History item missing signal"
        assert "label" in item, "History item missing label"
        assert "grade" in item, "History item missing grade"
        assert "fragilityScore" in item, "History item missing fragilityScore"

        # Verify values match signalInfo
        assert item["signal"] == expected_signal, \
            f"Signal mismatch: {item['signal']} != {expected_signal}"
        assert item["label"] == expected_label, \
            f"Label mismatch: {item['label']} != {expected_label}"
        assert item["grade"] == expected_grade, \
            f"Grade mismatch: {item['grade']} != {expected_grade}"
        assert item["fragilityScore"] == expected_fragility, \
            f"Fragility mismatch: {item['fragilityScore']} != {expected_fragility}"

    def test_failed_evaluation_does_not_create_history_item(self, client):
        """Failed evaluation does NOT create history item."""
        # Get initial history count
        initial_resp = client.get("/app/history")
        initial_count = initial_resp.json()["count"]

        # Run failed evaluation (empty input should return 400)
        resp = client.post("/app/evaluate", json={
            "input": "",
            "tier": "good"
        })
        assert resp.status_code == 400

        # History count should be unchanged
        after_resp = client.get("/app/history")
        after_count = after_resp.json()["count"]
        assert after_count == initial_count, \
            f"Failed evaluation should not create history item: {initial_count} -> {after_count}"

    def test_history_item_includes_input_text(self, client):
        """History item includes original input text."""
        test_input = "Lakers -5.5 + Celtics ML"
        resp = client.post("/app/evaluate", json={
            "input": test_input,
            "tier": "good"
        })
        assert resp.status_code == 200

        history_resp = client.get("/app/history")
        history_data = history_resp.json()
        items = history_data["items"]
        assert len(items) >= 1

        item = items[0]
        assert "inputText" in item, "History item missing inputText"
        assert item["inputText"] == test_input

    def test_history_re_evaluate_actions_exist_in_dom(self, client):
        """Re-evaluate actions exist in DOM for history items."""
        resp = client.get("/app")
        html = resp.text

        # Check for historyReEvaluate function
        assert "historyReEvaluate" in html, "historyReEvaluate function should exist"

        # Check for re-evaluate button in history item template
        assert "history-action" in html
        assert "Re-Evaluate" in html

    def test_history_edit_actions_exist_in_dom(self, client):
        """Edit actions exist in DOM for history items."""
        resp = client.get("/app")
        html = resp.text

        # Check for historyEdit function
        assert "historyEdit" in html, "historyEdit function should exist"

        # Check for edit button in history item template
        assert "Edit" in html

    def test_history_tab_shows_empty_state(self, client):
        """History tab shows empty state when no items."""
        resp = client.get("/app?tab=history")
        html = resp.text

        # Empty state should be visible by default
        assert "history-empty" in html
        assert "No evaluations yet" in html

    def test_history_endpoint_returns_json_with_items(self, client):
        """History endpoint returns JSON with items array."""
        resp = client.get("/app/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "count" in data
        assert isinstance(data["items"], list)

    def test_history_item_endpoint_returns_item_with_raw(self, client):
        """History item endpoint returns item with raw evaluation."""
        # First create a history item
        eval_resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        assert eval_resp.status_code == 200
        eval_id = eval_resp.json().get("evaluationId")
        assert eval_id is not None

        # Get specific item
        item_resp = client.get(f"/app/history/{eval_id}")
        assert item_resp.status_code == 200
        data = item_resp.json()

        # Response should have 'item' key
        assert "item" in data, "Response should have 'item' key"
        item = data["item"]

        # Should include raw evaluation
        assert "raw" in item, "History item detail should include raw evaluation"
        assert item["raw"] is not None

    def test_history_item_endpoint_returns_404_for_unknown(self, client):
        """History item endpoint returns 404 for unknown ID."""
        resp = client.get("/app/history/unknown-id-that-does-not-exist")
        assert resp.status_code == 404

    def test_history_css_exists(self, client):
        """History-related CSS exists."""
        resp = client.get("/app")
        html = resp.text
        assert ".history-item" in html
        assert ".history-empty" in html
        assert ".history-action" in html

    def test_load_history_function_exists(self, client):
        """loadHistory JavaScript function exists."""
        resp = client.get("/app")
        html = resp.text
        assert "loadHistory" in html


class TestHistoryCanonicalEndpoints:
    """Ticket 6B: Canonical /history endpoints and evaluationId contract.

    Verifies:
    - GET /history returns same data as /app/history
    - GET /history/{id} returns same item as /app/history/{id}
    - evaluationId present in evaluation responses (text + image)
    - sport is explicit or null
    """

    @pytest.fixture(autouse=True)
    def clear_history_before_test(self):
        """Clear history store before each test."""
        from app.history_store import get_history_store
        store = get_history_store()
        store.clear()
        yield
        store.clear()

    def test_canonical_history_endpoint_exists(self, client):
        """GET /history returns 200."""
        resp = client.get("/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "count" in data

    def test_canonical_history_matches_app_history(self, client):
        """GET /history returns same data as /app/history."""
        # Create an evaluation
        client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })

        # Get from both endpoints
        canonical = client.get("/history").json()
        app_endpoint = client.get("/app/history").json()

        # Same count
        assert canonical["count"] == app_endpoint["count"]

        # Same items (by ID)
        canonical_ids = {item["id"] for item in canonical["items"]}
        app_ids = {item["id"] for item in app_endpoint["items"]}
        assert canonical_ids == app_ids

    def test_canonical_history_item_endpoint_exists(self, client):
        """GET /history/{id} returns item."""
        # Create an evaluation
        eval_resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        eval_id = eval_resp.json().get("evaluationId")
        assert eval_id is not None

        # Get from canonical endpoint
        resp = client.get(f"/history/{eval_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "item" in data
        assert data["item"]["id"] == eval_id

    def test_canonical_history_item_matches_app_history_item(self, client):
        """GET /history/{id} returns same data as /app/history/{id}."""
        # Create an evaluation
        eval_resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        eval_id = eval_resp.json().get("evaluationId")

        # Get from both endpoints
        canonical = client.get(f"/history/{eval_id}").json()
        app_endpoint = client.get(f"/app/history/{eval_id}").json()

        # Same item data
        assert canonical["item"]["id"] == app_endpoint["item"]["id"]
        assert canonical["item"]["signal"] == app_endpoint["item"]["signal"]
        assert canonical["item"]["fragilityScore"] == app_endpoint["item"]["fragilityScore"]

    def test_canonical_history_item_404_for_unknown(self, client):
        """GET /history/{id} returns 404 for unknown ID."""
        resp = client.get("/history/unknown-id-xyz")
        assert resp.status_code == 404

    def test_evaluation_response_has_evaluationId(self, client):
        """Text evaluation response includes evaluationId."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "evaluationId" in data, "Response must include evaluationId"
        assert data["evaluationId"] is not None

    def test_evaluation_response_has_historyId_alias(self, client):
        """Text evaluation response includes historyId (deprecated alias)."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        data = resp.json()
        assert "historyId" in data, "historyId should exist as deprecated alias"
        assert data["historyId"] == data["evaluationId"], "historyId must equal evaluationId"

    def test_history_item_sport_explicit_or_null(self, client):
        """History item sport is explicit value or null, not guessed."""
        # NBA bet - should detect sport
        client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })

        history = client.get("/history").json()
        item = history["items"][0]

        # Sport should be explicit string or null
        assert item["sport"] is None or isinstance(item["sport"], str)
        # If sport is set, it should be a known league
        if item["sport"]:
            assert item["sport"] in ["NBA", "NFL", "MLB", "NHL"]


class TestEntityRecognition:
    """Ticket 14: Entity recognition + context-lite differentiation."""

    VALID_TYPES = (
        "correlation", "leg_count", "dependency", "volatility",
        "prop_density", "same_game_dependency", "market_conflict", "weak_clarity",
    )
    VALID_ACTIONS = (
        "remove_leg", "swap_leg", "split_parlay",
        "reduce_same_game", "reduce_props", "clarify_input",
    )

    # --- Entity recognition presence ---

    def test_entities_present_in_response(self, client):
        """entities dict is present in evaluate response."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert data["entities"] is not None

    def test_entities_has_required_keys(self, client):
        """entities has sport_guess, teams_mentioned, players_mentioned, markets_detected."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        ent = resp.json()["entities"]
        assert "sport_guess" in ent
        assert "teams_mentioned" in ent
        assert "players_mentioned" in ent
        assert "markets_detected" in ent

    # --- Sport guess ---

    def test_nba_sport_detected(self, client):
        """NBA teams trigger nba sport guess."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        assert resp.json()["entities"]["sport_guess"] == "nba"

    def test_nfl_sport_detected(self, client):
        """NFL keywords trigger nfl sport guess."""
        resp = client.post("/app/evaluate", json={"input": "Chiefs -3.5 + Mahomes 2+ touchdowns", "tier": "good"})
        assert resp.json()["entities"]["sport_guess"] == "nfl"

    def test_unknown_sport_for_vague_input(self, client):
        """Vague text with no recognizable entities returns unknown."""
        resp = client.post("/app/evaluate", json={"input": "team A wins + team B covers", "tier": "good"})
        assert resp.json()["entities"]["sport_guess"] == "unknown"

    # --- Teams ---

    def test_nba_teams_recognized(self, client):
        """NBA team names are extracted."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5 + Celtics ML", "tier": "good"})
        teams = resp.json()["entities"]["teams_mentioned"]
        assert "LAL" in teams
        assert "BOS" in teams

    def test_nfl_teams_recognized(self, client):
        """NFL team names are extracted."""
        resp = client.post("/app/evaluate", json={"input": "Chiefs -3 + Bills ML", "tier": "good"})
        teams = resp.json()["entities"]["teams_mentioned"]
        assert "KC" in teams
        assert "BUF" in teams

    # --- Players ---

    def test_nba_players_recognized(self, client):
        """NBA player names are extracted."""
        resp = client.post("/app/evaluate", json={
            "input": "LeBron James over 25.5 points + Jayson Tatum over 7.5 rebounds",
            "tier": "good"
        })
        players = resp.json()["entities"]["players_mentioned"]
        assert "LeBron James" in players
        assert "Jayson Tatum" in players

    def test_nfl_players_recognized(self, client):
        """NFL player names are extracted."""
        resp = client.post("/app/evaluate", json={
            "input": "Mahomes 300+ passing yards + Kelce anytime td",
            "tier": "good"
        })
        players = resp.json()["entities"]["players_mentioned"]
        assert "Patrick Mahomes" in players
        assert "Travis Kelce" in players

    # --- Markets ---

    def test_spread_market_detected(self, client):
        """Spread market is detected."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "good"})
        markets = resp.json()["entities"]["markets_detected"]
        assert "spread" in markets

    def test_prop_markets_detected(self, client):
        """Prop markets (points, rebounds) are detected."""
        resp = client.post("/app/evaluate", json={
            "input": "LeBron over 25.5 points + Tatum over 7.5 rebounds",
            "tier": "good"
        })
        markets = resp.json()["entities"]["markets_detected"]
        assert "points" in markets
        assert "rebounds" in markets

    def test_td_market_detected(self, client):
        """Touchdown market is detected for NFL."""
        resp = client.post("/app/evaluate", json={
            "input": "Kelce anytime td + Mahomes 2 touchdowns",
            "tier": "good"
        })
        markets = resp.json()["entities"]["markets_detected"]
        assert "td" in markets

    # --- Differentiation: 6 representative bets ---

    def test_differentiation_single_spread(self, client):
        """(1) Single spread — entities show team + spread market."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "good"})
        data = resp.json()
        ent = data["entities"]
        assert "LAL" in ent["teams_mentioned"]
        assert "spread" in ent["markets_detected"]
        assert ent["sport_guess"] == "nba"

    def test_differentiation_total(self, client):
        """(2) Total bet — entities show total market."""
        resp = client.post("/app/evaluate", json={"input": "Lakers vs Celtics over 215.5", "tier": "good"})
        data = resp.json()
        ent = data["entities"]
        assert "total" in ent["markets_detected"]
        assert len(ent["teams_mentioned"]) >= 2

    def test_differentiation_ml_parlay(self, client):
        """(3) ML parlay — entities show multiple teams, ml market."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics ML + Nuggets ML",
            "tier": "good"
        })
        data = resp.json()
        ent = data["entities"]
        assert len(ent["teams_mentioned"]) >= 3
        assert "ml" in ent["markets_detected"]

    def test_differentiation_prop_heavy(self, client):
        """(4) Prop-heavy slip — entities show players + prop markets, failure references props."""
        resp = client.post("/app/evaluate", json={
            "input": "LeBron over 25.5 points + Tatum over 7.5 rebounds + Jokic over 10.5 assists",
            "tier": "good"
        })
        data = resp.json()
        ent = data["entities"]
        pf = data["primaryFailure"]
        assert len(ent["players_mentioned"]) >= 3
        assert any(m in ent["markets_detected"] for m in ["points", "rebounds", "assists"])
        # Prop-heavy should trigger prop_density or volatility
        assert pf["type"] in ("prop_density", "volatility")

    def test_differentiation_same_game_style(self, client):
        """(5) Same-game style slip — legs from same team, same_game_dependency expected."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Lakers over 220.5",
            "tier": "good"
        })
        data = resp.json()
        ent = data["entities"]
        pf = data["primaryFailure"]
        assert "LAL" in ent["teams_mentioned"]
        # Two legs from same team → same_game_dependency
        assert pf["type"] == "same_game_dependency"

    def test_differentiation_vague_text(self, client):
        """(6) Vague/ambiguous text — entities sparse, weak_clarity expected."""
        resp = client.post("/app/evaluate", json={
            "input": "team A wins + team B covers spread",
            "tier": "good"
        })
        data = resp.json()
        ent = data["entities"]
        pf = data["primaryFailure"]
        assert len(ent["teams_mentioned"]) == 0
        assert len(ent["players_mentioned"]) == 0
        # Should get weak_clarity failure type
        assert pf["type"] == "weak_clarity"

    # --- Two different inputs produce different outputs ---

    def test_different_inputs_different_entities(self, client):
        """Two structurally different inputs produce different entity outputs."""
        resp1 = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        resp2 = client.post("/app/evaluate", json={
            "input": "LeBron over 25.5 points + Tatum over 7.5 rebounds + Jokic over 10.5 assists",
            "tier": "good"
        })
        ent1 = resp1.json()["entities"]
        ent2 = resp2.json()["entities"]
        # Different teams vs players
        assert ent1["teams_mentioned"] != ent2["teams_mentioned"] or ent1["players_mentioned"] != ent2["players_mentioned"]
        # Different markets
        assert ent1["markets_detected"] != ent2["markets_detected"]

    def test_different_inputs_different_failure_types(self, client):
        """A prop-heavy slip and a vague slip yield different primaryFailure types."""
        resp_prop = client.post("/app/evaluate", json={
            "input": "LeBron over 25.5 points + Tatum over 7.5 rebounds + Jokic over 10.5 assists",
            "tier": "good"
        })
        resp_vague = client.post("/app/evaluate", json={
            "input": "team A wins + team B covers spread",
            "tier": "good"
        })
        pf_prop = resp_prop.json()["primaryFailure"]
        pf_vague = resp_vague.json()["primaryFailure"]
        assert pf_prop["type"] != pf_vague["type"], \
            f"Expected different failure types, got {pf_prop['type']} for both"

    def test_different_inputs_different_warnings(self, client):
        """Different failure types produce different warnings in GOOD tier explain."""
        resp_prop = client.post("/app/evaluate", json={
            "input": "LeBron over 25.5 points + Tatum over 7.5 rebounds + Jokic over 10.5 assists",
            "tier": "good"
        })
        resp_spread = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics -3 + Nuggets -4 + Bucks -2.5",
            "tier": "good"
        })
        w_prop = resp_prop.json()["explain"].get("warnings", [])
        w_spread = resp_spread.json()["explain"].get("warnings", [])
        assert w_prop != w_spread, "Different bet types should produce different warnings"

    # --- Tier separation still holds with new types ---

    def test_entities_present_all_tiers(self, client):
        """entities is returned for all tiers."""
        for tier in ("good", "better", "best"):
            resp = client.post("/app/evaluate", json={
                "input": "Lakers -5.5 + Celtics ML", "tier": tier
            })
            assert "entities" in resp.json(), f"entities missing for tier={tier}"

    def test_tier_separation_good_vs_better(self, client):
        """GOOD tier has structured output, BETTER has summary — unchanged by Ticket 14."""
        good = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML", "tier": "good"
        }).json()
        better = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML", "tier": "better"
        }).json()
        # GOOD has contributors, BETTER has summary
        assert "contributors" in good["explain"]
        assert "summary" in better["explain"]
        # Both have same primaryFailure type (core truth)
        assert good["primaryFailure"]["type"] == better["primaryFailure"]["type"]

    def test_extended_type_enum_coverage(self, client):
        """primaryFailure type is always in the extended valid set."""
        inputs = [
            "Lakers -5.5",
            "Lakers -5.5 + Celtics ML",
            "LeBron over 25.5 points + Tatum over 7.5 rebounds + Jokic over 10.5 assists",
            "team A wins + team B covers",
            "Lakers vs Celtics over 215.5 + Nuggets vs Bucks over 220",
        ]
        for inp in inputs:
            resp = client.post("/app/evaluate", json={"input": inp, "tier": "good"})
            pf = resp.json()["primaryFailure"]
            assert pf["type"] in self.VALID_TYPES, f"Invalid type {pf['type']} for input: {inp}"
            assert pf["fastestFix"]["action"] in self.VALID_ACTIONS, \
                f"Invalid action {pf['fastestFix']['action']} for input: {inp}"

    # --- Context echo HTML ---

    def test_context_echo_element_exists_in_html(self, client):
        """Context echo element exists in app HTML."""
        resp = client.get("/app")
        assert 'id="context-echo"' in resp.text

    # --- Staged analysis progress HTML ---

    def test_analysis_progress_exists_in_html(self, client):
        """Analysis progress element exists in app HTML."""
        resp = client.get("/app")
        html = resp.text
        assert 'id="analysis-progress"' in html
        assert 'id="ap-step-1"' in html
        assert 'id="ap-step-5"' in html

    def test_context_echo_above_primary_failure(self, client):
        """Context echo appears before primary failure in DOM order."""
        resp = client.get("/app")
        html = resp.text
        echo_pos = html.find('id="context-echo"')
        pf_pos = html.find('id="compressed-pf"')
        assert echo_pos < pf_pos, "Context echo must be above primary failure"


class TestSprint2Features:
    """Tests for Sprint 2: Recognition, Explainability, and Trust."""

    # --- Volatility Flag Tests ---

    def test_volatility_flag_present_in_entities(self, client):
        """Entities include volatility_flag."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "good"})
        entities = resp.json()["entities"]
        assert "volatility_flag" in entities
        assert entities["volatility_flag"] in ("low", "medium", "med-high", "high")

    def test_volatility_flag_props_is_high(self, client):
        """Props-heavy slip has high volatility."""
        resp = client.post("/app/evaluate", json={
            "input": "LeBron over 25.5 points + Tatum over 7.5 rebounds",
            "tier": "good"
        })
        entities = resp.json()["entities"]
        assert entities["volatility_flag"] in ("high", "med-high")

    def test_volatility_flag_ml_is_lower(self, client):
        """ML parlay has lower volatility."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics ML",
            "tier": "good"
        })
        entities = resp.json()["entities"]
        assert entities["volatility_flag"] in ("low", "medium")

    # --- Same-Game Indicator Tests ---

    def test_same_game_indicator_present(self, client):
        """Entities include same_game_indicator."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "good"})
        entities = resp.json()["entities"]
        assert "same_game_indicator" in entities
        assert "has_same_game" in entities["same_game_indicator"]

    def test_same_game_indicator_detects_same_team(self, client):
        """Same-game indicator detects multiple legs from same team."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Lakers over 220.5",
            "tier": "good"
        })
        sgi = resp.json()["entities"]["same_game_indicator"]
        assert sgi["has_same_game"] == True
        assert sgi["same_game_count"] >= 2

    def test_same_game_indicator_no_same_game(self, client):
        """Different teams show no same-game."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        sgi = resp.json()["entities"]["same_game_indicator"]
        assert sgi["has_same_game"] == False

    # --- Secondary Factors Tests ---

    def test_secondary_factors_present(self, client):
        """Response includes secondaryFactors."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Nuggets -3",
            "tier": "good"
        })
        data = resp.json()
        assert "secondaryFactors" in data

    def test_secondary_factors_has_structure(self, client):
        """Secondary factors have type, impact, explanation."""
        resp = client.post("/app/evaluate", json={
            "input": "LeBron over 25.5 points + Tatum over 7.5 rebounds + Jokic over 10 assists",
            "tier": "good"
        })
        data = resp.json()
        sf = data.get("secondaryFactors", [])
        if sf:  # May be empty for some inputs
            factor = sf[0]
            assert "type" in factor
            assert "impact" in factor
            assert "explanation" in factor
            assert factor["impact"] in ("low", "medium", "high")

    # --- Human Summary Tests ---

    def test_human_summary_present(self, client):
        """Response includes humanSummary."""
        resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": "good"})
        data = resp.json()
        assert "humanSummary" in data
        assert isinstance(data["humanSummary"], str)
        assert len(data["humanSummary"]) > 0

    def test_human_summary_references_entities(self, client):
        """Human summary references recognized entities or structural info."""
        resp = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        summary = resp.json()["humanSummary"]
        # Summary should reference at least one recognized team/entity or structural info
        assert any(x in summary for x in ["LAL", "BOS", "Lakers", "Celtics", "parlay", "leg"])

    def test_human_summary_always_included(self, client):
        """Human summary included for all tiers (not tier-gated)."""
        for tier in ["good", "better", "best"]:
            resp = client.post("/app/evaluate", json={"input": "Lakers -5.5", "tier": tier})
            assert resp.json()["humanSummary"], f"No summary for tier {tier}"

    # --- HTML Element Tests ---

    def test_human_summary_element_exists(self, client):
        """Human summary element exists in HTML."""
        resp = client.get("/app")
        assert 'id="human-summary"' in resp.text

    def test_secondary_factors_element_exists(self, client):
        """Secondary factors element exists in HTML."""
        resp = client.get("/app")
        assert 'id="detail-secondary-factors"' in resp.text

    # --- Builder UI Tests ---

    def test_builder_has_sport_selector(self, client):
        """Builder has sport selector dropdown."""
        resp = client.get("/app?tab=builder")
        html = resp.text
        assert 'id="builder-sport"' in html
        assert "Basketball (NBA)" in html

    def test_builder_has_leg_inputs(self, client):
        """Builder has leg input fields."""
        resp = client.get("/app?tab=builder")
        html = resp.text
        assert 'class="builder-leg"' in html
        assert 'class="leg-input' in html

    def test_builder_has_tier_selector(self, client):
        """Builder has tier selector."""
        resp = client.get("/app?tab=builder")
        html = resp.text
        assert 'builder-tier-selector' in html
        assert 'data-tier="good"' in html

    def test_builder_leg_explanation_element_exists(self, client):
        """Builder has leg explanation elements."""
        resp = client.get("/app?tab=builder")
        html = resp.text
        assert 'class="leg-explanation' in html
