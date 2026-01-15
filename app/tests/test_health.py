# app/tests/test_health.py
"""Tests for health and observability endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


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


class TestRootEndpoint:
    """Tests for / endpoint."""

    def test_root_returns_200(self, client):
        """Root endpoint returns HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_status(self, client):
        """Root response contains status."""
        response = client.get("/")
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "dna-matrix"
