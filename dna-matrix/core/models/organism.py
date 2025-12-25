# core/models/organism.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


def _require_prefix(value: str, prefix: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValueError(f"{field_name} must be a string starting with '{prefix}'")


def _ensure_utc(dt: datetime, field_name: str) -> datetime:
    if not isinstance(dt, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if dt.tzinfo is None:
        # Treat naive datetimes as UTC to avoid silent local-time bugs
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_dt(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return _ensure_utc(value, field_name)
    if isinstance(value, str):
        # Accept "Z" suffix (common in APIs)
        v = value.replace("Z", "+00:00")
        return _ensure_utc(datetime.fromisoformat(v), field_name)
    raise TypeError(f"{field_name} must be an ISO8601 string or datetime")


@dataclass(frozen=True, slots=True)
class Organism:
    """
    SDK Spec v0.1 Organism model:
      id, organism_type, name, tags, created_at, updated_at
    
    Frozen dataclass for immutability.
    All mutations happen through the mutation engine.
    """
    id: str
    organism_type: str
    name: str
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _require_prefix(self.id, "org_", "id")

        if not isinstance(self.organism_type, str) or not self.organism_type.strip():
            raise ValueError("organism_type must be a non-empty string")

        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")

        if self.tags is None:
            object.__setattr__(self, "tags", [])
        if not isinstance(self.tags, list) or any(not isinstance(t, str) for t in self.tags):
            raise TypeError("tags must be a list[str]")

        object.__setattr__(self, "created_at", _ensure_utc(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", _ensure_utc(self.updated_at, "updated_at"))

        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")

    # ---------- API mapping (camelCase) ----------
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "Organism":
        """
        Accepts API shape:
          organismType, createdAt, updatedAt
        """
        if not isinstance(data, dict):
            raise TypeError("data must be a dict")

        return cls(
            id=data["id"],
            organism_type=data.get("organismType") or data.get("organism_type"),
            name=data["name"],
            tags=list(data.get("tags") or []),
            created_at=_parse_dt(data.get("createdAt") or data.get("created_at"), "created_at"),
            updated_at=_parse_dt(data.get("updatedAt") or data.get("updated_at"), "updated_at"),
        )

    def to_api(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "organismType": self.organism_type,
            "name": self.name,
            "tags": list(self.tags),
            "createdAt": self.created_at.isoformat().replace("+00:00", "Z"),
            "updatedAt": self.updated_at.isoformat().replace("+00:00", "Z"),
        }

    # ---------- Internal JSON (snake_case) ----------
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Organism":
        if not isinstance(data, dict):
            raise TypeError("data must be a dict")

        return cls(
            id=data["id"],
            organism_type=data["organism_type"],
            name=data["name"],
            tags=list(data.get("tags") or []),
            created_at=_parse_dt(data["created_at"], "created_at"),
            updated_at=_parse_dt(data["updated_at"], "updated_at"),
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "organism_type": self.organism_type,
            "name": self.name,
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat().replace("+00:00", "Z"),
            "updated_at": self.updated_at.isoformat().replace("+00:00", "Z"),
        }
