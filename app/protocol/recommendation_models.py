"""
Recommendation Models for Phase 3

Stores AI-generated bet recommendations linked to protocols.
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.protocol.models import Base


def _id(prefix: str) -> str:
    """Generate prefixed UUID."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Recommendation(Base):
    """AI-generated bet recommendation for a protocol."""
    __tablename__ = "recommendations"
    
    id = Column(String, primary_key=True, default=lambda: _id("rec"))
    protocol_id = Column(String, ForeignKey("protocols.id"), index=True, nullable=False)
    user_id = Column(String, nullable=False, index=True)
    
    # Recommendation content
    bet_type = Column(String, nullable=False)  # spread, total, moneyline, player_prop, parlay
    description = Column(String, nullable=False)  # "Lakers -4.5", "Over 220.5", etc.
    confidence = Column(Integer, nullable=False, default=50)  # 0-100
    
    # Analysis
    reasoning = Column(JSON, nullable=False, default=list)  # List of reason strings
    factors = Column(JSON, nullable=False, default=dict)  # Key factors considered
    
    # Status
    status = Column(String, nullable=False, default="active")  # active|accepted|rejected|expired
    
    # Metadata
    odds_snapshot = Column(JSON, nullable=True)  # Odds at time of recommendation
    result = Column(String, nullable=True)  # win|loss|push (filled after game)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # When game starts
    
    def to_dict(self):
        return {
            "id": self.id,
            "protocol_id": self.protocol_id,
            "bet_type": self.bet_type,
            "description": self.description,
            "confidence": self.confidence,
            "reasoning": self.reasoning or [],
            "factors": self.factors or {},
            "status": self.status,
            "odds_snapshot": self.odds_snapshot,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


class Parlay(Base):
    """User-created parlay from recommendations."""
    __tablename__ = "parlays"
    
    id = Column(String, primary_key=True, default=lambda: _id("parlay"))
    user_id = Column(String, nullable=False, index=True)
    
    # Parlay content
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    recommendation_ids = Column(JSON, nullable=False, default=list)  # List of rec IDs
    
    # Calculated fields
    total_odds = Column(Integer, nullable=True)  # American odds (e.g., +450)
    implied_probability = Column(Float, nullable=True)  # 0.0-1.0
    
    # Status
    status = Column(String, nullable=False, default="draft")  # draft|shared|converted|expired
    
    # Sharing
    share_token = Column(String, nullable=True, index=True, unique=True)  # For public preview
    view_count = Column(Integer, default=0)
    
    # Conversion tracking
    converted_to_bet_id = Column(String, nullable=True)  # If user placed the bet
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "recommendation_ids": self.recommendation_ids or [],
            "total_odds": self.total_odds,
            "implied_probability": self.implied_probability,
            "status": self.status,
            "share_token": self.share_token,
            "view_count": self.view_count,
            "converted_to_bet_id": self.converted_to_bet_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
