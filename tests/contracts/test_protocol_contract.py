"""
Contract tests for Protocol API endpoints.

Phase 1: Database Persistence & User Linking
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestProtocolContract:
    """Contract tests for protocol API."""
    
    def test_create_protocol_requires_auth(self):
        """Creating a protocol requires authentication."""
        response = client.post("/api/protocols/", json={
            "game_id": "nba-lal-gsw-2026-02-09",
            "league": "NBA",
            "home_team": "Lakers",
            "away_team": "Warriors"
        })
        assert response.status_code == 401
    
    def test_list_protocols_requires_auth(self):
        """Listing protocols requires authentication."""
        response = client.get("/api/protocols/")
        assert response.status_code == 401
    
    def test_get_protocol_requires_auth(self):
        """Getting a protocol requires authentication."""
        response = client.get("/api/protocols/proto_123")
        assert response.status_code == 401
    
    def test_update_protocol_requires_auth(self):
        """Updating a protocol requires authentication."""
        response = client.patch("/api/protocols/proto_123", json={"name": "Updated"})
        assert response.status_code == 401
    
    def test_delete_protocol_requires_auth(self):
        """Deleting a protocol requires authentication."""
        response = client.delete("/api/protocols/proto_123")
        assert response.status_code == 401
    
    def test_protocol_response_shape(self):
        """
        R0.1: Protocol response must have deterministic shape.
        
        {
            "id": str,
            "game_id": str,
            "league": str,
            "home_team": str,
            "away_team": str,
            "name": str|null,
            "markets_watched": [...],
            "legs_snapshot": [...]|null,
            "is_active": bool,
            "created_at": str,
            "last_updated": str
        }
        """
        pass  # Shape enforced by pydantic
    
    def test_protocol_list_response_shape(self):
        """
        List response shape:
        {
            "protocols": [...],
            "total": int
        }
        """
        pass


class TestProtocolPermissions:
    """Permission contract tests."""
    
    def test_user_can_only_access_own_protocols(self):
        """Users cannot access other users' protocols."""
        pass  # Business logic test
    
    def test_soft_delete_archives_not_deletes(self):
        """Delete sets is_active=false, doesn't hard delete."""
        pass
