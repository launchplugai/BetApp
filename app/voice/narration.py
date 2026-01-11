# app/voice/narration.py
"""
Voice Narration Scripts for Demo Cases.

Each script is optimized for TTS delivery (~20 seconds or less).
No prediction language. No "locks". No hype.
"""
from typing import Dict, Optional

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


def get_narration(case_name: str) -> Optional[str]:
    """
    Get the narration script for a demo case.

    Args:
        case_name: Name of the demo case (stable, loaded, tense, critical)

    Returns:
        Narration script string, or None if case not found
    """
    return DEMO_CASE_NARRATIONS.get(case_name.lower())


def list_available_narrations() -> list[str]:
    """Get list of demo cases with available narrations."""
    return list(DEMO_CASE_NARRATIONS.keys())
