"""
User Preferences model for storing user DNA profile.
Includes notification rules for S20.
"""

from sqlalchemy import Column, String, JSON, Integer, DateTime
from datetime import datetime
import uuid
from . import Base


class UserPreferences(Base):
    """User Preferences model for DNA betting engine."""
    __tablename__ = 'user_preferences'

    id = Column(String, primary_key=True, default=lambda: f"pref_{{uuid.uuid4().hex[:8]}}")
    user_id = Column(String, nullable=False, unique=True, index=True)
    risk_profile = Column(String, default="balanced")  # Options: conservative, balanced, aggressive
    bet_style = Column(JSON, default=lambda: ["props"])  # Preferred betting styles as list
    constraints = Column(JSON, default=dict)  # User-specific constraints for bets
    bankroll_policy = Column(JSON, default=dict)  # Bankroll management rules
    
    # S20: Notification rules
    notification_rules = Column(JSON, default=dict)  # User notification preferences
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "risk_profile": self.risk_profile,
            "bet_style": self.bet_style or ["props"],
            "constraints": self.constraints or {},
            "bankroll_policy": self.bankroll_policy or {},
            "notification_rules": self.notification_rules or self._default_notification_rules(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def _default_notification_rules(self) -> dict:
        """Return default notification rules."""
        return {
            "enabled": True,
            "opportunity_alerts": {
                "enabled": True,
                "min_confidence": 70,  # Minimum confidence score (0-100)
                "min_edge_percent": 5.0,  # Minimum edge percentage
                "sports": [],  # Empty = all sports
                "bet_types": ["moneyline", "spread", "total", "prop"],
                "odds_range": {
                    "min": -300,
                    "max": 500
                },
                "max_notifications_per_day": 10,
                "cooldown_minutes": 60  # Per-game cooldown
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
    
    def get_notification_rules(self) -> dict:
        """Get notification rules with defaults merged."""
        defaults = self._default_notification_rules()
        user_rules = self.notification_rules or {}
        
        # Merge user rules with defaults
        return self._deep_merge(defaults, user_rules)
    
    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
