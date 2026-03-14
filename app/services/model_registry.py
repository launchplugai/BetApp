"""Services for reading and seeding the governed model registry."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Dict

from app.db import get_app_database_backend, session_scope
from app.repositories.governance import ModelRegistryRepository

log = logging.getLogger(__name__)

DEFAULT_ACTIVE_VERSIONS = (
    {
        "entity_type": "dna_model",
        "entity_name": "DNA Scoring Model",
        "version": "dna_v1.0.0",
        "status": "production",
        "scope": ["global"],
    },
    {
        "entity_type": "protocol_library",
        "entity_name": "Protocol Library",
        "version": "pl_v1.0.0",
        "status": "production",
        "scope": ["global"],
    },
    {
        "entity_type": "calibration",
        "entity_name": "Calibration Table",
        "version": "cal_v1.0.0",
        "status": "production",
        "scope": ["global"],
    },
    {
        "entity_type": "recommendation_model",
        "entity_name": "Recommendation Logic",
        "version": "rec_v1.0.0",
        "status": "production",
        "scope": ["global"],
    },
)


def _default_version_map() -> Dict[str, str]:
    return {
        "dna_model_version": "dna_v1.0.0",
        "protocol_library_version": "pl_v1.0.0",
        "calibration_version": "cal_v1.0.0",
        "recommendation_version": "rec_v1.0.0",
    }


def ensure_default_registry_entries() -> None:
    """Seed default active versions if the registry is empty for those types."""
    try:
        with session_scope() as session:
            repository = ModelRegistryRepository(session)
            for item in DEFAULT_ACTIVE_VERSIONS:
                existing = repository.get_by_type_and_version(
                    entity_type=item["entity_type"],
                    version=item["version"],
                )
                if existing:
                    continue
                repository.create(
                    entity_type=item["entity_type"],
                    entity_name=item["entity_name"],
                    version=item["version"],
                    status=item["status"],
                    scope=item["scope"],
                    promoted_at=datetime.now(UTC),
                    meta={"seeded": True},
                )
    except Exception as exc:  # pragma: no cover - best-effort guard
        log.warning("Model registry seed skipped: %s", exc)


def get_active_model_versions() -> Dict[str, str]:
    """Return the active production versions used for evaluation logging."""
    ensure_default_registry_entries()

    try:
        with session_scope() as session:
            repository = ModelRegistryRepository(session)
            entries = repository.list_by_status(status="production")
            versions = {entry.entity_type: entry.version for entry in entries}
            default_versions = _default_version_map()
            return {
                "dna_model_version": versions.get("dna_model", default_versions["dna_model_version"]),
                "protocol_library_version": versions.get("protocol_library", default_versions["protocol_library_version"]),
                "calibration_version": versions.get("calibration", default_versions["calibration_version"]),
                "recommendation_version": versions.get("recommendation_model", default_versions["recommendation_version"]),
            }
    except Exception as exc:  # pragma: no cover - best-effort guard
        log.warning("Model registry read failed, using defaults: %s", exc)
        return _default_version_map()


def get_governance_summary() -> Dict[str, object]:
    """Return lightweight governance metadata for debug/admin introspection."""
    ensure_default_registry_entries()

    try:
        with session_scope() as session:
            repository = ModelRegistryRepository(session)
            total_registry_entries = repository.count_all()
            production_entries = repository.count_by_status(status="production")
            active_versions = get_active_model_versions()
            return {
                "total_registry_entries": total_registry_entries,
                "production_entries": production_entries,
                "app_database_backend": get_app_database_backend(),
                "active_versions": active_versions,
            }
    except Exception as exc:  # pragma: no cover - best-effort guard
        log.warning("Governance summary unavailable, using defaults: %s", exc)
        return {
            "total_registry_entries": 0,
            "production_entries": 0,
            "app_database_backend": get_app_database_backend(),
            "active_versions": _default_version_map(),
        }
