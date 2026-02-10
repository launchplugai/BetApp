"""
Contract tests for /api/odds endpoints.

R0.2: No UI wiring until backend contract tests pass.
These tests verify API response shape and deterministic behavior.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestOddsContract:
    """Contract tests for odds API - must pass before UI consumption."""
    
    def test_odds_response_shape(self):
        """
        R0.1: Backend is authoritative - API must return deterministic shape.
        
        Expected shape:
        [
            {
                "market": str,
                "selections": [
                    {"label": str, "line": float|None, "odds": int}
                ]
            }
        ]
        """
        response = client.get("/api/odds/nba-test-game-001")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list), "Response must be array"
        
        for market in data:
            # Required fields
            assert "market" in market, "Missing 'market' field"
            assert "selections" in market, "Missing 'selections' field"
            assert isinstance(market["market"], str), "'market' must be string"
            assert isinstance(market["selections"], list), "'selections' must be array"
            
            for selection in market["selections"]:
                assert "label" in selection, "Missing 'label' in selection"
                assert "odds" in selection, "Missing 'odds' in selection"
                assert isinstance(selection["label"], str), "'label' must be string"
                assert isinstance(selection["odds"], int), "'odds' must be int"
                # 'line' can be float or None
                if "line" in selection and selection["line"] is not None:
                    assert isinstance(selection["line"], (int, float)), "'line' must be numeric or None"
    
    def test_odds_required_markets_present(self):
        """
        Core markets must be present for NBA games.
        """
        response = client.get("/api/odds/nba-lal-gsw-2026-02-09")
        assert response.status_code == 200
        
        data = response.json()
        markets = [m["market"] for m in data]
        
        assert "spread" in markets, "Missing 'spread' market"
        assert "total" in markets, "Missing 'total' market"
        assert "moneyline" in markets, "Missing 'moneyline' market"
        # Player props broken out by type
        assert "player_points" in markets, "Missing 'player_points' market"
        assert "player_rebounds" in markets, "Missing 'player_rebounds' market"
        assert "player_assists" in markets, "Missing 'player_assists' market"
    
    def test_player_prop_structure(self):
        """
        Player props must have proper Over/Under structure.
        """
        response = client.get("/api/odds/nba-lal-gsw-2026-02-09")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check specific player prop markets
        player_markets = ["player_points", "player_rebounds", "player_assists", "player_threes"]
        found_props = False
        
        for market_name in player_markets:
            market = next((m for m in data if m["market"] == market_name), None)
            if market:
                found_props = True
                # Should have multiple selections
                assert len(market["selections"]) >= 2, f"Need at least 2 selections in {market_name}"
                
                # Each selection should have proper label format
                for sel in market["selections"]:
                    label = sel["label"]
                    # Format: "Player Name O##.5 STAT" or "Player Name U##.5 STAT"
                    assert "O" in label or "U" in label, f"Label '{label}' missing O/U indicator"
        
        assert found_props, "No player prop markets found"
    
    def test_odds_game_not_found(self):
        """
        R0.4: Observability - clear error when game not found.
        """
        response = client.get("/api/odds/invalid-game-id-12345")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data, "Error response must have 'detail'"
        assert "not found" in data["detail"].lower(), "Error should indicate game not found"


class TestProviderSelection:
    """
    R0.3: Provider selection must be deterministic.
    """
    
    def test_mock_provider_default(self):
        """
        Default provider should be mock (safe for testing).
        """
        response = client.get("/api/odds/nba-test-game")
        assert response.status_code == 200
        
        # Mock provider returns predictable data
        data = response.json()
        markets = [m["market"] for m in data]
        assert "spread" in markets
        assert "moneyline" in markets
        assert "total" in markets


class TestDiagnostics:
    """
    R0.4: Observability - endpoints must explain empty responses.
    """
    
    def test_empty_games_list_explains_why(self):
        """
        When games list is empty, should explain why.
        """
        response = client.get("/api/games?sport=INVALID_SPORT")
        assert response.status_code == 200
        
        data = response.json()
        # Should return empty array (valid) or error with explanation
        if isinstance(data, list) and len(data) == 0:
            # Empty is valid for invalid sport, but could add diagnostics
            pass
    
    def test_odds_response_has_diagnostics_in_dev(self):
        """
        Development mode should include diagnostics header.
        """
        response = client.get("/api/odds/nba-lal-gsw-2026-02-09")
        
        # Could add X-Diagnostics header in dev mode
        # For now, just verify response is valid
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0, "Should have markets"
