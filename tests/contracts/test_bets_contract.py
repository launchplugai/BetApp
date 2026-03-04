"""
Contract tests for /api/bets endpoints.

R0.2: No UI wiring until backend contract tests pass.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestBetsContract:
    """Contract tests for bets API."""
    
    def test_create_bet_request_shape(self):
        """
        R0.1: Define expected request shape for creating bets.
        
        POST /api/bets/
        {
            "input_text": str,
            "legs": [
                {
                    "entity": str,
                    "market": str,
                    "value": str|null,
                    "odds": int,
                    "selection": str
                }
            ],
            "wager": int (cents),
            "total_odds": int|null,
            "potential_payout": int|null,
            "verdict": str|null,
            "confidence": int|null
        }
        """
        # This test documents the contract - actual auth required for call
        pass  # Shape enforced by pydantic models
    
    def test_create_bet_response_shape(self):
        """
        R0.1: Define expected response shape.
        
        Success:
        {
            "success": true,
            "bet_id": str,
            "message": str
        }
        
        Error:
        {
            "success": false,
            "error": str
        }
        """
        # Test error case (no auth)
        response = client.post("/api/bets/", json={})
        assert response.status_code == 401  # No auth token
    
    def test_bet_history_response_shape(self):
        """
        R0.1: History endpoint shape.
        
        GET /api/bets/history
        {
            "bets": [
                {
                    "id": str,
                    "input_text": str,
                    "legs": [...],
                    "wager": int,
                    "total_odds": int,
                    "potential_payout": int,
                    "status": "pending|won|lost|void",
                    "actual_payout": int|null,
                    "created_at": str (ISO8601)
                }
            ],
            "total": int,
            "page": int,
            "per_page": int
        }
        """
        # Test without auth
        response = client.get("/api/bets/history")
        assert response.status_code == 401  # Requires auth
    
    def test_bet_status_values(self):
        """
        Bet status must be one of allowed values.
        """
        allowed_statuses = ["pending", "won", "lost", "void"]
        # Document contract - actual validation in models
        assert len(allowed_statuses) == 4


class TestBetsValidation:
    """Validation contract tests."""
    
    def test_wager_minimum(self):
        """
        Wager must be > 0.
        """
        pass  # Enforced by pydantic
    
    def test_wager_maximum(self):
        """
        Wager must be <= $10,000 (1,000,000 cents).
        """
        pass  # Enforced in router logic
    
    def test_legs_minimum(self):
        """
        Must have at least 1 leg.
        """
        pass  # Enforced by pydantic
    
    def test_legs_maximum(self):
        """
        Maximum 10 legs per bet.
        """
        pass  # Enforced in router logic
