"""
Tests for Protocol Observer (S20).
Tests the ProtocolObserver class that watches for opportunities and filters them
through user DNA constraints.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from app.services.protocol_observer import (
    ProtocolObserver, get_protocol_observer
)
from app.services.notification_types import (
    RawOpportunity, OpportunityStatus, OpportunityResult
)


@pytest.fixture
def sample_opportunity():
    """Create a sample raw opportunity."""
    return RawOpportunity(
        protocol_id="nba_ml_v1",
        protocol_source="nba",
        game_id="game_123",
        sport="NBA",
        league="NBA",
        home_team="Lakers",
        away_team="Warriors",
        event_time=datetime.utcnow() + timedelta(hours=2),
        bet_type="moneyline",
        market="game",
        selection="Lakers ML",
        odds=-150,
        odds_decimal=1.67,
        line=None,
        confidence_score=75.0,
        edge_percent=8.5,
        metadata={}
    )


@pytest.fixture
def observer():
    """Create a ProtocolObserver instance."""
    return ProtocolObserver()


class TestProtocolObserverCore:
    """Tests for core ProtocolObserver functionality."""
    
    def test_check_confidence_threshold_pass(self, observer, sample_opportunity):
        """Opportunity with high enough confidence passes."""
        result = observer.check_confidence_threshold(sample_opportunity, min_confidence=70.0)
        assert result is True
    
    def test_check_confidence_threshold_fail(self, observer, sample_opportunity):
        """Opportunity with low confidence fails."""
        sample_opportunity.confidence_score = 50.0
        result = observer.check_confidence_threshold(sample_opportunity, min_confidence=70.0)
        assert result is False
    
    def test_check_confidence_threshold_exact(self, observer, sample_opportunity):
        """Opportunity with exactly threshold confidence passes."""
        sample_opportunity.confidence_score = 70.0
        result = observer.check_confidence_threshold(sample_opportunity, min_confidence=70.0)
        assert result is True
    
    def test_check_misalignment_pass(self, observer, sample_opportunity):
        """Opportunity with acceptable misalignment passes."""
        result = observer.check_misalignment(sample_opportunity, max_misalignment=50.0)
        assert result is True
    
    def test_check_misalignment_fail(self, observer, sample_opportunity):
        """Opportunity with high misalignment fails."""
        sample_opportunity.edge_percent = 60.0
        result = observer.check_misalignment(sample_opportunity, max_misalignment=50.0)
        assert result is False
    
    def test_check_misalignment_no_edge(self, observer, sample_opportunity):
        """Opportunity with no edge data passes."""
        sample_opportunity.edge_percent = None
        result = observer.check_misalignment(sample_opportunity)
        assert result is True


class TestProtocolObserverWatch:
    """Tests for watch_protocol functionality."""
    
    def test_watch_protocol_filters_low_confidence(self, observer, sample_opportunity):
        """Low confidence opportunities are filtered."""
        sample_opportunity.confidence_score = 50.0
        
        results = observer.watch_protocol("nba_ml_v1", [sample_opportunity])
        
        # Should have 1 result (filtered out)
        assert len(results) == 1
        assert results[0].success is False
        assert "below threshold" in results[0].reason
    
    @patch('app.services.protocol_observer.get_session')
    @patch('app.services.protocol_observer.UserPreferences')
    def test_watch_protocol_processes_for_users(self, mock_prefs_cls, mock_get_session, 
                                                 observer, sample_opportunity):
        """Opportunities are processed for all users."""
        # Setup mock session
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        # Setup mock user preferences
        mock_prefs = MagicMock()
        mock_prefs.user_id = "user_123"
        mock_prefs.get_notification_rules.return_value = {
            "enabled": True,
            "opportunity_alerts": {
                "enabled": True,
                "min_confidence": 70,
                "sports": [],
                "bet_types": ["moneyline"]
            }
        }
        mock_session.query.return_value.all.return_value = [mock_prefs]
        
        # Setup mock guardrails to allow
        observer.guardrails.can_notify = Mock(return_value=Mock(
            allowed=True, reason="", remaining_today=9
        ))
        
        # Mock rules engine
        observer.rules_engine.matches_rules = Mock(return_value=Mock(
            matches=True, reason="", matched_criteria=["confidence"]
        ))
        
        results = observer.watch_protocol("nba_ml_v1", [sample_opportunity])
        
        # Should have results
        assert len(results) > 0
    
    def test_watch_multiple_opportunities(self, observer):
        """Multiple opportunities are processed."""
        opps = [
            RawOpportunity(
                protocol_id="nba_ml_v1",
                protocol_source="nba",
                game_id="game_123",
                sport="NBA",
                league="NBA",
                home_team="Lakers",
                away_team="Warriors",
                event_time=datetime.utcnow() + timedelta(hours=2),
                bet_type="moneyline",
                market="game",
                selection="Lakers ML",
                odds=-150,
                odds_decimal=1.67,
                line=None,
                confidence_score=75.0,
                edge_percent=8.5,
                metadata={}
            ),
            RawOpportunity(
                protocol_id="nba_ml_v1",
                protocol_source="nba",
                game_id="game_124",
                sport="NBA",
                league="NBA",
                home_team="Celtics",
                away_team="Heat",
                event_time=datetime.utcnow() + timedelta(hours=3),
                bet_type="spread",
                market="game",
                selection="Celtics -5.5",
                odds=-110,
                odds_decimal=1.91,
                line=-5.5,
                confidence_score=75.0,  # Above threshold
                edge_percent=5.0,
                metadata={}
            )
        ]
        
        results = observer.watch_protocol("nba_ml_v1", opps)
        
        # Should have 2 results (both pass confidence threshold)
        assert len(results) == 2


class TestProtocolObserverHandlers:
    """Tests for handler registration."""
    
    def test_add_handler(self, observer):
        """Handlers can be added."""
        handler = Mock()
        observer.add_handler(handler)
        
        assert handler in observer._handlers
    
    def test_handlers_notified(self, observer, sample_opportunity):
        """Handlers are called when opportunities are created."""
        handler = Mock()
        observer.add_handler(handler)
        
        # Create a mock eligible opportunity
        mock_opp = Mock()
        mock_opp.id = "opp_123"
        
        # Manually notify handlers
        observer._notify_handlers(mock_opp)
        
        handler.assert_called_once_with(mock_opp)


class TestProtocolObserverSingleton:
    """Tests for singleton behavior."""
    
    def test_get_protocol_observer_singleton(self):
        """get_protocol_observer returns same instance."""
        obs1 = get_protocol_observer()
        obs2 = get_protocol_observer()
        
        assert obs1 is obs2
    
    def test_get_protocol_observer_creates_instance(self):
        """get_protocol_observer creates instance if none exists."""
        # Reset singleton for test
        import app.services.protocol_observer as po
        po._observer_instance = None
        
        obs = get_protocol_observer()
        
        assert obs is not None
        assert isinstance(obs, ProtocolObserver)


class TestRawOpportunityDataclass:
    """Tests for RawOpportunity dataclass."""
    
    def test_raw_opportunity_creation(self):
        """RawOpportunity can be created with all fields."""
        opp = RawOpportunity(
            protocol_id="test_proto",
            protocol_source="nba",
            game_id="game_123",
            sport="NBA",
            league="NBA",
            home_team="Lakers",
            away_team="Warriors",
            event_time=datetime.utcnow(),
            bet_type="moneyline",
            market="game",
            selection="Lakers ML",
            odds=-150,
            odds_decimal=1.67,
            line=None,
            confidence_score=75.0,
            edge_percent=8.5,
            metadata={"key": "value"}
        )
        
        assert opp.protocol_id == "test_proto"
        assert opp.sport == "NBA"
        assert opp.confidence_score == 75.0


class TestOpportunityResultDataclass:
    """Tests for OpportunityResult dataclass."""
    
    def test_opportunity_result_success(self):
        """Successful result."""
        result = OpportunityResult(
            success=True,
            opportunity_id="opp_123",
            reason="Created successfully"
        )
        
        assert result.success is True
        assert result.opportunity_id == "opp_123"
    
    def test_opportunity_result_failure(self):
        """Failed result."""
        result = OpportunityResult(
            success=False,
            reason="Confidence too low"
        )
        
        assert result.success is False
        assert result.opportunity_id is None
        assert "Confidence" in result.reason
    
    def test_opportunity_result_guardrail_block(self):
        """Result blocked by guardrails."""
        result = OpportunityResult(
            success=False,
            passed_guardrails=False,
            guardrail_reason="Daily cap reached",
            reason="Guardrails blocked"
        )
        
        assert result.passed_guardrails is False
        assert result.guardrail_reason == "Daily cap reached"
