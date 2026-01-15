# app/tests/test_config.py
"""Tests for configuration management and startup validation."""
import os
from unittest.mock import patch

import pytest

from app.config import (
    DEFAULT_MAX_REQUEST_SIZE_BYTES,
    MIN_REQUEST_SIZE_BYTES,
    SENSITIVE_SUBSTRINGS,
    AppConfig,
    load_config,
    log_config_snapshot,
    validate_config_snapshot_safety,
)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_default_values(self):
        """Config loads with sensible defaults when no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()

        assert config.service_name == "dna-matrix"
        assert config.service_version == "0.1.0"
        assert config.environment == "development"
        assert config.max_request_size_bytes == DEFAULT_MAX_REQUEST_SIZE_BYTES
        assert config.leading_light_enabled is False
        assert config.voice_enabled is False
        assert config.openai_api_key_present is False

    def test_environment_from_railway(self):
        """Environment is read from RAILWAY_ENVIRONMENT."""
        with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT": "production"}, clear=True):
            config = load_config()

        assert config.environment == "production"

    def test_feature_flags_enabled(self):
        """Feature flags can be enabled via env vars."""
        with patch.dict(
            os.environ,
            {
                "LEADING_LIGHT_ENABLED": "true",
                "VOICE_ENABLED": "1",
            },
            clear=True,
        ):
            config = load_config()

        assert config.leading_light_enabled is True
        assert config.voice_enabled is True

    def test_api_key_presence_detected(self):
        """API key presence is detected without storing the value."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}, clear=True):
            config = load_config()

        assert config.openai_api_key_present is True

    def test_api_key_absence_detected(self):
        """Missing API key is correctly detected."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()

        assert config.openai_api_key_present is False


class TestMaxRequestSizeValidation:
    """Tests for MAX_REQUEST_SIZE_BYTES validation."""

    def test_valid_size_accepted(self):
        """Valid size value is accepted."""
        with patch.dict(
            os.environ, {"MAX_REQUEST_SIZE_BYTES": "2097152"}, clear=True
        ):
            config = load_config()

        assert config.max_request_size_bytes == 2097152

    def test_invalid_string_uses_default_with_warning(self):
        """Non-integer string falls back to default with warning."""
        with patch.dict(
            os.environ, {"MAX_REQUEST_SIZE_BYTES": "not-a-number"}, clear=True
        ):
            config = load_config()

        assert config.max_request_size_bytes == DEFAULT_MAX_REQUEST_SIZE_BYTES
        assert any("not a valid integer" in w for w in config.warnings)

    def test_below_minimum_uses_default_with_warning(self):
        """Value below minimum falls back to default with warning."""
        with patch.dict(os.environ, {"MAX_REQUEST_SIZE_BYTES": "100"}, clear=True):
            config = load_config()

        assert config.max_request_size_bytes == DEFAULT_MAX_REQUEST_SIZE_BYTES
        assert any("below minimum" in w for w in config.warnings)

    def test_zero_uses_default_with_warning(self):
        """Zero value falls back to default with warning."""
        with patch.dict(os.environ, {"MAX_REQUEST_SIZE_BYTES": "0"}, clear=True):
            config = load_config()

        assert config.max_request_size_bytes == DEFAULT_MAX_REQUEST_SIZE_BYTES
        assert any("below minimum" in w for w in config.warnings)

    def test_negative_uses_default_with_warning(self):
        """Negative value falls back to default with warning."""
        with patch.dict(os.environ, {"MAX_REQUEST_SIZE_BYTES": "-1000"}, clear=True):
            config = load_config()

        assert config.max_request_size_bytes == DEFAULT_MAX_REQUEST_SIZE_BYTES
        assert any("below minimum" in w for w in config.warnings)


class TestConfigSnapshotSafety:
    """Tests for config snapshot security."""

    def test_snapshot_contains_expected_fields(self):
        """Config snapshot contains required observability fields."""
        config = AppConfig()
        snapshot = log_config_snapshot(config)

        assert "service=" in snapshot
        assert "version=" in snapshot
        assert "environment=" in snapshot
        assert "max_request_size_bytes=" in snapshot
        assert "leading_light_enabled=" in snapshot
        assert "voice_enabled=" in snapshot
        assert "openai_api_key_present=" in snapshot

    def test_snapshot_never_contains_actual_secrets(self):
        """Config snapshot uses boolean presence, not actual values."""
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "sk-super-secret-key-12345"},
            clear=True,
        ):
            config = load_config()
            snapshot = log_config_snapshot(config)

        # Should NOT contain the actual key value
        assert "sk-super-secret-key" not in snapshot
        assert "12345" not in snapshot

        # Should contain boolean presence flag
        assert "openai_api_key_present=True" in snapshot

    def test_validate_config_snapshot_safety_passes_clean_snapshot(self):
        """Safety validator passes for clean snapshots."""
        config = AppConfig()
        snapshot = log_config_snapshot(config)

        assert validate_config_snapshot_safety(snapshot) is True

    def test_validate_config_snapshot_safety_catches_leaked_key(self):
        """Safety validator catches accidentally logged secrets."""
        # Simulating a bad snapshot that leaked a key
        bad_snapshot = "service=test key=sk-1234 version=1.0"

        assert validate_config_snapshot_safety(bad_snapshot) is False

    def test_validate_config_snapshot_safety_allows_presence_flags(self):
        """Safety validator allows *_present boolean flags."""
        good_snapshot = "api_key_present=True token_present=False"

        # This should pass because it's presence flags, not actual values
        assert validate_config_snapshot_safety(good_snapshot) is True


class TestFeatureWarnings:
    """Tests for feature configuration warnings."""

    def test_warning_when_feature_enabled_but_key_missing(self):
        """Warning is generated when feature enabled but API key missing."""
        with patch.dict(
            os.environ,
            {"LEADING_LIGHT_ENABLED": "true"},
            clear=True,
        ):
            config = load_config()

        assert any("OPENAI_API_KEY is not set" in w for w in config.warnings)

    def test_no_warning_when_feature_disabled(self):
        """No warning when feature is disabled."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()

        assert not any("OPENAI_API_KEY is not set" in w for w in config.warnings)

    def test_no_warning_when_key_present(self):
        """No warning when feature enabled and key present."""
        with patch.dict(
            os.environ,
            {
                "LEADING_LIGHT_ENABLED": "true",
                "OPENAI_API_KEY": "sk-test",
            },
            clear=True,
        ):
            config = load_config()

        assert not any("OPENAI_API_KEY is not set" in w for w in config.warnings)
