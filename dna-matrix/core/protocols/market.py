# core/protocols/market.py
"""
Market Behavior Protocols — sharp movement, trap lines, line manipulation.

These detect oddsmaker and market signals that reveal information
about where professional money is going and whether the public
is being set up.
"""
from __future__ import annotations

from typing import Any, Dict

from core.protocols.models import (
    Protocol,
    ProtocolCategory,
    ProtocolResult,
    RiskLevel,
)


class SharpMovementProtocol(Protocol):
    """
    Detects significant line movement indicating professional money.

    When lines move more than 1.5 points against public betting
    percentages, it signals sharp (professional) money on the
    opposite side. This is one of the strongest market signals.
    """

    name = "sharp_movement"
    category = ProtocolCategory.MARKET
    description = "Detects professional money movement against public betting"

    LINE_MOVE_MODERATE = 1.0  # points of line movement
    LINE_MOVE_HIGH = 2.0
    PUBLIC_IMBALANCE = 65.0  # % threshold for "heavy public"

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        line_movement = abs(context.get("line_movement", 0.0))
        public_pct = context.get("public_bet_pct_home", 50.0)
        sharp_side = context.get("sharp_money_side")
        opening = context.get("opening_spread", 0.0)
        current = context.get("current_spread", 0.0)

        if line_movement < self.LINE_MOVE_MODERATE:
            return self._no_trigger()

        public_heavy_home = public_pct >= self.PUBLIC_IMBALANCE
        public_heavy_away = public_pct <= (100 - self.PUBLIC_IMBALANCE)
        has_public_imbalance = public_heavy_home or public_heavy_away

        # Line moved opposite to heavy public side = sharp signal
        public_side = "home" if public_heavy_home else "away" if public_heavy_away else None

        if line_movement >= self.LINE_MOVE_HIGH and has_public_imbalance:
            return self._triggered(self._signal(
                risk_level=RiskLevel.HIGH,
                confidence=0.83,
                fragility_delta=5.0,
                explanation=f"Sharp money detected: line moved {line_movement:.1f} points "
                            f"(from {opening} to {current}) against {public_pct:.0f}% public "
                            f"money on {'home' if public_heavy_home else 'away'}. "
                            "Professional bettors see something the public doesn't.",
                evidence={
                    "opening_spread": opening,
                    "current_spread": current,
                    "line_movement": line_movement,
                    "public_pct_home": public_pct,
                    "sharp_side": sharp_side,
                    "signal_strength": "strong",
                },
            ))
        elif line_movement >= self.LINE_MOVE_MODERATE:
            return self._triggered(self._signal(
                risk_level=RiskLevel.MODERATE,
                confidence=0.70,
                fragility_delta=3.0,
                explanation=f"Line moved {line_movement:.1f} points since open. "
                            "Possible sharp action or model disagreement — "
                            "odds may not reflect final market position.",
                evidence={
                    "opening_spread": opening,
                    "current_spread": current,
                    "line_movement": line_movement,
                    "public_pct_home": public_pct,
                },
            ))

        return self._no_trigger()


class TrapLineProtocol(Protocol):
    """
    Detects suspicious odds patterns that may indicate bookmaker traps.

    When a heavy public favorite has a line that's too generous
    or moving in the wrong direction, the book may be setting a trap
    to maximize liability exposure on the public side.
    """

    name = "trap_line"
    category = ProtocolCategory.MARKET
    description = "Detects suspicious bookmaker trap line patterns"

    TRAP_PUBLIC_THRESHOLD = 70.0  # % public on one side
    TRAP_LINE_MOVE = 0.5  # points moving toward public side

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        public_pct = context.get("public_bet_pct_home", 50.0)
        line_movement = context.get("line_movement", 0.0)
        opening = context.get("opening_spread", 0.0)
        current = context.get("current_spread", 0.0)

        public_heavy_home = public_pct >= self.TRAP_PUBLIC_THRESHOLD
        public_heavy_away = public_pct <= (100 - self.TRAP_PUBLIC_THRESHOLD)

        if not (public_heavy_home or public_heavy_away):
            return self._no_trigger()

        # Trap detection: line moves TOWARD the public side
        # (making the public bet look even better — enticing more action)
        if public_heavy_home and line_movement > self.TRAP_LINE_MOVE:
            return self._triggered(self._signal(
                risk_level=RiskLevel.HIGH,
                confidence=0.73,
                fragility_delta=4.0,
                explanation=f"Potential trap line: {public_pct:.0f}% of public on home, "
                            f"yet line moved {line_movement:.1f} points toward home "
                            f"({opening} → {current}). Books rarely lose — "
                            "this pattern suggests they're comfortable with the exposure.",
                evidence={
                    "public_pct_home": public_pct,
                    "line_movement": line_movement,
                    "direction": "toward_public",
                    "pattern": "trap_line",
                    "opening": opening,
                    "current": current,
                },
            ))
        elif public_heavy_away and line_movement < -self.TRAP_LINE_MOVE:
            return self._triggered(self._signal(
                risk_level=RiskLevel.HIGH,
                confidence=0.73,
                fragility_delta=4.0,
                explanation=f"Potential trap line: {100 - public_pct:.0f}% of public on away, "
                            f"yet line moved {abs(line_movement):.1f} points toward away "
                            f"({opening} → {current}). Suspicious pattern — "
                            "the book may be inviting action on the losing side.",
                evidence={
                    "public_pct_home": public_pct,
                    "line_movement": line_movement,
                    "direction": "toward_public",
                    "pattern": "trap_line",
                },
            ))

        return self._no_trigger()


class WhistleShiftProtocol(Protocol):
    """
    Detects officiating patterns that affect game outcomes.

    Certain referee crews have measurable tendencies — some allow
    physical play (favoring unders), others call tight games
    (favoring overs via free throws). Home advantage also varies
    significantly by crew.
    """

    name = "whistle_shift"
    category = ProtocolCategory.MARKET
    description = "Detects referee-driven game flow patterns"

    HOME_ADVANTAGE_THRESHOLD = 2.0  # points of home advantage above average
    FOUL_RATE_IMPACT = 2.0

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        ref_crew = context.get("ref_crew")
        ref_home_adv = context.get("ref_home_advantage", 0.0)
        ref_foul_rate = context.get("ref_foul_rate", 0.0)

        if not ref_crew:
            return self._no_trigger()

        signals = []

        if abs(ref_home_adv) >= self.HOME_ADVANTAGE_THRESHOLD:
            direction = "favors home" if ref_home_adv > 0 else "favors away"
            signals.append(self._signal(
                risk_level=RiskLevel.MODERATE,
                confidence=0.68,
                fragility_delta=2.5,
                explanation=f"Referee crew ({ref_crew}) historically {direction} "
                            f"by {abs(ref_home_adv):.1f} points. "
                            "Spread bets should account for officiating bias.",
                evidence={
                    "ref_crew": ref_crew,
                    "home_advantage_delta": ref_home_adv,
                    "direction": direction,
                },
            ))

        if not signals:
            return self._no_trigger()
        return self._triggered(*signals)


MARKET_PROTOCOLS = [SharpMovementProtocol, TrapLineProtocol, WhistleShiftProtocol]
