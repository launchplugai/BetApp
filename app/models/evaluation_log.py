"""Evaluation log model for governed learning and auditability."""

from datetime import UTC, datetime
import uuid

from sqlalchemy import Column, DateTime, Integer, JSON, String

from . import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for defaults."""
    return datetime.now(UTC)


class EvaluationLog(Base):
    """Canonical evaluation event log."""

    __tablename__ = "evaluation_logs"

    id = Column(String, primary_key=True, default=lambda: f"elog_{uuid.uuid4().hex[:10]}")
    evaluation_id = Column(String, nullable=False, unique=True, index=True)
    bet_id = Column(String, nullable=True, index=True)
    user_id = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=utc_now, index=True)
    sport = Column(String, nullable=False, index=True)
    market_type = Column(String, nullable=False, index=True)
    bet_type = Column(String, nullable=True)
    legs = Column(Integer, nullable=False)
    stake = Column(Integer, nullable=True)
    odds_snapshot = Column(JSON, nullable=False, default=dict)
    best_book = Column(String, nullable=True)
    edge_score = Column(Integer, nullable=True)
    confidence_score = Column(Integer, nullable=False)
    fragility_score = Column(Integer, nullable=False)
    stability_score = Column(Integer, nullable=False)
    dna_mode = Column(String, nullable=False)
    triggered_protocols = Column(JSON, nullable=False, default=list)
    recommendation_type = Column(String, nullable=False)
    recommendation_details = Column(JSON, nullable=False, default=dict)
    user_action = Column(String, nullable=False, default="view_only")
    final_result = Column(String, nullable=True)
    legs_won = Column(Integer, nullable=True)
    legs_lost = Column(Integer, nullable=True)
    settlement_timestamp = Column(DateTime, nullable=True)
    dna_model_version = Column(String, nullable=False)
    protocol_library_version = Column(String, nullable=False)
    calibration_version = Column(String, nullable=False)
    recommendation_version = Column(String, nullable=False)
    meta = Column("metadata", JSON, nullable=False, default=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "evaluation_id": self.evaluation_id,
            "bet_id": self.bet_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "sport": self.sport,
            "market_type": self.market_type,
            "bet_type": self.bet_type,
            "legs": self.legs,
            "stake": self.stake,
            "odds_snapshot": self.odds_snapshot or {},
            "best_book": self.best_book,
            "edge_score": self.edge_score,
            "confidence_score": self.confidence_score,
            "fragility_score": self.fragility_score,
            "stability_score": self.stability_score,
            "dna_mode": self.dna_mode,
            "triggered_protocols": self.triggered_protocols or [],
            "recommendation_type": self.recommendation_type,
            "recommendation_details": self.recommendation_details or {},
            "user_action": self.user_action,
            "final_result": self.final_result,
            "legs_won": self.legs_won,
            "legs_lost": self.legs_lost,
            "settlement_timestamp": self.settlement_timestamp.isoformat() if self.settlement_timestamp else None,
            "dna_model_version": self.dna_model_version,
            "protocol_library_version": self.protocol_library_version,
            "calibration_version": self.calibration_version,
            "recommendation_version": self.recommendation_version,
            "metadata": self.meta or {},
        }
