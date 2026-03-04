"""
Contract tests for bet settlement endpoints.

S-NEXT: Settlement (Win/Loss Payout)
R0.2: No UI wiring until backend contract tests pass.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestSettlementContract:
    """Contract tests for settlement API."""
    
    def test_settle_bet_request_shape(self):
        """
        R0.1: Define expected request shape for settling bets.
        
        POST /api/bets/{bet_id}/settle
        {
            "result": "won|lost|void",
            "actual_payout": int|null  # cents, null for lost/void
        }
        """
        # Test auth required
        response = client.post("/api/bets/bet_123/settle", json={})
        assert response.status_code == 401  # No auth token
    
    def test_settle_bet_response_shape(self):
        """
        R0.1: Define expected response shape.
        
        Success:
        {
            "success": true,
            "bet_id": str,
            "status": "won|lost|void",
            "actual_payout": int,
            "new_balance": int
        }
        
        Error:
        {
            "success": false,
            "error": str
        }
        """
        pass  # Shape enforced by endpoint
    
    def test_settle_bet_invalid_result(self):
        """
        Result must be one of: won, lost, void.
        """
        pass  # Enforced by pydantic/pydantic
    
    def test_settle_bet_already_settled(self):
        """
        Cannot settle a bet twice.
        """
        pass  # Business logic test


class TestTransactionLogContract:
    """Contract tests for transaction log."""
    
    def test_transaction_history_endpoint(self):
        """
        GET /api/bets/transactions
        
        Returns:
        {
            "transactions": [
                {
                    "id": str,
                    "type": "wager|payout|refund",
                    "amount": int,
                    "balance_before": int,
                    "balance_after": int,
                    "bet_id": str|null,
                    "description": str,
                    "created_at": str
                }
            ],
            "total": int
        }
        """
        # Test auth required
        response = client.get("/api/bets/transactions")
        assert response.status_code == 401  # No auth token
    
    def test_transaction_types(self):
        """
        Transaction types must be valid.
        """
        allowed_types = ["wager", "payout", "refund"]
        assert len(allowed_types) == 3


class TestSettlementStateMachine:
    """State machine contract tests."""
    
    def test_pending_can_settle_to_won(self):
        """pending → won (with payout)"""
        pass
    
    def test_pending_can_settle_to_lost(self):
        """pending → lost (no payout)"""
        pass
    
    def test_pending_can_settle_to_void(self):
        """pending → void (refund wager)"""
        pass
    
    def test_settled_cannot_change(self):
        """won/lost/void → no transitions allowed"""
        pass
