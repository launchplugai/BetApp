# core/protocols/dna_mode.py
"""
DNA Logic Toggle System.

Controls whether evaluation uses:
- CORE_ONLY: Base statistical engine only (free tier)
- CORE_PLUS_PROTOCOLS: Statistical engine + contextual intelligence (pro/elite tier)

Rules:
- Protocols never override DNA base probability
- Protocols adjust risk interpretation via stability modifier
- Both modes run in parallel during development for validation

Final Score = DNA Score * Stability Modifier

Where Stability Modifier = 1.0 - (protocol_fragility * damping_factor)
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class DNAMode(str, Enum):
    """Evaluation mode toggle."""
    CORE_ONLY = "core_only"
    CORE_PLUS_PROTOCOLS = "core_plus_protocols"


# Default mode — switch to CORE_PLUS_PROTOCOLS when protocols are validated
_current_mode: DNAMode = DNAMode.CORE_PLUS_PROTOCOLS

# Damping factor: how much protocol risk affects the final score
# 0.0 = protocols have no effect, 1.0 = full effect
PROTOCOL_DAMPING_FACTOR = 0.35


def get_dna_mode() -> DNAMode:
    """Get current DNA evaluation mode."""
    return _current_mode


def set_dna_mode(mode: DNAMode) -> None:
    """Set DNA evaluation mode (for testing/feature flags)."""
    global _current_mode
    _current_mode = mode


def compute_stability_modifier(protocol_fragility: float) -> float:
    """
    Compute stability modifier from protocol fragility score.

    Args:
        protocol_fragility: 0.0-1.0 fragility from protocol pipeline

    Returns:
        Stability modifier (0.65-1.0) that scales the DNA score.

    Example:
        DNA Probability = 0.64
        Protocol Fragility = 0.28
        Stability Modifier = 1.0 - (0.28 * 0.35) = 0.902
        Final Adjusted = 0.64 * 0.902 = 0.577
    """
    modifier = 1.0 - (protocol_fragility * PROTOCOL_DAMPING_FACTOR)
    # Clamp to prevent protocols from destroying the score
    return max(0.65, min(1.0, modifier))


def should_run_protocols() -> bool:
    """Check if protocols should be evaluated."""
    return _current_mode == DNAMode.CORE_PLUS_PROTOCOLS


def get_mode_for_tier(tier: str) -> DNAMode:
    """
    Get DNA mode based on user tier.

    Free tier: CORE_ONLY
    Pro/Elite tier: CORE_PLUS_PROTOCOLS
    """
    if tier in ("pro", "elite", "best", "better"):
        return DNAMode.CORE_PLUS_PROTOCOLS
    return DNAMode.CORE_ONLY


def build_dual_evaluation(
    core_result: Dict[str, Any],
    protocol_result: Optional[Dict[str, Any]],
    protocol_fragility: float = 0.0,
) -> Dict[str, Any]:
    """
    Build dual evaluation record for development comparison.

    Stores both core-only and protocol-enhanced results
    for performance validation.

    Args:
        core_result: Base DNA evaluation dict
        protocol_result: Protocol risk assessment dict (or None)
        protocol_fragility: Protocol fragility score (0.0-1.0)

    Returns:
        Combined evaluation with both perspectives
    """
    stability_modifier = compute_stability_modifier(protocol_fragility)

    return {
        "mode": _current_mode.value,
        "core": {
            "final_fragility": core_result.get("final_fragility", 0),
            "recommendation": core_result.get("recommendation", "unknown"),
        },
        "protocol": {
            "enabled": protocol_result is not None,
            "fragility_score": round(protocol_fragility, 3),
            "stability_modifier": round(stability_modifier, 3),
            "triggered_count": protocol_result.get("triggeredCount", 0) if protocol_result else 0,
            "triggered_protocols": protocol_result.get("triggeredProtocols", []) if protocol_result else [],
        },
        "adjusted": {
            "stability_modifier": round(stability_modifier, 3),
            "protocol_impact": round(1.0 - stability_modifier, 3),
        },
    }
