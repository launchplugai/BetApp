"""
Slice 2A Tests - Feature-gated endpoints

Tests verify:
1. With flags OFF (default): endpoints return 404
2. With flags ON: endpoints return 200 + valid JSON structure
"""
import pytest
import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestFlagsOff:
    """Test behavior when FEATURE_DASHBOARD_COMMAND_CENTER is OFF (default)."""
    
    def test_system_health_gated(self):
        """System health returns 404 when flag OFF."""
        response = client.get("/api/system/health")
        assert response.status_code == 404
        assert "not enabled" in response.json()["detail"]
    
    def test_protocol_feed_gated(self):
        """Protocol feed returns 404 when flag OFF."""
        response = client.get("/api/protocol/feed")
        assert response.status_code == 404
        assert "not enabled" in response.json()["detail"]
    
    def test_dashboard_screen_exists(self):
        """Dashboard screen returns 200 even when flag OFF."""
        response = client.get("/app?screen=dashboard")
        assert response.status_code == 200
    
    def test_protocol_screen_exists(self):
        """Protocol screen returns 200 even when flag OFF."""
        response = client.get("/app?screen=protocol")
        assert response.status_code == 200


class TestFlagsOn:
    """Test behavior when FEATURE_DASHBOARD_COMMAND_CENTER is ON."""
    
    @pytest.fixture(autouse=True)
    def enable_dashboard(self, monkeypatch):
        """Enable dashboard feature for this test class."""
        monkeypatch.setenv("FEATURE_DASHBOARD_COMMAND_CENTER", "true")
        # Force reload of the router module to pick up new env var
        import importlib
        from app.routers import dashboard_stubs
        importlib.reload(dashboard_stubs)
        # Re-register the router
        from app.main import app
        # Router already included, just need env var change
    
    def test_system_health_live(self):
        """System health returns 200 + valid JSON when flag ON."""
        response = client.get("/api/system/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
    
    def test_protocol_feed_live(self):
        """Protocol feed returns 200 + valid JSON when flag ON."""
        response = client.get("/api/protocol/feed")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        
    def test_feature_flags_endpoint(self):
        """Feature flags endpoint returns current state."""
        response = client.get("/api/features")
        assert response.status_code == 200
        data = response.json()
        assert "dashboard_enabled" in data
        assert "protocol_feed_enabled" in data


def test_features_endpoint_always_available():
    """Features endpoint is public (not gated)."""
    response = client.get("/api/features")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["dashboard_enabled"], bool)
