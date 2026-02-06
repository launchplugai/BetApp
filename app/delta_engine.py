# app/delta_engine.py
"""
Change Delta Engine (Ticket 38B-B)

Compares structural snapshots and produces human-readable delta sentences.

Design Principles:
1. Deterministic — same snapshots → same delta sentence
2. Single sentence — exactly one sentence describing change
3. Leg matching by stable leg_id (from Ticket 37)
4. No delta on first evaluation (no previous snapshot)

Delta Contract:
{
  "has_delta": bool,
  "delta_sentence": str | None,
  "changes_detected": [str, ...]  # List of change types
}
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SnapshotDelta:
    """
    Result of comparing two structural snapshots.

    Attributes:
        has_delta: True if any changes detected
        delta_sentence: Single sentence describing changes (None if no changes)
        changes_detected: List of change types (e.g., "leg_removed", "correlation_added")
    """
    has_delta: bool
    delta_sentence: Optional[str]
    changes_detected: tuple[str, ...]

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "has_delta": self.has_delta,
            "delta_sentence": self.delta_sentence,
            "changes_detected": list(self.changes_detected),
        }


def compute_snapshot_delta(
    previous: Optional[dict],
    current: dict,
) -> SnapshotDelta:
    """
    Compare two structural snapshots and generate a delta.

    Args:
        previous: Previous snapshot (None if first evaluation)
        current: Current snapshot (just generated)

    Returns:
        SnapshotDelta with has_delta, delta_sentence, and changes_detected

    Design:
        - Returns no delta if previous is None
        - Matches legs by leg_id (stable identifier)
        - Generates exactly one sentence summarizing changes
        - Deterministic template-based generation
    """
    # No previous snapshot = no delta (first evaluation)
    if previous is None:
        return SnapshotDelta(
            has_delta=False,
            delta_sentence=None,
            changes_detected=(),
        )

    changes = []

    # Compare leg counts
    prev_leg_count = previous.get("leg_count", 0)
    curr_leg_count = current.get("leg_count", 0)

    if curr_leg_count < prev_leg_count:
        removed_count = prev_leg_count - curr_leg_count
        changes.append(f"leg_removed:{removed_count}")
    elif curr_leg_count > prev_leg_count:
        added_count = curr_leg_count - prev_leg_count
        changes.append(f"leg_added:{added_count}")

    # Compare leg types (composition change even if count same)
    prev_leg_ids = set(previous.get("leg_ids", []))
    curr_leg_ids = set(current.get("leg_ids", []))

    removed_legs = prev_leg_ids - curr_leg_ids
    added_legs = curr_leg_ids - prev_leg_ids

    if removed_legs and not changes:  # If not already counted in leg_count
        changes.append(f"leg_replaced:{len(removed_legs)}")

    # Compare correlation flags
    prev_flags = set(previous.get("correlation_flags", []))
    curr_flags = set(current.get("correlation_flags", []))

    added_flags = curr_flags - prev_flags
    removed_flags = prev_flags - curr_flags

    if added_flags:
        changes.append(f"correlation_added:{','.join(sorted(added_flags))}")
    if removed_flags:
        changes.append(f"correlation_removed:{','.join(sorted(removed_flags))}")

    # Compare volatility sources
    prev_sources = set(previous.get("volatility_sources", []))
    curr_sources = set(current.get("volatility_sources", []))

    added_sources = curr_sources - prev_sources
    removed_sources = prev_sources - curr_sources

    if added_sources:
        changes.append(f"volatility_added:{','.join(sorted(added_sources))}")
    if removed_sources:
        changes.append(f"volatility_removed:{','.join(sorted(removed_sources))}")

    # No changes detected
    if not changes:
        return SnapshotDelta(
            has_delta=False,
            delta_sentence=None,
            changes_detected=(),
        )

    # Generate single sentence from changes
    delta_sentence = _generate_delta_sentence(changes, prev_leg_count, curr_leg_count)

    return SnapshotDelta(
        has_delta=True,
        delta_sentence=delta_sentence,
        changes_detected=tuple(changes),
    )


def _generate_delta_sentence(
    changes: list[str],
    prev_leg_count: int,
    curr_leg_count: int,
) -> str:
    """
    Generate a single sentence from detected changes.

    Uses deterministic templates based on change types.

    Args:
        changes: List of change descriptors (e.g., "leg_removed:1")
        prev_leg_count: Previous leg count
        curr_leg_count: Current leg count

    Returns:
        Single sentence describing changes
    """
    # Parse changes into structured data
    leg_removed = 0
    leg_added = 0
    leg_replaced = 0
    correlation_changes = []
    volatility_changes = []

    for change in changes:
        if change.startswith("leg_removed:"):
            leg_removed = int(change.split(":", 1)[1])
        elif change.startswith("leg_added:"):
            leg_added = int(change.split(":", 1)[1])
        elif change.startswith("leg_replaced:"):
            leg_replaced = int(change.split(":", 1)[1])
        elif change.startswith("correlation_"):
            correlation_changes.append(change)
        elif change.startswith("volatility_"):
            volatility_changes.append(change)

    # Build sentence components
    parts = []

    # Leg changes
    if leg_removed > 0:
        leg_word = "leg" if leg_removed == 1 else "legs"
        parts.append(f"removed {leg_removed} {leg_word}")
    
    if leg_added > 0:
        leg_word = "leg" if leg_added == 1 else "legs"
        parts.append(f"added {leg_added} {leg_word}")

    if leg_replaced > 0 and leg_removed == 0 and leg_added == 0:
        # Replacement without count change
        leg_word = "leg" if leg_replaced == 1 else "legs"
        parts.append(f"replaced {leg_replaced} {leg_word}")

    # Correlation changes
    for corr_change in correlation_changes:
        if corr_change.startswith("correlation_added:"):
            flag = corr_change.split(":", 1)[1]
            parts.append(f"added {flag} correlation")
        elif corr_change.startswith("correlation_removed:"):
            flag = corr_change.split(":", 1)[1]
            parts.append(f"removed {flag} correlation")

    # Volatility changes
    for vol_change in volatility_changes:
        if vol_change.startswith("volatility_added:"):
            source = vol_change.split(":", 1)[1]
            # Make it readable
            readable = source.replace("_", " ")
            parts.append(f"added {readable}")
        elif vol_change.startswith("volatility_removed:"):
            source = vol_change.split(":", 1)[1]
            readable = source.replace("_", " ")
            parts.append(f"removed {readable}")

    # Combine parts into sentence
    if not parts:
        return "Structure unchanged."

    if len(parts) == 1:
        return f"You {parts[0]}."

    if len(parts) == 2:
        return f"You {parts[0]} and {parts[1]}."

    # 3+ parts
    return f"You {', '.join(parts[:-1])}, and {parts[-1]}."


def store_snapshot_for_session(
    session_id: str,
    snapshot: dict,
) -> None:
    """
    Store snapshot for later comparison.

    Note: This is a placeholder. Actual storage would use:
    - Session storage (if available)
    - In-memory cache with TTL
    - Redis or similar for production

    For now, we'll use a simple in-memory dict.
    """
    # Import here to avoid circular dependency
    global _snapshot_storage
    if "_snapshot_storage" not in globals():
        _snapshot_storage = {}
    
    _snapshot_storage[session_id] = snapshot


def get_previous_snapshot_for_session(
    session_id: str,
) -> Optional[dict]:
    """
    Retrieve previous snapshot for session.

    Returns:
        Previous snapshot dict, or None if not found
    """
    global _snapshot_storage
    if "_snapshot_storage" not in globals():
        return None
    
    return _snapshot_storage.get(session_id)


# Module-level storage (temporary, for MVP)
_snapshot_storage: dict[str, dict] = {}


# =============================================================================
# S7-B: Confidence Trend Tracking
# =============================================================================

# Signal ordinal mapping (higher = better)
_SIGNAL_ORDER = {"red": 0, "yellow": 1, "green": 2, "blue": 3}


def store_signal_for_session(
    session_id: str,
    signal_info: dict,
) -> None:
    """
    Store signal info for trend comparison.

    Args:
        session_id: Session identifier (parlay_id)
        signal_info: Current signal info dict with 'signal' and 'fragilityScore'
    """
    global _signal_storage
    if "_signal_storage" not in globals():
        _signal_storage = {}
    
    _signal_storage[session_id] = {
        "signal": signal_info.get("signal", "yellow"),
        "fragility_score": signal_info.get("fragilityScore", 50),
    }


def get_previous_signal_for_session(
    session_id: str,
) -> Optional[dict]:
    """
    Retrieve previous signal info for session.

    Returns:
        Previous signal dict with 'signal' and 'fragility_score', or None
    """
    global _signal_storage
    if "_signal_storage" not in globals():
        return None
    
    return _signal_storage.get(session_id)


def compute_confidence_trend(
    previous_signal: Optional[dict],
    current_signal: dict,
) -> dict:
    """
    S7-B: Compute confidence trend between evaluations.

    Compares signal level and fragility score to determine if confidence
    has improved, softened, or remained unchanged.

    Args:
        previous_signal: Previous evaluation's signal info (or None for first eval)
        current_signal: Current evaluation's signal info

    Returns:
        dict with:
        - has_trend: bool (False if first evaluation)
        - trend: str ("improved", "softened", "unchanged")
        - trend_text: str (human-readable description, subtle)
    """
    if previous_signal is None:
        return {
            "has_trend": False,
            "trend": None,
            "trend_text": None,
        }

    prev_signal = previous_signal.get("signal", "yellow")
    curr_signal = current_signal.get("signal", "yellow")
    prev_score = previous_signal.get("fragility_score", 50)
    curr_score = current_signal.get("fragilityScore", 50)

    prev_order = _SIGNAL_ORDER.get(prev_signal, 1)
    curr_order = _SIGNAL_ORDER.get(curr_signal, 1)

    # Determine trend based on signal change and fragility score
    if curr_order > prev_order:
        trend = "improved"
        trend_text = "Confidence has strengthened since your last evaluation"
    elif curr_order < prev_order:
        trend = "softened"
        trend_text = "Confidence has softened since your last evaluation"
    else:
        # Same signal level - compare fragility scores
        # Lower fragility = better (more confident)
        score_diff = prev_score - curr_score
        if score_diff > 2:  # Meaningful improvement (lower fragility)
            trend = "improved"
            trend_text = "Slightly more confident than your last evaluation"
        elif score_diff < -2:  # Meaningful softening (higher fragility)
            trend = "softened"
            trend_text = "Slightly less confident than your last evaluation"
        else:
            trend = "unchanged"
            trend_text = "Confidence level is similar to your last evaluation"

    return {
        "has_trend": True,
        "trend": trend,
        "trend_text": trend_text,
    }


# Module-level storage for signal tracking
_signal_storage: dict[str, dict] = {}
