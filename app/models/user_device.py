"""
User device model for storing push notification tokens.
"""

from sqlalchemy import Column, String, DateTime, Boolean
from datetime import datetime
import uuid
from . import Base


class UserDevice(Base):
    """User device for push notifications."""
    __tablename__ = 'user_devices'

    id = Column(String, primary_key=True, default=lambda: f"device_{uuid.uuid4().hex[:8]}")
    user_id = Column(String, nullable=False, index=True)
    device_id = Column(String, nullable=False, unique=True)  # Unique device identifier
    push_token = Column(String, nullable=False)  # FCM token
    platform = Column(String, nullable=False)  # ios, android, web
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "platform": self.platform,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None
        }
