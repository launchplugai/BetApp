"""Learning proposal model for governed adaptive changes."""

from datetime import UTC, datetime
import uuid

from sqlalchemy import Column, DateTime, JSON, String

from . import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for defaults."""
    return datetime.now(UTC)


class LearningProposal(Base):
    """Proposal record produced by governed learning systems."""

    __tablename__ = "learning_proposals"

    id = Column(String, primary_key=True, default=lambda: f"prop_{uuid.uuid4().hex[:10]}")
    proposal_type = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now, index=True)
    status = Column(String, nullable=False, default="draft", index=True)
    target = Column(JSON, nullable=False, default=dict)
    current_value = Column(JSON, nullable=True)
    proposed_value = Column(JSON, nullable=True)
    reason = Column(String, nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    allowed_range = Column(JSON, nullable=False, default=list)
    model_scope = Column(JSON, nullable=False, default=list)
    review = Column(JSON, nullable=False, default=dict)
    meta = Column("metadata", JSON, nullable=False, default=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "proposal_type": self.proposal_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "status": self.status,
            "target": self.target or {},
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "reason": self.reason,
            "evidence": self.evidence or {},
            "allowed_range": self.allowed_range or [],
            "model_scope": self.model_scope or [],
            "review": self.review or {},
            "metadata": self.meta or {},
        }
