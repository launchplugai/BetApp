# app/demo/leading_light_demo_cases.py
"""
Leading Light Demo Cases.

Four deterministic demo requests that exercise the full system:
STABLE, LOADED, TENSE, CRITICAL.

Each case includes:
- blocks with human-readable labels
- optional context_signals
- optional dna_profile
- optional bankroll
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


# =============================================================================
# Demo Case Type
# =============================================================================


class DemoCase:
    """A demo case configuration."""

    def __init__(
        self,
        name: str,
        description: str,
        expected_inductor: str,
        blocks: List[Dict[str, Any]],
        context_signals: Optional[List[Dict[str, Any]]] = None,
        dna_profile: Optional[Dict[str, Any]] = None,
        bankroll: Optional[float] = None,
        candidates: Optional[List[Dict[str, Any]]] = None,
    ):
        self.name = name
        self.description = description
        self.expected_inductor = expected_inductor
        self.blocks = blocks
        self.context_signals = context_signals
        self.dna_profile = dna_profile
        self.bankroll = bankroll
        self.candidates = candidates

    def to_request_json(self) -> Dict[str, Any]:
        """Convert to API request JSON."""
        request: Dict[str, Any] = {
            "blocks": self.blocks,
        }
        if self.context_signals:
            request["context_signals"] = self.context_signals
        if self.dna_profile:
            request["dna_profile"] = self.dna_profile
        if self.bankroll is not None:
            request["bankroll"] = self.bankroll
        if self.candidates:
            request["candidates"] = self.candidates
        return request


# =============================================================================
# Case 1: STABLE
# =============================================================================
# - 1 straight bet
# - no correlations
# - no context signals
# - finalFragility <= 30

STABLE_CASE = DemoCase(
    name="stable",
    description="Simple single bet with low fragility - demonstrates STABLE state",
    expected_inductor="stable",
    blocks=[
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-kc-buf",
            "bet_type": "spread",
            "selection": "Kansas City Chiefs -3.5",
            "base_fragility": 12.0,
            "correlation_tags": [],
        }
    ],
    context_signals=None,
    dna_profile={
        "risk": {
            "tolerance": 50,
            "max_parlay_legs": 4,
            "max_stake_pct": 0.10,
            "avoid_live_bets": False,
            "avoid_props": False,
        },
        "behavior": {
            "discipline": 0.7,
        },
    },
    bankroll=1000.0,
)


# =============================================================================
# Case 2: LOADED
# =============================================================================
# - 2 legs
# - small correlationPenalty (<20)
# - finalFragility 31-55

LOADED_CASE = DemoCase(
    name="loaded",
    description="Two-leg parlay with moderate fragility - demonstrates LOADED state",
    expected_inductor="loaded",
    blocks=[
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-kc-buf",
            "bet_type": "spread",
            "selection": "Kansas City Chiefs -3.5",
            "base_fragility": 10.0,  # Lower to stay in LOADED range
            "correlation_tags": [],
        },
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-phi-dal",
            "bet_type": "total",
            "selection": "Over 48.5 Points",
            "base_fragility": 12.0,  # Lower to stay in LOADED range
            "correlation_tags": [],
        },
    ],
    # sumBlocks=22, legPenalty=22.6, finalFragility=44.6 (LOADED: 31-55)
    context_signals=None,
    dna_profile={
        "risk": {
            "tolerance": 60,
            "max_parlay_legs": 4,
            "max_stake_pct": 0.08,
            "avoid_live_bets": False,
            "avoid_props": False,
        },
        "behavior": {
            "discipline": 0.6,
        },
    },
    bankroll=1000.0,
    candidates=[
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-sf-lar",
            "bet_type": "spread",
            "selection": "San Francisco 49ers -6.5",
            "base_fragility": 8.0,
            "correlation_tags": [],
        },
    ],
)


# =============================================================================
# Case 3: TENSE
# =============================================================================
# - 3 legs with at least one context signal increasing deltas
# - correlationPenalty modest (<20) OR legs <4
# - finalFragility 56-75

TENSE_CASE = DemoCase(
    name="tense",
    description="Three-leg parlay with context impacts - demonstrates TENSE state with alerts",
    expected_inductor="tense",
    blocks=[
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-kc-buf",
            "bet_type": "spread",
            "selection": "Kansas City Chiefs -3.5",
            "base_fragility": 3.0,  # +7 from weather = 10 effective
            "correlation_tags": [],
        },
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-kc-buf",
            "bet_type": "player_prop",
            "selection": "Patrick Mahomes Over 275.5 Pass Yds",
            "base_fragility": 5.0,  # +7 from weather = 12 effective
            "player_id": "mahomes-15",
            "correlation_tags": ["passing", "qb"],
        },
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-phi-dal",
            "bet_type": "ml",
            "selection": "Philadelphia Eagles ML",
            "base_fragility": 5.0,  # No weather impact
            "correlation_tags": [],
        },
    ],
    # sumBlocks=27, legPenalty=41.6, finalFragility≈68.6 (TENSE: 56-75)
    context_signals=[
        {
            "type": "weather",
            "game_id": "nfl-2024-wk15-kc-buf",
            "wind_mph": 18,
            "precip": True,
            "conditions": "Snow expected",
        },
        {
            "type": "injury",
            "player_id": "kelce-87",
            "player_name": "Travis Kelce",
            "status": "QUESTIONABLE",
            "injury": "Knee",
        },
    ],
    dna_profile={
        "risk": {
            "tolerance": 70,
            "max_parlay_legs": 5,
            "max_stake_pct": 0.06,
            "avoid_live_bets": False,
            "avoid_props": False,
        },
        "behavior": {
            "discipline": 0.5,
        },
    },
    bankroll=1000.0,
)


# =============================================================================
# Case 4: CRITICAL
# =============================================================================
# - 4+ legs OR correlationPenalty >= 20
# - finalFragility > 75
# - include at least one: same_player_multi_props correlation
# - include context signals (weather + injury + trade) to show edge

CRITICAL_CASE = DemoCase(
    name="critical",
    description="High-risk parlay with correlations and full context - demonstrates CRITICAL state",
    expected_inductor="critical",
    blocks=[
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-kc-buf",
            "bet_type": "spread",
            "selection": "Kansas City Chiefs -3.5",
            "base_fragility": 5.0,  # +7 weather = 12 effective
            "correlation_tags": [],
        },
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-kc-buf",
            "bet_type": "player_prop",
            "selection": "Patrick Mahomes Over 275.5 Pass Yds",
            "base_fragility": 5.0,  # +7 weather = 12 effective
            "player_id": "mahomes-15",
            "correlation_tags": ["passing", "qb"],
        },
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-kc-buf",
            "bet_type": "player_prop",
            "selection": "Patrick Mahomes Over 1.5 Pass TDs",
            "base_fragility": 5.0,  # +7 weather = 12 effective
            "player_id": "mahomes-15",
            "correlation_tags": ["passing", "qb", "td"],
        },
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-kc-buf",
            "bet_type": "player_prop",
            "selection": "Travis Kelce Over 75.5 Rec Yds",
            "base_fragility": 5.0,  # +7 weather +6 injury = 18 effective
            "player_id": "kelce-87",
            "correlation_tags": ["receiving"],
        },
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-phi-dal",
            "bet_type": "total",
            "selection": "Over 52.5 Points",
            "base_fragility": 3.0,  # No weather
            "correlation_tags": [],
        },
    ],
    # 5 legs (escalation factor), same_player correlations, full context
    # sumBlocks≈57, legPenalty=89.4, correlationPenalty≈12, finalFragility>75 (CRITICAL)
    context_signals=[
        {
            "type": "weather",
            "game_id": "nfl-2024-wk15-kc-buf",
            "wind_mph": 22,
            "precip": True,
            "conditions": "Heavy snow, 20+ mph gusts",
        },
        {
            "type": "injury",
            "player_id": "kelce-87",
            "player_name": "Travis Kelce",
            "status": "DOUBTFUL",
            "injury": "Knee - limited practice all week",
        },
        {
            "type": "trade",
            "player_id": "new-wr-88",
            "player_name": "Recent Acquisition",
            "from_team_id": "team-nyj",
            "to_team_id": "team-kc",
            "games_affected": 3,
        },
    ],
    dna_profile={
        "risk": {
            "tolerance": 50,  # Low tolerance triggers violation
            "max_parlay_legs": 4,  # Exceed this to trigger max_legs_exceeded
            "max_stake_pct": 0.05,
            "avoid_live_bets": False,
            "avoid_props": False,
        },
        "behavior": {
            "discipline": 0.4,
        },
    },
    bankroll=1000.0,
    candidates=[
        {
            "sport": "NFL",
            "game_id": "nfl-2024-wk15-sf-lar",
            "bet_type": "spread",
            "selection": "San Francisco 49ers -6.5",
            "base_fragility": 5.0,  # Low fragility candidate
            "correlation_tags": [],
        },
    ],
)


# =============================================================================
# Demo Cases Registry
# =============================================================================

DEMO_CASES: Dict[str, DemoCase] = {
    "stable": STABLE_CASE,
    "loaded": LOADED_CASE,
    "tense": TENSE_CASE,
    "critical": CRITICAL_CASE,
}


def get_demo_case(name: str) -> Optional[DemoCase]:
    """Get a demo case by name."""
    return DEMO_CASES.get(name.lower())


def list_demo_cases() -> List[Dict[str, str]]:
    """List all available demo cases."""
    return [
        {
            "name": case.name,
            "description": case.description,
            "expected_inductor": case.expected_inductor,
        }
        for case in DEMO_CASES.values()
    ]


# =============================================================================
# JSON Payloads for External Use
# =============================================================================

def get_all_demo_payloads() -> Dict[str, Dict[str, Any]]:
    """Get all demo case request payloads."""
    return {
        name: case.to_request_json()
        for name, case in DEMO_CASES.items()
    }
