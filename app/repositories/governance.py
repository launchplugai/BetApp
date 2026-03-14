"""Repositories for governed learning and control-plane persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models import Bet, EvaluationLog, LearningProposal, ModelRegistryEntry, PromotionAuditRecord


class ModelRegistryRepository:
    """Read/write access for versioned governance entries."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_type_and_version(self, *, entity_type: str, version: str) -> Optional[ModelRegistryEntry]:
        return (
            self.session.query(ModelRegistryEntry)
            .filter(
                ModelRegistryEntry.entity_type == entity_type,
                ModelRegistryEntry.version == version,
            )
            .first()
        )

    def list_by_status(self, *, status: str) -> List[ModelRegistryEntry]:
        return (
            self.session.query(ModelRegistryEntry)
            .filter(ModelRegistryEntry.status == status)
            .all()
        )

    def list_by_type_and_status(self, *, entity_type: str, status: str) -> List[ModelRegistryEntry]:
        return (
            self.session.query(ModelRegistryEntry)
            .filter(
                ModelRegistryEntry.entity_type == entity_type,
                ModelRegistryEntry.status == status,
            )
            .all()
        )

    def count_all(self) -> int:
        return self.session.query(ModelRegistryEntry).count()

    def count_by_status(self, *, status: str) -> int:
        return (
            self.session.query(ModelRegistryEntry)
            .filter(ModelRegistryEntry.status == status)
            .count()
        )

    def create(
        self,
        *,
        entity_type: str,
        entity_name: str,
        version: str,
        status: str,
        scope: Iterable[str],
        promoted_at: Optional[datetime] = None,
        meta: Optional[dict] = None,
    ) -> ModelRegistryEntry:
        entry = ModelRegistryEntry(
            entity_type=entity_type,
            entity_name=entity_name,
            version=version,
            status=status,
            scope=list(scope),
            promoted_at=promoted_at,
            meta=meta or {},
        )
        self.session.add(entry)
        self.session.flush()
        return entry

    def mark_status(self, entry: ModelRegistryEntry, *, status: str) -> ModelRegistryEntry:
        entry.status = status
        return entry


class EvaluationLogRepository:
    """Read/write access for canonical evaluation logs."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_evaluation_id(self, evaluation_id: str) -> Optional[EvaluationLog]:
        return (
            self.session.query(EvaluationLog)
            .filter(EvaluationLog.evaluation_id == evaluation_id)
            .first()
        )

    def count_all(self) -> int:
        return self.session.query(EvaluationLog).count()

    def list_recent(self, *, limit: int = 5) -> List[EvaluationLog]:
        return (
            self.session.query(EvaluationLog)
            .order_by(EvaluationLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    def create(self, **kwargs) -> EvaluationLog:
        record = EvaluationLog(**kwargs)
        self.session.add(record)
        self.session.flush()
        return record

    def list_unsettled(self, *, limit: int = 200) -> List[EvaluationLog]:
        return (
            self.session.query(EvaluationLog)
            .filter(EvaluationLog.final_result.is_(None))
            .order_by(EvaluationLog.timestamp.desc())
            .limit(limit)
            .all()
        )


class BetRepository:
    """Read access for stored bets used in outcome enrichment."""

    def __init__(self, session: Session):
        self.session = session

    def find_latest_by_input_text(self, input_text: str) -> Optional[Bet]:
        return (
            self.session.query(Bet)
            .filter(Bet.input_text == input_text)
            .order_by(Bet.created_at.desc())
            .first()
        )

    def find_latest_by_evaluation_id(self, evaluation_id: str) -> Optional[Bet]:
        return (
            self.session.query(Bet)
            .filter(Bet.evaluation_id == evaluation_id)
            .order_by(Bet.created_at.desc())
            .first()
        )

    def list_recent_settled(self, *, limit: int = 500) -> List[Bet]:
        return (
            self.session.query(Bet)
            .filter(Bet.status.in_(["won", "lost", "void", "push"]))
            .order_by(Bet.settled_at.desc(), Bet.created_at.desc())
            .limit(limit)
            .all()
        )


class LearningControlRepository:
    """Read access for proposals and promotions shown in control-plane surfaces."""

    PROPOSAL_STATUSES = ("draft", "pending_review", "approved", "rejected", "promoted", "rolled_back")

    def __init__(self, session: Session):
        self.session = session

    def proposal_counts(self) -> Dict[str, int]:
        return {
            status: (
                self.session.query(LearningProposal)
                .filter(LearningProposal.status == status)
                .count()
            )
            for status in self.PROPOSAL_STATUSES
        }

    def list_proposals(self, *, status: Optional[str] = None, limit: int = 20) -> List[LearningProposal]:
        query = self.session.query(LearningProposal)
        if status:
            query = query.filter(LearningProposal.status == status)
        return query.order_by(LearningProposal.created_at.desc()).limit(limit).all()

    def get_proposal(self, proposal_id: str) -> Optional[LearningProposal]:
        return (
            self.session.query(LearningProposal)
            .filter(LearningProposal.id == proposal_id)
            .first()
        )

    def create_proposal(self, **kwargs) -> LearningProposal:
        proposal = LearningProposal(**kwargs)
        self.session.add(proposal)
        self.session.flush()
        return proposal

    def list_promotions(self, *, limit: int = 20) -> List[PromotionAuditRecord]:
        return (
            self.session.query(PromotionAuditRecord)
            .order_by(PromotionAuditRecord.promoted_at.desc())
            .limit(limit)
            .all()
        )

    def get_promotion(self, promotion_id: str) -> Optional[PromotionAuditRecord]:
        return (
            self.session.query(PromotionAuditRecord)
            .filter(PromotionAuditRecord.id == promotion_id)
            .first()
        )

    def promotion_count(self) -> int:
        return self.session.query(PromotionAuditRecord).count()

    def recent_promotions(self, *, limit: int = 5) -> List[PromotionAuditRecord]:
        return (
            self.session.query(PromotionAuditRecord)
            .order_by(PromotionAuditRecord.promoted_at.desc())
            .limit(limit)
            .all()
        )

    def create_promotion(self, **kwargs) -> PromotionAuditRecord:
        record = PromotionAuditRecord(**kwargs)
        self.session.add(record)
        self.session.flush()
        return record
