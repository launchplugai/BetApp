# app/tests/test_voice.py
"""
Tests for Voice Narration module.

Covers:
- Service enable/disable flag
- Plan gating (BEST only or VOICE_OVERRIDE)
- Narration endpoints
- Generic TTS endpoint
- Caching behavior
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.voice.tts_client import (
    clear_cache,
    get_cached_audio,
    set_cached_audio,
    _get_text_hash,
)
from app.voice.narration import get_narration, list_available_narrations


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_audio_cache():
    """Clear audio cache before each test."""
    clear_cache()
    yield
    clear_cache()


# =============================================================================
# Test Narration Scripts
# =============================================================================


class TestNarrationScripts:
    """Tests for narration script retrieval."""

    def test_get_stable_narration(self):
        """Stable case has narration."""
        narration = get_narration("stable")
        assert narration is not None
        assert "stable" in narration.lower()

    def test_get_loaded_narration(self):
        """Loaded case has narration."""
        narration = get_narration("loaded")
        assert narration is not None
        assert "loaded" in narration.lower()

    def test_get_tense_narration(self):
        """Tense case has narration."""
        narration = get_narration("tense")
        assert narration is not None
        assert "tense" in narration.lower()

    def test_get_critical_narration(self):
        """Critical case has narration."""
        narration = get_narration("critical")
        assert narration is not None
        assert "critical" in narration.lower()

    def test_unknown_case_returns_none(self):
        """Unknown case returns None."""
        narration = get_narration("nonexistent")
        assert narration is None

    def test_case_insensitive(self):
        """Case names are case-insensitive."""
        assert get_narration("STABLE") == get_narration("stable")
        assert get_narration("Loaded") == get_narration("loaded")

    def test_list_available_narrations(self):
        """List returns all available narrations."""
        available = list_available_narrations()
        assert "stable" in available
        assert "loaded" in available
        assert "tense" in available
        assert "critical" in available


# =============================================================================
# Test Service Disabled (503)
# =============================================================================


class TestServiceDisabled:
    """Tests for when VOICE_ENABLED=false."""

    def test_narration_returns_503_when_disabled(self, client):
        """Narration endpoint returns 503 when voice disabled."""
        with patch.dict("os.environ", {"VOICE_ENABLED": "false", "VOICE_OVERRIDE": "true"}):
            response = client.get("/leading-light/demo/stable/narration?plan=best")

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "SERVICE_DISABLED"

    def test_tts_returns_503_when_disabled(self, client):
        """TTS endpoint returns 503 when voice disabled."""
        with patch.dict("os.environ", {"VOICE_ENABLED": "false", "VOICE_OVERRIDE": "true"}):
            response = client.post(
                "/voice/tts",
                json={"text": "Hello world", "plan": "best"},
            )

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "SERVICE_DISABLED"

    def test_status_shows_disabled(self, client):
        """Status endpoint shows disabled state."""
        with patch.dict("os.environ", {"VOICE_ENABLED": "false"}):
            response = client.get("/voice/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["service"] == "voice-tts"


# =============================================================================
# Test Plan Gating (BEST Only)
# =============================================================================


class TestPlanGating:
    """Tests for plan-based access control."""

    def test_good_plan_denied(self, client):
        """GOOD plan is denied voice access."""
        with patch.dict("os.environ", {"VOICE_ENABLED": "true", "VOICE_OVERRIDE": "false"}):
            response = client.get("/leading-light/demo/stable/narration?plan=good")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "VOICE_ACCESS_DENIED"

    def test_better_plan_denied(self, client):
        """BETTER plan is denied voice access."""
        with patch.dict("os.environ", {"VOICE_ENABLED": "true", "VOICE_OVERRIDE": "false"}):
            response = client.get("/leading-light/demo/stable/narration?plan=better")

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "VOICE_ACCESS_DENIED"

    def test_best_plan_allowed(self, client):
        """BEST plan is allowed voice access."""
        mock_audio = b"fake audio bytes"

        with patch.dict("os.environ", {
            "VOICE_ENABLED": "true",
            "VOICE_OVERRIDE": "false",
            "OPENAI_API_KEY": "test-key",
        }):
            with patch("app.voice.tts_client.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.content = mock_audio
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                response = client.get("/leading-light/demo/stable/narration?plan=best")

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"

    def test_voice_override_bypasses_plan_check(self, client):
        """VOICE_OVERRIDE=true bypasses plan check."""
        mock_audio = b"fake audio bytes"

        with patch.dict("os.environ", {
            "VOICE_ENABLED": "true",
            "VOICE_OVERRIDE": "true",
            "OPENAI_API_KEY": "test-key",
        }):
            with patch("app.voice.tts_client.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.content = mock_audio
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                # Using GOOD plan but with override
                response = client.get("/leading-light/demo/stable/narration?plan=good")

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"

    def test_tts_plan_gating(self, client):
        """TTS endpoint also respects plan gating."""
        with patch.dict("os.environ", {"VOICE_ENABLED": "true", "VOICE_OVERRIDE": "false"}):
            response = client.post(
                "/voice/tts",
                json={"text": "Hello world", "plan": "good"},
            )

        assert response.status_code == 403
        data = response.json()
        assert data["detail"]["code"] == "VOICE_ACCESS_DENIED"


# =============================================================================
# Test Narration Endpoint
# =============================================================================


class TestNarrationEndpoint:
    """Tests for demo case narration endpoint."""

    def test_unknown_case_returns_404(self, client):
        """Unknown demo case returns 404."""
        with patch.dict("os.environ", {"VOICE_ENABLED": "true", "VOICE_OVERRIDE": "true"}):
            response = client.get("/leading-light/demo/unknown_case/narration")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == "NOT_FOUND"

    def test_returns_audio_with_correct_headers(self, client):
        """Successful response has correct content type and headers."""
        mock_audio = b"fake audio bytes for testing"

        with patch.dict("os.environ", {
            "VOICE_ENABLED": "true",
            "VOICE_OVERRIDE": "true",
            "OPENAI_API_KEY": "test-key",
        }):
            with patch("app.voice.tts_client.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.content = mock_audio
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                response = client.get("/leading-light/demo/stable/narration")

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert "stable_narration.mp3" in response.headers.get("content-disposition", "")
        assert response.content == mock_audio

    def test_custom_voice_parameter(self, client):
        """Custom voice parameter is passed to TTS."""
        mock_audio = b"fake audio"

        with patch.dict("os.environ", {
            "VOICE_ENABLED": "true",
            "VOICE_OVERRIDE": "true",
            "OPENAI_API_KEY": "test-key",
        }):
            with patch("app.voice.tts_client.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.content = mock_audio

                mock_post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.post = mock_post

                response = client.get("/leading-light/demo/stable/narration?voice=nova")

        assert response.status_code == 200
        # Verify voice was passed (check the json payload)
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["voice"] == "nova"


# =============================================================================
# Test Generic TTS Endpoint
# =============================================================================


class TestTTSEndpoint:
    """Tests for generic TTS endpoint."""

    def test_requires_text(self, client):
        """Text field is required."""
        with patch.dict("os.environ", {"VOICE_ENABLED": "true", "VOICE_OVERRIDE": "true"}):
            response = client.post("/voice/tts", json={"plan": "best"})

        assert response.status_code == 422  # Validation error

    def test_text_max_length(self, client):
        """Text has max length limit."""
        with patch.dict("os.environ", {"VOICE_ENABLED": "true", "VOICE_OVERRIDE": "true"}):
            response = client.post(
                "/voice/tts",
                json={"text": "x" * 5000, "plan": "best"},  # Over 4096 limit
            )

        assert response.status_code == 422  # Validation error

    def test_successful_tts(self, client):
        """Successful TTS returns audio."""
        mock_audio = b"generated audio bytes"

        with patch.dict("os.environ", {
            "VOICE_ENABLED": "true",
            "VOICE_OVERRIDE": "true",
            "OPENAI_API_KEY": "test-key",
        }):
            with patch("app.voice.tts_client.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.content = mock_audio
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                response = client.post(
                    "/voice/tts",
                    json={"text": "Hello world", "plan": "best"},
                )

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert response.content == mock_audio

    def test_custom_model_and_voice(self, client):
        """Custom model and voice parameters are used."""
        mock_audio = b"audio"

        with patch.dict("os.environ", {
            "VOICE_ENABLED": "true",
            "VOICE_OVERRIDE": "true",
            "OPENAI_API_KEY": "test-key",
        }):
            with patch("app.voice.tts_client.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.content = mock_audio

                mock_post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.post = mock_post

                response = client.post(
                    "/voice/tts",
                    json={
                        "text": "Test",
                        "voice": "shimmer",
                        "model": "tts-1-hd",
                        "plan": "best",
                    },
                )

        assert response.status_code == 200
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["voice"] == "shimmer"
        assert call_kwargs[1]["json"]["model"] == "tts-1-hd"


# =============================================================================
# Test OpenAI API Error Handling
# =============================================================================


class TestAPIErrorHandling:
    """Tests for OpenAI API error handling."""

    def test_api_error_returns_502(self, client):
        """OpenAI API errors return 502."""
        with patch.dict("os.environ", {
            "VOICE_ENABLED": "true",
            "VOICE_OVERRIDE": "true",
            "OPENAI_API_KEY": "test-key",
        }):
            with patch("app.voice.tts_client.httpx.AsyncClient") as mock_client:
                mock_response = AsyncMock()
                mock_response.status_code = 429
                mock_response.text = "Rate limited"
                mock_response.json = lambda: {"error": {"message": "Rate limited"}}
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    return_value=mock_response
                )

                response = client.get("/leading-light/demo/stable/narration")

        assert response.status_code == 502
        data = response.json()
        assert data["detail"]["code"] == "TTS_API_ERROR"

    def test_missing_api_key_returns_503(self, client):
        """Missing API key returns 503."""
        with patch.dict("os.environ", {
            "VOICE_ENABLED": "true",
            "VOICE_OVERRIDE": "true",
        }, clear=False):
            # Remove OPENAI_API_KEY if set
            import os
            os.environ.pop("OPENAI_API_KEY", None)

            response = client.get("/leading-light/demo/stable/narration")

        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["code"] == "SERVICE_MISCONFIGURED"


# =============================================================================
# Test Caching
# =============================================================================


class TestCaching:
    """Tests for in-memory audio caching."""

    def test_cache_stores_audio(self):
        """Cache stores and retrieves audio."""
        audio = b"cached audio data"
        set_cached_audio("stable", "alloy", "gpt-4o-mini-tts", "test text", audio)

        cached = get_cached_audio("stable", "alloy", "gpt-4o-mini-tts", "test text")
        assert cached == audio

    def test_cache_miss_returns_none(self):
        """Cache miss returns None."""
        cached = get_cached_audio("stable", "alloy", "gpt-4o-mini-tts", "different text")
        assert cached is None

    def test_cache_key_includes_voice(self):
        """Different voices have different cache keys."""
        audio1 = b"audio1"
        audio2 = b"audio2"

        set_cached_audio("stable", "alloy", "gpt-4o-mini-tts", "same text", audio1)
        set_cached_audio("stable", "nova", "gpt-4o-mini-tts", "same text", audio2)

        assert get_cached_audio("stable", "alloy", "gpt-4o-mini-tts", "same text") == audio1
        assert get_cached_audio("stable", "nova", "gpt-4o-mini-tts", "same text") == audio2

    def test_cache_key_includes_model(self):
        """Different models have different cache keys."""
        audio1 = b"audio1"
        audio2 = b"audio2"

        set_cached_audio("stable", "alloy", "gpt-4o-mini-tts", "same text", audio1)
        set_cached_audio("stable", "alloy", "tts-1-hd", "same text", audio2)

        assert get_cached_audio("stable", "alloy", "gpt-4o-mini-tts", "same text") == audio1
        assert get_cached_audio("stable", "alloy", "tts-1-hd", "same text") == audio2

    def test_text_hash_deterministic(self):
        """Text hashing is deterministic."""
        text = "This is a test narration"
        hash1 = _get_text_hash(text)
        hash2 = _get_text_hash(text)
        assert hash1 == hash2

    def test_text_hash_differs_for_different_text(self):
        """Different texts produce different hashes."""
        hash1 = _get_text_hash("text one")
        hash2 = _get_text_hash("text two")
        assert hash1 != hash2


# =============================================================================
# Test Status Endpoint
# =============================================================================


class TestStatusEndpoint:
    """Tests for voice status endpoint."""

    def test_status_when_enabled(self, client):
        """Status shows enabled state with config."""
        with patch.dict("os.environ", {
            "VOICE_ENABLED": "true",
            "OPENAI_API_KEY": "test-key",
            "OPENAI_TTS_MODEL": "custom-model",
            "OPENAI_TTS_VOICE": "nova",
        }):
            response = client.get("/voice/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["configured"] is True
        assert data["model"] == "custom-model"
        assert data["voice"] == "nova"

    def test_status_when_enabled_but_no_key(self, client):
        """Status shows not configured when API key missing."""
        with patch.dict("os.environ", {"VOICE_ENABLED": "true"}, clear=False):
            import os
            os.environ.pop("OPENAI_API_KEY", None)

            response = client.get("/voice/status")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["configured"] is False
