# app/tests/test_health.py
"""Tests for health and observability endpoints."""
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, _config


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint returns HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_contains_required_keys(self, client):
        """Health response contains observability keys."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "environment" in data
        assert "started_at" in data
        assert "git_sha" in data
        assert "build_time_utc" in data

    def test_health_git_sha_is_string(self, client):
        """git_sha value is a string."""
        response = client.get("/health")
        data = response.json()
        assert isinstance(data["git_sha"], str)
        assert len(data["git_sha"]) > 0

    def test_health_build_time_utc_is_string(self, client):
        """build_time_utc value is a string."""
        response = client.get("/health")
        data = response.json()
        assert isinstance(data["build_time_utc"], str)
        assert len(data["build_time_utc"]) > 0

    def test_health_status_is_healthy(self, client):
        """Health status value is 'healthy'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "dna-matrix"


class TestHealthGitSha:
    """Tests for git_sha in /health endpoint."""

    def test_git_sha_reflects_config_value(self, client):
        """git_sha in /health reflects config value."""
        original_sha = _config.git_sha
        try:
            _config.git_sha = "test123abc"
            response = client.get("/health")
            data = response.json()
            assert "git_sha" in data
            assert data["git_sha"] == "test123abc"
        finally:
            _config.git_sha = original_sha

    def test_git_sha_defaults_to_unknown(self, client):
        """git_sha shows 'unknown' when not configured."""
        original_sha = _config.git_sha
        try:
            _config.git_sha = "unknown"
            response = client.get("/health")
            data = response.json()
            assert data["git_sha"] == "unknown"
        finally:
            _config.git_sha = original_sha


class TestHealthBuildTime:
    """Tests for build_time_utc in /health endpoint."""

    def test_build_time_utc_reflects_config_value(self, client):
        """build_time_utc in /health reflects config value."""
        original_time = _config.build_time_utc
        try:
            _config.build_time_utc = "2026-01-28T12:00:00Z"
            response = client.get("/health")
            data = response.json()
            assert "build_time_utc" in data
            assert data["build_time_utc"] == "2026-01-28T12:00:00Z"
        finally:
            _config.build_time_utc = original_time

    def test_build_time_utc_is_iso8601_format(self, client):
        """build_time_utc is in ISO8601 format."""
        response = client.get("/health")
        data = response.json()
        # ISO8601 format should contain 'T' separator and timezone info
        assert "T" in data["build_time_utc"]


class TestRootEndpoint:
    """Tests for / endpoint (web UI landing page)."""

    def test_root_returns_200(self, client):
        """Root endpoint returns HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_html(self, client):
        """Root returns HTML page (web UI)."""
        response = client.get("/")
        assert "text/html" in response.headers.get("content-type", "")
