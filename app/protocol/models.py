"""
Protocol Models - Phase 1 Foundation

Tables:
- protocols: Main protocol/workspace for game analysis
- protocol_items: Timeline entries (stats snapshots, notes, events)
- protocol_targets: Links to games/teams/players
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models import Base


def _id(prefix: str) -> str:
    """Generate prefixed UUID."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Protocol(Base):
    """A protocol (game analysis workspace) linked to a user."""
    __tablename__ = "protocols"

    id = Column(String, primary_key=True, default=lambda: _id("prot"))
    user_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)

    sport = Column(String, nullable=False, default="nba")
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")  # draft|active|archived
    description = Column(String, nullable=True)

    # Wiring Spec v1.0: Strategy engine fields
    rules = Column(JSON, nullable=False, default=list)  # Machine-readable rule definitions
    enabled = Column(Boolean, nullable=False, default=True)
    visibility = Column(String, nullable=False, default="private")  # private|public

    # Configuration and notes
    context = Column(JSON, nullable=False, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    targets = relationship("ProtocolTarget", back_populates="protocol", 
                          cascade="all, delete-orphan", lazy="dynamic")
    items = relationship("ProtocolItem", back_populates="protocol",
                        cascade="all, delete-orphan", lazy="dynamic",
                        order_by="desc(ProtocolItem.created_at)")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "sport": self.sport,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "rules": self.rules or [],
            "enabled": self.enabled,
            "visibility": self.visibility,
            "context": self.context or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "target_count": self.targets.count() if hasattr(self.targets, 'count') else len(list(self.targets)),
            "item_count": self.items.count() if hasattr(self.items, 'count') else len(list(self.items))
        }


class ProtocolTarget(Base):
    """Links protocol to external game/team/player identifiers."""
    __tablename__ = "protocol_targets"
    
    id = Column(String, primary_key=True, default=lambda: _id("ptgt"))
    protocol_id = Column(String, ForeignKey("protocols.id"), index=True, nullable=False)
    
    target_type = Column(String, nullable=False)  # game|team|player
    provider = Column(String, nullable=False)  # nba_api|internal
    external_id = Column(String, nullable=False)
    meta = Column(JSON, nullable=False, default=dict)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    protocol = relationship("Protocol", back_populates="targets")
    
    def to_dict(self):
        return {
            "id": self.id,
            "protocol_id": self.protocol_id,
            "target_type": self.target_type,
            "provider": self.provider,
            "external_id": self.external_id,
            "meta": self.meta or {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ProtocolItem(Base):
    """Timeline entries: stats snapshots, notes, system events."""
    __tablename__ = "protocol_items"
    
    id = Column(String, primary_key=True, default=lambda: _id("pitem"))
    protocol_id = Column(String, ForeignKey("protocols.id"), index=True, nullable=False)
    
    type = Column(String, nullable=False)  # stats_snapshot|note|system_event
    payload = Column(JSON, nullable=False, default=dict)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    protocol = relationship("Protocol", back_populates="items")
    
    def to_dict(self):
        return {
            "id": self.id,
            "protocol_id": self.protocol_id,
            "type": self.type,
            "payload": self.payload or {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
