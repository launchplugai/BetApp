"""Read-side governance summaries for the control plane."""

from __future__ import annotations

from app.db import session_scope
from app.repositories.governance import LearningControlRepository


def get_learning_control_summary() -> dict:
    """Return lightweight summaries for proposals and promotions."""
    with session_scope() as session:
        repository = LearningControlRepository(session)
        proposal_counts = repository.proposal_counts()
        promotion_count = repository.promotion_count()
        recent_promotions = repository.recent_promotions(limit=5)

        return {
            "proposal_counts": proposal_counts,
            "promotion_count": promotion_count,
            "recent_promotions": [
                {
                    "proposal_id": item.proposal_id,
                    "promoted_at": item.promoted_at.isoformat() if item.promoted_at else None,
                    "approved_by": item.approved_by,
                    "old_version": item.old_version,
                    "new_version": item.new_version,
                    "rollback_version": item.rollback_version,
                }
                for item in recent_promotions
            ],
        }
