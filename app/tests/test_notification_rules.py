"""
Tests for Notification Rules Engine (S20).
Tests the NotificationRulesEngine class that validates opportunities against
user notification rules.
"""

import pytest
from datetime import time

from app.services.notification_rules import (
    NotificationRulesEngine
)
from app.services.notification_types import RawOpportunity, MatchResult


@pytest.fixture
def engine():
    """Create a NotificationRulesEngine instance."""
    return NotificationRulesEngine()


@pytest.fixture
def sample_opportunity():
    """Create a sample raw opportunity."""
    from datetime import datetime, timedelta
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
def default_rules():
    """Create default notification rules."""
    return {
        "enabled": True,
        "min_confidence": 70.0,
        "min_edge_percent": 5.0,
        "sports": [],
        "bet_types": ["moneyline", "spread", "total", "prop"],
        "odds_range": {
            "min": -300,
            "max": 500
        },
        "max_notifications_per_day": 10,
        "cooldown_minutes": 60
    }


class TestConfidenceCheck:
    """Tests for confidence threshold checking."""
    
    def test_confidence_above_threshold(self, engine, sample_opportunity, default_rules):
        """Opportunity above confidence threshold passes."""
        result = engine._check_confidence(sample_opportunity, default_rules)
        assert result[0] is True
    
    def test_confidence_below_threshold(self, engine, sample_opportunity, default_rules):
        """Opportunity below confidence threshold fails."""
        sample_opportunity.confidence_score = 50.0
        result = engine._check_confidence(sample_opportunity, default_rules)
        assert result[0] is False
        assert "50.0" in result[1]
        assert "70" in result[1]
    
    def test_confidence_exact_threshold(self, engine, sample_opportunity, default_rules):
        """Opportunity at exact threshold passes."""
        sample_opportunity.confidence_score = 70.0
        result = engine._check_confidence(sample_opportunity, default_rules)
        assert result[0] is True


class TestEdgeCheck:
    """Tests for edge percentage checking."""
    
    def test_edge_above_threshold(self, engine, sample_opportunity, default_rules):
        """Opportunity above edge threshold passes."""
        result = engine._check_edge(sample_opportunity, default_rules)
        assert result[0] is True
        assert result[2] is True  # was_checked
    
    def test_edge_below_threshold(self, engine, sample_opportunity, default_rules):
        """Opportunity below edge threshold fails."""
        sample_opportunity.edge_percent = 3.0
        result = engine._check_edge(sample_opportunity, default_rules)
        assert result[0] is False
        assert "3.0" in result[1]
    
    def test_edge_no_min_set(self, engine, sample_opportunity):
        """When no min_edge set, check is skipped."""
        rules = {"min_edge_percent": None}
        result = engine._check_edge(sample_opportunity, rules)
        assert result[0] is True
        assert result[2] is False  # was_checked = False
    
    def test_edge_no_edge_data(self, engine, sample_opportunity, default_rules):
        """Opportunity with no edge data fails when min is set."""
        sample_opportunity.edge_percent = None
        result = engine._check_edge(sample_opportunity, default_rules)
        assert result[0] is False
        assert "not available" in result[1]


class TestSportsCheck:
    """Tests for sports filtering."""
    
    def test_sport_allowed_empty_list(self, engine, sample_opportunity):
        """Empty sports list allows all sports."""
        rules = {"sports": []}
        result = engine._check_sports(sample_opportunity, rules)
        assert result[0] is True
        assert result[2] is False  # was_checked = False
    
    def test_sport_in_allowed_list(self, engine, sample_opportunity):
        """Sport in allowed list passes."""
        rules = {"sports": ["NBA", "NFL"]}
        result = engine._check_sports(sample_opportunity, rules)
        assert result[0] is True
        assert result[2] is True
    
    def test_sport_not_in_allowed_list(self, engine, sample_opportunity):
        """Sport not in allowed list fails."""
        rules = {"sports": ["NFL", "MLB"]}
        result = engine._check_sports(sample_opportunity, rules)
        assert result[0] is False
        assert "NBA" in result[1]
    
    def test_sport_case_insensitive(self, engine, sample_opportunity):
        """Sport matching is case insensitive."""
        rules = {"sports": ["nba", "nfl"]}  # lowercase
        # Sample opportunity has sport="NBA" (uppercase)
        result = engine._check_sports(sample_opportunity, rules)
        assert result[0] is True


class TestBetTypesCheck:
    """Tests for bet type filtering."""
    
    def test_bet_type_allowed(self, engine, sample_opportunity, default_rules):
        """Bet type in allowed list passes."""
        result = engine._check_bet_types(sample_opportunity, default_rules)
        assert result[0] is True
    
    def test_bet_type_not_allowed(self, engine, sample_opportunity):
        """Bet type not in allowed list fails."""
        rules = {"bet_types": ["prop", "parlay"]}
        result = engine._check_bet_types(sample_opportunity, rules)
        assert result[0] is False
        assert "moneyline" in result[1]
    
    def test_bet_type_case_insensitive(self, engine, sample_opportunity):
        """Bet type matching is case insensitive."""
        sample_opportunity.bet_type = "MONEYLINE"  # uppercase
        rules = {"bet_types": ["moneyline"]}  # lowercase
        result = engine._check_bet_types(sample_opportunity, rules)
        assert result[0] is True


class TestOddsRangeCheck:
    """Tests for odds range checking."""
    
    def test_odds_within_range(self, engine, sample_opportunity):
        """Odds within range passes."""
        rules = {"odds_range": {"min": -200, "max": 200}}
        result = engine._check_odds_range(sample_opportunity, rules)
        assert result[0] is True
    
    def test_odds_below_min(self, engine, sample_opportunity):
        """Odds below minimum fails."""
        rules = {"odds_range": {"min": -100, "max": 200}}
        result = engine._check_odds_range(sample_opportunity, rules)
        assert result[0] is False
        assert "below minimum" in result[1]
    
    def test_odds_above_max(self, engine, sample_opportunity):
        """Odds above maximum fails."""
        sample_opportunity.odds = 600
        rules = {"odds_range": {"min": -300, "max": 500}}
        result = engine._check_odds_range(sample_opportunity, rules)
        assert result[0] is False
        assert "above maximum" in result[1]
    
    def test_odds_no_range_set(self, engine, sample_opportunity):
        """When no range set, always passes."""
        rules = {"odds_range": {}}
        result = engine._check_odds_range(sample_opportunity, rules)
        assert result[0] is True


class TestMatchesRules:
    """Tests for complete rule matching."""
    
    def test_all_rules_pass(self, engine, sample_opportunity, default_rules):
        """Opportunity passing all rules returns success."""
        result = engine.matches_rules(sample_opportunity, default_rules)
        
        assert isinstance(result, MatchResult)
        assert result.matches is True
        assert len(result.matched_criteria) > 0
    
    def test_rules_disabled(self, engine, sample_opportunity):
        """Disabled rules reject all."""
        rules = {"enabled": False}
        result = engine.matches_rules(sample_opportunity, rules)
        
        assert result.matches is False
        assert "disabled" in result.reason
    
    def test_confidence_fails(self, engine, sample_opportunity, default_rules):
        """Low confidence causes match failure."""
        sample_opportunity.confidence_score = 50.0
        result = engine.matches_rules(sample_opportunity, default_rules)
        
        assert result.matches is False
        assert "confidence" in result.reason.lower()
    
    def test_sport_fails(self, engine, sample_opportunity):
        """Wrong sport causes match failure."""
        rules = {
            "enabled": True,
            "min_confidence": 70.0,
            "sports": ["NFL"],  # Not NBA
            "bet_types": ["moneyline"]
        }
        result = engine.matches_rules(sample_opportunity, rules)
        
        assert result.matches is False
        assert "sport" in result.reason.lower() or "NBA" in result.reason


class TestValidateNotificationRules:
    """Tests for notification rules validation."""
    
    def test_valid_rules(self, engine):
        """Valid rules pass validation."""
        rules = {
            "enabled": True,
            "opportunity_alerts": {
                "min_confidence": 70,
                "min_edge_percent": 5.0,
                "sports": ["NBA", "NFL"],
                "bet_types": ["moneyline", "spread"],
                "odds_range": {"min": -300, "max": 500},
                "max_notifications_per_day": 10,
                "cooldown_minutes": 60
            },
            "quiet_hours": {
                "enabled": True,
                "start": "22:00",
                "end": "08:00"
            }
        }
        
        is_valid, errors = engine.validate_notification_rules(rules)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_invalid_confidence(self, engine):
        """Invalid confidence fails validation."""
        rules = {
            "opportunity_alerts": {
                "min_confidence": 150  # Over 100
            }
        }
        
        is_valid, errors = engine.validate_notification_rules(rules)
        assert is_valid is False
        assert any("confidence" in e.lower() for e in errors)
    
    def test_invalid_confidence_negative(self, engine):
        """Negative confidence fails validation."""
        rules = {
            "opportunity_alerts": {
                "min_confidence": -10
            }
        }
        
        is_valid, errors = engine.validate_notification_rules(rules)
        assert is_valid is False
        assert any("confidence" in e.lower() for e in errors)
    
    def test_invalid_bet_type(self, engine):
        """Invalid bet type fails validation."""
        rules = {
            "opportunity_alerts": {
                "bet_types": ["invalid_type"]
            }
        }
        
        is_valid, errors = engine.validate_notification_rules(rules)
        assert is_valid is False
        assert any("bet_type" in e.lower() for e in errors)
    
    def test_invalid_max_notifications(self, engine):
        """Invalid max_notifications_per_day fails validation."""
        rules = {
            "opportunity_alerts": {
                "max_notifications_per_day": 0  # Must be >= 1
            }
        }
        
        is_valid, errors = engine.validate_notification_rules(rules)
        assert is_valid is False
        assert any("max_notifications" in e.lower() for e in errors)
    
    def test_invalid_cooldown(self, engine):
        """Negative cooldown fails validation."""
        rules = {
            "opportunity_alerts": {
                "cooldown_minutes": -5
            }
        }
        
        is_valid, errors = engine.validate_notification_rules(rules)
        assert is_valid is False
        assert any("cooldown" in e.lower() for e in errors)
    
    def test_invalid_quiet_hours_format(self, engine):
        """Invalid quiet hours format fails validation."""
        rules = {
            "quiet_hours": {
                "enabled": True,
                "start": "25:00",  # Invalid time
                "end": "08:00"
            }
        }
        
        is_valid, errors = engine.validate_notification_rules(rules)
        assert is_valid is False
        assert any("quiet_hours" in e.lower() or "format" in e.lower() for e in errors)


class TestDefaultRules:
    """Tests for default rules generation."""
    
    def test_default_rules_structure(self, engine):
        """Default rules have expected structure."""
        defaults = engine.get_default_rules()
        
        assert "enabled" in defaults
        assert "opportunity_alerts" in defaults
        assert "bet_outcomes" in defaults
        assert "game_reminders" in defaults
        assert "quiet_hours" in defaults
    
    def test_default_opportunity_alerts(self, engine):
        """Default opportunity alerts have expected values."""
        defaults = engine.get_default_rules()
        alerts = defaults["opportunity_alerts"]
        
        assert alerts["enabled"] is True
        assert alerts["min_confidence"] == 70
        assert alerts["min_edge_percent"] == 5.0
        assert alerts["sports"] == []
        assert "moneyline" in alerts["bet_types"]
        assert alerts["max_notifications_per_day"] == 10
        assert alerts["cooldown_minutes"] == 60
    
    def test_default_quiet_hours(self, engine):
        """Default quiet hours have expected values."""
        defaults = engine.get_default_rules()
        quiet = defaults["quiet_hours"]
        
        assert quiet["enabled"] is True
        assert quiet["start"] == "22:00"
        assert quiet["end"] == "08:00"


class TestMatchResult:
    """Tests for MatchResult dataclass."""
    
    def test_match_result_success(self):
        """Successful match result."""
        result = MatchResult(
            matches=True,
            reason="All rules passed",
            matched_criteria=["confidence", "sport"]
        )
        
        assert result.matches is True
        assert len(result.matched_criteria) == 2
    
    def test_match_result_failure(self):
        """Failed match result."""
        result = MatchResult(
            matches=False,
            reason="Confidence too low",
            matched_criteria=[]
        )
        
        assert result.matches is False
        assert "Confidence" in result.reason
