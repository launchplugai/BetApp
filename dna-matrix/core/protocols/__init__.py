# Protocol System — Contextual Reasoning Layer
#
# The Protocol System sits between raw data and the DNA engine.
# It detects contextual patterns (fatigue, psychology, matchups, market behavior)
# and produces risk signals that feed into fragility calculation.
#
# Architecture:
#   Data Layer → Protocol System → DNA Engine → Sherlock → User
#
# Protocol Categories:
#   1. Physical State (fatigue, travel, rest)
#   2. Tactical (pace, matchups, defensive gaps)
#   3. Volatility (foul trouble, lineup instability)
#   4. Psychological (revenge, momentum, narrative)
#   5. Market Behavior (sharp movement, trap lines)

from core.protocols.models import (
    Protocol,
    ProtocolCategory,
    ProtocolResult,
    ProtocolSignal,
    RiskLevel,
    AggregatedRisk,
)
from core.protocols.registry import ProtocolRegistry, registry
from core.protocols.pipeline import ProtocolPipeline

__all__ = [
    "Protocol",
    "ProtocolCategory",
    "ProtocolResult",
    "ProtocolSignal",
    "RiskLevel",
    "AggregatedRisk",
    "ProtocolRegistry",
    "registry",
    "ProtocolPipeline",
]
