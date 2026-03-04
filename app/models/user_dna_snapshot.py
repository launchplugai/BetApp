"""
User DNA Snapshot model for versioning user preferences.
"""

from sqlalchemy import Column, String, JSON, DateTime
from datetime import datetime
import uuid
from . import Base


class UserDnaSnapshot(Base):
    """User DNA Snapshot model to version user preferences."""
    __tablename__ = 'user_dna_snapshots'

    id = Column(String, primary_key=True, default=lambda: f"snapshot_{{uuid.uuid4().hex[:8]}}")
    user_id = Column(String, nullable=False, index=True)
    preferences = Column(JSON, nullable=False)  # Represents User Preferences at snapshot time
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "preferences": self.preferences or {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
