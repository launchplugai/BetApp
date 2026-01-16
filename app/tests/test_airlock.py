# app/tests/test_airlock.py
"""
Tests for Airlock - the single source of truth for input validation.

These tests verify:
1. Input validation (empty, whitespace, too long)
2. Tier normalization (case-insensitive, aliases, defaults)
3. Integration with routes
"""
import os
import pytest

from app.airlock import (
    airlock_ingest,
    AirlockError,
    EmptyInputError,
    InputTooLongError,
    InvalidTierError,
    Tier,
    NormalizedInput,
    get_max_input_length,
    get_valid_tiers,
    MAX_INPUT_LENGTH,
)


class TestInputValidation:
    """Tests for input text validation."""

    def test_valid_input_accepted(self):
        """Valid input is accepted and trimmed."""
        result = airlock_ingest("Lakers -5.5")
        assert result.input_text == "Lakers -5.5"

    def test_input_trimmed(self):
        """Leading/trailing whitespace is trimmed."""
        result = airlock_ingest("  Lakers -5.5  ")
        assert result.input_text == "Lakers -5.5"

    def test_empty_string_rejected(self):
        """Empty string raises EmptyInputError."""
        with pytest.raises(EmptyInputError) as exc:
            airlock_ingest("")
        assert exc.value.code == "EMPTY_INPUT"

    def test_none_rejected(self):
        """None raises EmptyInputError."""
        with pytest.raises(EmptyInputError) as exc:
            airlock_ingest(None)
        assert exc.value.code == "EMPTY_INPUT"

    def test_whitespace_only_rejected(self):
        """Whitespace-only input raises EmptyInputError."""
        with pytest.raises(EmptyInputError) as exc:
            airlock_ingest("   \t\n  ")
        assert exc.value.code == "EMPTY_INPUT"

    def test_input_too_long_rejected(self):
        """Input exceeding max length raises InputTooLongError."""
        long_input = "a" * (MAX_INPUT_LENGTH + 1)
        with pytest.raises(InputTooLongError) as exc:
            airlock_ingest(long_input)
        assert exc.value.code == "INPUT_TOO_LONG"
        assert exc.value.length == MAX_INPUT_LENGTH + 1
        assert exc.value.max_length == MAX_INPUT_LENGTH

    def test_max_length_accepted(self):
        """Input at exactly max length is accepted."""
        max_input = "a" * MAX_INPUT_LENGTH
        result = airlock_ingest(max_input)
        assert len(result.input_text) == MAX_INPUT_LENGTH


class TestTierNormalization:
    """Tests for tier normalization."""

    def test_lowercase_accepted(self):
        """Lowercase tier values are accepted."""
        result = airlock_ingest("test", tier="good")
        assert result.tier == Tier.GOOD

    def test_uppercase_normalized(self):
        """Uppercase tier values are normalized to lowercase."""
        result = airlock_ingest("test", tier="GOOD")
        assert result.tier == Tier.GOOD

    def test_mixed_case_normalized(self):
        """Mixed case tier values are normalized."""
        result = airlock_ingest("test", tier="GoOd")
        assert result.tier == Tier.GOOD

    def test_all_tiers_recognized(self):
        """All valid tiers are recognized."""
        assert airlock_ingest("test", tier="good").tier == Tier.GOOD
        assert airlock_ingest("test", tier="better").tier == Tier.BETTER
        assert airlock_ingest("test", tier="best").tier == Tier.BEST

    def test_none_defaults_to_good(self):
        """None tier defaults to GOOD."""
        result = airlock_ingest("test", tier=None)
        assert result.tier == Tier.GOOD

    def test_free_alias_maps_to_good(self):
        """Legacy 'free' alias maps to GOOD."""
        result = airlock_ingest("test", tier="free")
        assert result.tier == Tier.GOOD

    def test_invalid_tier_rejected(self):
        """Invalid tier raises InvalidTierError."""
        with pytest.raises(InvalidTierError) as exc:
            airlock_ingest("test", tier="premium")
        assert exc.value.code == "INVALID_TIER"
        assert "premium" in exc.value.message

    def test_tier_whitespace_trimmed(self):
        """Tier whitespace is trimmed."""
        result = airlock_ingest("test", tier="  good  ")
        assert result.tier == Tier.GOOD


class TestNormalizedInput:
    """Tests for NormalizedInput dataclass."""

    def test_input_length_property(self):
        """input_length property returns correct length."""
        result = airlock_ingest("Lakers -5.5")
        assert result.input_length == 11

    def test_session_id_optional(self):
        """session_id is optional and defaults to None."""
        result = airlock_ingest("test")
        assert result.session_id is None

    def test_session_id_preserved(self):
        """session_id is preserved when provided."""
        result = airlock_ingest("test", session_id="sess_123")
        assert result.session_id == "sess_123"

    def test_frozen_immutable(self):
        """NormalizedInput is immutable (frozen dataclass)."""
        result = airlock_ingest("test")
        with pytest.raises(Exception):
            result.input_text = "modified"


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_get_max_input_length(self):
        """get_max_input_length returns the constant."""
        assert get_max_input_length() == MAX_INPUT_LENGTH

    def test_get_valid_tiers(self):
        """get_valid_tiers returns all tier values."""
        tiers = get_valid_tiers()
        assert "good" in tiers
        assert "better" in tiers
        assert "best" in tiers
        assert len(tiers) == 3


class TestAirlockErrorBase:
    """Tests for AirlockError base class."""

    def test_error_has_message_and_code(self):
        """AirlockError has message and code attributes."""
        try:
            airlock_ingest("")
        except AirlockError as e:
            assert hasattr(e, "message")
            assert hasattr(e, "code")
            assert e.message == str(e)


class TestIntegrationWithRoutes:
    """Integration tests with FastAPI routes."""

    @pytest.fixture
    def client(self):
        """Create test client with Leading Light enabled."""
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        from app.rate_limiter import set_rate_limiter, RateLimiter
        set_rate_limiter(RateLimiter(requests_per_minute=100, burst_size=100))
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_empty_input_returns_400(self, client):
        """Empty input returns 400 with EMPTY_INPUT code."""
        response = client.post(
            "/app/evaluate",
            json={"input": "", "tier": "good"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "EMPTY_INPUT"

    def test_whitespace_input_returns_400(self, client):
        """Whitespace-only input returns 400."""
        response = client.post(
            "/app/evaluate",
            json={"input": "   ", "tier": "good"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "EMPTY_INPUT"

    def test_input_too_long_returns_400(self, client):
        """Input too long returns 400 with INPUT_TOO_LONG code."""
        long_input = "a" * (MAX_INPUT_LENGTH + 1)
        response = client.post(
            "/app/evaluate",
            json={"input": long_input, "tier": "good"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INPUT_TOO_LONG"

    def test_invalid_tier_returns_400(self, client):
        """Invalid tier returns 400 with INVALID_TIER code."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "premium"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INVALID_TIER"

    def test_valid_request_succeeds(self, client):
        """Valid request with good input and tier succeeds."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "evaluation" in data
        assert data["input"]["tier"] == "good"

    def test_tier_case_insensitive(self, client):
        """Tier is case-insensitive."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "GOOD"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["input"]["tier"] == "good"

    def test_free_tier_alias_works(self, client):
        """Legacy 'free' tier alias works."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "free"},
        )
        assert response.status_code == 200
        data = response.json()
        # 'free' maps to 'good'
        assert data["input"]["tier"] == "good"

    def test_default_tier_when_none(self, client):
        """Default tier is used when not provided."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["input"]["tier"] == "good"
