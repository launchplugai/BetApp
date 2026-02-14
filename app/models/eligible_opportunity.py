"""
Eligible Opportunity model for storing opportunities that matched user criteria.
These are opportunities discovered by the Protocol Observer that passed user filters.
"""

from sqlalchemy import Column, String, DateTime, Boolean, JSON, Integer, Float
from datetime import datetime
import uuid
from . import Base


class EligibleOpportunity(Base):
    """Eligible Opportunity model - opportunities matching user DNA criteria."""
    __tablename__ = 'eligible_opportunities'

    id = Column(String, primary_key=True, default=lambda: f"opp_{uuid.uuid4().hex[:8]}")
    user_id = Column(String, nullable=False, index=True)
    
    # Source information
    protocol_id = Column(String, nullable=False, index=True)  # e.g., "nba_ml_v1"
    protocol_source = Column(String, nullable=False)  # e.g., "nba", "nfl", "mlb"
    
    # Game/Event details
    game_id = Column(String, nullable=False, index=True)
    sport = Column(String, nullable=False, index=True)
    league = Column(String, nullable=True)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    event_time = Column(DateTime, nullable=False)  # When the game starts
    
    # Opportunity details
    bet_type = Column(String, nullable=False)  # moneyline, spread, total, prop
    market = Column(String, nullable=False)  # e.g., "player_points", "game_spread"
    selection = Column(String, nullable=False)  # e.g., "Lakers -5.5", "LeBron Over 25.5"
    
    # Odds and pricing
    odds = Column(Integer, nullable=False)  # American odds (-110, +150, etc.)
    odds_decimal = Column(Float, nullable=True)  # Decimal odds (1.91, 2.50, etc.)
    line = Column(Float, nullable=True)  # Spread or total line
    
    # Confidence and scoring
    confidence_score = Column(Float, nullable=False)  # 0-100
    edge_percent = Column(Float, nullable=True)  # Estimated edge %
    misalignment_score = Column(Float, nullable=True)  # Market misalignment metric
    
    # DNA matching metadata
    matched_criteria = Column(JSON, default=list)  # Which criteria matched
    dna_snapshot_id = Column(String, nullable=True)  # User DNA at detection time
    
    # Status tracking
    status = Column(String, default="active")  # active, notified, expired, placed, rejected
    notification_sent = Column(Boolean, default=False)
    notification_id = Column(String, nullable=True)  # Link to notification_event
    
    # User action tracking
    viewed_at = Column(DateTime, nullable=True)
    dismissed_at = Column(DateTime, nullable=True)
    bet_placed_at = Column(DateTime, nullable=True)
    
    # Timestamps
    detected_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # When opportunity expires (game start)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "protocol_id": self.protocol_id,
            "protocol_source": self.protocol_source,
            "game_id": self.game_id,
            "sport": self.sport,
            "league": self.league,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "bet_type": self.bet_type,
            "market": self.market,
            "selection": self.selection,
            "odds": self.odds,
            "odds_decimal": self.odds_decimal,
            "line": self.line,
            "confidence_score": self.confidence_score,
            "edge_percent": self.edge_percent,
            "misalignment_score": self.misalignment_score,
            "matched_criteria": self.matched_criteria or [],
            "dna_snapshot_id": self.dna_snapshot_id,
            "status": self.status,
            "notification_sent": self.notification_sent,
            "notification_id": self.notification_id,
            "viewed_at": self.viewed_at.isoformat() if self.viewed_at else None,
            "dismissed_at": self.dismissed_at.isoformat() if self.dismissed_at else None,
            "bet_placed_at": self.bet_placed_at.isoformat() if self.bet_placed_at else None,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
    
    def mark_notified(self, notification_id: str):
        """Mark opportunity as notified."""
        self.notification_sent = True
        self.notification_id = notification_id
        self.status = "notified"
    
    def mark_viewed(self):
        """Mark opportunity as viewed by user."""
        self.viewed_at = datetime.utcnow()
    
    def mark_dismissed(self):
        """Mark opportunity as dismissed by user."""
        self.dismissed_at = datetime.utcnow()
        self.status = "rejected"
    
    def mark_placed(self):
        """Mark opportunity as bet placed."""
        self.bet_placed_at = datetime.utcnow()
        self.status = "placed"
    
    def mark_expired(self):
        """Mark opportunity as expired."""
        self.status = "expired"
    
    def is_expired(self) -> bool:
        """Check if opportunity has expired."""
        return datetime.utcnow() >= self.expires_at
    
    def is_active(self) -> bool:
        """Check if opportunity is still active."""
        return self.status == "active" and not self.is_expired()
