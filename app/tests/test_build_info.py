# app/tests/test_build_info.py
"""Tests for build info module."""
import os
import pytest
from unittest.mock import patch

from app.build_info import (
    get_commit_sha,
    get_short_commit_sha,
    get_environment,
    get_build_time_utc,
    get_build_info,
    is_commit_unknown,
)


class TestGetCommitSha:
    """Tests for commit SHA resolution."""

    def test_returns_unknown_when_no_env_vars(self):
        """Returns 'unknown' when no env vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_commit_sha() == "unknown"

    def test_git_sha_takes_priority(self):
        """GIT_SHA takes priority over other env vars."""
        with patch.dict(os.environ, {
            "GIT_SHA": "abc123git",
            "RAILWAY_GIT_COMMIT_SHA": "def456railway",
            "COMMIT_SHA": "ghi789commit",
        }):
            assert get_commit_sha() == "abc123git"

    def test_railway_sha_second_priority(self):
        """RAILWAY_GIT_COMMIT_SHA is used when GIT_SHA is not set."""
        with patch.dict(os.environ, {
            "RAILWAY_GIT_COMMIT_SHA": "def456railway",
            "COMMIT_SHA": "ghi789commit",
        }, clear=True):
            assert get_commit_sha() == "def456railway"

    def test_commit_sha_fallback(self):
        """COMMIT_SHA is used as last fallback."""
        with patch.dict(os.environ, {
            "COMMIT_SHA": "ghi789commit",
        }, clear=True):
            assert get_commit_sha() == "ghi789commit"


class TestGetShortCommitSha:
    """Tests for short commit SHA."""

    def test_returns_first_7_chars(self):
        """Returns first 7 characters of SHA."""
        with patch.dict(os.environ, {"GIT_SHA": "abc123456789def"}):
            assert get_short_commit_sha() == "abc1234"

    def test_returns_unknown_when_unknown(self):
        """Returns 'unknown' as-is."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_short_commit_sha() == "unknown"


class TestGetEnvironment:
    """Tests for environment resolution."""

    def test_returns_unknown_when_no_env_vars(self):
        """Returns 'unknown' when no env vars are set."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_environment() == "unknown"

    def test_railway_environment_priority(self):
        """RAILWAY_ENVIRONMENT takes priority."""
        with patch.dict(os.environ, {
            "RAILWAY_ENVIRONMENT": "production",
            "ENVIRONMENT": "development",
        }):
            assert get_environment() == "production"

    def test_environment_fallback(self):
        """ENVIRONMENT is used as fallback."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}, clear=True):
            assert get_environment() == "staging"


class TestGetBuildTimeUtc:
    """Tests for build time resolution."""

    def test_returns_unknown_when_not_set(self):
        """Returns 'unknown' when BUILD_TIME_UTC is not set."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_build_time_utc() == "unknown"

    def test_returns_value_when_set(self):
        """Returns the value when BUILD_TIME_UTC is set."""
        with patch.dict(os.environ, {"BUILD_TIME_UTC": "2024-01-15T10:30:00Z"}):
            assert get_build_time_utc() == "2024-01-15T10:30:00Z"


class TestGetBuildInfo:
    """Tests for complete build info."""

    def test_returns_build_info_dataclass(self):
        """Returns a BuildInfo dataclass."""
        with patch.dict(os.environ, {
            "GIT_SHA": "abc123",
            "RAILWAY_ENVIRONMENT": "production",
            "BUILD_TIME_UTC": "2024-01-15T10:30:00Z",
        }):
            info = get_build_info()
            assert info.service == "dna-bet-engine"
            assert info.commit == "abc123"
            assert info.environment == "production"
            assert info.build_time_utc == "2024-01-15T10:30:00Z"
            assert info.server_time_utc is not None

    def test_handles_missing_values(self):
        """All fields default to 'unknown' when not set."""
        with patch.dict(os.environ, {}, clear=True):
            info = get_build_info()
            assert info.service == "dna-bet-engine"
            assert info.commit == "unknown"
            assert info.environment == "unknown"
            assert info.build_time_utc == "unknown"


class TestIsCommitUnknown:
    """Tests for commit unknown check."""

    def test_returns_true_when_unknown(self):
        """Returns True when commit is unknown."""
        with patch.dict(os.environ, {}, clear=True):
            assert is_commit_unknown() is True

    def test_returns_false_when_known(self):
        """Returns False when commit is set."""
        with patch.dict(os.environ, {"GIT_SHA": "abc123"}):
            assert is_commit_unknown() is False


class TestBuildEndpoint:
    """Tests for /build endpoint."""

    def test_build_endpoint_returns_json(self):
        """The /build endpoint returns JSON."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/build")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "environment" in data
        assert "commit" in data
        assert "build_time_utc" in data
        assert "server_time_utc" in data

    def test_build_endpoint_service_is_correct(self):
        """The service name is dna-bet-engine."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/build")
        data = response.json()
        assert data["service"] == "dna-bet-engine"
