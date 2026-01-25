# app/history_store.py
"""
In-memory history store for evaluation results.

Ticket 6: Minimum viable history implementation.
Stores evaluation results without requiring authentication.

Note: This is an in-memory store. Data is lost on server restart.
For production, migrate to persistence/evaluations.py with proper DB backing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4


@dataclass
class HistoryItem:
    """
    Represents a saved evaluation result.

    Uses signalInfo from pipeline as single source of truth.
    """
    id: str
    created_at: str  # ISO8601 string
    input_text: str
    sport: Optional[str]
    signal: str  # blue|green|yellow|red
    label: str  # Strong|Solid|Fixable|Fragile
    grade: str  # A|B|C|D
    fragility_score: float
    # Store raw evaluation for re-evaluate/edit
    raw_evaluation: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "id": self.id,
            "createdAt": self.created_at,
            "inputText": self.input_text,
            "sport": self.sport,
            "signal": self.signal,
            "label": self.label,
            "grade": self.grade,
            "fragilityScore": self.fragility_score,
        }

    def to_dict_with_raw(self) -> dict:
        """Convert to dict including raw evaluation."""
        result = self.to_dict()
        result["raw"] = self.raw_evaluation
        return result


class HistoryStore:
    """
    In-memory store for evaluation history.

    Thread-safe for basic operations.
    Items stored in reverse chronological order (newest first).
    """

    def __init__(self, max_items: int = 100):
        """
        Initialize history store.

        Args:
            max_items: Maximum items to keep (oldest evicted when exceeded)
        """
        self._items: Dict[str, HistoryItem] = {}
        self._order: List[str] = []  # IDs in reverse chronological order
        self._max_items = max_items

    def add(self, item: HistoryItem) -> HistoryItem:
        """
        Add a history item.

        Args:
            item: HistoryItem to add

        Returns:
            The added item
        """
        self._items[item.id] = item
        self._order.insert(0, item.id)  # Newest first

        # Evict oldest if over limit
        while len(self._order) > self._max_items:
            oldest_id = self._order.pop()
            del self._items[oldest_id]

        return item

    def list(self, limit: int = 50) -> List[HistoryItem]:
        """
        Get history items in reverse chronological order.

        Args:
            limit: Maximum items to return

        Returns:
            List of HistoryItem objects
        """
        result = []
        for item_id in self._order[:limit]:
            if item_id in self._items:
                result.append(self._items[item_id])
        return result

    def get(self, item_id: str) -> Optional[HistoryItem]:
        """
        Get a specific history item by ID.

        Args:
            item_id: Item ID to retrieve

        Returns:
            HistoryItem or None if not found
        """
        return self._items.get(item_id)

    def clear(self) -> int:
        """
        Clear all history items.

        Returns:
            Number of items cleared
        """
        count = len(self._items)
        self._items.clear()
        self._order.clear()
        return count

    def count(self) -> int:
        """Get number of items in store."""
        return len(self._items)


def create_history_item(
    evaluation_result: dict,
    input_text: str,
) -> HistoryItem:
    """
    Create a HistoryItem from an evaluation result.

    Uses signalInfo as single source of truth for signal/label/grade.

    Args:
        evaluation_result: Full evaluation response dict
        input_text: Original input text

    Returns:
        HistoryItem ready to be stored
    """
    signal_info = evaluation_result.get("signalInfo", {})

    # Extract signal info (single source of truth)
    signal = signal_info.get("signal", "green")
    label = signal_info.get("label", "Solid")
    grade = signal_info.get("grade", "B")
    fragility_score = signal_info.get("fragilityScore", 0)

    # Try to extract sport from input (basic heuristic)
    sport = None
    input_lower = input_text.lower()
    if any(word in input_lower for word in ["nba", "lakers", "celtics", "basketball"]):
        sport = "NBA"
    elif any(word in input_lower for word in ["nfl", "chiefs", "eagles", "football"]):
        sport = "NFL"
    elif any(word in input_lower for word in ["mlb", "yankees", "dodgers", "baseball"]):
        sport = "MLB"
    elif any(word in input_lower for word in ["nhl", "hockey", "bruins", "rangers"]):
        sport = "NHL"

    return HistoryItem(
        id=str(uuid4()),
        created_at=datetime.now(timezone.utc).isoformat(),
        input_text=input_text,
        sport=sport,
        signal=signal,
        label=label,
        grade=grade,
        fragility_score=fragility_score,
        raw_evaluation=evaluation_result,
    )


# Module-level singleton store
_store: Optional[HistoryStore] = None


def get_history_store() -> HistoryStore:
    """Get the global history store singleton."""
    global _store
    if _store is None:
        _store = HistoryStore()
    return _store
