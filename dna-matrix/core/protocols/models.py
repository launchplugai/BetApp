# core/protocols/models.py
"""
Protocol System Data Models.

A protocol is a structured rule set that detects specific contextual patterns
affecting a wager. Protocols operate as intelligent detectors — they scan
incoming data and produce signals.

Protocol Structure:
    Protocol
    ├─ Name
    ├─ Category
    ├─ Trigger Conditions
    ├─ Data Inputs
    ├─ Evaluation Logic
    ├─ Risk Contribution
    ├─ Confidence Weight
    └─ Explanation Template
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class ProtocolCategory(str, Enum):
    """Behavioral domain groupings for protocols."""
    PHYSICAL = "physical"       # Fatigue, travel, rest
    TACTICAL = "tactical"       # Pace, matchups, defensive gaps
    VOLATILITY = "volatility"   # Foul trouble, lineup instability
    PSYCHOLOGICAL = "psychological"  # Revenge, momentum, narrative
    MARKET = "market"           # Sharp movement, trap lines


class RiskLevel(str, Enum):
    """Risk severity produced by a protocol."""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def numeric(self) -> float:
        """Numeric weight for aggregation."""
        return {
            RiskLevel.NONE: 0.0,
            RiskLevel.LOW: 0.15,
            RiskLevel.MODERATE: 0.35,
            RiskLevel.HIGH: 0.60,
            RiskLevel.CRITICAL: 0.85,
        }[self]


# =============================================================================
# Protocol Signal (output of a single protocol)
# =============================================================================


@dataclass(frozen=True)
class ProtocolSignal:
    """
    Output from a single protocol execution.

    Each protocol produces a signal with:
    - risk_level: severity classification
    - confidence: how sure the protocol is (0.0-1.0)
    - fragility_delta: additional fragility to add to the parlay
    - explanation: human-readable description of what was detected
    - evidence: structured data supporting the signal
    """
    protocol_name: str
    category: ProtocolCategory
    risk_level: RiskLevel
    confidence: float
    fragility_delta: float
    explanation: str
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")
        if self.fragility_delta < 0:
            raise ValueError("fragility_delta must be >= 0")


# =============================================================================
# Protocol Result (collection of signals from all protocols)
# =============================================================================


@dataclass(frozen=True)
class ProtocolResult:
    """
    Result from running a single protocol against game context.

    A protocol either triggers (producing signals) or doesn't.
    """
    protocol_name: str
    category: ProtocolCategory
    triggered: bool
    signals: tuple[ProtocolSignal, ...] = ()

    @property
    def total_fragility_delta(self) -> float:
        return sum(s.fragility_delta for s in self.signals)

    @property
    def max_risk_level(self) -> RiskLevel:
        if not self.signals:
            return RiskLevel.NONE
        return max(self.signals, key=lambda s: s.risk_level.numeric).risk_level


# =============================================================================
# Aggregated Risk (output of the full protocol pipeline)
# =============================================================================


@dataclass(frozen=True)
class AggregatedRisk:
    """
    Aggregated risk profile from all triggered protocols.

    This is the final output of the protocol pipeline, combining
    all individual protocol signals into a unified risk assessment.
    """
    protocol_results: tuple[ProtocolResult, ...]
    fragility_score: float        # 0.0-1.0, aggregate fragility contribution
    confidence_score: float       # 0.0-1.0, how confident the system is
    triggered_protocols: tuple[str, ...]  # names of protocols that fired
    risk_summary: str             # human-readable summary
    category_risks: Dict[str, RiskLevel]  # risk level per category

    @property
    def total_fragility_delta(self) -> float:
        """Total fragility adjustment from all protocols."""
        return sum(r.total_fragility_delta for r in self.protocol_results)

    @property
    def triggered_count(self) -> int:
        return len(self.triggered_protocols)

    @property
    def has_critical(self) -> bool:
        return any(
            r.max_risk_level == RiskLevel.CRITICAL
            for r in self.protocol_results
            if r.triggered
        )

    def signals_by_category(self, category: ProtocolCategory) -> list[ProtocolSignal]:
        """Get all signals for a specific category."""
        signals = []
        for result in self.protocol_results:
            if result.category == category and result.triggered:
                signals.extend(result.signals)
        return signals

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fragilityScore": round(self.fragility_score, 3),
            "confidenceScore": round(self.confidence_score, 3),
            "triggeredProtocols": list(self.triggered_protocols),
            "triggeredCount": self.triggered_count,
            "riskSummary": self.risk_summary,
            "categoryRisks": {k: v.value for k, v in self.category_risks.items()},
            "hasCritical": self.has_critical,
            "totalFragilityDelta": round(self.total_fragility_delta, 2),
            "signals": [
                {
                    "protocol": s.protocol_name,
                    "category": s.category.value,
                    "risk": s.risk_level.value,
                    "confidence": round(s.confidence, 2),
                    "fragilityDelta": round(s.fragility_delta, 2),
                    "explanation": s.explanation,
                    "evidence": s.evidence,
                }
                for r in self.protocol_results
                if r.triggered
                for s in r.signals
            ],
        }


# =============================================================================
# Protocol Base Class
# =============================================================================


class Protocol:
    """
    Base class for all protocols.

    Subclasses implement `evaluate()` which receives game context
    and returns a ProtocolResult.

    Protocol lifecycle:
        1. Check trigger conditions against context
        2. If triggered, evaluate and score
        3. Produce signal(s) with risk level, confidence, explanation
    """

    name: str = "base_protocol"
    category: ProtocolCategory = ProtocolCategory.PHYSICAL
    description: str = ""

    def evaluate(self, context: Dict[str, Any]) -> ProtocolResult:
        """
        Evaluate this protocol against game context.

        Args:
            context: Game context dict containing relevant data.
                     Keys vary by protocol category.

        Returns:
            ProtocolResult with triggered=True/False and signals
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement evaluate()")

    def _no_trigger(self) -> ProtocolResult:
        """Convenience: return a non-triggered result."""
        return ProtocolResult(
            protocol_name=self.name,
            category=self.category,
            triggered=False,
        )

    def _signal(
        self,
        risk_level: RiskLevel,
        confidence: float,
        fragility_delta: float,
        explanation: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> ProtocolSignal:
        """Convenience: build a signal for this protocol."""
        return ProtocolSignal(
            protocol_name=self.name,
            category=self.category,
            risk_level=risk_level,
            confidence=confidence,
            fragility_delta=fragility_delta,
            explanation=explanation,
            evidence=evidence or {},
        )

    def _triggered(self, *signals: ProtocolSignal) -> ProtocolResult:
        """Convenience: return a triggered result with signals."""
        return ProtocolResult(
            protocol_name=self.name,
            category=self.category,
            triggered=True,
            signals=tuple(signals),
        )


# =============================================================================
# Game Context Schema
# =============================================================================


@dataclass
class GameContext:
    """
    Structured game context fed into the protocol pipeline.

    This is the normalized input that protocols consume.
    Not all fields are required — protocols check what they need.
    """
    game_id: str
    league: str
    home_team: str
    away_team: str
    # Schedule
    is_back_to_back_home: bool = False
    is_back_to_back_away: bool = False
    home_rest_days: int = 2
    away_rest_days: int = 2
    home_travel_miles: float = 0.0
    away_travel_miles: float = 0.0
    # Tactical
    home_pace: float = 0.0
    away_pace: float = 0.0
    home_def_rating: float = 0.0
    away_def_rating: float = 0.0
    # Roster
    home_injuries: List[Dict[str, Any]] = field(default_factory=list)
    away_injuries: List[Dict[str, Any]] = field(default_factory=list)
    home_lineup_changes: int = 0
    away_lineup_changes: int = 0
    home_starter_out: bool = False
    away_starter_out: bool = False
    # Psychological
    revenge_players: List[Dict[str, Any]] = field(default_factory=list)
    home_streak: int = 0  # positive=wins, negative=losses
    away_streak: int = 0
    home_clutch_rating: float = 0.5
    away_clutch_rating: float = 0.5
    # Market
    opening_spread: float = 0.0
    current_spread: float = 0.0
    public_bet_pct_home: float = 50.0
    sharp_money_side: Optional[str] = None  # "home" | "away" | None
    line_movement: float = 0.0  # positive = moved toward home
    # Officiating
    ref_crew: Optional[str] = None
    ref_foul_rate: float = 0.0  # fouls per game above league avg
    ref_home_advantage: float = 0.0
    # Environment
    altitude_ft: float = 0.0
    is_playoff: bool = False
    # Raw extras
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for protocol consumption."""
        import dataclasses
        return dataclasses.asdict(self)
