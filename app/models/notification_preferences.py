"""
Notification preferences model for per-user notification settings.
"""

from sqlalchemy import Column, String, Time, Boolean
from datetime import time
import uuid
from . import Base


class NotificationPreferences(Base):
    """User notification preferences."""
    __tablename__ = 'notification_preferences'

    id = Column(String, primary_key=True, default=lambda: f"npref_{uuid.uuid4().hex[:8]}")
    user_id = Column(String, nullable=False, unique=True, index=True)
    
    # Notification type toggles
    bet_outcomes = Column(Boolean, default=True)
    signals = Column(Boolean, default=True)
    game_reminders = Column(Boolean, default=True)
    promotions = Column(Boolean, default=False)
    
    # Quiet hours (no notifications during these times)
    quiet_hours_start = Column(Time, nullable=True)  # e.g., 22:00
    quiet_hours_end = Column(Time, nullable=True)    # e.g., 08:00
    
    # Push notification enabled
    push_enabled = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "bet_outcomes": self.bet_outcomes,
            "signals": self.signals,
            "game_reminders": self.game_reminders,
            "promotions": self.promotions,
            "quiet_hours_start": self.quiet_hours_start.isoformat() if self.quiet_hours_start else None,
            "quiet_hours_end": self.quiet_hours_end.isoformat() if self.quiet_hours_end else None,
            "push_enabled": self.push_enabled
        }
    
    def should_send_notification(self, notif_type: str, current_time: time = None) -> bool:
        """Check if notification should be sent based on preferences."""
        from datetime import datetime
        
        if not self.push_enabled:
            return False
        
        # Check notification type
        type_mapping = {
            "bet_won": self.bet_outcomes,
            "bet_lost": self.bet_outcomes,
            "bet_settled": self.bet_outcomes,
            "signal_detected": self.signals,
            "game_starting": self.game_reminders,
            "game_ended": self.game_reminders,
            "promotion": self.promotions,
        }
        
        if not type_mapping.get(notif_type, True):
            return False
        
        # Check quiet hours
        if self.quiet_hours_start and self.quiet_hours_end and current_time:
            # Handle overnight quiet hours (e.g., 22:00 - 08:00)
            if self.quiet_hours_start > self.quiet_hours_end:
                # Overnight span
                if current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end:
                    return False
            else:
                # Same day span
                if self.quiet_hours_start <= current_time <= self.quiet_hours_end:
                    return False
        
        return True
