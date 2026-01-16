# context/snapshot.py
"""
ContextSnapshot Schema - Normalized context data model.

This is the canonical format for all external context data.
Providers fetch and parse data, then normalize it into this schema.

Key design principles:
- Additive only: context affects confidence, not core scoring
- Source-agnostic: same schema regardless of data source
- Cacheable: immutable snapshots with timestamps
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class PlayerStatus(Enum):
    """Player availability status (NBA standard designations)."""

    AVAILABLE = "available"       # No injury designation, expected to play
    PROBABLE = "probable"         # Minor concern, likely to play
    QUESTIONABLE = "questionable" # Uncertain, may or may not play
    DOUBTFUL = "doubtful"         # Unlikely to play
    OUT = "out"                   # Confirmed not playing
    UNKNOWN = "unknown"           # Status not reported


@dataclass(frozen=True)
class PlayerAvailability:
    """Individual player availability record."""

    player_id: str                      # Unique identifier (can be name if no ID)
    player_name: str                    # Display name
    team: str                           # Team abbreviation (e.g., "LAL", "BOS")
    status: PlayerStatus                # Current availability status
    reason: Optional[str] = None        # Injury description if applicable
    updated_at: Optional[datetime] = None  # When this status was last updated


@dataclass(frozen=True)
class ContextSnapshot:
    """
    Normalized snapshot of external context data.

    Immutable point-in-time capture of context that can affect
    evaluation confidence. Does NOT modify core scoring logic.

    Minimum fields per Sprint 3 spec:
    - sport: Sport this context applies to
    - as_of: When this snapshot was captured
    - source: Where the data came from
    - players: List of player availability records
    - missing_data: What we couldn't fetch (transparency)
    - confidence_hint: Simple adjustment guidance
    """

    # Required fields
    sport: str                          # e.g., "NBA"
    as_of: datetime                     # When snapshot was created
    source: str                         # Data source identifier

    # Player availability data
    players: tuple[PlayerAvailability, ...] = field(default_factory=tuple)

    # Transparency: what we don't know
    missing_data: tuple[str, ...] = field(default_factory=tuple)

    # Simple confidence adjustment hint
    # Positive = more confidence in evaluation, Negative = less
    # Range: -1.0 to 1.0 (additive modifier)
    confidence_hint: float = 0.0

    def __post_init__(self) -> None:
        """Validate confidence_hint is in valid range."""
        if not -1.0 <= self.confidence_hint <= 1.0:
            # Clamp to valid range rather than raise
            object.__setattr__(
                self,
                "confidence_hint",
                max(-1.0, min(1.0, self.confidence_hint))
            )

    def get_player(self, player_name: str) -> Optional[PlayerAvailability]:
        """Look up player by name (case-insensitive)."""
        name_lower = player_name.lower()
        for player in self.players:
            if player.player_name.lower() == name_lower:
                return player
        return None

    def get_team_players(self, team: str) -> tuple[PlayerAvailability, ...]:
        """Get all players for a team."""
        team_upper = team.upper()
        return tuple(p for p in self.players if p.team.upper() == team_upper)

    def get_unavailable_players(self) -> tuple[PlayerAvailability, ...]:
        """Get all players who are OUT or DOUBTFUL."""
        return tuple(
            p for p in self.players
            if p.status in (PlayerStatus.OUT, PlayerStatus.DOUBTFUL)
        )

    @property
    def has_missing_data(self) -> bool:
        """Check if any data is missing."""
        return len(self.missing_data) > 0

    @property
    def player_count(self) -> int:
        """Number of players in snapshot."""
        return len(self.players)


# Factory function for empty snapshot
def empty_snapshot(sport: str = "NBA", source: str = "none") -> ContextSnapshot:
    """Create an empty snapshot when no data is available."""
    return ContextSnapshot(
        sport=sport,
        as_of=datetime.utcnow(),
        source=source,
        players=(),
        missing_data=("No data source available",),
        confidence_hint=0.0,
    )
