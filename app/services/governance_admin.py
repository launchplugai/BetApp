"""Admin-facing governed learning workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from app.db import session_scope
from app.repositories.governance import LearningControlRepository, ModelRegistryRepository


def list_learning_proposals(*, status: Optional[str] = None, limit: int = 20) -> list[dict]:
    """List proposals for admin inspection."""
    with session_scope() as session:
        repository = LearningControlRepository(session)
        return [proposal.to_dict() for proposal in repository.list_proposals(status=status, limit=limit)]


def get_learning_proposal(proposal_id: str) -> dict | None:
    """Return a single proposal if it exists."""
    with session_scope() as session:
        repository = LearningControlRepository(session)
        proposal = repository.get_proposal(proposal_id)
        return proposal.to_dict() if proposal else None


def list_promotion_audits(*, limit: int = 20) -> list[dict]:
    """List recent promotion audit records."""
    with session_scope() as session:
        repository = LearningControlRepository(session)
        return [record.to_dict() for record in repository.list_promotions(limit=limit)]


def _suggest_next_version(current_version: str | None, *, entity_type: str) -> str:
    """Suggest the next patch version while preserving existing prefix format."""
    if not current_version:
        default_prefix = {
            "dna_model": "dna_v",
            "protocol_library": "pl_v",
            "calibration": "cal_v",
            "recommendation_model": "rec_v",
        }.get(entity_type, "v")
        return f"{default_prefix}1.0.0"

    prefix, numeric = current_version.rsplit("v", 1) if "v" in current_version else ("", current_version)
    parts = numeric.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return current_version
    major, minor, patch = [int(part) for part in parts]
    return f"{prefix}v{major}.{minor}.{patch + 1}"


def get_version_hint(entity_type: str) -> dict:
    """Return current production version and a suggested next version for an entity type."""
    with session_scope() as session:
        repository = ModelRegistryRepository(session)
        active_entries = repository.list_by_type_and_status(entity_type=entity_type, status="production")
        active_entry = active_entries[0] if active_entries else None
        current_version = active_entry.version if active_entry else None
        rollback_version = active_entry.rollback_version if active_entry else None
        return {
            "entity_type": entity_type,
            "current_version": current_version,
            "suggested_version": _suggest_next_version(current_version, entity_type=entity_type),
            "rollback_version": rollback_version or current_version,
        }


def approve_learning_proposal(
    *,
    proposal_id: str,
    approved_by: str,
    old_version: str,
    new_version: str,
    rollback_version: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """
    Promote a reviewed proposal into the governed registry and audit log.

    This is intentionally explicit: version movement must be supplied by the caller.
    """
    with session_scope() as session:
        learning_repository = LearningControlRepository(session)
        registry_repository = ModelRegistryRepository(session)

        proposal = learning_repository.get_proposal(proposal_id)
        if proposal is None:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.status not in {"pending_review", "approved"}:
            raise ValueError(
                f"Proposal {proposal_id} must be pending_review or approved before promotion; got {proposal.status}"
            )

        target = proposal.target or {}
        entity_type = target.get("entityType", proposal.proposal_type)
        entity_name = target.get("entityName") or target.get("entityId") or proposal.proposal_type
        scope = proposal.model_scope or ["global"]

        for entry in registry_repository.list_by_type_and_status(entity_type=entity_type, status="production"):
            registry_repository.mark_status(entry, status="superseded")

        registry_entry = registry_repository.create(
            entity_type=entity_type,
            entity_name=entity_name,
            version=new_version,
            status="production",
            scope=scope,
            promoted_at=datetime.now(UTC),
            meta={
                "source_proposal_id": proposal.id,
                "old_version": old_version,
            },
        )
        registry_entry.rollback_version = rollback_version or old_version
        registry_entry.source_proposal_id = proposal.id

        proposal.status = "promoted"
        proposal.review = {
            **(proposal.review or {}),
            "required": True,
            "reviewedBy": approved_by,
            "reviewedAt": datetime.now(UTC).isoformat(),
            "decision": "approved",
            "notes": notes,
        }

        promotion = learning_repository.create_promotion(
            proposal_id=proposal.id,
            approved_by=approved_by,
            old_version=old_version,
            new_version=new_version,
            rollback_version=rollback_version or old_version,
            notes=notes,
            meta={
                "entity_type": entity_type,
                "entity_name": entity_name,
            },
        )

        return {
            "proposal": proposal.to_dict(),
            "promotion": promotion.to_dict(),
            "registry_entry": registry_entry.to_dict(),
        }


def rollback_promotion(
    *,
    promotion_id: str,
    rolled_back_by: str,
    notes: Optional[str] = None,
) -> dict:
    """Rollback a promoted registry version to its explicit rollback target."""
    with session_scope() as session:
        learning_repository = LearningControlRepository(session)
        registry_repository = ModelRegistryRepository(session)

        source_promotion = learning_repository.get_promotion(promotion_id)
        if source_promotion is None:
            raise ValueError(f"Promotion not found: {promotion_id}")

        rollback_version = source_promotion.rollback_version
        if not rollback_version:
            raise ValueError(f"Promotion {promotion_id} has no rollback target")

        source_meta = source_promotion.meta or {}
        if source_meta.get("rollback_event"):
            raise ValueError(f"Promotion {promotion_id} is already a rollback event")

        entity_type = source_meta.get("entity_type")
        entity_name = source_meta.get("entity_name")
        if not entity_type or not entity_name:
            raise ValueError(f"Promotion {promotion_id} is missing entity metadata")

        for entry in registry_repository.list_by_type_and_status(entity_type=entity_type, status="production"):
            registry_repository.mark_status(entry, status="rolled_back")

        rollback_registry_entry = registry_repository.create(
            entity_type=entity_type,
            entity_name=entity_name,
            version=rollback_version,
            status="production",
            scope=["global"],
            promoted_at=datetime.now(UTC),
            meta={
                "rollback_from": source_promotion.new_version,
                "source_promotion_id": source_promotion.id,
            },
        )
        rollback_registry_entry.rollback_version = source_promotion.old_version
        rollback_registry_entry.source_proposal_id = source_promotion.proposal_id

        rollback_record = learning_repository.create_promotion(
            proposal_id=source_promotion.proposal_id,
            approved_by=rolled_back_by,
            old_version=source_promotion.new_version,
            new_version=rollback_version,
            rollback_version=source_promotion.old_version,
            notes=notes or f"Rollback of promotion {promotion_id}",
            meta={
                "entity_type": entity_type,
                "entity_name": entity_name,
                "rollback_event": True,
                "source_promotion_id": source_promotion.id,
            },
        )

        source_promotion.meta = {
            **source_meta,
            "rolled_back": True,
            "rolled_back_by": rolled_back_by,
            "rolled_back_at": datetime.now(UTC).isoformat(),
            "rollback_record_id": rollback_record.id,
        }

        return {
            "source_promotion": source_promotion.to_dict(),
            "rollback_promotion": rollback_record.to_dict(),
            "registry_entry": rollback_registry_entry.to_dict(),
        }
