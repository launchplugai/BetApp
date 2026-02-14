"""
Shared types for notification system (S20).
Prevents circular imports between protocol_observer and notification_rules.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class OpportunityStatus(str, Enum):
    """Status of an opportunity in the pipeline."""
    DETECTED = "detected"
    FILTERED = "filtered"
    ELIGIBLE = "eligible"
    NOTIFIED = "notified"
    EXPIRED = "expired"
    REJECTED = "rejected"


@dataclass
class RawOpportunity:
    """Raw opportunity from a protocol before filtering."""
    protocol_id: str
    protocol_source: str  # nba, nfl, mlb, etc.
    game_id: str
    sport: str
    league: Optional[str]
    home_team: str
    away_team: str
    event_time: datetime
    bet_type: str
    market: str
    selection: str
    odds: int
    odds_decimal: Optional[float]
    line: Optional[float]
    confidence_score: float
    edge_percent: Optional[float]
    metadata: Dict[str, Any]


@dataclass
class OpportunityResult:
    """Result of opportunity processing."""
    success: bool
    opportunity_id: Optional[str] = None
    reason: Optional[str] = None
    passed_guardrails: bool = True
    guardrail_reason: Optional[str] = None


@dataclass
class MatchResult:
    """Result of rule matching."""
    matches: bool
    reason: str
    matched_criteria: List[str]


@dataclass
class GuardrailResult:
    """Result of guardrail check."""
    allowed: bool
    reason: str
    remaining_today: int
