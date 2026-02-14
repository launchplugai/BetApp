"""
Notification Event model for storing notification history.
Tracks all notifications sent to users for audit and analytics.
"""

from sqlalchemy import Column, String, DateTime, Boolean, JSON, Integer, Float
from datetime import datetime
import uuid
from . import Base


class NotificationEvent(Base):
    """Notification Event model for tracking all notification activity."""
    __tablename__ = 'notification_events'

    id = Column(String, primary_key=True, default=lambda: f"nevt_{uuid.uuid4().hex[:8]}")
    user_id = Column(String, nullable=False, index=True)
    
    # Notification classification
    type = Column(String, nullable=False, index=True)  # opportunity_alert, bet_won, etc.
    category = Column(String, nullable=False, default="signal")  # signal, system, promotional
    priority = Column(String, default="normal")  # low, normal, high, urgent
    
    # Content
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    data = Column(JSON, default=dict)  # Deep link payload, opportunity details
    
    # Delivery tracking
    channel = Column(String, default="push")  # push, email, sms, in_app
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String, default="sent")  # pending, sent, delivered, read, dismissed, failed
    error_message = Column(String, nullable=True)  # If delivery failed
    
    # Related entities
    opportunity_id = Column(String, nullable=True, index=True)  # Link to eligible_opportunity if applicable
    bet_id = Column(String, nullable=True, index=True)  # Link to bet if applicable
    
    # Guardrail metadata (for audit)
    guardrail_passed = Column(Boolean, default=True)
    guardrail_reason = Column(String, nullable=True)  # Why it passed/failed guardrails
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "body": self.body,
            "data": self.data or {},
            "channel": self.channel,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "dismissed_at": self.dismissed_at.isoformat() if self.dismissed_at else None,
            "opportunity_id": self.opportunity_id,
            "bet_id": self.bet_id,
            "guardrail_passed": self.guardrail_passed,
            "guardrail_reason": self.guardrail_reason
        }
    
    def mark_read(self):
        """Mark notification as read."""
        self.status = "read"
        self.read_at = datetime.utcnow()
    
    def mark_dismissed(self):
        """Mark notification as dismissed."""
        self.status = "dismissed"
        self.dismissed_at = datetime.utcnow()
    
    def mark_delivered(self):
        """Mark notification as delivered."""
        self.status = "delivered"
        self.delivered_at = datetime.utcnow()
    
    def mark_failed(self, error: str):
        """Mark notification as failed with error."""
        self.status = "failed"
        self.error_message = error
