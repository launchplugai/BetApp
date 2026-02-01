# app/tests/test_leading_light_api.py
"""
Integration tests for Leading Light API.

Tests the HTTP endpoint for parlay evaluation.
"""
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def minimal_block():
    """Minimal valid block for testing."""
    return {
        "sport": "NFL",
        "game_id": "game-123",
        "bet_type": "spread",
        "selection": "Team A -3.5",
        "base_fragility": 15.0,
    }


@pytest.fixture
def player_prop_block():
    """Player prop block for testing."""
    return {
        "sport": "NFL",
        "game_id": "game-123",
        "bet_type": "player_prop",
        "selection": "Player X Over 100 yards",
        "base_fragility": 20.0,
        "player_id": "player-1",
    }


@pytest.fixture
def dna_profile():
    """DNA profile for testing."""
    return {
        "risk": {
            "tolerance": 50,
            "max_parlay_legs": 4,
            "max_stake_pct": 0.10,
            "avoid_live_bets": False,
            "avoid_props": False,
        },
        "behavior": {
            "discipline": 0.5,
        },
    }


@pytest.fixture
def conservative_profile():
    """Conservative DNA profile that triggers violations."""
    return {
        "risk": {
            "tolerance": 30,
            "max_parlay_legs": 2,
            "max_stake_pct": 0.05,
            "avoid_live_bets": True,
            "avoid_props": True,
        },
        "behavior": {
            "discipline": 0.8,
        },
    }


# =============================================================================
# Required Test Vectors
# =============================================================================


class TestRequiredVectors:
    """Required test vectors from specification."""

    def test_vector_a_flag_disabled(self, client, minimal_block):
        """
        Test A: Flag disabled.

        LEADING_LIGHT_ENABLED=false
        POST request to endpoint
        Expected: 503 + message "Leading Light disabled"
        """
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "false"}):
            response = client.post(
                "/leading-light/evaluate",
                json={"blocks": [minimal_block]},
            )

            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            assert data["detail"]["error"] == "Leading Light disabled"
            assert data["detail"]["code"] == "SERVICE_DISABLED"

    def test_vector_b_minimal_request(self, client, minimal_block):
        """
        Test B: Minimal request.

        blocks only
        Expected: 200 + valid EvaluationResponse JSON
        """
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={"blocks": [minimal_block]},
            )

            assert response.status_code == 200
            data = response.json()

            # Check all required fields present
            assert "parlay_id" in data
            assert "inductor" in data
            assert "metrics" in data
            assert "correlations" in data
            assert "dna" in data
            assert "recommendation" in data

            # Check inductor structure
            assert "level" in data["inductor"]
            assert "explanation" in data["inductor"]
            assert data["inductor"]["level"] in ["stable", "loaded", "tense", "critical"]

            # Check metrics structure
            assert "raw_fragility" in data["metrics"]
            assert "final_fragility" in data["metrics"]
            assert "leg_penalty" in data["metrics"]
            assert "correlation_penalty" in data["metrics"]
            assert "correlation_multiplier" in data["metrics"]

            # Check dna structure (empty violations since no profile)
            assert "violations" in data["dna"]
            assert data["dna"]["violations"] == []

            # Check recommendation structure
            assert "action" in data["recommendation"]
            assert "reason" in data["recommendation"]
            assert data["recommendation"]["action"] in ["accept", "reduce", "avoid"]

    def test_vector_c_with_dna_and_bankroll(
        self, client, minimal_block, player_prop_block, conservative_profile
    ):
        """
        Test C: With DNA and bankroll.

        Expected:
        - dna fields populated
        - recommended_stake present
        - violations populated when triggered
        """
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [minimal_block, player_prop_block],
                    "dna_profile": conservative_profile,
                    "bankroll": 1000.0,
                },
            )

            assert response.status_code == 200
            data = response.json()

            # DNA fields populated
            assert data["dna"]["base_stake_cap"] is not None
            assert data["dna"]["base_stake_cap"] == 50.0  # 1000 * 0.05
            assert data["dna"]["recommended_stake"] is not None
            assert data["dna"]["max_legs"] == 2
            assert data["dna"]["fragility_tolerance"] == 30

            # Violations triggered (avoid_props=True but we have a player_prop)
            assert "props_not_allowed" in data["dna"]["violations"]

    def test_vector_d_with_candidates(self, client, minimal_block):
        """
        Test D: With candidates.

        Expected:
        - suggestions present and sorted
        """
        candidates = [
            {
                "sport": "NFL",
                "game_id": "game-456",
                "bet_type": "spread",
                "selection": "Team B +3.5",
                "base_fragility": 10.0,
            },
            {
                "sport": "NFL",
                "game_id": "game-789",
                "bet_type": "total",
                "selection": "Over 45.5",
                "base_fragility": 5.0,
            },
            {
                "sport": "NFL",
                "game_id": "game-101",
                "bet_type": "ml",
                "selection": "Team C ML",
                "base_fragility": 20.0,
            },
        ]

        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [minimal_block],
                    "candidates": candidates,
                    "plan": "better",  # Required for suggestions
                },
            )

            assert response.status_code == 200
            data = response.json()

            # Suggestions present (BETTER plan allows suggestions)
            assert data["suggestions"] is not None
            assert len(data["suggestions"]) == 3

            # Suggestions sorted by delta_fragility (ascending)
            deltas = [s["delta_fragility"] for s in data["suggestions"]]
            assert deltas == sorted(deltas)


# =============================================================================
# Feature Flag Tests
# =============================================================================


class TestFeatureFlag:
    """Tests for feature flag behavior."""

    def test_flag_disabled_returns_503(self, client, minimal_block):
        """Disabled flag returns 503."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "false"}):
            response = client.post(
                "/leading-light/evaluate",
                json={"blocks": [minimal_block]},
            )
            assert response.status_code == 503

    def test_flag_enabled_returns_200(self, client, minimal_block):
        """Enabled flag returns 200."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={"blocks": [minimal_block]},
            )
            assert response.status_code == 200

    def test_flag_not_set_defaults_to_disabled(self, client, minimal_block):
        """Missing flag defaults to disabled."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove LEADING_LIGHT_ENABLED if present
            os.environ.pop("LEADING_LIGHT_ENABLED", None)
            response = client.post(
                "/leading-light/evaluate",
                json={"blocks": [minimal_block]},
            )
            assert response.status_code == 503

    def test_flag_case_insensitive(self, client, minimal_block):
        """Flag value is case insensitive."""
        for value in ["TRUE", "True", "true"]:
            with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": value}):
                response = client.post(
                    "/leading-light/evaluate",
                    json={"blocks": [minimal_block]},
                )
                assert response.status_code == 200

    def test_status_endpoint(self, client):
        """Status endpoint reports feature state."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.get("/leading-light/status")
            assert response.status_code == 200
            assert response.json()["enabled"] is True

        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "false"}):
            response = client.get("/leading-light/status")
            assert response.status_code == 200
            assert response.json()["enabled"] is False


# =============================================================================
# Request Validation Tests
# =============================================================================


class TestRequestValidation:
    """Tests for request validation."""

    def test_empty_blocks_allowed(self, client):
        """Empty blocks list is allowed."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={"blocks": []},
            )
            assert response.status_code == 200

    def test_invalid_bet_type_rejected(self, client):
        """Invalid bet type is rejected."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "game-123",
                            "bet_type": "invalid_type",
                            "selection": "Test",
                            "base_fragility": 10.0,
                        }
                    ]
                },
            )
            assert response.status_code == 400

    def test_negative_bankroll_rejected(self, client, minimal_block):
        """Negative bankroll is rejected."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [minimal_block],
                    "bankroll": -100,
                },
            )
            assert response.status_code == 422  # Pydantic validation

    def test_missing_required_block_fields_rejected(self, client):
        """Missing required block fields are rejected."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            # Missing game_id, bet_type, selection, base_fragility
                        }
                    ]
                },
            )
            assert response.status_code == 422


# =============================================================================
# Response Structure Tests
# =============================================================================


class TestResponseStructure:
    """Tests for response structure."""

    def test_response_uses_snake_case(self, client, minimal_block):
        """Response uses snake_case keys."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={"blocks": [minimal_block]},
            )

            data = response.json()

            # Check snake_case keys
            assert "parlay_id" in data
            assert "final_fragility" in data["metrics"]
            assert "raw_fragility" in data["metrics"]
            assert "leg_penalty" in data["metrics"]
            assert "correlation_penalty" in data["metrics"]
            assert "correlation_multiplier" in data["metrics"]
            assert "base_stake_cap" in data["dna"]
            assert "recommended_stake" in data["dna"]
            assert "max_legs" in data["dna"]
            assert "fragility_tolerance" in data["dna"]

    def test_correlations_structure(self, client):
        """Correlations have correct structure when present."""
        # Create blocks that will correlate (same player, multi-props)
        blocks = [
            {
                "sport": "NFL",
                "game_id": "game-123",
                "bet_type": "player_prop",
                "selection": "Player X Over 100 yards",
                "base_fragility": 15.0,
                "player_id": "player-1",
            },
            {
                "sport": "NFL",
                "game_id": "game-123",
                "bet_type": "player_prop",
                "selection": "Player X Over 5 receptions",
                "base_fragility": 15.0,
                "player_id": "player-1",
            },
        ]

        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={"blocks": blocks},
            )

            assert response.status_code == 200
            data = response.json()

            # Should have correlations
            assert len(data["correlations"]) > 0

            # Check correlation structure
            for corr in data["correlations"]:
                assert "block_a_id" in corr
                assert "block_b_id" in corr
                assert "correlation_type" in corr
                assert "penalty" in corr


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_large_number_of_blocks(self, client):
        """Handles large number of blocks."""
        blocks = [
            {
                "sport": "NFL",
                "game_id": f"game-{i}",
                "bet_type": "spread",
                "selection": f"Team {i}",
                "base_fragility": 10.0,
            }
            for i in range(10)
        ]

        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={"blocks": blocks},
            )
            assert response.status_code == 200

    def test_all_bet_types(self, client):
        """All bet types are accepted."""
        bet_types = ["player_prop", "spread", "total", "ml", "team_total"]

        for bet_type in bet_types:
            with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
                response = client.post(
                    "/leading-light/evaluate",
                    json={
                        "blocks": [
                            {
                                "sport": "NFL",
                                "game_id": "game-123",
                                "bet_type": bet_type,
                                "selection": "Test",
                                "base_fragility": 10.0,
                            }
                        ]
                    },
                )
                assert response.status_code == 200, f"Failed for bet_type: {bet_type}"

    def test_with_context_modifiers(self, client):
        """Blocks with context modifiers are processed."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "game-123",
                            "bet_type": "spread",
                            "selection": "Test",
                            "base_fragility": 10.0,
                            "context_modifiers": {
                                "weather": {
                                    "applied": True,
                                    "delta": 5.0,
                                    "reason": "Heavy rain expected",
                                },
                                "injury": {"applied": False, "delta": 0.0},
                                "trade": {"applied": False, "delta": 0.0},
                                "role": {"applied": False, "delta": 0.0},
                            },
                        }
                    ]
                },
            )

            assert response.status_code == 200
            data = response.json()
            # Effective fragility should be 10 + 5 = 15, affecting metrics
            assert data["metrics"]["final_fragility"] > 0

    def test_with_correlation_tags(self, client):
        """Blocks with correlation tags are processed."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "game-123",
                            "bet_type": "spread",
                            "selection": "Test",
                            "base_fragility": 10.0,
                            "correlation_tags": ["live", "pace"],
                        }
                    ]
                },
            )
            assert response.status_code == 200


# =============================================================================
# Context Signals Tests
# =============================================================================


class TestContextSignals:
    """Tests for context_signals API parameter."""

    def test_weather_signal_increases_fragility(self, client):
        """Weather signal increases fragility via context adapters."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "game-123",
                            "bet_type": "player_prop",
                            "selection": "QB Over 250 passing yards",
                            "base_fragility": 10.0,
                            "player_id": "player-1",
                            "correlation_tags": ["passing"],
                        }
                    ],
                    "context_signals": [
                        {
                            "type": "weather",
                            "game_id": "game-123",
                            "wind_mph": 20,
                            "precip": False,
                        }
                    ],
                },
            )

            assert response.status_code == 200
            data = response.json()
            # Base fragility 10 + wind delta 4 = 14, plus leg penalty
            assert data["metrics"]["raw_fragility"] >= 14.0

    def test_injury_signal_increases_fragility(self, client):
        """Injury signal increases fragility via context adapters."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "game-123",
                            "bet_type": "player_prop",
                            "selection": "Star RB Over 100 yards",
                            "base_fragility": 10.0,
                            "player_id": "player-1",
                        }
                    ],
                    "context_signals": [
                        {
                            "type": "injury",
                            "player_id": "player-1",
                            "player_name": "Star RB",
                            "status": "OUT",
                            "injury": "Knee",
                        }
                    ],
                    "plan": "better",  # Required for injury signals
                },
            )

            assert response.status_code == 200
            data = response.json()
            # Base 10 + injury delta 10 + role delta 3 = 23
            assert data["metrics"]["raw_fragility"] >= 23.0

    def test_trade_signal_increases_fragility(self, client):
        """Trade signal increases fragility and adds role delta."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "game-123",
                            "bet_type": "player_prop",
                            "selection": "New WR Over 50 yards",
                            "base_fragility": 10.0,
                            "player_id": "player-1",
                        }
                    ],
                    "context_signals": [
                        {
                            "type": "trade",
                            "player_id": "player-1",
                            "player_name": "New WR",
                            "from_team_id": "team-old",
                            "to_team_id": "team-new",
                            "games_affected": 3,
                        }
                    ],
                    "plan": "best",  # Required for trade signals
                },
            )

            assert response.status_code == 200
            data = response.json()
            # Base 10 + trade delta 5 + role delta 4 = 19
            assert data["metrics"]["raw_fragility"] >= 19.0

    def test_multiple_signals_stack(self, client):
        """Multiple context signals stack their effects."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "game-123",
                            "bet_type": "player_prop",
                            "selection": "QB Over 250 passing yards",
                            "base_fragility": 10.0,
                            "player_id": "player-1",
                            "correlation_tags": ["passing"],
                        }
                    ],
                    "context_signals": [
                        {
                            "type": "weather",
                            "game_id": "game-123",
                            "wind_mph": 15,
                            "precip": True,
                        },
                        {
                            "type": "injury",
                            "player_id": "player-1",
                            "status": "DOUBTFUL",
                            "injury": "Shoulder",
                        },
                    ],
                    "plan": "better",  # Required for injury signals
                },
            )

            assert response.status_code == 200
            data = response.json()
            # Base 10 + weather (4+3) + injury 6 + role 3 = 26
            assert data["metrics"]["raw_fragility"] >= 26.0

    def test_no_signals_no_change(self, client):
        """Empty context_signals has no effect."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            # First request without signals
            response1 = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "game-123",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 15.0,
                        }
                    ],
                },
            )

            # Second request with empty signals
            response2 = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "game-123",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 15.0,
                        }
                    ],
                    "context_signals": [],
                },
            )

            assert response1.status_code == 200
            assert response2.status_code == 200
            data1 = response1.json()
            data2 = response2.json()
            assert data1["metrics"]["raw_fragility"] == data2["metrics"]["raw_fragility"]

    def test_unknown_signal_type_rejected(self, client):
        """Unknown signal types are rejected with 400 error (tier gating)."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate",
                json={
                    "blocks": [
                        {
                            "sport": "NFL",
                            "game_id": "game-123",
                            "bet_type": "spread",
                            "selection": "Team A -3.5",
                            "base_fragility": 15.0,
                        }
                    ],
                    "context_signals": [
                        {
                            "type": "unknown_type",
                        }
                    ],
                },
            )

            # Unknown signal types are rejected by tier gating
            assert response.status_code == 400
            data = response.json()
            assert data["detail"]["code"] == "SIGNAL_NOT_ALLOWED"


# =============================================================================
# OCR Endpoint Tests (Ticket: OCR Verification)
# =============================================================================


class TestOCREndpoint:
    """
    Integration tests for /leading-light/evaluate/image endpoint.

    Ticket: OCR Verification + Hard Proof
    """

    def test_ocr_endpoint_exists(self, client):
        """OCR endpoint is reachable (not 404)."""
        # Create minimal 1x1 white PNG
        # PNG header + IHDR chunk + IDAT chunk + IEND chunk
        minimal_png = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D,  # IHDR length
            0x49, 0x48, 0x44, 0x52,  # IHDR
            0x00, 0x00, 0x00, 0x01,  # width: 1
            0x00, 0x00, 0x00, 0x01,  # height: 1
            0x08, 0x02,              # bit depth: 8, color type: 2 (RGB)
            0x00, 0x00, 0x00,        # compression, filter, interlace
            0x90, 0x77, 0x53, 0xDE,  # CRC
            0x00, 0x00, 0x00, 0x0C,  # IDAT length
            0x49, 0x44, 0x41, 0x54,  # IDAT
            0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF, 0x00,  # compressed data
            0x05, 0xFE, 0x02, 0xFE,  # CRC
            0x00, 0x00, 0x00, 0x00,  # IEND length
            0x49, 0x45, 0x4E, 0x44,  # IEND
            0xAE, 0x42, 0x60, 0x82,  # CRC
        ])

        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate/image",
                files={"image": ("test.png", minimal_png, "image/png")},
                data={"plan": "free"},
            )

        # Should NOT be 404 (endpoint exists)
        assert response.status_code != 404, "OCR endpoint not found"

    def test_ocr_requires_image_field(self, client):
        """OCR endpoint requires 'image' form field (not 'file')."""
        minimal_png = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE,
            0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41, 0x54,
            0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF, 0x00,
            0x05, 0xFE, 0x02, 0xFE,
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
            0xAE, 0x42, 0x60, 0x82,
        ])

        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            # Send with WRONG field name 'file' instead of 'image'
            response = client.post(
                "/leading-light/evaluate/image",
                files={"file": ("test.png", minimal_png, "image/png")},
                data={"plan": "free"},
            )

        # Should fail with 422 (validation error) because 'image' field missing
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        # Pydantic validation error mentions the missing field
        assert any("image" in str(d).lower() for d in data["detail"])

    def test_ocr_correct_field_name_accepted(self, client):
        """OCR endpoint accepts 'image' form field."""
        minimal_png = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE,
            0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41, 0x54,
            0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF, 0x00,
            0x05, 0xFE, 0x02, 0xFE,
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
            0xAE, 0x42, 0x60, 0x82,
        ])

        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            # Send with CORRECT field name 'image'
            response = client.post(
                "/leading-light/evaluate/image",
                files={"image": ("test.png", minimal_png, "image/png")},
                data={"plan": "free"},
            )

        # Should NOT be 422 (field is recognized)
        # May be 200 (success) or 500 (OCR service error) but NOT 422
        assert response.status_code != 422, f"Field 'image' should be accepted"

    def test_ocr_rejects_non_image_content_type(self, client):
        """OCR endpoint rejects non-image content types."""
        text_file = b"This is not an image"

        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate/image",
                files={"image": ("test.txt", text_file, "text/plain")},
                data={"plan": "free"},
            )

        # Should reject with 400
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_FILE_TYPE"

    def test_ocr_response_structure(self, client):
        """OCR endpoint returns expected response structure on success."""
        minimal_png = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE,
            0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41, 0x54,
            0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0xFF, 0x00,
            0x05, 0xFE, 0x02, 0xFE,
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
            0xAE, 0x42, 0x60, 0x82,
        ])

        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post(
                "/leading-light/evaluate/image",
                files={"image": ("test.png", minimal_png, "image/png")},
                data={"plan": "free"},
            )

        # If 200, check response structure
        if response.status_code == 200:
            data = response.json()
            assert "input" in data, "Response missing 'input' field"
            assert "image_filename" in data["input"], "Response missing filename"
