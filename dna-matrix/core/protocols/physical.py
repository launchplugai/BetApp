# core/protocols/physical.py
"""
Physical State Protocols — fatigue, travel, rest.

These evaluate player and team fatigue conditions that affect
performance in ways the odds market often misprices.
"""
from __future__ import annotations

from typing import Any, Dict

from core.protocols.models import (
    Protocol,
    ProtocolCategory,
    ProtocolResult,
    ProtocolSignal,
    RiskLevel,
)


class BackToBackFatigueProtocol(Protocol):
    """
    Detects back-to-back game fatigue.

    Triggers when a team played the previous night.
    Historical data shows B2B teams shoot ~3% worse from 3PT range,
    commit ~1.5 more turnovers, and see reduced minutes efficiency.
    """

    name = "back_to_back_fatigue"
    category = ProtocolCategory.PHYSICAL
    description = "Detects back-to-back game fatigue conditions"

    # Thresholds
    REST_CRITICAL_DAYS = 0  # same day / previous night
    REST_SHORT_DAYS = 1

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        signals = []

        for side in ("home", "away"):
            is_b2b = context.get(f"is_back_to_back_{side}", False)
            rest_days = context.get(f"{side}_rest_days", 2)
            team = context.get(f"{side}_team", side)

            if is_b2b or rest_days <= self.REST_CRITICAL_DAYS:
                signals.append(self._signal(
                    risk_level=RiskLevel.HIGH,
                    confidence=0.88,
                    fragility_delta=6.0,
                    explanation=f"{team} playing on zero rest (back-to-back). "
                                "Expect reduced shooting efficiency, higher turnovers, "
                                "and compressed rotation minutes.",
                    evidence={
                        "team": team,
                        "side": side,
                        "rest_days": rest_days,
                        "is_b2b": True,
                        "expected_impact": {
                            "three_pt_drop": "~3%",
                            "turnover_increase": "~1.5",
                            "minutes_efficiency": "reduced",
                        },
                    },
                ))
            elif rest_days <= self.REST_SHORT_DAYS:
                signals.append(self._signal(
                    risk_level=RiskLevel.MODERATE,
                    confidence=0.75,
                    fragility_delta=3.0,
                    explanation=f"{team} on short rest ({rest_days} day). "
                                "Minor fatigue risk — watch for late-game efficiency drops.",
                    evidence={
                        "team": team,
                        "side": side,
                        "rest_days": rest_days,
                    },
                ))

        if not signals:
            return self._no_trigger()
        return self._triggered(*signals)


class TravelStressProtocol(Protocol):
    """
    Detects schedule travel stress.

    Cross-country travel, altitude changes, and timezone shifts
    all affect team performance. Denver at altitude is the classic example.
    """

    name = "travel_stress"
    category = ProtocolCategory.PHYSICAL
    description = "Detects travel distance and altitude-related fatigue"

    TRAVEL_MODERATE_MILES = 800
    TRAVEL_HIGH_MILES = 1500
    ALTITUDE_THRESHOLD_FT = 4500  # Denver is 5,280 ft

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        signals = []
        altitude = context.get("altitude_ft", 0.0)

        for side in ("home", "away"):
            miles = context.get(f"{side}_travel_miles", 0.0)
            team = context.get(f"{side}_team", side)

            if miles >= self.TRAVEL_HIGH_MILES:
                signals.append(self._signal(
                    risk_level=RiskLevel.HIGH,
                    confidence=0.80,
                    fragility_delta=5.0,
                    explanation=f"{team} traveled {int(miles)} miles. "
                                "Cross-country travel creates significant fatigue, "
                                "especially with timezone adjustment.",
                    evidence={
                        "team": team,
                        "travel_miles": miles,
                        "severity": "high",
                    },
                ))
            elif miles >= self.TRAVEL_MODERATE_MILES:
                signals.append(self._signal(
                    risk_level=RiskLevel.LOW,
                    confidence=0.70,
                    fragility_delta=2.0,
                    explanation=f"{team} traveled {int(miles)} miles. "
                                "Moderate travel — minor stamina impact possible.",
                    evidence={
                        "team": team,
                        "travel_miles": miles,
                        "severity": "moderate",
                    },
                ))

        # Altitude penalty (visiting team at altitude)
        if altitude >= self.ALTITUDE_THRESHOLD_FT:
            away_team = context.get("away_team", "away")
            signals.append(self._signal(
                risk_level=RiskLevel.MODERATE,
                confidence=0.82,
                fragility_delta=4.0,
                explanation=f"Game at {int(altitude)} ft altitude. "
                            f"{away_team} faces conditioning disadvantage — "
                            "expect reduced late-game stamina.",
                evidence={
                    "altitude_ft": altitude,
                    "affected_team": away_team,
                    "historical_note": "Denver historically ~8% better at home vs visitors",
                },
            ))

        if not signals:
            return self._no_trigger()
        return self._triggered(*signals)


# All physical protocols for registration
PHYSICAL_PROTOCOLS = [BackToBackFatigueProtocol, TravelStressProtocol]
