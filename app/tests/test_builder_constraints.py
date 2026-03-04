"""
Integration tests for builder constraints API (S21-D).

Tests API endpoints with constraints:
- Constraint checking endpoint
- Constraint violations returned correctly
- Bet submission with constraints
- Bet history with DNA receipts
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.main import app
from app.models import User, Bet, get_session, init_db
from app.models.user_preferences import UserPreferences
from app.models.user_dna_snapshot import UserDnaSnapshot


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
        balance=100000  # $1000 in cents
    )
    return user


@pytest.fixture
def mock_preferences():
    """Create mock user preferences with constraints."""
    prefs = UserPreferences(
        id="pref_test123",
        user_id="user_test123",
        risk_profile="balanced",
        bet_style=["props"],
        constraints={
            "max_legs": 2,
            "no_unders": True,
            "max_correlated_legs": 1,
            "favorite_sports": ["NBA"],
            "min_odds": 1.5,
            "max_odds": 5.0,
            "avoid_teams": ["Lakers"],
            "avoid_players": ["LeBron James"]
        },
        bankroll_policy={
            "unit_size_percent": 1.0,
            "max_units_per_bet": 3.0
        }
    )
    return prefs


class TestPreferencesCheckEndpoint:
    """Tests for POST /api/preferences/check endpoint."""
    
    @patch('app.routers.preferences.get_current_user_id')
    @patch('app.routers.preferences.get_session')
    def test_check_constraints_returns_violations(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Check endpoint should return constraint violations."""
        mock_get_user.return_value = mock_user.id
        
        # Mock database session
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_preferences
        mock_get_session.return_value = mock_db
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "sport": "NBA"},
            {"entity": "Warriors", "market": "spread", "sport": "NBA"},
            {"entity": "Celtics", "market": "total", "sport": "NBA"}  # Exceeds max_legs
        ]
        
        response = client.post(
            "/api/preferences/check",
            json=picks,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "violations" in data
        assert data["violation_count"] > 0
        assert data["has_warnings"] == True
    
    @patch('app.routers.preferences.get_current_user_id')
    @patch('app.routers.preferences.get_session')
    def test_check_constraints_detects_no_unders(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Check endpoint should detect under bet violations."""
        mock_get_user.return_value = mock_user.id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_preferences
        mock_get_session.return_value = mock_db
        
        picks = [
            {"entity": "Lakers", "market": "total", "selection": "Under 220.5", "sport": "NBA"}
        ]
        
        response = client.post(
            "/api/preferences/check",
            json=picks,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        violation_types = [v["constraint_type"] for v in data["violations"]]
        assert "no_unders" in violation_types
    
    @patch('app.routers.preferences.get_current_user_id')
    @patch('app.routers.preferences.get_session')
    def test_check_constraints_detects_avoided_teams(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Check endpoint should detect avoided team violations."""
        mock_get_user.return_value = mock_user.id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_preferences
        mock_get_session.return_value = mock_db
        
        picks = [
            {"entity": "Lakers", "market": "moneyline", "selection": "Lakers to win", "sport": "NBA"}
        ]
        
        response = client.post(
            "/api/preferences/check",
            json=picks,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        violation_types = [v["constraint_type"] for v in data["violations"]]
        assert "avoid_teams" in violation_types
    
    @patch('app.routers.preferences.get_current_user_id')
    @patch('app.routers.preferences.get_session')
    def test_check_constraints_uses_defaults_when_no_prefs(self, mock_get_session, mock_get_user, client, mock_user):
        """Check endpoint should use defaults when user has no preferences."""
        mock_get_user.return_value = mock_user.id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value = mock_db
        
        picks = [
            {"entity": "Lakers", "market": "moneyline"}
        ]
        
        response = client.post(
            "/api/preferences/check",
            json=picks,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "violations" in data
        assert "preferences_summary" in data
        assert data["preferences_summary"]["risk_profile"] == "balanced"
    
    @patch('app.routers.preferences.get_current_user_id')
    @patch('app.routers.preferences.get_session')
    def test_check_constraints_returns_summary(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Check endpoint should return preferences summary."""
        mock_get_user.return_value = mock_user.id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_preferences
        mock_get_session.return_value = mock_db
        
        picks = [{"entity": "Lakers", "market": "moneyline"}]
        
        response = client.post(
            "/api/preferences/check",
            json=picks,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "preferences_summary" in data
        assert data["preferences_summary"]["risk_profile"] == "balanced"
        assert data["preferences_summary"]["max_legs"] == 2


class TestPreferencesSummaryEndpoint:
    """Tests for GET /api/preferences/summary endpoint."""
    
    @patch('app.routers.preferences.get_current_user_id')
    @patch('app.routers.preferences.get_session')
    def test_summary_returns_constraints(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Summary endpoint should return active constraints."""
        mock_get_user.return_value = mock_user.id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_preferences
        mock_get_session.return_value = mock_db
        
        response = client.get(
            "/api/preferences/summary",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_preferences"] == True
        assert "summary" in data
        assert data["summary"]["max_legs"] == 2
        assert data["summary"]["no_unders"] == True
    
    @patch('app.routers.preferences.get_current_user_id')
    @patch('app.routers.preferences.get_session')
    def test_summary_returns_defaults_when_no_prefs(self, mock_get_session, mock_get_user, client, mock_user):
        """Summary endpoint should return defaults when no preferences exist."""
        mock_get_user.return_value = mock_user.id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value = mock_db
        
        response = client.get(
            "/api/preferences/summary",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["has_preferences"] == False
        assert "Using default preferences" in data["message"]


class TestBetSubmissionWithConstraints:
    """Tests for bet submission with constraint checking."""
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_create_bet_records_dna_snapshot(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Bet creation should record DNA snapshot."""
        mock_get_user.return_value = mock_user
        
        # Mock database session with chainable queries
        mock_db = MagicMock()
        
        # Setup query chain for UserPreferences
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = mock_preferences
        
        # Setup query chain for Bet
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None  # For balance check
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        bet_request = {
            "input_text": "Lakers ML",
            "legs": [
                {"entity": "Warriors", "market": "moneyline", "odds": 150, "selection": "Warriors"}
            ],
            "wager": 1000
        }
        
        response = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include DNA snapshot info
        assert "dna_snapshot_id" in data
        assert "risk_profile" in data
        assert data["risk_profile"] == "balanced"
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_create_bet_returns_constraint_violations(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Bet creation should return constraint violations if any."""
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = mock_preferences
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        # Bet with under selection (violates no_unders)
        bet_request = {
            "input_text": "Lakers Under",
            "legs": [
                {"entity": "Lakers", "market": "total", "odds": -110, "selection": "Under 220.5"}
            ],
            "wager": 1000
        }
        
        response = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include constraint violations
        assert "constraint_violations" in data
        if data["constraint_violations"]:
            violation_types = [v["constraint_type"] for v in data["constraint_violations"]]
            assert "no_unders" in violation_types


class TestBetHistoryWithDNA:
    """Tests for bet history with DNA receipt info."""
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_history_includes_dna_snapshot_id(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet history should include DNA snapshot IDs."""
        mock_get_user.return_value = mock_user
        
        # Mock bet with DNA snapshot
        mock_bet = MagicMock()
        mock_bet.id = "bet_123"
        mock_bet.user_id = mock_user.id
        mock_bet.input_text = "Lakers ML"
        mock_bet.legs = [{"entity": "Lakers", "market": "moneyline"}]
        mock_bet.wager = 1000
        mock_bet.total_odds = 150
        mock_bet.potential_payout = 2500
        mock_bet.status = "pending"
        mock_bet.verdict = "PROCEED"
        mock_bet.confidence = 75
        mock_bet.user_dna_snapshot_id = "snapshot_abc123"
        mock_bet.risk_profile_at_bet = "balanced"
        mock_bet.created_at = datetime.utcnow()
        mock_bet.settled_at = None
        
        # Mock database
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
        assert data["bets"][0]["user_dna_snapshot_id"] == "snapshot_abc123"
        assert data["bets"][0]["risk_profile_at_bet"] == "balanced"
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_detail_includes_dna_snapshot(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet detail should include full DNA snapshot."""
        mock_get_user.return_value = mock_user
        
        # Mock bet with DNA receipt data
        mock_bet = MagicMock()
        mock_bet.id = "bet_123"
        mock_bet.user_id = mock_user.id
        mock_bet.input_text = "Lakers ML"
        mock_bet.legs = [{"entity": "Lakers", "market": "moneyline"}]
        mock_bet.wager = 1000
        mock_bet.total_odds = 150
        mock_bet.potential_payout = 2500
        mock_bet.status = "pending"
        mock_bet.verdict = "PROCEED"
        mock_bet.confidence = 75
        mock_bet.user_dna_snapshot_id = "snapshot_abc123"
        mock_bet.applied_constraints = [{"type": "max_legs", "value": 3}]
        mock_bet.blocked_actions = []
        mock_bet.risk_profile_at_bet = "balanced"
        mock_bet.created_at = datetime.utcnow()
        mock_bet.settled_at = None
        mock_bet.to_dict.return_value = {
            "id": "bet_123",
            "user_id": mock_user.id,
            "input_text": "Lakers ML",
            "legs": [{"entity": "Lakers", "market": "moneyline"}],
            "wager": 1000,
            "user_dna_snapshot_id": "snapshot_abc123",
            "applied_constraints": [{"type": "max_legs", "value": 3}],
            "blocked_actions": [],
            "risk_profile_at_bet": "balanced"
        }
        
        # Mock snapshot
        mock_snapshot = MagicMock()
        mock_snapshot.id = "snapshot_abc123"
        mock_snapshot.preferences = {
            "risk_profile": "balanced",
            "constraints": {"max_legs": 3}
        }
        mock_snapshot.created_at = datetime.utcnow()
        
        # Mock database
        mock_db = MagicMock()
        
        def mock_query_side_effect(model):
            mock_query = MagicMock()
            if model == Bet:
                mock_query.filter.return_value.first.return_value = mock_bet
            elif model == UserDnaSnapshot:
                mock_query.filter_by.return_value.first.return_value = mock_snapshot
            return mock_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        response = client.get(
            "/api/bets/bet_123",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_dna_snapshot_id"] == "snapshot_abc123"
        assert "dna_snapshot" in data
        assert data["dna_snapshot"]["id"] == "snapshot_abc123"
        assert "preferences" in data["dna_snapshot"]


class TestConstraintViolationsResponseFormat:
    """Tests for constraint violation response format."""
    
    @patch('app.routers.preferences.get_current_user_id')
    @patch('app.routers.preferences.get_session')
    def test_violation_has_required_fields(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Each violation should have required fields."""
        mock_get_user.return_value = mock_user.id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_preferences
        mock_get_session.return_value = mock_db
        
        # Bet that violates max_legs
        picks = [
            {"entity": "A", "market": "ml", "sport": "NBA"},
            {"entity": "B", "market": "ml", "sport": "NBA"},
            {"entity": "C", "market": "ml", "sport": "NBA"}
        ]
        
        response = client.post(
            "/api/preferences/check",
            json=picks,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        for violation in data["violations"]:
            assert "constraint_type" in violation
            assert "message" in violation
            assert "severity" in violation
            assert violation["severity"] in ["info", "warning", "error"]
    
    @patch('app.routers.preferences.get_current_user_id')
    @patch('app.routers.preferences.get_session')
    def test_violation_counts_are_accurate(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Violation count should match actual violations."""
        mock_get_user.return_value = mock_user.id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_preferences
        mock_get_session.return_value = mock_db
        
        picks = [
            {"entity": "Lakers", "market": "total", "selection": "Under 220.5", "sport": "NBA"}
        ]
        
        response = client.post(
            "/api/preferences/check",
            json=picks,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["violation_count"] == len(data["violations"])
    
    @patch('app.routers.preferences.get_current_user_id')
    @patch('app.routers.preferences.get_session')
    def test_has_warnings_flag(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """has_warnings should be true when there are warnings or errors."""
        mock_get_user.return_value = mock_user.id
        
        mock_db = MagicMock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_preferences
        mock_get_session.return_value = mock_db
        
        # Bet with violations
        picks = [
            {"entity": "Lakers", "market": "total", "selection": "Under 220.5", "sport": "NBA"}
        ]
        
        response = client.post(
            "/api/preferences/check",
            json=picks,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that has_warnings matches violations
        has_severe_violations = any(
            v["severity"] in ["warning", "error"] 
            for v in data["violations"]
        )
        assert data["has_warnings"] == has_severe_violations
