"""
Database models for DNA Bet Engine.
"""

from sqlalchemy import create_engine, Column, String, DateTime, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

Base = declarative_base()


class User(Base):
    """User account model."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: f"user_{uuid.uuid4().hex[:8]}")
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    tier = Column(String, default="GOOD")  # GOOD, BETTER, BEST
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    preferences = Column(JSON, default=dict)
    
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "tier": self.tier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "preferences": self.preferences or {}
        }


class Bet(Base):
    """Stored bet/parlay for history."""
    __tablename__ = "bets"
    
    id = Column(String, primary_key=True, default=lambda: f"bet_{uuid.uuid4().hex[:8]}")
    user_id = Column(String, nullable=False, index=True)
    input_text = Column(String, nullable=False)
    legs = Column(JSON, default=list)
    wager = Column(Integer, default=0)
    total_odds = Column(Integer)
    potential_payout = Column(Integer)
    
    # Result tracking
    status = Column(String, default="pending")  # pending, won, lost, void
    actual_payout = Column(Integer, nullable=True)
    
    # DNA analysis snapshot
    verdict = Column(String)
    confidence = Column(Integer)  # 0-100
    fragility = Column(Integer)   # 0-100
    
    created_at = Column(DateTime, default=datetime.utcnow)
    settled_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "input_text": self.input_text,
            "legs": self.legs,
            "wager": self.wager,
            "total_odds": self.total_odds,
            "potential_payout": self.potential_payout,
            "status": self.status,
            "actual_payout": self.actual_payout,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "fragility": self.fragility,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None
        }


# Database setup
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        # Use SQLite for now, can switch to PostgreSQL later
        _engine = create_engine(
            "sqlite:///./dna_bets.db",
            connect_args={"check_same_thread": False}
        )
    return _engine


def get_session():
    """Get a database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=get_engine())
