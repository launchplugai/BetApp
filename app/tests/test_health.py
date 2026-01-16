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

    def test_health_status_is_healthy(self, client):
        """Health status value is 'healthy'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "dna-matrix"


class TestHealthGitSha:
    """Tests for git_sha in /health endpoint."""

    def test_git_sha_included_when_configured(self, client):
        """git_sha appears in /health when config has it set."""
        # Temporarily set git_sha on the config
        original_sha = _config.git_sha
        try:
            _config.git_sha = "test123abc"
            response = client.get("/health")
            data = response.json()
            assert "git_sha" in data
            assert data["git_sha"] == "test123abc"
        finally:
            _config.git_sha = original_sha

    def test_git_sha_excluded_when_not_configured(self, client):
        """git_sha is not in /health when config has None."""
        # Temporarily unset git_sha on the config
        original_sha = _config.git_sha
        try:
            _config.git_sha = None
            response = client.get("/health")
            data = response.json()
            assert "git_sha" not in data
        finally:
            _config.git_sha = original_sha


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
