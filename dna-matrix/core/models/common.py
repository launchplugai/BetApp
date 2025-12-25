# core/models/common.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ValueKind(str, Enum):
    """Types of claim values."""
    STRING = "string"
    NUMBER = "number"
    BOOL = "bool"
    ENUM = "enum"
    JSON = "json"


@dataclass(frozen=True, slots=True)
class Value:
    """
    A typed value container.
    Used for claim values and baseline values.
    """
    kind: ValueKind
    data: Any

    def __post_init__(self) -> None:
        # Normalize kind to enum
        if isinstance(self.kind, str):
            object.__setattr__(self, "kind", ValueKind(self.kind))
        
        # Type check data against kind
        if self.kind == ValueKind.STRING and not isinstance(self.data, str):
            raise TypeError(f"data must be str for kind=string, got {type(self.data)}")
        if self.kind == ValueKind.NUMBER and not isinstance(self.data, (int, float)):
            raise TypeError(f"data must be int/float for kind=number, got {type(self.data)}")
        if self.kind == ValueKind.BOOL and not isinstance(self.data, bool):
            raise TypeError(f"data must be bool for kind=bool, got {type(self.data)}")
        if self.kind == ValueKind.ENUM and not isinstance(self.data, str):
            raise TypeError(f"data must be str for kind=enum, got {type(self.data)}")
        # JSON kind accepts any serializable data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Value":
        """Create from dict with 'kind' and 'data' keys."""
        return cls(
            kind=ValueKind(data["kind"]),
            data=data["data"]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "data": self.data
        }
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Value):
            return False
        return self.kind == other.kind and self.data == other.data


@dataclass(frozen=True, slots=True)
class LensRef:
    """
    Reference to a lens (semantic key).
    cluster.key format, e.g., "brand.voice.tone"
    """
    cluster: str
    key: str

    def __post_init__(self) -> None:
        if not isinstance(self.cluster, str) or not self.cluster.strip():
            raise ValueError("cluster must be a non-empty string")
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValueError("key must be a non-empty string")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LensRef":
        return cls(
            cluster=data["cluster"],
            key=data["key"]
        )

    @classmethod
    def from_string(cls, s: str) -> "LensRef":
        """
        Parse from dot-notation string.
        First segment is cluster, rest is key.
        e.g., "brand.voice.tone" -> cluster="brand", key="voice.tone"
        """
        parts = s.split(".", 1)
        if len(parts) < 2:
            raise ValueError(f"Invalid lens string: {s}. Expected 'cluster.key' format.")
        return cls(cluster=parts[0], key=parts[1])

    def to_dict(self) -> Dict[str, str]:
        return {
            "cluster": self.cluster,
            "key": self.key
        }

    def to_string(self) -> str:
        """Convert to dot-notation string."""
        return f"{self.cluster}.{self.key}"

    def __str__(self) -> str:
        return self.to_string()


class ActorType(str, Enum):
    """Types of actors that can make changes."""
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


@dataclass(frozen=True, slots=True)
class Actor:
    """
    Who made a change.
    """
    type: ActorType
    id: str
    label: str

    def __post_init__(self) -> None:
        # Normalize type to enum
        if isinstance(self.type, str):
            object.__setattr__(self, "type", ActorType(self.type))
        
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id must be a non-empty string")
        if not isinstance(self.label, str):
            raise ValueError("label must be a string")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Actor":
        return cls(
            type=ActorType(data["type"]),
            id=data["id"],
            label=data.get("label", "")
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "type": self.type.value,
            "id": self.id,
            "label": self.label
        }


@dataclass(frozen=True, slots=True)
class TradeoffEntry:
    """
    Record of what was traded during a mutation or conflict resolution.
    """
    gave_up: Dict[str, Any]
    gained: Dict[str, Any]
    weight: float
    cost: Optional[str] = None
    justification: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.gave_up, dict):
            raise TypeError("gave_up must be a dict")
        if not isinstance(self.gained, dict):
            raise TypeError("gained must be a dict")
        if not isinstance(self.weight, (int, float)):
            raise TypeError("weight must be a number")
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("weight must be between 0.0 and 1.0")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TradeoffEntry":
        return cls(
            gave_up=data["gaveUp"] if "gaveUp" in data else data["gave_up"],
            gained=data["gained"],
            weight=data["weight"],
            cost=data.get("cost"),
            justification=data.get("justification")
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "gaveUp": self.gave_up,
            "gained": self.gained,
            "weight": self.weight,
        }
        if self.cost:
            result["cost"] = self.cost
        if self.justification:
            result["justification"] = self.justification
        return result


class BaselineMode(str, Enum):
    """How the baseline was established."""
    SNAPSHOT = "snapshot"
    DECLARED = "declared"
    IDEAL = "ideal"
    HISTORICAL = "historical"
    SELECTED = "selected"


@dataclass(frozen=True, slots=True)
class Baseline:
    """
    Reference point for drift calculation.
    """
    mode: BaselineMode
    ref: Optional[str] = None  # claimId, snapshotId, or None
    value: Optional[Value] = None
    captured_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        # Normalize mode to enum
        if isinstance(self.mode, str):
            object.__setattr__(self, "mode", BaselineMode(self.mode))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Baseline":
        value = None
        if data.get("value"):
            value = Value.from_dict(data["value"])
        
        captured_at = None
        captured_str = data.get("capturedAt") or data.get("captured_at")
        if captured_str:
            if isinstance(captured_str, datetime):
                captured_at = captured_str
            else:
                captured_at = datetime.fromisoformat(captured_str.replace("Z", "+00:00"))
        
        return cls(
            mode=BaselineMode(data["mode"]),
            ref=data.get("ref"),
            value=value,
            captured_at=captured_at
        )

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "mode": self.mode.value,
        }
        if self.ref:
            result["ref"] = self.ref
        if self.value:
            result["value"] = self.value.to_dict()
        if self.captured_at:
            result["capturedAt"] = self.captured_at.isoformat().replace("+00:00", "Z")
        return result
