# app/voice/narration.py
"""
Voice Narration Scripts for Demo Cases.

Each script is optimized for TTS delivery (~20 seconds or less).
No prediction language. No "locks". No hype.

Also contains plain-English explanations and glossary terms for each demo case.
"""
from typing import Dict, List, Optional, TypedDict


class GlossaryTerm(TypedDict):
    """A glossary term with its meaning."""

    term: str
    meaning: str


class DemoCaseContext(TypedDict):
    """Context framing for a demo case."""

    who_its_for: str
    why_this_case: str
    what_to_notice: str


class DemoCaseNarration(TypedDict):
    """Complete narration data for a demo case."""

    narration: str
    plain_english: List[str]
    glossary: List[GlossaryTerm]
    context: DemoCaseContext


# =============================================================================
# Narration Scripts (Voice-Ready)
# =============================================================================

DEMO_CASE_NARRATIONS: Dict[str, str] = {
    "stable": (
        "This is a stable parlay. "
        "A single spread bet on Kansas City, sitting at low fragility. "
        "No correlations. No context signals affecting it. "
        "The structure is clean. "
        "Your DNA profile shows tolerance for this type of action. "
        "Stake recommendation stays within your defined limits."
    ),
    "loaded": (
        "This parlay is loaded. "
        "Two legs: a spread and a total from different games. "
        "Fragility has climbed into the moderate zone. "
        "No correlations between these selections, which helps. "
        "But the two-leg structure adds inherent variance. "
        "DNA check passes, but the system flags this as requiring attention."
    ),
    "tense": (
        "This parlay is tense. "
        "Three legs, including a player prop on Mahomes. "
        "Weather signals show snow and wind at Arrowhead. "
        "That pushes fragility on any pass-related selection. "
        "Kelce is listed questionable, adding injury context. "
        "The correlation between same-game bets compounds the exposure. "
        "Structure fragility sits in the elevated range."
    ),
    "critical": (
        "This parlay is critical. "
        "Five legs with multiple same-player props on Mahomes. "
        "Weather, injury, and trade signals all active. "
        "Heavy snow forecast with twenty-plus mile per hour gusts. "
        "Kelce doubtful with a knee issue. "
        "Same-player correlation penalty stacks significantly. "
        "Final fragility exceeds your DNA tolerance threshold. "
        "The system recommends avoiding this structure entirely."
    ),
}


# =============================================================================
# Plain-English Explanations
# =============================================================================

DEMO_CASE_PLAIN_ENGLISH: Dict[str, List[str]] = {
    "stable": [
        "This is a simple bet with very few moving parts.",
        "Lower fragility means fewer ways the bet can fall apart.",
        "This tool evaluates structure, not who will win.",
        "Your betting profile says you're comfortable with this level of risk.",
    ],
    "loaded": [
        "Two separate bets combined into one parlay.",
        "More legs means more things have to go right for you to win.",
        "The bets are independent—one doesn't affect the other.",
        "Still within your comfort zone, but pay attention.",
    ],
    "tense": [
        "Three bets stacked together, including a player-specific prop.",
        "Weather and injuries make some outcomes less predictable.",
        "When bets are from the same game, they can influence each other.",
        "This structure has more risk than what you usually take.",
    ],
    "critical": [
        "Five bets, multiple props on the same player.",
        "Bad weather, injury concerns, and other red flags are all present.",
        "Betting on the same player multiple times multiplies your risk.",
        "This structure exceeds your risk tolerance—the tool suggests skipping it.",
    ],
}


# =============================================================================
# Glossary Terms
# =============================================================================

DEMO_CASE_GLOSSARIES: Dict[str, List[GlossaryTerm]] = {
    "stable": [
        {"term": "Fragility", "meaning": "How many things must go right for the bet to win."},
        {"term": "Spread", "meaning": "Betting on a team to win by more than a certain number of points."},
        {"term": "DNA Profile", "meaning": "Your personalized risk tolerance settings."},
    ],
    "loaded": [
        {"term": "Fragility", "meaning": "How many things must go right for the bet to win."},
        {"term": "Parlay", "meaning": "Multiple bets combined—all must win for payout."},
        {"term": "Total", "meaning": "Betting on combined score being over or under a number."},
        {"term": "Variance", "meaning": "How unpredictable or swingy the outcomes can be."},
    ],
    "tense": [
        {"term": "Fragility", "meaning": "How many things must go right for the bet to win."},
        {"term": "Player Prop", "meaning": "A bet on a specific player's performance (yards, touchdowns, etc.)."},
        {"term": "Correlation", "meaning": "When two bets depend on similar outcomes or the same game."},
        {"term": "Context Signals", "meaning": "External factors like weather, injuries, or trades."},
    ],
    "critical": [
        {"term": "Fragility", "meaning": "How many things must go right for the bet to win."},
        {"term": "Same-Player Correlation", "meaning": "Betting on the same player multiple times—multiplies risk."},
        {"term": "Context Signals", "meaning": "External factors like weather, injuries, or trades."},
        {"term": "DNA Tolerance", "meaning": "The maximum risk level you've set in your profile."},
    ],
}


# =============================================================================
# Context Framing
# =============================================================================

DEMO_CASE_CONTEXT: Dict[str, DemoCaseContext] = {
    "stable": {
        "who_its_for": "A cautious bettor placing a simple wager",
        "why_this_case": "Shows how low-fragility bets are evaluated",
        "what_to_notice": "Structure matters more than picking winners",
    },
    "loaded": {
        "who_its_for": "Someone comfortable with moderate-complexity parlays",
        "why_this_case": "Demonstrates how adding legs increases fragility",
        "what_to_notice": "Independent bets reduce correlation penalties",
    },
    "tense": {
        "who_its_for": "An experienced bettor evaluating contextual risks",
        "why_this_case": "Shows how weather and injuries affect fragility scoring",
        "what_to_notice": "Same-game selections create compounding correlation risk",
    },
    "critical": {
        "who_its_for": "Anyone considering complex same-player props",
        "why_this_case": "Illustrates when a bet structure exceeds safe thresholds",
        "what_to_notice": "Multiple red flags combine to push past tolerance limits",
    },
}



# =============================================================================
# Public Functions
# =============================================================================


def get_narration(case_name: str) -> Optional[str]:
    """
    Get the narration script for a demo case.

    Args:
        case_name: Name of the demo case (stable, loaded, tense, critical)

    Returns:
        Narration script string, or None if case not found
    """
    return DEMO_CASE_NARRATIONS.get(case_name.lower())


def get_demo_case_data(case_name: str) -> Optional[DemoCaseNarration]:
    """
    Get complete narration data for a demo case.

    Includes narration script, plain-English explanation, and glossary.

    Args:
        case_name: Name of the demo case (stable, loaded, tense, critical)

    Returns:
        Complete demo case narration data, or None if case not found
    """
    key = case_name.lower()

    if key not in DEMO_CASE_NARRATIONS:
        return None

    return DemoCaseNarration(
        narration=DEMO_CASE_NARRATIONS[key],
        plain_english=DEMO_CASE_PLAIN_ENGLISH[key],
        glossary=DEMO_CASE_GLOSSARIES[key],
        context=DEMO_CASE_CONTEXT[key],
    )


def list_available_narrations() -> list[str]:
    """Get list of demo cases with available narrations."""
    return list(DEMO_CASE_NARRATIONS.keys())
