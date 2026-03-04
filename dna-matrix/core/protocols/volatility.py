# core/protocols/volatility.py
"""
Volatility Protocols — foul trouble, lineup instability, injury shadows.

These track variance risks that increase the unpredictability
of outcomes beyond what baseline statistics capture.
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.protocols.models import (
    Protocol,
    ProtocolCategory,
    ProtocolResult,
    RiskLevel,
)


class FoulTroubleProtocol(Protocol):
    """
    Detects foul trouble risk from referee tendencies.

    Certain referee crews call significantly more fouls,
    affecting star player minutes, game flow, and totals.
    """

    name = "foul_trouble"
    category = ProtocolCategory.VOLATILITY
    description = "Detects foul trouble risk from referee patterns"

    FOUL_RATE_MODERATE = 1.5  # fouls above league average per game
    FOUL_RATE_HIGH = 3.0

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        ref_foul_rate = context.get("ref_foul_rate", 0.0)
        ref_crew = context.get("ref_crew")

        if not ref_crew or ref_foul_rate <= 0:
            return self._no_trigger()

        if ref_foul_rate >= self.FOUL_RATE_HIGH:
            return self._triggered(self._signal(
                risk_level=RiskLevel.HIGH,
                confidence=0.76,
                fragility_delta=4.0,
                explanation=f"Referee crew ({ref_crew}) calls {ref_foul_rate:.1f} more fouls "
                            "per game than league average. High foul trouble risk — "
                            "star player minutes threatened, game flow disrupted.",
                evidence={
                    "ref_crew": ref_crew,
                    "foul_rate_above_avg": ref_foul_rate,
                    "impact": ["star_minutes_risk", "game_flow_disruption", "free_throw_volume"],
                },
            ))
        elif ref_foul_rate >= self.FOUL_RATE_MODERATE:
            return self._triggered(self._signal(
                risk_level=RiskLevel.MODERATE,
                confidence=0.70,
                fragility_delta=2.5,
                explanation=f"Referee crew ({ref_crew}) trends whistle-heavy "
                            f"(+{ref_foul_rate:.1f} fouls/game). "
                            "Moderate foul trouble risk for aggressive players.",
                evidence={
                    "ref_crew": ref_crew,
                    "foul_rate_above_avg": ref_foul_rate,
                },
            ))

        return self._no_trigger()


class LineupInstabilityProtocol(Protocol):
    """
    Detects lineup instability from frequent rotation changes,
    new starting lineups, or injury replacements.

    Chemistry uncertainty produces higher variance outcomes.
    """

    name = "lineup_instability"
    category = ProtocolCategory.VOLATILITY
    description = "Detects roster instability and chemistry disruption"

    CHANGES_MODERATE = 2
    CHANGES_HIGH = 3

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        signals = []

        for side in ("home", "away"):
            changes = context.get(f"{side}_lineup_changes", 0)
            team = context.get(f"{side}_team", side)
            starter_out = context.get(f"{side}_starter_out", False)

            if changes >= self.CHANGES_HIGH or (changes >= self.CHANGES_MODERATE and starter_out):
                signals.append(self._signal(
                    risk_level=RiskLevel.HIGH,
                    confidence=0.80,
                    fragility_delta=5.0,
                    explanation=f"{team} has {changes} lineup changes"
                                f"{' with a starter out' if starter_out else ''}. "
                                "Chemistry disruption creates unpredictable outcomes — "
                                "player props and team totals carry elevated variance.",
                    evidence={
                        "team": team,
                        "lineup_changes": changes,
                        "starter_out": starter_out,
                        "impact": "chemistry_uncertainty",
                    },
                ))
            elif changes >= self.CHANGES_MODERATE:
                signals.append(self._signal(
                    risk_level=RiskLevel.MODERATE,
                    confidence=0.72,
                    fragility_delta=3.0,
                    explanation=f"{team} has {changes} rotation changes. "
                                "Minor chemistry disruption — role adjustments may affect props.",
                    evidence={
                        "team": team,
                        "lineup_changes": changes,
                    },
                ))

        if not signals:
            return self._no_trigger()
        return self._triggered(*signals)


class InjuryShadowProtocol(Protocol):
    """
    Detects when a star returns from injury on restricted minutes,
    or when a key player's injury status creates role uncertainty.

    Odds markets often misprice these situations.
    """

    name = "injury_shadow"
    category = ProtocolCategory.VOLATILITY
    description = "Detects injury-related role and minutes uncertainty"

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        signals = []

        for side in ("home", "away"):
            injuries: List[Dict[str, Any]] = context.get(f"{side}_injuries", [])
            team = context.get(f"{side}_team", side)

            questionable_count = 0
            key_injuries = []

            for inj in injuries:
                status = inj.get("status", "").upper()
                player = inj.get("player", "Unknown")
                is_star = inj.get("is_star", False)
                minutes_limit = inj.get("minutes_limit")

                if status == "QUESTIONABLE":
                    questionable_count += 1

                if is_star and minutes_limit:
                    signals.append(self._signal(
                        risk_level=RiskLevel.HIGH,
                        confidence=0.85,
                        fragility_delta=5.0,
                        explanation=f"{player} ({team}) returning on restricted minutes "
                                    f"(~{minutes_limit} min). Market likely overvaluing their "
                                    "impact — props and team lines may be mispriced.",
                        evidence={
                            "player": player,
                            "team": team,
                            "minutes_limit": minutes_limit,
                            "status": status,
                            "mispricing_risk": "high",
                        },
                    ))
                elif is_star and status in ("OUT", "DOUBTFUL"):
                    key_injuries.append(player)

            if key_injuries:
                signals.append(self._signal(
                    risk_level=RiskLevel.MODERATE,
                    confidence=0.90,
                    fragility_delta=4.0,
                    explanation=f"{team} missing key player(s): {', '.join(key_injuries)}. "
                                "Role redistribution creates uncertainty in props and totals.",
                    evidence={
                        "team": team,
                        "missing_stars": key_injuries,
                        "impact": "role_redistribution",
                    },
                ))

            if questionable_count >= 2:
                signals.append(self._signal(
                    risk_level=RiskLevel.LOW,
                    confidence=0.65,
                    fragility_delta=2.0,
                    explanation=f"{team} has {questionable_count} questionable players. "
                                "Game-time decisions add variance to lineup construction.",
                    evidence={
                        "team": team,
                        "questionable_count": questionable_count,
                    },
                ))

        if not signals:
            return self._no_trigger()
        return self._triggered(*signals)


VOLATILITY_PROTOCOLS = [FoulTroubleProtocol, LineupInstabilityProtocol, InjuryShadowProtocol]
