# core/protocols/shadow_logger.py
"""
Shadow Compare Logger — runs CORE_ONLY and CORE_PLUS_PROTOCOLS
in parallel and logs both for calibration and premium justification.

Log Schema:
{
    "betId": "...",
    "timestamp": "2026-03-04T...",
    "modeReturned": "CORE_ONLY",     // what the user saw
    "modeShadow": "CORE_PLUS_PROTOCOLS",  // what ran in background
    "core": {"fragility": 0.41, "recommendation": "accept", "signal": "green"},
    "protocol": {
        "fragility": 0.63,
        "recommendation": "reduce",
        "signal": "yellow",
        "triggered": ["fatigue_b2b", "lineup_instability"],
        "stabilityModifier": 0.87
    },
    "delta": {
        "fragilityDiff": 0.22,
        "recommendationChanged": true,
        "signalChanged": true
    }
}

Later join with outcome data for:
- calibration curves
- ROI impact analysis
- premium tier justification
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_logger = logging.getLogger(__name__)

# In-memory log buffer (persists for session, flushed to file on threshold)
_LOG_BUFFER: List[Dict[str, Any]] = []
_BUFFER_THRESHOLD = 50  # flush to disk every N records
_LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "logs")


def log_shadow_compare(
    bet_id: str,
    mode_returned: str,
    core_result: Dict[str, Any],
    protocol_result: Optional[Dict[str, Any]],
    stability_modifier: float = 1.0,
    triggered_protocols: Optional[List[str]] = None,
    user_tier: str = "free",
) -> Dict[str, Any]:
    """
    Log a shadow comparison between core-only and protocol-enhanced results.

    Args:
        bet_id: Unique bet/parlay identifier
        mode_returned: The mode actually returned to the user
        core_result: Core engine output (fragility, recommendation, signal)
        protocol_result: Protocol engine output (or None if not run)
        stability_modifier: Protocol stability modifier applied
        triggered_protocols: List of triggered protocol names
        user_tier: User's tier level

    Returns:
        The log record (for testing)
    """
    now = datetime.now(timezone.utc).isoformat()

    core_fragility = core_result.get("final_fragility", 0)
    core_recommendation = core_result.get("recommendation", "unknown")
    core_signal = core_result.get("signal", "unknown")

    protocol_fragility = 0.0
    protocol_recommendation = "unknown"
    protocol_signal = "unknown"
    protocol_triggered = triggered_protocols or []

    if protocol_result:
        protocol_fragility = protocol_result.get("fragilityScore", 0)
        # Derive recommendation from fragility
        if protocol_fragility >= 0.7:
            protocol_recommendation = "avoid"
            protocol_signal = "red"
        elif protocol_fragility >= 0.4:
            protocol_recommendation = "reduce"
            protocol_signal = "yellow"
        else:
            protocol_recommendation = core_recommendation
            protocol_signal = core_signal

    # Compute delta
    fragility_diff = abs(protocol_fragility - (core_fragility / 100.0))  # normalize core to 0-1
    rec_changed = protocol_recommendation != core_recommendation
    signal_changed = protocol_signal != core_signal

    record = {
        "betId": bet_id,
        "timestamp": now,
        "userTier": user_tier,
        "modeReturned": mode_returned,
        "modeShadow": "core_plus_protocols" if protocol_result else "core_only",
        "core": {
            "fragility": round(core_fragility, 2),
            "recommendation": core_recommendation,
            "signal": core_signal,
        },
        "protocol": {
            "fragility": round(protocol_fragility, 3),
            "recommendation": protocol_recommendation,
            "signal": protocol_signal,
            "triggered": protocol_triggered,
            "triggeredCount": len(protocol_triggered),
            "stabilityModifier": round(stability_modifier, 3),
        },
        "delta": {
            "fragilityDiff": round(fragility_diff, 3),
            "recommendationChanged": rec_changed,
            "signalChanged": signal_changed,
        },
    }

    _LOG_BUFFER.append(record)

    _logger.info(
        f"Shadow compare: bet={bet_id} "
        f"core_frag={core_fragility:.1f} proto_frag={protocol_fragility:.3f} "
        f"delta={fragility_diff:.3f} rec_changed={rec_changed} "
        f"triggered={len(protocol_triggered)}"
    )

    # Flush if buffer is full
    if len(_LOG_BUFFER) >= _BUFFER_THRESHOLD:
        flush_log()

    return record


def get_log_buffer() -> List[Dict[str, Any]]:
    """Get the current in-memory log buffer (for testing/inspection)."""
    return list(_LOG_BUFFER)


def get_log_stats() -> Dict[str, Any]:
    """Get summary statistics from the log buffer."""
    if not _LOG_BUFFER:
        return {
            "totalRecords": 0,
            "recommendationChanges": 0,
            "signalChanges": 0,
            "avgFragilityDiff": 0,
            "protocolTriggeredCount": 0,
        }

    rec_changes = sum(1 for r in _LOG_BUFFER if r["delta"]["recommendationChanged"])
    sig_changes = sum(1 for r in _LOG_BUFFER if r["delta"]["signalChanged"])
    avg_diff = sum(r["delta"]["fragilityDiff"] for r in _LOG_BUFFER) / len(_LOG_BUFFER)
    total_triggered = sum(r["protocol"]["triggeredCount"] for r in _LOG_BUFFER)

    return {
        "totalRecords": len(_LOG_BUFFER),
        "recommendationChanges": rec_changes,
        "recommendationChangeRate": round(rec_changes / len(_LOG_BUFFER), 3),
        "signalChanges": sig_changes,
        "signalChangeRate": round(sig_changes / len(_LOG_BUFFER), 3),
        "avgFragilityDiff": round(avg_diff, 3),
        "protocolTriggeredCount": total_triggered,
        "avgTriggeredPerBet": round(total_triggered / len(_LOG_BUFFER), 1),
    }


def flush_log() -> int:
    """
    Flush the in-memory log buffer to disk.

    Returns:
        Number of records flushed
    """
    global _LOG_BUFFER
    if not _LOG_BUFFER:
        return 0

    count = len(_LOG_BUFFER)
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        log_file = os.path.join(
            _LOG_DIR,
            f"protocol_shadow_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl",
        )
        with open(log_file, "a") as f:
            for record in _LOG_BUFFER:
                f.write(json.dumps(record) + "\n")
        _LOG_BUFFER = []
        _logger.info(f"Flushed {count} shadow compare records to {log_file}")
    except Exception as e:
        _logger.warning(f"Failed to flush shadow log: {e}")

    return count


def clear_log() -> None:
    """Clear the in-memory buffer without flushing."""
    global _LOG_BUFFER
    _LOG_BUFFER = []
