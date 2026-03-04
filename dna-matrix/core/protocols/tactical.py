# core/protocols/tactical.py
"""
Tactical Protocols — pace mismatches, defensive gaps, matchup dynamics.

These examine how teams interact strategically, detecting situations
where the matchup itself creates exploitable or dangerous conditions.
"""
from __future__ import annotations

from typing import Any, Dict

from core.protocols.models import (
    Protocol,
    ProtocolCategory,
    ProtocolResult,
    RiskLevel,
)


class PaceShockProtocol(Protocol):
    """
    Detects large pace mismatches between teams.

    When two teams with significantly different paces collide,
    totals become volatile and possession counts get mispriced.
    A delta of 6+ possessions per game is meaningful.
    """

    name = "pace_shock"
    category = ProtocolCategory.TACTICAL
    description = "Detects pace mismatch volatility between teams"

    PACE_DELTA_MODERATE = 5
    PACE_DELTA_HIGH = 8

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        home_pace = context.get("home_pace", 0)
        away_pace = context.get("away_pace", 0)

        if not home_pace or not away_pace:
            return self._no_trigger()

        delta = abs(home_pace - away_pace)
        faster = context.get("home_team", "home") if home_pace > away_pace else context.get("away_team", "away")
        slower = context.get("away_team", "away") if home_pace > away_pace else context.get("home_team", "home")

        if delta >= self.PACE_DELTA_HIGH:
            return self._triggered(self._signal(
                risk_level=RiskLevel.HIGH,
                confidence=0.78,
                fragility_delta=5.0,
                explanation=f"Major pace mismatch: {faster} ({max(home_pace, away_pace):.1f}) "
                            f"vs {slower} ({min(home_pace, away_pace):.1f}). "
                            f"Delta of {delta:.1f} possessions creates scoring volatility. "
                            "Over/under bets are structurally unstable.",
                evidence={
                    "home_pace": home_pace,
                    "away_pace": away_pace,
                    "delta": round(delta, 1),
                    "faster_team": faster,
                    "implication": "totals_volatile",
                },
            ))
        elif delta >= self.PACE_DELTA_MODERATE:
            return self._triggered(self._signal(
                risk_level=RiskLevel.MODERATE,
                confidence=0.70,
                fragility_delta=3.0,
                explanation=f"Pace mismatch: {delta:.1f} possession delta between "
                            f"{faster} and {slower}. Totals may be slightly mispriced.",
                evidence={
                    "home_pace": home_pace,
                    "away_pace": away_pace,
                    "delta": round(delta, 1),
                },
            ))

        return self._no_trigger()


class DefensiveMismatchProtocol(Protocol):
    """
    Analyzes defensive rating gaps and key defender absences.

    When a team's defensive anchor is missing or one team has a
    significantly worse defensive rating, scoring opportunities spike.
    """

    name = "defensive_mismatch"
    category = ProtocolCategory.TACTICAL
    description = "Detects defensive matchup vulnerabilities"

    DEF_RATING_GAP_MODERATE = 3.0  # points per 100 possessions
    DEF_RATING_GAP_HIGH = 6.0

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        home_def = context.get("home_def_rating", 0)
        away_def = context.get("away_def_rating", 0)

        if not home_def or not away_def:
            return self._no_trigger()

        signals = []
        gap = abs(home_def - away_def)
        # Lower defensive rating = better defense
        weaker = context.get("home_team", "home") if home_def > away_def else context.get("away_team", "away")
        stronger = context.get("away_team", "away") if home_def > away_def else context.get("home_team", "home")

        if gap >= self.DEF_RATING_GAP_HIGH:
            signals.append(self._signal(
                risk_level=RiskLevel.HIGH,
                confidence=0.75,
                fragility_delta=4.0,
                explanation=f"Significant defensive gap: {weaker} allows {gap:.1f} more points "
                            f"per 100 possessions than {stronger}. "
                            "Expect scoring opportunity spike on one side.",
                evidence={
                    "home_def_rating": home_def,
                    "away_def_rating": away_def,
                    "gap": round(gap, 1),
                    "weaker_defense": weaker,
                },
            ))
        elif gap >= self.DEF_RATING_GAP_MODERATE:
            signals.append(self._signal(
                risk_level=RiskLevel.LOW,
                confidence=0.65,
                fragility_delta=2.0,
                explanation=f"Moderate defensive rating gap ({gap:.1f} pts/100 poss) "
                            f"favoring {stronger}. Minor matchup edge.",
                evidence={
                    "gap": round(gap, 1),
                    "weaker_defense": weaker,
                },
            ))

        # Check for key defender out
        for side in ("home", "away"):
            if context.get(f"{side}_starter_out", False):
                team = context.get(f"{side}_team", side)
                signals.append(self._signal(
                    risk_level=RiskLevel.MODERATE,
                    confidence=0.80,
                    fragility_delta=3.0,
                    explanation=f"{team} missing a starter — defensive structure impacted. "
                                "Opponent scoring opportunities may increase.",
                    evidence={
                        "team": team,
                        "starter_out": True,
                    },
                ))

        if not signals:
            return self._no_trigger()
        return self._triggered(*signals)


class PaceCollapseProtocol(Protocol):
    """
    Detects conditions where both teams may slow down unexpectedly.

    Playoff-style defensive games, rivalry games, and situations where
    both teams have strong defenses can cause pace collapse — making
    totals bets dangerous.
    """

    name = "pace_collapse"
    category = ProtocolCategory.TACTICAL
    description = "Detects conditions for unexpected pace slowdown"

    SLOW_PACE = 96  # NBA average ~100
    STRONG_DEF = 108  # good defensive rating

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        home_pace = context.get("home_pace", 0)
        away_pace = context.get("away_pace", 0)
        home_def = context.get("home_def_rating", 0)
        away_def = context.get("away_def_rating", 0)
        is_playoff = context.get("is_playoff", False)

        if not home_pace or not away_pace:
            return self._no_trigger()

        both_slow = home_pace < self.SLOW_PACE and away_pace < self.SLOW_PACE
        both_strong_d = (home_def and away_def and
                         home_def < self.STRONG_DEF and away_def < self.STRONG_DEF)

        if is_playoff and (both_slow or both_strong_d):
            return self._triggered(self._signal(
                risk_level=RiskLevel.HIGH,
                confidence=0.82,
                fragility_delta=5.0,
                explanation="Playoff game with two defensive-minded teams. "
                            "Pace collapse likely — totals bets are high risk.",
                evidence={
                    "is_playoff": True,
                    "home_pace": home_pace,
                    "away_pace": away_pace,
                    "both_slow": both_slow,
                    "both_strong_defense": both_strong_d,
                },
            ))
        elif both_slow and both_strong_d:
            return self._triggered(self._signal(
                risk_level=RiskLevel.MODERATE,
                confidence=0.72,
                fragility_delta=3.0,
                explanation="Both teams play slow with strong defense. "
                            "Scoring could be suppressed — under bets more favorable, "
                            "but totals carry elevated variance.",
                evidence={
                    "home_pace": home_pace,
                    "away_pace": away_pace,
                    "both_slow": True,
                    "both_strong_defense": True,
                },
            ))

        return self._no_trigger()


TACTICAL_PROTOCOLS = [PaceShockProtocol, DefensiveMismatchProtocol, PaceCollapseProtocol]
