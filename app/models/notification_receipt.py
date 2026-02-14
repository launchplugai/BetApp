"""
Notification Receipt model for S20-P4: Telemetry + Receipts for Observer Loop.
Tracks the complete lifecycle of notifications from detection through delivery or suppression.
"""

from sqlalchemy import Column, String, DateTime, Float, JSON
from datetime import datetime
import uuid
from . import Base


class NotificationReceipt(Base):
    """
    Notification Receipt model - tracks notification lifecycle for telemetry.
    
    Lifecycle stages:
    1. DETECTED - Opportunity detected by observer
    2. ELIGIBLE - Passed user constraint checks
    3. SENT - Notification successfully delivered
    4. SUPPRESSED - Blocked by guardrails or constraints
    """
    __tablename__ = 'notification_receipts'

    id = Column(String, primary_key=True, default=lambda: f"rcpt_{uuid.uuid4().hex[:8]}")
    user_id = Column(String, nullable=False, index=True)
    opportunity_id = Column(String, nullable=True, index=True)
    
    # Reason codes for why this notification was triggered (e.g., ['high_confidence', 'user_preference_match'])
    reason_codes = Column(JSON, default=list)
    
    # Constraints that were applied (e.g., ['confidence_threshold', 'dna_match'])
    constraints_applied = Column(JSON, default=list)
    
    # Scoring
    confidence = Column(Float, nullable=True)  # Opportunity confidence score
    weight_tier = Column(String, nullable=True)  # Weight tier (A, B, C, etc.)
    
    # Lifecycle timestamps
    detected_at = Column(DateTime, nullable=True)  # When opportunity was first detected
    eligible_at = Column(DateTime, nullable=True)  # When it passed constraint checks
    sent_at = Column(DateTime, nullable=True)  # When notification was sent
    
    # Status: detected, eligible, sent, suppressed
    status = Column(String, default="detected", nullable=False, index=True)
    
    # If suppressed, the reason why
    suppression_reason = Column(String, nullable=True)
    
    # Additional metadata for telemetry
    additional_metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "opportunity_id": self.opportunity_id,
            "reason_codes": self.reason_codes or [],
            "constraints_applied": self.constraints_applied or [],
            "confidence": self.confidence,
            "weight_tier": self.weight_tier,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "eligible_at": self.eligible_at.isoformat() if self.eligible_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "status": self.status,
            "suppression_reason": self.suppression_reason,
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def mark_detected(self, detected_at: datetime = None):
        """Mark receipt as detected."""
        self.status = "detected"
        self.detected_at = detected_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_eligible(self, eligible_at: datetime = None):
        """Mark receipt as eligible (passed constraints)."""
        self.status = "eligible"
        self.eligible_at = eligible_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_sent(self, sent_at: datetime = None):
        """Mark receipt as sent."""
        self.status = "sent"
        self.sent_at = sent_at or datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def mark_suppressed(self, reason: str):
        """Mark receipt as suppressed with reason."""
        self.status = "suppressed"
        self.suppression_reason = reason
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def create_for_detection(cls, user_id: str, opportunity_id: str = None,
                             confidence: float = None, reason_codes: list = None,
                             weight_tier: str = None, metadata: dict = None):
        """Factory method to create a receipt at detection stage."""
        receipt = cls(
            user_id=user_id,
            opportunity_id=opportunity_id,
            confidence=confidence,
            reason_codes=reason_codes or [],
            weight_tier=weight_tier,
            metadata=metadata or {},
            detected_at=datetime.utcnow(),
            status="detected"
        )
        return receipt


# Telemetry counters for in-memory aggregation
class TelemetryCounters:
    """In-memory counters for notification telemetry."""
    
    def __init__(self):
        self.detected = 0
        self.eligible_after_constraints = 0
        self.sent = 0
        self.suppressed_cooldown = 0
        self.suppressed_daily_cap = 0
        self.suppressed_quiet_hours = 0
        self.suppressed_constraints = 0
        self.suppressed_beta_gate = 0
        self.suppressed_other = 0
    
    def to_dict(self):
        return {
            "detected": self.detected,
            "eligible_after_constraints": self.eligible_after_constraints,
            "sent": self.sent,
            "suppressed": {
                "cooldown": self.suppressed_cooldown,
                "daily_cap": self.suppressed_daily_cap,
                "quiet_hours": self.suppressed_quiet_hours,
                "constraints": self.suppressed_constraints,
                "beta_gate": self.suppressed_beta_gate,
                "other": self.suppressed_other
            }
        }
    
    def increment_suppressed(self, reason: str):
        """Increment the appropriate suppression counter based on reason."""
        if "cooldown" in reason.lower():
            self.suppressed_cooldown += 1
        elif "daily cap" in reason.lower() or "cap reached" in reason.lower():
            self.suppressed_daily_cap += 1
        elif "quiet hours" in reason.lower():
            self.suppressed_quiet_hours += 1
        elif "constraint" in reason.lower():
            self.suppressed_constraints += 1
        elif "beta" in reason.lower() or "kill switch" in reason.lower():
            self.suppressed_beta_gate += 1
        else:
            self.suppressed_other += 1


# Global telemetry counters instance
_telemetry_counters = TelemetryCounters()


def get_telemetry_counters() -> TelemetryCounters:
    """Get the global telemetry counters instance."""
    return _telemetry_counters


def reset_telemetry_counters():
    """Reset all telemetry counters to zero."""
    global _telemetry_counters
    _telemetry_counters = TelemetryCounters()
