"""
Notification Rules Engine for S20.
Validates if opportunities match user notification rules and preferences.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import time

from app.services.notification_types import RawOpportunity, MatchResult

logger = logging.getLogger(__name__)


class NotificationRulesEngine:
    """
    Validates opportunities against user notification rules.
    Checks confidence thresholds, sports, odds ranges, etc.
    """
    
    def __init__(self):
        pass
    
    def matches_rules(self, opportunity: RawOpportunity, 
                      rules: Dict[str, Any]) -> MatchResult:
        """
        Check if an opportunity matches user notification rules.
        
        Args:
            opportunity: The raw opportunity to check
            rules: User's opportunity_alert rules
            
        Returns:
            MatchResult with match status and details
        """
        if not rules.get("enabled", True):
            return MatchResult(
                matches=False,
                reason="Opportunity alerts disabled",
                matched_criteria=[]
            )
        
        matched_criteria = []
        
        # Check confidence threshold
        confidence_result = self._check_confidence(opportunity, rules)
        if not confidence_result[0]:
            return MatchResult(
                matches=False,
                reason=confidence_result[1],
                matched_criteria=matched_criteria
            )
        matched_criteria.append("confidence_threshold")
        
        # Check edge percentage
        edge_result = self._check_edge(opportunity, rules)
        if not edge_result[0]:
            return MatchResult(
                matches=False,
                reason=edge_result[1],
                matched_criteria=matched_criteria
            )
        if edge_result[1]:
            matched_criteria.append("edge_threshold")
        
        # Check sports filter
        sport_result = self._check_sports(opportunity, rules)
        if not sport_result[0]:
            return MatchResult(
                matches=False,
                reason=sport_result[1],
                matched_criteria=matched_criteria
            )
        if sport_result[1]:
            matched_criteria.append("sport_match")
        
        # Check bet types
        bet_type_result = self._check_bet_types(opportunity, rules)
        if not bet_type_result[0]:
            return MatchResult(
                matches=False,
                reason=bet_type_result[1],
                matched_criteria=matched_criteria
            )
        matched_criteria.append("bet_type_match")
        
        # Check odds range
        odds_result = self._check_odds_range(opportunity, rules)
        if not odds_result[0]:
            return MatchResult(
                matches=False,
                reason=odds_result[1],
                matched_criteria=matched_criteria
            )
        matched_criteria.append("odds_range")
        
        return MatchResult(
            matches=True,
            reason="All rules passed",
            matched_criteria=matched_criteria
        )
    
    def _check_confidence(self, opportunity: RawOpportunity, 
                          rules: Dict[str, Any]) -> tuple[bool, str]:
        """Check if opportunity meets confidence threshold."""
        min_confidence = rules.get("min_confidence", 70)
        
        if opportunity.confidence_score < min_confidence:
            return False, f"Confidence {opportunity.confidence_score:.1f} below minimum {min_confidence}"
        
        return True, ""
    
    def _check_edge(self, opportunity: RawOpportunity,
                    rules: Dict[str, Any]) -> tuple[bool, str, bool]:
        """
        Check if opportunity meets edge percentage threshold.
        
        Returns:
            Tuple of (passed, reason, was_checked)
        """
        min_edge = rules.get("min_edge_percent")
        
        # If no min_edge set, skip this check
        if min_edge is None:
            return True, "", False
        
        if opportunity.edge_percent is None:
            return False, "Edge percentage not available", True
        
        if opportunity.edge_percent < min_edge:
            return False, f"Edge {opportunity.edge_percent:.1f}% below minimum {min_edge}%", True
        
        return True, "", True
    
    def _check_sports(self, opportunity: RawOpportunity,
                      rules: Dict[str, Any]) -> tuple[bool, str, bool]:
        """
        Check if opportunity is in user's preferred sports.
        
        Returns:
            Tuple of (passed, reason, was_checked)
        """
        allowed_sports = rules.get("sports", [])
        
        # Empty list means all sports allowed
        if not allowed_sports:
            return True, "", False
        
        sport_upper = opportunity.sport.upper()
        allowed_upper = [s.upper() for s in allowed_sports]
        
        if sport_upper not in allowed_upper:
            return False, f"Sport '{opportunity.sport}' not in allowed list", True
        
        return True, "", True
    
    def _check_bet_types(self, opportunity: RawOpportunity,
                         rules: Dict[str, Any]) -> tuple[bool, str]:
        """Check if bet type is in user's preferred types."""
        allowed_types = rules.get("bet_types", ["moneyline", "spread", "total", "prop"])
        
        bet_type_lower = opportunity.bet_type.lower()
        allowed_lower = [t.lower() for t in allowed_types]
        
        if bet_type_lower not in allowed_lower:
            return False, f"Bet type '{opportunity.bet_type}' not in allowed types"
        
        return True, ""
    
    def _check_odds_range(self, opportunity: RawOpportunity,
                          rules: Dict[str, Any]) -> tuple[bool, str]:
        """Check if odds are within user's preferred range."""
        odds_range = rules.get("odds_range", {})
        min_odds = odds_range.get("min")
        max_odds = odds_range.get("max")
        
        odds = opportunity.odds
        
        if min_odds is not None and odds < min_odds:
            return False, f"Odds {odds} below minimum {min_odds}"
        
        if max_odds is not None and odds > max_odds:
            return False, f"Odds {odds} above maximum {max_odds}"
        
        return True, ""
    
    def validate_notification_rules(self, rules: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate notification rules configuration.
        
        Args:
            rules: The notification rules to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate opportunity_alerts
        alerts = rules.get("opportunity_alerts", {})
        
        if "min_confidence" in alerts:
            mc = alerts["min_confidence"]
            if not isinstance(mc, (int, float)) or mc < 0 or mc > 100:
                errors.append("min_confidence must be a number between 0 and 100")
        
        if "min_edge_percent" in alerts:
            me = alerts["min_edge_percent"]
            if not isinstance(me, (int, float)) or me < 0:
                errors.append("min_edge_percent must be a positive number")
        
        if "sports" in alerts:
            if not isinstance(alerts["sports"], list):
                errors.append("sports must be a list")
        
        if "bet_types" in alerts:
            valid_types = ["moneyline", "spread", "total", "prop", "parlay"]
            for bt in alerts["bet_types"]:
                if bt.lower() not in valid_types:
                    errors.append(f"Invalid bet_type: {bt}")
        
        if "odds_range" in alerts:
            orng = alerts["odds_range"]
            if "min" in orng and orng["min"] is not None:
                if not isinstance(orng["min"], (int, float)):
                    errors.append("odds_range.min must be a number")
            if "max" in orng and orng["max"] is not None:
                if not isinstance(orng["max"], (int, float)):
                    errors.append("odds_range.max must be a number")
        
        if "max_notifications_per_day" in alerts:
            mnpd = alerts["max_notifications_per_day"]
            if not isinstance(mnpd, int) or mnpd < 1:
                errors.append("max_notifications_per_day must be a positive integer")
        
        if "cooldown_minutes" in alerts:
            cm = alerts["cooldown_minutes"]
            if not isinstance(cm, int) or cm < 0:
                errors.append("cooldown_minutes must be a non-negative integer")
        
        # Validate quiet_hours
        quiet = rules.get("quiet_hours", {})
        if quiet.get("enabled", False):
            start = quiet.get("start")
            end = quiet.get("end")
            
            if start:
                try:
                    time.fromisoformat(start)
                except ValueError:
                    errors.append("quiet_hours.start must be in HH:MM format")
            
            if end:
                try:
                    time.fromisoformat(end)
                except ValueError:
                    errors.append("quiet_hours.end must be in HH:MM format")
        
        return len(errors) == 0, errors
    
    def get_default_rules(self) -> Dict[str, Any]:
        """Get default notification rules."""
        return {
            "enabled": True,
            "opportunity_alerts": {
                "enabled": True,
                "min_confidence": 70,
                "min_edge_percent": 5.0,
                "sports": [],
                "bet_types": ["moneyline", "spread", "total", "prop"],
                "odds_range": {
                    "min": -300,
                    "max": 500
                },
                "max_notifications_per_day": 10,
                "cooldown_minutes": 60
            },
            "bet_outcomes": {
                "enabled": True,
                "wins": True,
                "losses": True
            },
            "game_reminders": {
                "enabled": False,
                "before_minutes": 30
            },
            "quiet_hours": {
                "enabled": True,
                "start": "22:00",
                "end": "08:00"
            }
        }
