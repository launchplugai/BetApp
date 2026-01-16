# context/apply.py
"""
Context Application - Convert snapshots to confidence modifiers.

This module translates ContextSnapshot data into actionable modifiers
that affect evaluation confidence WITHOUT modifying core engine logic.

Key principle: ADDITIVE ONLY
- Context adjusts confidence display/interpretation
- Core fragility scores remain unchanged
- All modifications are transparent and traceable
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from context.snapshot import ContextSnapshot, PlayerAvailability, PlayerStatus


@dataclass(frozen=True)
class ContextModifier:
    """
    Modifier derived from context data.

    Applied to confidence display, not core scoring.
    """

    # Adjustment to confidence (-1.0 to 1.0)
    # Negative = reduced confidence, Positive = increased confidence
    adjustment: float

    # Human-readable reason for the adjustment
    reason: str

    # Source of this modifier (for transparency)
    source: str

    # Affected players (if applicable)
    affected_players: tuple[str, ...] = ()


@dataclass(frozen=True)
class ContextImpact:
    """
    Aggregated impact of context on an evaluation.

    This is what gets displayed in the Confidence panel.
    """

    # Overall confidence adjustment (sum of modifiers, clamped)
    total_adjustment: float

    # Individual modifiers for transparency
    modifiers: tuple[ContextModifier, ...]

    # Summary for display
    summary: str

    # Any missing data that affects confidence
    missing_data: tuple[str, ...]

    # Whether context data is fresh
    is_fresh: bool


def apply_context(
    snapshot: ContextSnapshot,
    player_names: Optional[list[str]] = None,
    team_names: Optional[list[str]] = None,
) -> ContextImpact:
    """
    Apply context snapshot to derive confidence modifiers.

    Args:
        snapshot: Context data snapshot
        player_names: Players in the bet (for specific lookups)
        team_names: Teams in the bet (for team-level lookups)

    Returns:
        ContextImpact with modifiers and summary
    """
    modifiers: list[ContextModifier] = []

    # Check for missing data impact
    if snapshot.has_missing_data:
        modifiers.append(
            ContextModifier(
                adjustment=-0.1,
                reason="Some context data unavailable",
                source=snapshot.source,
                affected_players=(),
            )
        )

    # Check specific players if provided
    if player_names:
        player_modifiers = _check_players(snapshot, player_names)
        modifiers.extend(player_modifiers)

    # Check teams if provided
    if team_names:
        team_modifiers = _check_teams(snapshot, team_names)
        modifiers.extend(team_modifiers)

    # Add base confidence hint from snapshot
    if snapshot.confidence_hint != 0.0:
        modifiers.append(
            ContextModifier(
                adjustment=snapshot.confidence_hint,
                reason="Data source confidence",
                source=snapshot.source,
                affected_players=(),
            )
        )

    # Calculate total adjustment (clamped to -1.0 to 1.0)
    total = sum(m.adjustment for m in modifiers)
    total_clamped = max(-1.0, min(1.0, total))

    # Generate summary
    summary = _generate_summary(modifiers, total_clamped)

    return ContextImpact(
        total_adjustment=total_clamped,
        modifiers=tuple(modifiers),
        summary=summary,
        missing_data=snapshot.missing_data,
        is_fresh=True,  # Determined by cache in service layer
    )


def _check_players(
    snapshot: ContextSnapshot,
    player_names: list[str],
) -> list[ContextModifier]:
    """Check availability of specific players."""
    modifiers = []

    for name in player_names:
        player = snapshot.get_player(name)
        if player is None:
            # Player not in data - minor confidence reduction
            modifiers.append(
                ContextModifier(
                    adjustment=-0.05,
                    reason=f"No availability data for {name}",
                    source=snapshot.source,
                    affected_players=(name,),
                )
            )
            continue

        # Apply modifier based on status
        modifier = _status_to_modifier(player, snapshot.source)
        if modifier is not None:
            modifiers.append(modifier)

    return modifiers


def _check_teams(
    snapshot: ContextSnapshot,
    team_names: list[str],
) -> list[ContextModifier]:
    """Check team-level availability impacts."""
    modifiers = []

    for team in team_names:
        team_players = snapshot.get_team_players(team)
        if not team_players:
            continue

        # Check for significant injuries
        out_players = [
            p for p in team_players
            if p.status in (PlayerStatus.OUT, PlayerStatus.DOUBTFUL)
        ]

        if out_players:
            names = [p.player_name for p in out_players]
            # More OUT players = bigger impact
            adjustment = -0.1 * len(out_players)
            adjustment = max(-0.3, adjustment)  # Cap team impact

            modifiers.append(
                ContextModifier(
                    adjustment=adjustment,
                    reason=f"{team}: {len(out_players)} key player(s) out/doubtful",
                    source=snapshot.source,
                    affected_players=tuple(names),
                )
            )

    return modifiers


def _status_to_modifier(
    player: PlayerAvailability,
    source: str,
) -> Optional[ContextModifier]:
    """Convert player status to confidence modifier."""

    status_impacts = {
        PlayerStatus.OUT: (-0.15, "confirmed out"),
        PlayerStatus.DOUBTFUL: (-0.10, "doubtful to play"),
        PlayerStatus.QUESTIONABLE: (-0.05, "questionable"),
        PlayerStatus.PROBABLE: (0.0, None),  # No impact
        PlayerStatus.AVAILABLE: (0.02, None),  # Slight positive
        PlayerStatus.UNKNOWN: (-0.05, "status unknown"),
    }

    adjustment, reason_suffix = status_impacts.get(
        player.status,
        (0.0, None)
    )

    # Only create modifier if there's an impact
    if adjustment == 0.0 or reason_suffix is None:
        return None

    reason = f"{player.player_name} ({player.team}): {reason_suffix}"
    if player.reason:
        reason += f" - {player.reason}"

    return ContextModifier(
        adjustment=adjustment,
        reason=reason,
        source=source,
        affected_players=(player.player_name,),
    )


def _generate_summary(
    modifiers: list[ContextModifier],
    total: float,
) -> str:
    """Generate human-readable summary of context impact."""

    if not modifiers:
        return "No context factors affecting this evaluation."

    if total > 0.1:
        sentiment = "Favorable context"
    elif total < -0.1:
        sentiment = "Context concerns present"
    else:
        sentiment = "Context is neutral"

    # Count significant factors
    negative_count = sum(1 for m in modifiers if m.adjustment < 0)
    positive_count = sum(1 for m in modifiers if m.adjustment > 0)

    parts = [sentiment]
    if negative_count > 0:
        parts.append(f"{negative_count} concern(s)")
    if positive_count > 0:
        parts.append(f"{positive_count} positive factor(s)")

    return " | ".join(parts)
