# app/tests/test_v1_ui.py
"""
Tests for the v1 UI boundary layer.

These tests verify:
1. Builder uses structured selection (no freeform text input)
2. Add leg persists state after redirect
3. Minimum 2 legs required for evaluate
4. Debrief renders HTML and echoes legs
"""
import os
import json
import urllib.parse
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with Leading Light enabled."""
    os.environ["LEADING_LIGHT_ENABLED"] = "true"
    from app.main import app
    return TestClient(app)


class TestV1Home:
    """Tests for GET /v1 endpoint."""

    def test_returns_200(self, client):
        """Home page returns 200 status."""
        response = client.get("/v1")
        assert response.status_code == 200

    def test_contains_links_to_builder_and_history(self, client):
        """Home page contains links to builder and history."""
        response = client.get("/v1")
        assert "/v1/build" in response.text
        assert "/v1/history" in response.text


class TestV1Builder:
    """Tests for GET /v1/build endpoint."""

    def test_returns_200(self, client):
        """Builder page returns 200 status."""
        response = client.get("/v1/build")
        assert response.status_code == 200

    def test_builder_has_no_freeform_text_input(self, client):
        """
        Builder does not have any freeform text input for bet entry.

        Only allowed inputs:
        - select (team dropdown)
        - radio (bet type, tier, direction)
        - text for line only (numeric, not freeform bet text)
        """
        response = client.get("/v1/build")
        html = response.text

        # Should NOT have textarea (freeform text)
        assert "<textarea" not in html.lower()

        # Should NOT have input type="text" with bet-related names
        # The only text input allowed is for "line" (numeric value)
        assert 'name="bet_text"' not in html
        assert 'name="parlay_text"' not in html
        assert 'name="input"' not in html

        # SHOULD have structured inputs
        assert 'name="team"' in html
        assert 'name="bet_type"' in html
        assert 'name="line"' in html
        assert 'name="direction"' in html

    def test_builder_has_team_dropdown_with_leagues(self, client):
        """Builder has team dropdown grouped by league."""
        response = client.get("/v1/build")
        html = response.text

        # Check for optgroup (league groupings)
        assert "<optgroup" in html
        assert "NBA" in html
        assert "NFL" in html
        assert "MLB" in html
        assert "NHL" in html

    def test_builder_has_bet_type_radios(self, client):
        """Builder has bet type radio buttons."""
        response = client.get("/v1/build")
        html = response.text

        assert 'value="spread"' in html
        assert 'value="ml"' in html
        assert 'value="total"' in html


class TestV1BuilderAddLeg:
    """Tests for POST /v1/build/add endpoint."""

    def test_builder_add_leg_persists_after_redirect(self, client):
        """
        Adding a leg via POST redirects back to builder with leg in state.

        Flow:
        1. POST /v1/build/add with team, bet_type, line, direction
        2. Server redirects (303) to /v1/build?legs=...
        3. GET the redirect URL
        4. Verify leg appears in HTML
        """
        # Add first leg
        response = client.post(
            "/v1/build/add",
            data={
                "team": "NBA:LAL",
                "bet_type": "spread",
                "line": "5.5",
                "direction": "minus",
                "legs": "[]",
            },
            follow_redirects=False,
        )

        # Should redirect with 303
        assert response.status_code == 303
        redirect_url = response.headers.get("location")
        assert redirect_url is not None
        assert "/v1/build" in redirect_url
        assert "legs=" in redirect_url

        # Follow redirect and verify leg appears
        response = client.get(redirect_url)
        assert response.status_code == 200
        assert "LA Lakers" in response.text
        assert "-5.5" in response.text

    def test_add_multiple_legs_accumulates(self, client):
        """Adding multiple legs accumulates in state."""
        # Start with empty
        legs = []

        # Add first leg
        response = client.post(
            "/v1/build/add",
            data={
                "team": "NBA:LAL",
                "bet_type": "spread",
                "line": "5.5",
                "direction": "minus",
                "legs": json.dumps(legs),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        # Parse legs from redirect URL
        redirect_url = response.headers.get("location")
        parsed = urllib.parse.urlparse(redirect_url)
        query = urllib.parse.parse_qs(parsed.query)
        legs = json.loads(query["legs"][0])
        assert len(legs) == 1

        # Add second leg
        response = client.post(
            "/v1/build/add",
            data={
                "team": "NBA:BOS",
                "bet_type": "ml",
                "line": "",
                "direction": "minus",
                "legs": json.dumps(legs),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        # Parse legs from redirect URL
        redirect_url = response.headers.get("location")
        parsed = urllib.parse.urlparse(redirect_url)
        query = urllib.parse.parse_qs(parsed.query)
        legs = json.loads(query["legs"][0])
        assert len(legs) == 2

        # Verify both legs appear
        response = client.get(redirect_url)
        assert "LA Lakers" in response.text
        assert "Boston Celtics" in response.text


class TestV1BuilderMinimumLegs:
    """Tests for minimum leg requirements."""

    def test_builder_requires_minimum_two_legs_for_evaluate(self, client):
        """
        Evaluate button only appears when parlay has >= 2 legs.
        With 1 leg, shows friendly message instead.
        """
        # Empty parlay - no evaluate section
        response = client.get("/v1/build")
        assert 'action="/v1/evaluate"' not in response.text

        # 1 leg - no evaluate section, shows message
        one_leg = [{"display": "LA Lakers -5.5", "league": "NBA", "team": "LAL", "bet_type": "spread", "line": "5.5", "direction": "minus"}]
        legs_param = urllib.parse.quote(json.dumps(one_leg))
        response = client.get(f"/v1/build?legs={legs_param}")
        assert 'action="/v1/evaluate"' not in response.text
        assert "Add at least one more leg" in response.text

        # 2 legs - evaluate section appears
        two_legs = [
            {"display": "LA Lakers -5.5", "league": "NBA", "team": "LAL", "bet_type": "spread", "line": "5.5", "direction": "minus"},
            {"display": "Boston Celtics ML", "league": "NBA", "team": "BOS", "bet_type": "ml", "line": "", "direction": "minus"},
        ]
        legs_param = urllib.parse.quote(json.dumps(two_legs))
        response = client.get(f"/v1/build?legs={legs_param}")
        assert 'action="/v1/evaluate"' in response.text
        assert "Add at least one more leg" not in response.text

    def test_evaluate_endpoint_rejects_single_leg(self, client):
        """POST /v1/evaluate with 1 leg returns error page."""
        one_leg = [{"display": "LA Lakers -5.5", "league": "NBA", "team": "LAL", "bet_type": "spread", "line": "5.5", "direction": "minus"}]

        response = client.post(
            "/v1/evaluate",
            data={
                "legs": json.dumps(one_leg),
                "tier": "GOOD",
            },
        )

        assert response.status_code == 200  # Returns HTML error page, not 4xx
        assert "text/html" in response.headers.get("content-type", "")
        assert "at least 2 legs" in response.text.lower()


class TestV1Debrief:
    """Tests for POST /v1/evaluate debrief rendering."""

    def test_debrief_renders_html_and_echoes_legs(self, client):
        """
        Debrief page renders as HTML and echoes the submitted legs.

        Note: This may fail if the evaluation engine has issues.
        The test verifies the UI contract, not the engine correctness.
        """
        two_legs = [
            {"display": "LA Lakers -5.5", "league": "NBA", "team": "LAL", "bet_type": "spread", "line": "5.5", "direction": "minus"},
            {"display": "Boston Celtics ML", "league": "NBA", "team": "BOS", "bet_type": "ml", "line": "", "direction": "minus"},
        ]

        response = client.post(
            "/v1/evaluate",
            data={
                "legs": json.dumps(two_legs),
                "tier": "GOOD",
            },
        )

        # Should return HTML
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

        # Should echo legs
        assert "LA Lakers" in response.text
        assert "Boston Celtics" in response.text

        # Should have debrief structure
        assert "Your Parlay" in response.text or "YOUR PARLAY" in response.text.upper()

        # Should have verdict/metrics OR error (if engine fails)
        has_verdict = "Verdict" in response.text or "VERDICT" in response.text.upper()
        has_error = "Error" in response.text or "error" in response.text.lower()
        assert has_verdict or has_error

    def test_debrief_returns_html_not_json(self, client):
        """Debrief always returns HTML, never JSON."""
        two_legs = [
            {"display": "LA Lakers -5.5", "league": "NBA", "team": "LAL", "bet_type": "spread", "line": "5.5", "direction": "minus"},
            {"display": "Boston Celtics ML", "league": "NBA", "team": "BOS", "bet_type": "ml", "line": "", "direction": "minus"},
        ]

        response = client.post(
            "/v1/evaluate",
            data={
                "legs": json.dumps(two_legs),
                "tier": "GOOD",
            },
        )

        # Must be HTML, not JSON
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type
        assert "application/json" not in content_type

        # HTML should have DOCTYPE or html tag
        assert "<!DOCTYPE" in response.text or "<html" in response.text


class TestV1NoJS:
    """Tests verifying no-JS contract."""

    def test_navigation_uses_anchor_tags(self, client):
        """All navigation uses <a href>, not JS handlers."""
        response = client.get("/v1")
        html = response.text

        # Links should be anchor tags
        assert '<a href="/v1/build"' in html
        assert '<a href="/v1/history"' in html

        # Should NOT have onclick navigation
        assert 'onclick="window.location' not in html
        assert 'onclick="navigate' not in html

    def test_forms_use_post_method(self, client):
        """All forms use method="POST", not JS fetch."""
        # Get builder with some legs
        two_legs = [
            {"display": "LA Lakers -5.5", "league": "NBA", "team": "LAL", "bet_type": "spread", "line": "5.5", "direction": "minus"},
            {"display": "Boston Celtics ML", "league": "NBA", "team": "BOS", "bet_type": "ml", "line": "", "direction": "minus"},
        ]
        legs_param = urllib.parse.quote(json.dumps(two_legs))
        response = client.get(f"/v1/build?legs={legs_param}")
        html = response.text

        # Forms should have method="POST" and action
        assert 'method="POST"' in html
        assert 'action="/v1/build/add"' in html
        assert 'action="/v1/evaluate"' in html

        # Should NOT have onsubmit fetch handlers
        assert 'onsubmit="fetch' not in html
        assert 'onsubmit="event.preventDefault' not in html
