"""
Contract tests for /api/games endpoints.

R0.2: No UI wiring until backend contract tests pass.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestGamesContract:
    """Contract tests for games API."""
    
    def test_games_response_shape(self):
        """
        R0.1: Backend is authoritative - API must return deterministic shape.
        
        Expected shape:
        [
            {
                "id": str,
                "league": str,
                "home": str,
                "away": str,
                "start_time": str (ISO8601),
                "status": str
            }
        ]
        """
        response = client.get("/api/games?sport=NBA")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Response must be array"
        
        for game in data:
            # Required fields
            assert "id" in game, "Missing 'id' field"
            assert "league" in game, "Missing 'league' field"
            assert "home" in game, "Missing 'home' field"
            assert "away" in game, "Missing 'away' field"
            assert "start_time" in game, "Missing 'start_time' field"
            assert "status" in game, "Missing 'status' field"
            
            # Types
            assert isinstance(game["id"], str), "'id' must be string"
            assert isinstance(game["league"], str), "'league' must be string"
            assert isinstance(game["home"], str), "'home' must be string"
            assert isinstance(game["away"], str), "'away' must be string"
            assert isinstance(game["start_time"], str), "'start_time' must be string (ISO8601)"
            assert isinstance(game["status"], str), "'status' must be string"
    
    def test_games_required_fields_present(self):
        """
        All NBA games must have teams and valid status.
        """
        response = client.get("/api/games?sport=NBA")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0, "Should have NBA games"
        
        for game in data:
            assert game["home"], "Home team must not be empty"
            assert game["away"], "Away team must not be empty"
            assert game["status"] in ["SCHEDULED", "LIVE", "FINISHED"], \
                f"Invalid status: {game['status']}"
    
    def test_games_invalid_sport(self):
        """
        R0.4: Invalid sport should return empty with diagnostic.
        """
        response = client.get("/api/games?sport=INVALID")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Should return array even for invalid sport"
        # R0.4: Could add X-Diagnostic header in future
    
    def test_games_missing_sport_param(self):
        """
        Missing sport param should error clearly.
        """
        response = client.get("/api/games")
        assert response.status_code == 422  # FastAPI validation error
        
        data = response.json()
        assert "detail" in data, "Error must have 'detail'"
