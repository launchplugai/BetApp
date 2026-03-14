"""Promotion and rollback audit model for governed changes."""

from datetime import UTC, datetime
import uuid

from sqlalchemy import Column, DateTime, JSON, String

from . import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for defaults."""
    return datetime.now(UTC)


class PromotionAuditRecord(Base):
    """Audit record for promotions and rollbacks."""

    __tablename__ = "promotion_audit"

    id = Column(String, primary_key=True, default=lambda: f"prom_{uuid.uuid4().hex[:10]}")
    proposal_id = Column(String, nullable=False, index=True)
    promoted_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    approved_by = Column(String, nullable=False, index=True)
    old_version = Column(String, nullable=False)
    new_version = Column(String, nullable=False, index=True)
    rollback_version = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    meta = Column("metadata", JSON, nullable=False, default=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "proposal_id": self.proposal_id,
            "promoted_at": self.promoted_at.isoformat() if self.promoted_at else None,
            "approved_by": self.approved_by,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "rollback_version": self.rollback_version,
            "notes": self.notes,
            "metadata": self.meta or {},
        }
