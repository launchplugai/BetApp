"""
Canonical scoring bridge for the current runtime.

The current engine already computes real fragility and recommendation data, but
it does not emit the new contract-aligned score payload. This module derives a
deterministic payload from existing engine outputs plus protocol impacts.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _confidence_badge(confidence: int) -> str:
    if confidence >= 85:
        return "green"
    if confidence >= 70:
        return "yellow"
    if confidence >= 55:
        return "orange"
    return "red"


def _confidence_label(confidence: int) -> str:
    if confidence >= 85:
        return "High"
    if confidence >= 70:
        return "Moderate"
    if confidence >= 55:
        return "Cautious"
    return "Fragile"


def _map_recommendation(confidence: int, fragility: int) -> str:
    if fragility >= 70 or confidence < 45:
        return "avoid_fragile_structure"
    if fragility >= 50 or confidence < 60:
        return "consider_simplifying"
    if fragility >= 30 or confidence < 75:
        return "proceed_with_caution"
    return "proceed"


def _signal_edge_baseline(signal: str | None) -> int:
    return {
        "blue": 8,
        "green": 4,
        "yellow": 0,
        "red": -6,
    }.get(signal or "", 0)


def _calibration_adjustment(
    *,
    signal: str | None,
    confidence: int,
    fragility: int,
    protocol_count: int,
    protocol_summary: dict,
) -> int:
    adjustment = 0
    fragility_penalty = int(round(float(protocol_summary.get("fragility_penalty", 0))))
    stability_penalty = int(round(float(protocol_summary.get("stability_penalty", 0))))
    volatility_penalty = int(round(float(protocol_summary.get("volatility_penalty", 0))))

    if protocol_count >= 3:
        adjustment -= 4
    elif protocol_count == 2:
        adjustment -= 2

    if fragility_penalty >= 12:
        adjustment -= 4
    elif fragility_penalty >= 6:
        adjustment -= 2

    if stability_penalty >= 7:
        adjustment -= 2

    if volatility_penalty >= 5:
        adjustment -= 2

    if signal == "red":
        adjustment -= 3
    elif signal == "blue" and protocol_count == 0 and fragility <= 20 and confidence < 85:
        adjustment += 2

    if fragility >= 70 and confidence >= 55:
        adjustment -= 6
    elif fragility >= 55 and confidence >= 70:
        adjustment -= 4

    return adjustment


def build_canonical_scoring_payload(
    *,
    evaluation: Any,
    signal_info: dict,
    triggered_protocols: List[dict],
    protocol_summary: dict,
    primary_failure: dict,
) -> Dict[str, Any]:
    base_fragility = float(getattr(evaluation.metrics, "final_fragility", 0.0))
    fragility_penalty = float(protocol_summary.get("fragility_penalty", 0))
    volatility_penalty = float(protocol_summary.get("volatility_penalty", 0))
    protocol_adjusted_fragility = base_fragility + fragility_penalty + (volatility_penalty * 0.5)
    fragility = int(round(_clamp(protocol_adjusted_fragility, 0, 100)))

    stability = int(
        round(
            _clamp(
                100
                - protocol_summary.get("stability_penalty", 0)
                - volatility_penalty
                - (fragility * 0.12),
                0,
                100,
            )
        )
    )

    edge = int(
        round(
            _clamp(
                _signal_edge_baseline(signal_info.get("signal"))
                + protocol_summary.get("edge_bonus", 0)
                - (volatility_penalty * 0.5),
                -100,
                100,
            )
        )
    )

    probability_strength = int(round(_clamp(100 - fragility, 0, 100)))
    edge_component = _clamp(50 + (edge * 5), 0, 100)
    raw_confidence = int(
        round(
            _clamp(
                (0.40 * probability_strength)
                + (0.25 * stability)
                + (0.20 * edge_component)
                - (0.15 * fragility),
                0,
                100,
            )
        )
    )
    calibration_adjustment = _calibration_adjustment(
        signal=signal_info.get("signal"),
        confidence=raw_confidence,
        fragility=fragility,
        protocol_count=len(triggered_protocols),
        protocol_summary=protocol_summary,
    )
    confidence = int(round(_clamp(raw_confidence + calibration_adjustment, 0, 100)))
    recommendation = _map_recommendation(confidence, fragility)

    strengths: List[str] = []
    risks: List[str] = []

    if edge > 0:
        strengths.append(f"Context signals show a small edge ({edge:+d}).")
    if stability >= 70:
        strengths.append("Environment looks reasonably stable for this structure.")
    if fragility <= 35:
        strengths.append("Structural fragility remains contained.")

    for protocol in triggered_protocols:
        impact = protocol.get("impact", {})
        if impact.get("edge_delta", 0) > 0:
            strengths.append(f"{protocol['name']} improved edge context.")
        if impact.get("stability_delta", 0) < 0 or impact.get("fragility_delta", 0) > 0:
            evidence = protocol.get("evidence", [])
            risks.append(evidence[0] if evidence else protocol["name"])

    if primary_failure and primary_failure.get("description"):
        risks.insert(0, primary_failure["description"])

    return {
        "score_model_version": "1.2.0",
        "scores": {
            "confidence": confidence,
            "fragility": fragility,
            "edge": edge,
            "stability": stability,
        },
        "components": {
            "base_fragility": int(round(_clamp(base_fragility, 0, 100))),
            "protocol_fragility_penalty": int(round(fragility_penalty)),
            "protocol_volatility_penalty": int(round(volatility_penalty)),
            "probability_strength": probability_strength,
            "edge_baseline": _signal_edge_baseline(signal_info.get("signal")),
            "edge_component": int(round(edge_component)),
            "raw_confidence": raw_confidence,
            "calibration_adjustment": calibration_adjustment,
        },
        "calibration": {
            "bucket": f"{(confidence // 5) * 5}-{((confidence // 5) * 5) + 4}",
            "adjustment": calibration_adjustment,
        },
        "badge": _confidence_badge(confidence),
        "recommendation": recommendation,
        "protocols_triggered": triggered_protocols,
        "explanation": {
            "confidence_label": _confidence_label(confidence),
            "strengths": strengths[:3],
            "risks": risks[:4],
            "recommendation": primary_failure.get("fastestFix", {}).get("description", "") or recommendation,
        },
        "legacy_alignment": {
            "signal": signal_info.get("signal"),
            "grade": signal_info.get("grade"),
            "fragility_score": signal_info.get("fragilityScore"),
        },
    }
