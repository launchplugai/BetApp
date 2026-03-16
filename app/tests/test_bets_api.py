"""Tests for bets history API (S18-D)."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError

from app.main import app
from app.models import User, Bet, get_session, init_db


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create mock user for testing."""
    user = User(
        id="user_test123",
        email="test@example.com",
        password_hash="hashed_password",
        name="Test User",
        tier="GOOD",
        balance=100000,
    )
    return user


@pytest.fixture
def mock_token():
    """Mock JWT token."""
    return "mock_jwt_token_12345"


@pytest.fixture
def db_session():
    """Create test database session."""
    init_db()
    session = get_session()
    yield session
    session.close()


class TestBetHistoryEndpoint:
    """Tests for GET /api/bets/history endpoint."""

    @patch('app.routers.bets.get_current_user_from_token')
    def test_history_requires_auth(self, mock_get_user, client):
        """History endpoint requires authentication."""
        mock_get_user.return_value = None
        
        response = client.get(
            "/api/bets/history",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid or expired token" in response.json()["detail"]

    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_history_returns_empty_for_new_user(self, mock_get_session, mock_get_user, client, mock_user):
        """History returns empty list for user with no bets."""
        mock_get_user.return_value = mock_user
        
        # Mock database session
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query
        mock_get_session.return_value = mock_db
        
        response = client.get(
            "/api/bets/history",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["bets"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["per_page"] == 10

    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_history_returns_bets_with_pagination(self, mock_get_session, mock_get_user, client, mock_user):
        """History returns paginated bets."""
        mock_get_user.return_value = mock_user
        
        # Mock bet
        mock_bet = Bet(
            id="bet_123",
            user_id=mock_user.id,
            input_text="Lakers ML + Warriors spread",
            legs=[
                {"entity": "Lakers", "market": "moneyline", "value": None, "odds": -150},
                {"entity": "Warriors", "market": "spread", "value": "-5.5", "odds": -110}
            ],
            wager=10000,  # $100.00 in cents
            total_odds=275,
            potential_payout=27500,
            status="pending",
            verdict="PROCEED WITH CAUTION",
            confidence=65
        )
        
        # Mock database session
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_bet]
        mock_db.query.return_value = mock_query
        mock_get_session.return_value = mock_db
        
        response = client.get(
            "/api/bets/history",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["bets"]) == 1
        assert data["bets"][0]["id"] == "bet_123"
        assert data["bets"][0]["status"] == "pending"
        assert data["bets"][0]["confidence"] == 65
        assert data["bets"][0]["inputText"] == "Lakers ML + Warriors spread"
        assert data["bets"][0]["evaluationId"] is None
        assert data["total"] == 1

    @patch('app.routers.bets.get_current_user_from_token')
    def test_history_supports_status_filter(self, mock_get_user, client, mock_user):
        """History endpoint accepts status filter."""
        mock_get_user.return_value = mock_user
        
        response = client.get(
            "/api/bets/history?status=won",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        # Should not error, even if no bets match
        assert response.status_code == 200

    @patch('app.routers.bets.get_current_user_from_token')
    def test_history_supports_pagination_params(self, mock_get_user, client, mock_user):
        """History endpoint accepts page and per_page params."""
        mock_get_user.return_value = mock_user
        
        response = client.get(
            "/api/bets/history?page=2&per_page=5",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["per_page"] == 5


class TestBetDetailEndpoint:
    """Tests for GET /api/bets/{bet_id} endpoint."""

    @patch('app.routers.bets.get_current_user_from_token')
    def test_bet_detail_requires_auth(self, mock_get_user, client):
        """Bet detail endpoint requires authentication."""
        mock_get_user.return_value = None
        
        response = client.get(
            "/api/bets/bet_123",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401

    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_detail_returns_404_for_nonexistent(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet detail returns 404 for non-existent bet."""
        mock_get_user.return_value = mock_user
        
        # Mock database session returning None
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query
        mock_get_session.return_value = mock_db
        
        response = client.get(
            "/api/bets/nonexistent_bet",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_detail_returns_bet_data(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet detail returns full bet data."""
        mock_get_user.return_value = mock_user
        
        # Mock bet
        mock_bet = Bet(
            id="bet_123",
            user_id=mock_user.id,
            input_text="Lakers ML",
            legs=[{"entity": "Lakers", "market": "moneyline"}],
            wager=5000,
            status="won",
            actual_payout=9500
        )
        
        # Mock database session
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_bet
        mock_db.query.return_value = mock_query
        mock_get_session.return_value = mock_db
        
        response = client.get(
            "/api/bets/bet_123",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "bet_123"
        assert data["status"] == "won"
        assert data["wager"] == 5000
        assert data["actual_payout"] == 9500

    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_detail_includes_replay_payload(self, mock_get_session, mock_get_user, client, mock_user):
        """Persisted bet detail exposes additive replay context for the new frontend."""
        mock_get_user.return_value = mock_user

        mock_bet = Bet(
            id="bet_456",
            user_id=mock_user.id,
            evaluation_id="eval_456",
            input_text="Lakers ML + Celtics ML",
            legs=[{"entity": "Lakers", "market": "moneyline"}],
            wager=5000,
            status="pending",
            verdict="Fixable",
            confidence=63,
        )

        mock_eval_record = MagicMock()
        mock_eval_record.meta = {"tier": "better"}
        mock_eval_record.recommendation_details = {
            "primary_failure": {
                "type": "stacked_risk",
                "fastestFix": {"action": "trim_legs", "description": "Cut one leg"},
            }
        }
        mock_eval_record.triggered_protocols = ["schedule_check"]

        mock_db = MagicMock()
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value = mock_bet_query
        mock_bet_query.first.return_value = mock_bet

        mock_eval_query = MagicMock()
        mock_eval_query.filter.return_value = mock_eval_query
        mock_eval_query.first.return_value = mock_eval_record

        def mock_query_side_effect(model):
            model_name = getattr(model, "__name__", "")
            if model_name == "Bet":
                return mock_bet_query
            if model_name == "EvaluationLog":
                return mock_eval_query
            fallback_query = MagicMock()
            fallback_query.filter_by.return_value.first.return_value = None
            return fallback_query

        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db

        response = client.get(
            "/api/bets/bet_456",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["evaluationId"] == "eval_456"
        assert data["replay"]["evaluationId"] == "eval_456"
        assert data["replay"]["builderHandoff"]["inputText"] == "Lakers ML + Celtics ML"
        assert data["replay"]["builderHandoff"]["fastestFix"]["action"] == "trim_legs"
        assert data["replay"]["triggeredProtocols"] == ["schedule_check"]

    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_detail_survives_missing_evaluation_log_table(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet detail should still work when evaluation log enrichment is unavailable."""
        mock_get_user.return_value = mock_user

        mock_bet = Bet(
            id="bet_789",
            user_id=mock_user.id,
            evaluation_id="eval_789",
            input_text="Knicks ML",
            legs=[{"entity": "Knicks", "market": "moneyline"}],
            wager=2500,
            status="pending",
            verdict="Stored bet",
            confidence=52,
        )

        mock_db = MagicMock()
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value = mock_bet_query
        mock_bet_query.first.return_value = mock_bet

        mock_eval_query = MagicMock()
        mock_eval_query.filter.side_effect = OperationalError("select", {}, Exception("missing table"))

        def mock_query_side_effect(model):
            model_name = getattr(model, "__name__", "")
            if model_name == "Bet":
                return mock_bet_query
            if model_name == "EvaluationLog":
                return mock_eval_query
            fallback_query = MagicMock()
            fallback_query.filter_by.return_value.first.return_value = None
            return fallback_query

        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db

        response = client.get(
            "/api/bets/bet_789",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["evaluationId"] == "eval_789"
        assert data["replay"]["evaluationId"] == "eval_789"
        assert data["replay"]["signalInfo"]["source"] == "bet_fallback"
        assert data["replay"]["signalInfo"]["isDerivedFallback"] is True


class TestBetCreateEndpoint:
    """Tests for POST /api/bets/ endpoint."""

    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_create_bet_returns_evaluation_id(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet creation should persist and return explicit evaluation linkage."""
        mock_get_user.return_value = mock_user

        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = None

        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None

        captured_bet = {}

        def mock_add(obj):
            if isinstance(obj, Bet):
                captured_bet["bet"] = obj
                obj.id = "bet_eval_123"

        def mock_query_side_effect(model):
            model_name = getattr(model, "__name__", "")
            if model_name == "UserPreferences":
                return mock_prefs_query
            return mock_bet_query

        mock_db.add.side_effect = mock_add
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db

        response = client.post(
            "/api/bets/",
            json={
                "input_text": "Warriors ML",
                "evaluation_id": "eval_123",
                "legs": [
                    {"entity": "Warriors", "market": "moneyline", "odds": 150, "selection": "Warriors"}
                ],
                "wager": 1000,
            },
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["evaluation_id"] == "eval_123"
        assert captured_bet["bet"].evaluation_id == "eval_123"


class TestBetHistoryResponseContract:
    """Tests for API response contract compliance."""

    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_history_response_schema(self, mock_get_session, mock_get_user, client, mock_user):
        """History response matches expected schema."""
        mock_get_user.return_value = mock_user
        
        # Mock database
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query
        mock_get_session.return_value = mock_db
        
        response = client.get(
            "/api/bets/history",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        data = response.json()
        
        # Validate schema
        assert "bets" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert isinstance(data["bets"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["per_page"], int)

    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_history_includes_evaluation_id_when_present(self, mock_get_session, mock_get_user, client, mock_user):
        """History responses should expose evaluation linkage."""
        mock_get_user.return_value = mock_user

        mock_bet = Bet(
            id="bet_123",
            user_id=mock_user.id,
            evaluation_id="eval_hist_123",
            input_text="Warriors ML",
            legs=[{"entity": "Warriors", "market": "moneyline", "value": None, "odds": 150}],
            wager=1000,
            total_odds=150,
            potential_payout=2500,
            status="pending",
            verdict="PROCEED",
            confidence=72,
        )

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_bet]
        mock_db.query.return_value = mock_query
        mock_get_session.return_value = mock_db

        response = client.get(
            "/api/bets/history",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["bets"][0]["evaluation_id"] == "eval_hist_123"
