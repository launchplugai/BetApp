"""
Tests for Bet DNA Receipts (S21-E).

Tests that:
- Bets record DNA snapshot at creation time
- Bet history returns DNA info
- Applied constraints are recorded
- Blocked actions are recorded
- Risk profile at bet time is captured
- Edge cases are handled
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime

from app.main import app
from app.models import User, Bet, get_session
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
        balance=100000
    )
    return user


@pytest.fixture
def mock_preferences():
    """Create mock user preferences."""
    prefs = UserPreferences(
        id="pref_test123",
        user_id="user_test123",
        risk_profile="conservative",
        bet_style=["props", "parlays"],
        constraints={
            "max_legs": 3,
            "no_unders": True,
            "max_correlated_legs": 2,
            "favorite_sports": ["NBA", "NFL"],
            "min_odds": 1.5,
            "max_odds": 10.0,
            "avoid_teams": ["Lakers", "Cowboys"],
            "avoid_players": ["LeBron James"]
        },
        bankroll_policy={
            "unit_size_percent": 2.0,
            "max_units_per_bet": 5.0
        }
    )
    return prefs


class TestBetRecordsDNASnapshot:
    """Tests that bets record DNA snapshot at creation time."""
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_creates_dna_snapshot(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Creating a bet should create a DNA snapshot."""
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = mock_preferences
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        captured_snapshot = {}
        
        def mock_add(obj):
            if isinstance(obj, UserDnaSnapshot):
                captured_snapshot['snapshot'] = obj
                obj.id = "snapshot_test123"
        
        mock_db.add.side_effect = mock_add
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        bet_request = {
            "input_text": "Warriors ML",
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
        
        # Verify snapshot was created with user preferences
        assert 'snapshot' in captured_snapshot
        snapshot = captured_snapshot['snapshot']
        assert snapshot.user_id == mock_user.id
        assert snapshot.preferences is not None
        assert snapshot.preferences.get("risk_profile") == "conservative"
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_links_to_snapshot(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Bet should be linked to the created DNA snapshot."""
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = mock_preferences
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        captured_bet = {}
        
        def mock_add(obj):
            if isinstance(obj, Bet):
                captured_bet['bet'] = obj
                obj.id = "bet_test123"
        
        mock_db.add.side_effect = mock_add
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        bet_request = {
            "input_text": "Warriors ML",
            "legs": [{"entity": "Warriors", "market": "moneyline", "odds": 150, "selection": "Warriors"}],
            "wager": 1000
        }
        
        response = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        
        # Verify bet has snapshot ID
        assert 'bet' in captured_bet
        bet = captured_bet['bet']
        assert bet.user_dna_snapshot_id is not None
        assert bet.risk_profile_at_bet == "conservative"
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_without_preferences_no_snapshot(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet without user preferences should not create snapshot but still succeed."""
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = None  # No preferences
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        captured_bet = {}
        
        def mock_add(obj):
            if isinstance(obj, Bet):
                captured_bet['bet'] = obj
                obj.id = "bet_test123"
        
        mock_db.add.side_effect = mock_add
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        bet_request = {
            "input_text": "Warriors ML",
            "legs": [{"entity": "Warriors", "market": "moneyline", "odds": 150, "selection": "Warriors"}],
            "wager": 1000
        }
        
        response = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Bet should succeed
        assert data["success"] == True


class TestAppliedConstraintsRecording:
    """Tests that applied constraints are recorded with the bet."""
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_records_applied_constraints(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Bet should record which constraints were applied."""
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = mock_preferences
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        captured_bet = {}
        
        def mock_add(obj):
            if isinstance(obj, Bet):
                captured_bet['bet'] = obj
                obj.id = "bet_test123"
        
        mock_db.add.side_effect = mock_add
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        bet_request = {
            "input_text": "Warriors ML",
            "legs": [{"entity": "Warriors", "market": "moneyline", "odds": 150, "selection": "Warriors"}],
            "wager": 1000
        }
        
        response = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        
        # Verify bet has applied constraints
        assert 'bet' in captured_bet
        bet = captured_bet['bet']
        assert isinstance(bet.applied_constraints, list)
        
        # Check specific constraints are recorded
        constraint_types = [c.get("type") for c in bet.applied_constraints]
        assert "max_legs" in constraint_types
        assert "no_unders" in constraint_types
        assert "max_correlated_legs" in constraint_types
        assert "favorite_sports" in constraint_types
        assert "avoid_teams" in constraint_types
        assert "avoid_players" in constraint_types
        assert "odds_range" in constraint_types
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_applied_constraints_include_values(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Applied constraints should include the constraint values."""
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = mock_preferences
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        captured_bet = {}
        
        def mock_add(obj):
            if isinstance(obj, Bet):
                captured_bet['bet'] = obj
                obj.id = "bet_test123"
        
        mock_db.add.side_effect = mock_add
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        bet_request = {
            "input_text": "Warriors ML",
            "legs": [{"entity": "Warriors", "market": "moneyline", "odds": 150, "selection": "Warriors"}],
            "wager": 1000
        }
        
        response = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        
        bet = captured_bet['bet']
        max_legs_constraint = next(
            (c for c in bet.applied_constraints if c["type"] == "max_legs"), 
            None
        )
        assert max_legs_constraint is not None
        assert max_legs_constraint["value"] == 3


class TestBlockedActionsRecording:
    """Tests that blocked actions are recorded with the bet."""
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_records_blocked_actions(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Bet should record blocked actions from constraint violations."""
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = mock_preferences
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        captured_bet = {}
        
        def mock_add(obj):
            if isinstance(obj, Bet):
                captured_bet['bet'] = obj
                obj.id = "bet_test123"
        
        mock_db.add.side_effect = mock_add
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        # Bet with violations
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
        
        bet = captured_bet['bet']
        assert isinstance(bet.blocked_actions, list)
        
        # Should have blocked under bet
        blocked_types = [b.get("action") for b in bet.blocked_actions]
        assert "no_unders" in blocked_types


class TestRiskProfileCapture:
    """Tests that risk profile at bet time is captured."""
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_captures_risk_profile(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Bet should capture the user's risk profile at bet time."""
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = mock_preferences
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        captured_bet = {}
        
        def mock_add(obj):
            if isinstance(obj, Bet):
                captured_bet['bet'] = obj
                obj.id = "bet_test123"
        
        mock_db.add.side_effect = mock_add
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        bet_request = {
            "input_text": "Warriors ML",
            "legs": [{"entity": "Warriors", "market": "moneyline", "odds": 150, "selection": "Warriors"}],
            "wager": 1000
        }
        
        response = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        
        bet = captured_bet['bet']
        assert bet.risk_profile_at_bet == "conservative"
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_uses_default_risk_profile(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet should use default risk profile when user has no preferences."""
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = None
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        captured_bet = {}
        
        def mock_add(obj):
            if isinstance(obj, Bet):
                captured_bet['bet'] = obj
                obj.id = "bet_test123"
        
        mock_db.add.side_effect = mock_add
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        bet_request = {
            "input_text": "Warriors ML",
            "legs": [{"entity": "Warriors", "market": "moneyline", "odds": 150, "selection": "Warriors"}],
            "wager": 1000
        }
        
        response = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        
        bet = captured_bet['bet']
        assert bet.risk_profile_at_bet == "balanced"  # Default


class TestBetHistoryReturnsDNAInfo:
    """Tests that bet history returns DNA receipt information."""
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_history_returns_dna_snapshot_id(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet history should include DNA snapshot IDs."""
        mock_get_user.return_value = mock_user
        
        mock_bet = MagicMock()
        mock_bet.id = "bet_123"
        mock_bet.user_id = mock_user.id
        mock_bet.input_text = "Lakers ML"
        mock_bet.legs = [{"entity": "Lakers", "market": "moneyline"}]
        mock_bet.wager = 1000
        mock_bet.total_odds = 150
        mock_bet.potential_payout = 2500
        mock_bet.status = "pending"
        mock_bet.actual_payout = None
        mock_bet.verdict = "PROCEED"
        mock_bet.confidence = 75
        mock_bet.user_dna_snapshot_id = "snapshot_abc123"
        mock_bet.risk_profile_at_bet = "conservative"
        mock_bet.created_at = datetime.utcnow()
        mock_bet.settled_at = None
        
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
        assert data["bets"][0]["risk_profile_at_bet"] == "conservative"
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_detail_returns_full_dna_info(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet detail should return full DNA receipt info."""
        mock_get_user.return_value = mock_user
        
        # Mock bet with proper to_dict method
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
        mock_bet.applied_constraints = [
            {"type": "max_legs", "value": 3, "enforced": True},
            {"type": "no_unders", "value": True, "enforced": True}
        ]
        mock_bet.blocked_actions = []
        mock_bet.risk_profile_at_bet = "conservative"
        mock_bet.created_at = datetime.utcnow()
        mock_bet.settled_at = None
        # Set up to_dict to return a dict with all the DNA fields
        mock_bet.to_dict.return_value = {
            "id": "bet_123",
            "user_id": mock_user.id,
            "input_text": "Lakers ML",
            "legs": [{"entity": "Lakers", "market": "moneyline"}],
            "wager": 1000,
            "total_odds": 150,
            "potential_payout": 2500,
            "status": "pending",
            "actual_payout": None,
            "verdict": "PROCEED",
            "confidence": 75,
            "fragility": None,
            "user_dna_snapshot_id": "snapshot_abc123",
            "applied_constraints": [
                {"type": "max_legs", "value": 3, "enforced": True},
                {"type": "no_unders", "value": True, "enforced": True}
            ],
            "blocked_actions": [],
            "risk_profile_at_bet": "conservative",
            "created_at": datetime.utcnow().isoformat(),
            "settled_at": None
        }
        
        # Mock snapshot
        mock_snapshot = MagicMock()
        mock_snapshot.id = "snapshot_abc123"
        mock_snapshot.preferences = {
            "risk_profile": "conservative",
            "constraints": {"max_legs": 3}
        }
        mock_snapshot.created_at = datetime.utcnow()
        
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
        assert data["risk_profile_at_bet"] == "conservative"
        assert data["applied_constraints"] == [
            {"type": "max_legs", "value": 3, "enforced": True},
            {"type": "no_unders", "value": True, "enforced": True}
        ]
        assert "dna_snapshot" in data
        assert data["dna_snapshot"]["preferences"]["risk_profile"] == "conservative"


class TestEdgeCases:
    """Tests for edge cases."""
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_with_empty_constraints(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet with user having empty constraints should still work."""
        prefs = UserPreferences(
            id="pref_test123",
            user_id="user_test123",
            risk_profile="balanced",
            bet_style=["props"],
            constraints={},
            bankroll_policy={}
        )
        
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = prefs
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        captured_bet = {}
        
        def mock_add(obj):
            if isinstance(obj, Bet):
                captured_bet['bet'] = obj
                obj.id = "bet_test123"
        
        mock_db.add.side_effect = mock_add
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        bet_request = {
            "input_text": "Warriors ML",
            "legs": [{"entity": "Warriors", "market": "moneyline", "odds": 150, "selection": "Warriors"}],
            "wager": 1000
        }
        
        response = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        assert response.json()["success"] == True
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_bet_detail_without_snapshot(self, mock_get_session, mock_get_user, client, mock_user):
        """Bet detail without snapshot should work gracefully."""
        mock_get_user.return_value = mock_user
        
        mock_bet = MagicMock()
        mock_bet.id = "bet_123"
        mock_bet.user_id = mock_user.id
        mock_bet.input_text = "Lakers ML"
        mock_bet.legs = []
        mock_bet.wager = 1000
        mock_bet.total_odds = 150
        mock_bet.potential_payout = 2500
        mock_bet.status = "pending"
        mock_bet.verdict = None
        mock_bet.confidence = None
        mock_bet.user_dna_snapshot_id = None  # No snapshot
        mock_bet.applied_constraints = []
        mock_bet.blocked_actions = []
        mock_bet.risk_profile_at_bet = None
        mock_bet.created_at = datetime.utcnow()
        mock_bet.settled_at = None
        mock_bet.to_dict.return_value = {
            "id": "bet_123",
            "user_id": mock_user.id,
            "user_dna_snapshot_id": None,
            "applied_constraints": [],
            "blocked_actions": [],
            "risk_profile_at_bet": None
        }
        
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_bet
        mock_db.query.return_value = mock_query
        mock_get_session.return_value = mock_db
        
        response = client.get(
            "/api/bets/bet_123",
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_dna_snapshot_id"] is None
        assert "dna_snapshot" not in data  # Should not include snapshot if none exists
    
    @patch('app.routers.bets.get_current_user_from_token')
    @patch('app.routers.bets.get_session')
    def test_multiple_bets_same_session(self, mock_get_session, mock_get_user, client, mock_user, mock_preferences):
        """Multiple bets in same session should each get their own snapshot."""
        mock_get_user.return_value = mock_user
        
        mock_db = MagicMock()
        mock_prefs_query = MagicMock()
        mock_prefs_query.filter_by.return_value.first.return_value = mock_preferences
        
        mock_bet_query = MagicMock()
        mock_bet_query.filter.return_value.first.return_value = None
        
        snapshots_created = []
        
        def mock_add(obj):
            if isinstance(obj, UserDnaSnapshot):
                obj.id = f"snapshot_{len(snapshots_created)}"
                snapshots_created.append(obj)
        
        mock_db.add.side_effect = mock_add
        
        def mock_query_side_effect(model):
            if model == UserPreferences:
                return mock_prefs_query
            return mock_bet_query
        
        mock_db.query.side_effect = mock_query_side_effect
        mock_get_session.return_value = mock_db
        
        bet_request = {
            "input_text": "Warriors ML",
            "legs": [{"entity": "Warriors", "market": "moneyline", "odds": 150, "selection": "Warriors"}],
            "wager": 1000
        }
        
        # Create two bets
        response1 = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        response2 = client.post(
            "/api/bets/",
            json=bet_request,
            headers={"Authorization": "Bearer valid_token"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Each bet should create its own snapshot
        assert len(snapshots_created) == 2
        assert snapshots_created[0].id != snapshots_created[1].id
