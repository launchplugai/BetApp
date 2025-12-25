# core/models/claim.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.models.common import Value, ValueKind, LensRef, Baseline


def _require_prefix(value: str, prefix: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValueError(f"{field_name} must be a string starting with '{prefix}'")


def _ensure_utc(dt: datetime, field_name: str) -> datetime:
    if not isinstance(dt, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_dt(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return _ensure_utc(value, field_name)
    if isinstance(value, str):
        v = value.replace("Z", "+00:00")
        return _ensure_utc(datetime.fromisoformat(v), field_name)
    raise TypeError(f"{field_name} must be an ISO8601 string or datetime")


@dataclass(frozen=True, slots=True)
class Claim:
    """
    Atomic unit of meaning.
    A claim is: "something asserted about an organism through a lens."
    
    Per ARCHITECTURE.md v3:
    - Claims are the units of meaning
    - Mutations are the only way claims change
    - Lineage is tracked via lastMutationId
    """
    id: str
    organism_id: str
    lens_id: str
    lens: LensRef
    value: Value
    weight: float
    constraints: List[str] = field(default_factory=list)  # constraint IDs
    baseline: Optional[Baseline] = None
    last_mutation_id: Optional[str] = None
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        _require_prefix(self.id, "clm_", "id")
        _require_prefix(self.organism_id, "org_", "organism_id")
        _require_prefix(self.lens_id, "lns_", "lens_id")
        
        if not isinstance(self.lens, LensRef):
            raise TypeError("lens must be a LensRef")
        
        if not isinstance(self.value, Value):
            raise TypeError("value must be a Value")
        
        if not isinstance(self.weight, (int, float)):
            raise TypeError("weight must be a number")
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("weight must be between 0.0 and 1.0")
        
        if self.constraints is None:
            object.__setattr__(self, "constraints", [])
        if not isinstance(self.constraints, list):
            raise TypeError("constraints must be a list")
        
        if self.baseline is not None and not isinstance(self.baseline, Baseline):
            raise TypeError("baseline must be a Baseline or None")
        
        if self.last_mutation_id is not None:
            _require_prefix(self.last_mutation_id, "mut_", "last_mutation_id")
        
        if not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be a positive integer")
        
        object.__setattr__(self, "created_at", _ensure_utc(self.created_at, "created_at"))
        object.__setattr__(self, "updated_at", _ensure_utc(self.updated_at, "updated_at"))
        
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")

    def compute_drift(self) -> float:
        """
        Compute drift from baseline.
        Drift is always computed, never stored (per PRIMITIVES.md).
        """
        if self.baseline is None or self.baseline.value is None:
            return 0.0
        
        return self._distance(self.value, self.baseline.value)

    def compute_weighted_drift(self) -> float:
        """Compute drift weighted by claim weight."""
        return self.compute_drift() * self.weight

    @staticmethod
    def _distance(current: Value, baseline: Value) -> float:
        """
        Compute distance between two values.
        Per INTERACTIONS.md:
        - number: normalized absolute difference
        - enum: 0/1
        - bool: 0/1
        - string: 0/1 (exact match)
        - json: per-key diff (simplified to 0/1 for now)
        """
        if current.kind != baseline.kind:
            return 1.0  # Different kinds = maximum drift
        
        if current.kind in (ValueKind.ENUM, ValueKind.STRING, ValueKind.BOOL):
            return 0.0 if current.data == baseline.data else 1.0
        
        if current.kind == ValueKind.NUMBER:
            # Normalize to 0-1 range (assumes values are already normalized)
            # For unbounded numbers, cap the difference
            diff = abs(current.data - baseline.data)
            return min(1.0, diff)
        
        # JSON: simplified comparison
        return 0.0 if current.data == baseline.data else 1.0

    # ---------- API mapping (camelCase) ----------
    @classmethod
    def from_api(cls, data: Dict[str, Any]) -> "Claim":
        """Create from API payload (camelCase)."""
        lens_data = data.get("lens") or {}
        lens = LensRef.from_dict(lens_data)
        
        value = Value.from_dict(data["value"])
        
        baseline = None
        if data.get("baseline"):
            baseline = Baseline.from_dict(data["baseline"])
        
        return cls(
            id=data["id"],
            organism_id=data.get("organismId") or data.get("organism_id"),
            lens_id=data.get("lensId") or data.get("lens_id"),
            lens=lens,
            value=value,
            weight=data["weight"],
            constraints=list(data.get("constraints") or []),
            baseline=baseline,
            last_mutation_id=data.get("lastMutationId") or data.get("last_mutation_id"),
            version=data.get("version", 1),
            created_at=_parse_dt(data.get("createdAt") or data.get("created_at"), "created_at"),
            updated_at=_parse_dt(data.get("updatedAt") or data.get("updated_at"), "updated_at"),
        )

    def to_api(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "organismId": self.organism_id,
            "lensId": self.lens_id,
            "lens": self.lens.to_dict(),
            "value": self.value.to_dict(),
            "weight": self.weight,
            "constraints": list(self.constraints),
            "version": self.version,
            "createdAt": self.created_at.isoformat().replace("+00:00", "Z"),
            "updatedAt": self.updated_at.isoformat().replace("+00:00", "Z"),
        }
        if self.baseline:
            result["baseline"] = self.baseline.to_dict()
        if self.last_mutation_id:
            result["lastMutationId"] = self.last_mutation_id
        return result

    # ---------- Internal JSON (snake_case) ----------
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Claim":
        """Create from internal JSON (snake_case)."""
        lens = LensRef.from_dict(data["lens"])
        value = Value.from_dict(data["value"])
        
        baseline = None
        if data.get("baseline"):
            baseline = Baseline.from_dict(data["baseline"])
        
        return cls(
            id=data["id"],
            organism_id=data["organism_id"],
            lens_id=data["lens_id"],
            lens=lens,
            value=value,
            weight=data["weight"],
            constraints=list(data.get("constraints") or []),
            baseline=baseline,
            last_mutation_id=data.get("last_mutation_id"),
            version=data.get("version", 1),
            created_at=_parse_dt(data["created_at"], "created_at"),
            updated_at=_parse_dt(data["updated_at"], "updated_at"),
        )

    def to_json(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "organism_id": self.organism_id,
            "lens_id": self.lens_id,
            "lens": self.lens.to_dict(),
            "value": self.value.to_dict(),
            "weight": self.weight,
            "constraints": list(self.constraints),
            "version": self.version,
            "created_at": self.created_at.isoformat().replace("+00:00", "Z"),
            "updated_at": self.updated_at.isoformat().replace("+00:00", "Z"),
        }
        if self.baseline:
            result["baseline"] = self.baseline.to_dict()
        if self.last_mutation_id:
            result["last_mutation_id"] = self.last_mutation_id
        return result

    def with_mutation(
        self,
        value: Optional[Value] = None,
        weight: Optional[float] = None,
        baseline: Optional[Baseline] = None,
        mutation_id: str = None,
    ) -> "Claim":
        """
        Create a new Claim with updated fields.
        Used by mutation engine to create new version.
        """
        return Claim(
            id=self.id,
            organism_id=self.organism_id,
            lens_id=self.lens_id,
            lens=self.lens,
            value=value if value is not None else self.value,
            weight=weight if weight is not None else self.weight,
            constraints=list(self.constraints),
            baseline=baseline if baseline is not None else self.baseline,
            last_mutation_id=mutation_id or self.last_mutation_id,
            version=self.version + 1,
            created_at=self.created_at,
            updated_at=datetime.now(timezone.utc),
        )
