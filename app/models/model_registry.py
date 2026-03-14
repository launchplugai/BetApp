"""Version registry models for governed learning and promotion."""

from datetime import UTC, datetime
import uuid

from sqlalchemy import Column, DateTime, JSON, String

from . import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for defaults."""
    return datetime.now(UTC)


class ModelRegistryEntry(Base):
    """Registry entry for a production-affecting model or config version."""

    __tablename__ = "model_registry"

    id = Column(String, primary_key=True, default=lambda: f"reg_{uuid.uuid4().hex[:10]}")
    entity_type = Column(String, nullable=False, index=True)
    entity_name = Column(String, nullable=False)
    version = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="draft", index=True)
    scope = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    promoted_at = Column(DateTime, nullable=True)
    rollback_version = Column(String, nullable=True)
    source_proposal_id = Column(String, nullable=True, index=True)
    meta = Column("metadata", JSON, nullable=False, default=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "version": self.version,
            "status": self.status,
            "scope": self.scope or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "promoted_at": self.promoted_at.isoformat() if self.promoted_at else None,
            "rollback_version": self.rollback_version,
            "source_proposal_id": self.source_proposal_id,
            "metadata": self.meta or {},
        }
