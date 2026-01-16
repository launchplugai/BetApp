# alerts/detector.py
"""
Delta detector for ContextSnapshot changes.

Compares previous and current snapshots to identify:
- Player status changes (especially worsening)
- Confidence drops
- Source availability issues
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from context.snapshot import ContextSnapshot, PlayerStatus


# Status severity ordering (higher = worse)
STATUS_SEVERITY = {
    PlayerStatus.AVAILABLE: 0,
    PlayerStatus.PROBABLE: 1,
    PlayerStatus.QUESTIONABLE: 2,
    PlayerStatus.DOUBTFUL: 3,
    PlayerStatus.OUT: 4,
    PlayerStatus.UNKNOWN: 2,  # Treat unknown as questionable-level concern
}


@dataclass(frozen=True)
class PlayerDelta:
    """Represents a change in player status."""

    player_name: str
    team: str
    previous_status: PlayerStatus
    current_status: PlayerStatus

    @property
    def is_worsened(self) -> bool:
        """True if status got worse (higher severity)."""
        prev_sev = STATUS_SEVERITY.get(self.previous_status, 0)
        curr_sev = STATUS_SEVERITY.get(self.current_status, 0)
        return curr_sev > prev_sev

    @property
    def is_improved(self) -> bool:
        """True if status got better (lower severity)."""
        prev_sev = STATUS_SEVERITY.get(self.previous_status, 0)
        curr_sev = STATUS_SEVERITY.get(self.current_status, 0)
        return curr_sev < prev_sev

    @property
    def severity_change(self) -> int:
        """Positive = worsened, negative = improved."""
        prev_sev = STATUS_SEVERITY.get(self.previous_status, 0)
        curr_sev = STATUS_SEVERITY.get(self.current_status, 0)
        return curr_sev - prev_sev


@dataclass(frozen=True)
class ConfidenceDelta:
    """Represents a change in data confidence."""

    previous_confidence: float
    current_confidence: float
    reason: str

    @property
    def is_dropped(self) -> bool:
        """True if confidence decreased."""
        return self.current_confidence < self.previous_confidence

    @property
    def drop_amount(self) -> float:
        """How much confidence dropped (positive = dropped)."""
        return self.previous_confidence - self.current_confidence


@dataclass(frozen=True)
class SourceDelta:
    """Represents a change in data source status."""

    previous_source: str
    current_source: str
    is_degraded: bool
    is_unreachable: bool
    missing_data: tuple[str, ...]


@dataclass(frozen=True)
class SnapshotDelta:
    """
    Complete delta between two snapshots.

    Collects all changes for alert generation.
    """

    player_changes: tuple[PlayerDelta, ...]
    confidence_change: Optional[ConfidenceDelta]
    source_change: Optional[SourceDelta]

    @property
    def has_changes(self) -> bool:
        """True if any changes detected."""
        return (
            len(self.player_changes) > 0
            or self.confidence_change is not None
            or self.source_change is not None
        )

    @property
    def worsened_players(self) -> tuple[PlayerDelta, ...]:
        """Get only players whose status worsened."""
        return tuple(p for p in self.player_changes if p.is_worsened)


def detect_delta(
    previous: Optional[ContextSnapshot],
    current: ContextSnapshot,
    player_names: Optional[list[str]] = None,
    team_names: Optional[list[str]] = None,
) -> SnapshotDelta:
    """
    Detect changes between two snapshots.

    Args:
        previous: Previous snapshot (None if first check)
        current: Current snapshot
        player_names: Optional filter - only check these players
        team_names: Optional filter - only check players on these teams

    Returns:
        SnapshotDelta with all detected changes
    """
    player_changes: list[PlayerDelta] = []
    confidence_change: Optional[ConfidenceDelta] = None
    source_change: Optional[SourceDelta] = None

    # If no previous snapshot, check for immediate concerns in current
    if previous is None:
        # Check for source issues on first load
        if current.source in ("sample-fallback", "error-fallback", "none"):
            source_change = SourceDelta(
                previous_source="none",
                current_source=current.source,
                is_degraded=current.source == "sample-fallback",
                is_unreachable=current.source in ("error-fallback", "none"),
                missing_data=current.missing_data,
            )

        # Check for already-problematic players in filter list
        if player_names:
            for name in player_names:
                player = current.get_player(name)
                if player and player.status in (
                    PlayerStatus.OUT,
                    PlayerStatus.DOUBTFUL,
                    PlayerStatus.QUESTIONABLE,
                ):
                    # Report as "new" concern (previous was assumed available)
                    player_changes.append(PlayerDelta(
                        player_name=player.player_name,
                        team=player.team,
                        previous_status=PlayerStatus.AVAILABLE,
                        current_status=player.status,
                    ))

        return SnapshotDelta(
            player_changes=tuple(player_changes),
            confidence_change=confidence_change,
            source_change=source_change,
        )

    # Compare player statuses
    players_to_check = set()

    # Add filtered players
    if player_names:
        players_to_check.update(name.lower() for name in player_names)

    # Add players from filtered teams
    if team_names:
        for team in team_names:
            for player in current.get_team_players(team):
                players_to_check.add(player.player_name.lower())
            for player in previous.get_team_players(team):
                players_to_check.add(player.player_name.lower())

    # If no filters, check all players that exist in either snapshot
    if not player_names and not team_names:
        for player in current.players:
            players_to_check.add(player.player_name.lower())
        for player in previous.players:
            players_to_check.add(player.player_name.lower())

    # Detect player status changes
    for player_name_lower in players_to_check:
        prev_player = previous.get_player(player_name_lower)
        curr_player = current.get_player(player_name_lower)

        # Get statuses (default to AVAILABLE if not in snapshot)
        prev_status = prev_player.status if prev_player else PlayerStatus.AVAILABLE
        curr_status = curr_player.status if curr_player else PlayerStatus.AVAILABLE

        # Get team (prefer current, fall back to previous)
        team = (curr_player.team if curr_player else
                prev_player.team if prev_player else "UNK")

        # Get canonical name
        name = (curr_player.player_name if curr_player else
                prev_player.player_name if prev_player else player_name_lower.title())

        # Record if changed
        if prev_status != curr_status:
            player_changes.append(PlayerDelta(
                player_name=name,
                team=team,
                previous_status=prev_status,
                current_status=curr_status,
            ))

    # Detect confidence changes
    if previous.confidence_hint != current.confidence_hint:
        # Determine reason
        if current.confidence_hint < previous.confidence_hint:
            if current.source in ("sample-fallback", "error-fallback"):
                reason = "Data source degraded to fallback"
            elif current.has_missing_data:
                reason = f"Missing data: {', '.join(current.missing_data[:3])}"
            else:
                reason = "Data quality decreased"
        else:
            reason = "Data quality improved"

        confidence_change = ConfidenceDelta(
            previous_confidence=previous.confidence_hint,
            current_confidence=current.confidence_hint,
            reason=reason,
        )

    # Detect source changes
    if previous.source != current.source:
        is_degraded = (
            previous.source in ("nba-official", "espn-injuries")
            and current.source in ("sample-fallback", "error-fallback")
        )
        is_unreachable = current.source in ("error-fallback", "none")

        source_change = SourceDelta(
            previous_source=previous.source,
            current_source=current.source,
            is_degraded=is_degraded,
            is_unreachable=is_unreachable,
            missing_data=current.missing_data,
        )

    return SnapshotDelta(
        player_changes=tuple(player_changes),
        confidence_change=confidence_change,
        source_change=source_change,
    )
