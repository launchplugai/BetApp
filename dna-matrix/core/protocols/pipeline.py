# core/protocols/pipeline.py
"""
Protocol Execution Pipeline.

Runs all registered protocols against game context and aggregates
their signals into a unified risk profile.

Pipeline:
    Data ingestion
        ↓
    Normalization
        ↓
    Protocol trigger scanning
        ↓
    Signal scoring
        ↓
    Risk aggregation
        ↓
    Narrative generation
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from core.protocols.models import (
    AggregatedRisk,
    GameContext,
    Protocol,
    ProtocolCategory,
    ProtocolResult,
    ProtocolSignal,
    RiskLevel,
)
from core.protocols.registry import registry


class ProtocolPipeline:
    """
    Executes all protocols against game context and aggregates results.

    Usage:
        pipeline = ProtocolPipeline()
        risk = pipeline.run(game_context)
        print(risk.fragility_score)
        print(risk.risk_summary)
    """

    def __init__(
        self,
        protocol_weights: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Args:
            protocol_weights: Optional per-protocol weight overrides (0.0-2.0).
                             Used for personalized protocol weighting based on
                             user behavior. Default weight is 1.0.
        """
        self._weights = protocol_weights or {}

    def run(
        self,
        context: Dict[str, Any],
        categories: Optional[Sequence[ProtocolCategory]] = None,
    ) -> AggregatedRisk:
        """
        Run protocols against context and return aggregated risk.

        Args:
            context: Game context dict (or GameContext.to_dict())
            categories: Optional filter — only run these categories.
                       None = run all.

        Returns:
            AggregatedRisk with all signals aggregated
        """
        # Get protocols to run
        if categories:
            protocols: List[Protocol] = []
            for cat in categories:
                protocols.extend(registry.get_by_category(cat))
        else:
            protocols = registry.get_all()

        # Execute each protocol
        results: List[ProtocolResult] = []
        for protocol in protocols:
            result = protocol.evaluate(context)
            results.append(result)

        # Aggregate
        return self._aggregate(results)

    def run_for_parlay(
        self,
        contexts: Sequence[Dict[str, Any]],
    ) -> AggregatedRisk:
        """
        Run protocols against multiple game contexts (one per leg).

        Aggregates risk across all games in a parlay.

        Args:
            contexts: List of game context dicts, one per game in the parlay

        Returns:
            AggregatedRisk across all games
        """
        all_results: List[ProtocolResult] = []

        for ctx in contexts:
            single_risk = self.run(ctx)
            all_results.extend(single_risk.protocol_results)

        return self._aggregate(all_results)

    def _aggregate(self, results: Sequence[ProtocolResult]) -> AggregatedRisk:
        """Aggregate protocol results into unified risk profile."""
        triggered = [r for r in results if r.triggered]
        triggered_names = tuple(r.protocol_name for r in triggered)

        # Collect all signals, applying weights
        all_signals: List[ProtocolSignal] = []
        for result in triggered:
            weight = self._weights.get(result.protocol_name, 1.0)
            for signal in result.signals:
                # Apply weight to fragility delta
                weighted_signal = ProtocolSignal(
                    protocol_name=signal.protocol_name,
                    category=signal.category,
                    risk_level=signal.risk_level,
                    confidence=signal.confidence,
                    fragility_delta=signal.fragility_delta * weight,
                    explanation=signal.explanation,
                    evidence=signal.evidence,
                )
                all_signals.append(weighted_signal)

        # Compute aggregate fragility score (0.0-1.0)
        if all_signals:
            total_delta = sum(s.fragility_delta for s in all_signals)
            # Normalize: 20 delta = 1.0 fragility score (fully fragile)
            fragility_score = min(total_delta / 20.0, 1.0)
        else:
            fragility_score = 0.0

        # Compute confidence score (weighted average of signal confidences)
        if all_signals:
            weighted_conf = sum(s.confidence * s.fragility_delta for s in all_signals)
            total_weight = sum(s.fragility_delta for s in all_signals)
            confidence_score = weighted_conf / total_weight if total_weight > 0 else 0.5
        else:
            confidence_score = 0.5  # neutral when no signals

        # Compute per-category risk levels
        category_risks: Dict[str, RiskLevel] = {}
        for cat in ProtocolCategory:
            cat_signals = [s for s in all_signals if s.category == cat]
            if cat_signals:
                category_risks[cat.value] = max(
                    cat_signals, key=lambda s: s.risk_level.numeric
                ).risk_level
            else:
                category_risks[cat.value] = RiskLevel.NONE

        # Generate risk summary
        risk_summary = self._generate_summary(
            triggered_names, all_signals, fragility_score, category_risks
        )

        return AggregatedRisk(
            protocol_results=tuple(results),
            fragility_score=round(fragility_score, 3),
            confidence_score=round(confidence_score, 3),
            triggered_protocols=triggered_names,
            risk_summary=risk_summary,
            category_risks=category_risks,
        )

    def _generate_summary(
        self,
        triggered: tuple[str, ...],
        signals: List[ProtocolSignal],
        fragility_score: float,
        category_risks: Dict[str, RiskLevel],
    ) -> str:
        """Generate human-readable risk summary."""
        if not triggered:
            return "No contextual risk factors detected. Standard statistical analysis applies."

        # Count by severity
        high_count = sum(1 for s in signals if s.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL))
        mod_count = sum(1 for s in signals if s.risk_level == RiskLevel.MODERATE)

        parts = []

        if fragility_score >= 0.7:
            parts.append("This bet has significant hidden fragility.")
        elif fragility_score >= 0.4:
            parts.append("This bet has hidden structural weaknesses.")
        else:
            parts.append("Minor contextual factors are present.")

        # Describe the biggest risks by category
        risk_descriptions = []
        for cat_name, risk in category_risks.items():
            if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                cat_signals = [s for s in signals if s.category.value == cat_name]
                if cat_signals:
                    risk_descriptions.append(cat_signals[0].explanation.split(".")[0])

        if risk_descriptions:
            parts.append(" ".join(risk_descriptions[:2]) + ".")

        if fragility_score >= 0.5:
            parts.append(
                "The bet could still hit, but its stability is weaker than it appears."
            )

        return " ".join(parts)


def initialize_protocols() -> None:
    """Register all protocol implementations."""
    from core.protocols.physical import PHYSICAL_PROTOCOLS
    from core.protocols.tactical import TACTICAL_PROTOCOLS
    from core.protocols.volatility import VOLATILITY_PROTOCOLS
    from core.protocols.psychological import PSYCHOLOGICAL_PROTOCOLS
    from core.protocols.market import MARKET_PROTOCOLS

    all_protocols = (
        PHYSICAL_PROTOCOLS
        + TACTICAL_PROTOCOLS
        + VOLATILITY_PROTOCOLS
        + PSYCHOLOGICAL_PROTOCOLS
        + MARKET_PROTOCOLS
    )

    for proto_cls in all_protocols:
        registry.register(proto_cls)


# Auto-initialize on import
initialize_protocols()
