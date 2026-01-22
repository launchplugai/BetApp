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

    def test_tier_selector_has_detail_label(self, client):
        """Tier selector shows 'detail level' label without billing language."""
        response = client.get("/app")
        assert "tier-selector-label" in response.text
        assert "Analysis detail level" in response.text

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

    def test_evaluate_has_explainer(self, client):
        """Evaluate tab has short explainer text."""
        response = client.get("/app")
        assert "eval-explainer" in response.text
        assert "Submit your bet for analysis" in response.text

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
        """Tier selector uses 'Analysis detail level', not pricing language."""
        response = client.get("/app")
        assert "Analysis detail level" in response.text
        # Must NOT contain pricing language in main app flow
        # (Account page is separate and allowed to have pricing)
        # Check that the upgrade CTA in the builder results doesn't have pricing
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
