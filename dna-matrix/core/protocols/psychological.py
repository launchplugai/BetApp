# core/protocols/psychological.py
"""
Psychological Protocols — revenge games, momentum, narrative pressure.

Sports betting ignores psychology at its own risk.
These protocols capture motivational and narrative forces
that create performance variance beyond statistical baselines.
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.protocols.models import (
    Protocol,
    ProtocolCategory,
    ProtocolResult,
    RiskLevel,
)


class RevengeGameProtocol(Protocol):
    """
    Detects revenge game scenarios.

    Triggers when a player faces their former team, especially
    after a recent trade or contentious departure. Historical data
    shows usage rate spikes of ~3-5% in revenge games.
    """

    name = "revenge_game"
    category = ProtocolCategory.PSYCHOLOGICAL
    description = "Detects player revenge game motivation spikes"

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        revenge_players: List[Dict[str, Any]] = context.get("revenge_players", [])

        if not revenge_players:
            return self._no_trigger()

        signals = []
        for rp in revenge_players:
            player = rp.get("player", "Unknown")
            former_team = rp.get("former_team", "")
            current_team = rp.get("current_team", "")
            games_since_trade = rp.get("games_since_trade", 999)
            is_contentious = rp.get("is_contentious", False)

            if games_since_trade <= 5 or is_contentious:
                signals.append(self._signal(
                    risk_level=RiskLevel.MODERATE,
                    confidence=0.72,
                    fragility_delta=3.0,
                    explanation=f"{player} facing former team {former_team}"
                                f"{' (contentious departure)' if is_contentious else ''}. "
                                "Expect usage rate spike and heightened motivation — "
                                "player props may be undervalued, "
                                "but emotional play increases variance.",
                    evidence={
                        "player": player,
                        "former_team": former_team,
                        "current_team": current_team,
                        "games_since_trade": games_since_trade,
                        "is_contentious": is_contentious,
                        "expected_usage_spike": "3-5%",
                    },
                ))
            else:
                signals.append(self._signal(
                    risk_level=RiskLevel.LOW,
                    confidence=0.60,
                    fragility_delta=1.5,
                    explanation=f"{player} facing former team {former_team}. "
                                "Minor motivational factor — may see slight usage bump.",
                    evidence={
                        "player": player,
                        "former_team": former_team,
                    },
                ))

        return self._triggered(*signals)


class MomentumProtocol(Protocol):
    """
    Tracks win/loss streaks and evaluates whether momentum
    historically correlates with outcomes for each team.

    Does NOT blindly assume momentum always matters.
    Instead evaluates whether the team's historical pattern
    supports momentum continuation.
    """

    name = "momentum"
    category = ProtocolCategory.PSYCHOLOGICAL
    description = "Evaluates streak-based momentum and its reliability"

    STREAK_MODERATE = 3
    STREAK_HIGH = 5

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        signals = []

        for side in ("home", "away"):
            streak = context.get(f"{side}_streak", 0)
            team = context.get(f"{side}_team", side)
            clutch = context.get(f"{side}_clutch_rating", 0.5)

            abs_streak = abs(streak)
            direction = "winning" if streak > 0 else "losing"

            if abs_streak >= self.STREAK_HIGH:
                if streak > 0:
                    # Long win streak — fragile because regression is likely
                    signals.append(self._signal(
                        risk_level=RiskLevel.MODERATE,
                        confidence=0.68,
                        fragility_delta=3.0,
                        explanation=f"{team} on a {abs_streak}-game win streak. "
                                    "Extended streaks increase regression risk — "
                                    "the market may be overvaluing continuation.",
                        evidence={
                            "team": team,
                            "streak": streak,
                            "direction": direction,
                            "clutch_rating": clutch,
                            "implication": "regression_risk",
                        },
                    ))
                else:
                    # Long loss streak — potential value or continued collapse
                    signals.append(self._signal(
                        risk_level=RiskLevel.MODERATE,
                        confidence=0.65,
                        fragility_delta=2.5,
                        explanation=f"{team} on a {abs_streak}-game losing streak. "
                                    "Could be value opportunity or sign of deeper issues. "
                                    "Team morale and effort level become unpredictable.",
                        evidence={
                            "team": team,
                            "streak": streak,
                            "direction": direction,
                            "implication": "morale_uncertainty",
                        },
                    ))
            elif abs_streak >= self.STREAK_MODERATE:
                signals.append(self._signal(
                    risk_level=RiskLevel.LOW,
                    confidence=0.55,
                    fragility_delta=1.5,
                    explanation=f"{team} on a {abs_streak}-game {direction} streak. "
                                "Moderate momentum signal — monitor but don't overweight.",
                    evidence={
                        "team": team,
                        "streak": streak,
                        "direction": direction,
                    },
                ))

        if not signals:
            return self._no_trigger()
        return self._triggered(*signals)


PSYCHOLOGICAL_PROTOCOLS = [RevengeGameProtocol, MomentumProtocol]
