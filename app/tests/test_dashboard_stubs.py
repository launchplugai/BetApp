"""
Test dashboard stub endpoints.
With FEATURE_DASHBOARD_COMMAND_CENTER=false (default), all should return 404.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_edge_feed_gated():
    """Edge feed stub returns 404 when dashboard feature disabled."""
    response = client.get("/api/edge-feed")
    assert response.status_code == 404
    assert "not enabled" in response.json()["detail"]


def test_risk_profile_gated():
    """Risk profile stub returns 404 when dashboard feature disabled."""
    response = client.get("/api/risk-profile")
    assert response.status_code == 404
    assert "not enabled" in response.json()["detail"]


def test_system_health_gated():
    """System health stub returns 404 when dashboard feature disabled."""
    response = client.get("/api/system/health")
    assert response.status_code == 404
    assert "not enabled" in response.json()["detail"]
