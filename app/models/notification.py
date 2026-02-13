"""
Notification model for user alerts and messages.
"""

from sqlalchemy import Column, String, DateTime, Boolean, JSON
from datetime import datetime
import uuid
from . import Base


class Notification(Base):
    """Notification model for user alerts."""
    __tablename__ = 'notifications'

    id = Column(String, primary_key=True, default=lambda: f"notif_{uuid.uuid4().hex[:8]}")
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # bet_won, bet_lost, signal_detected, etc.
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    data = Column(JSON, default=dict)  # Deep link payload
    read = Column(Boolean, default=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "title": self.title,
            "body": self.body,
            "data": self.data or {},
            "read": self.read,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None
        }
