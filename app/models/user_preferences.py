"""
User Preferences model for storing user DNA profile.
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
