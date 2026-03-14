"""
DNA fragment adapter for the first Sherlock ↔ DNA boundary slice.

This module does not replace the DNA Matrix engine. It provides a small,
explicit adapter that turns current runtime/context state into structured
fragments protocols and future Sherlock-facing adapters can request.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_slip_structure_fragment(*, entities: dict, evaluation: Any, blocks: list) -> Dict[str, Any]:
    same_game = (entities or {}).get("same_game_indicator", {}) or {}
    markets = (entities or {}).get("markets_detected", []) or []
    correlations = getattr(evaluation, "correlations", []) or []
    metrics = getattr(evaluation, "metrics", None)
    return {
        "fragment_type": "slip_structure",
        "leg_count": len(blocks or []),
        "same_game_count": int(same_game.get("same_game_count", 0) or 0),
        "correlation_count": int(getattr(evaluation, "correlation_count", len(correlations)) or 0),
        "correlation_penalty": float(
            getattr(
                evaluation,
                "correlation_penalty",
                getattr(metrics, "correlation_penalty", 0.0),
            )
            or 0.0
        ),
        "markets_detected": markets,
    }


def build_team_schedule_context_fragment(*, nba_heuristics: Optional[dict]) -> Dict[str, Any]:
    heuristics = nba_heuristics or {}
    return {
        "fragment_type": "team_schedule_context",
        "context_summary": heuristics.get("context_summary", ""),
        "risk_flags": list(heuristics.get("risk_flags", []) or []),
    }


def build_player_availability_fragment(*, input_text: str, context_data: Optional[dict], nba_heuristics: Optional[dict]) -> Dict[str, Any]:
    impact = (context_data or {}).get("impact", {}) or {}
    modifiers = impact.get("modifiers", []) or []
    missing_data = (context_data or {}).get("missing_data", []) or []
    return {
        "fragment_type": "player_availability",
        "input_text": input_text,
        "negative_modifiers": [
            {
                "reason": modifier.get("reason"),
                "adjustment": modifier.get("adjustment"),
            }
            for modifier in modifiers
            if float(modifier.get("adjustment", 0.0) or 0.0) < 0
        ],
        "missing_data": [str(item) for item in missing_data],
        "context_summary": (nba_heuristics or {}).get("context_summary", ""),
        "risk_flags": list((nba_heuristics or {}).get("risk_flags", []) or []),
    }


def build_team_lineup_stability_fragment(*, context_data: Optional[dict], nba_heuristics: Optional[dict]) -> Dict[str, Any]:
    impact = (context_data or {}).get("impact", {}) or {}
    modifiers = impact.get("modifiers", []) or []
    return {
        "fragment_type": "team_lineup_stability",
        "negative_modifiers": [
            {
                "reason": modifier.get("reason"),
                "adjustment": modifier.get("adjustment"),
            }
            for modifier in modifiers
            if float(modifier.get("adjustment", 0.0) or 0.0) < 0
        ],
        "risk_flags": list((nba_heuristics or {}).get("risk_flags", []) or []),
        "context_summary": (nba_heuristics or {}).get("context_summary", ""),
    }


def build_game_tempo_context_fragment(*, entities: dict, nba_heuristics: Optional[dict]) -> Dict[str, Any]:
    same_game = (entities or {}).get("same_game_indicator", {}) or {}
    markets = (entities or {}).get("markets_detected", []) or []
    return {
        "fragment_type": "game_tempo_context",
        "same_game_count": int(same_game.get("same_game_count", 0) or 0),
        "markets_detected": markets,
        "context_summary": (nba_heuristics or {}).get("context_summary", ""),
        "risk_flags": list((nba_heuristics or {}).get("risk_flags", []) or []),
    }


def build_market_sensitivity_fragment(*, entities: dict) -> Dict[str, Any]:
    markets = (entities or {}).get("markets_detected", []) or []
    pace_sensitive_markets = {
        "total",
        "points",
        "assists",
        "rebounds",
        "threes",
        "pra",
        "pr",
        "ra",
        "pa",
    }
    detected: List[str] = [market for market in markets if market in pace_sensitive_markets]
    return {
        "fragment_type": "market_sensitivity",
        "markets_detected": markets,
        "pace_sensitive_markets": detected,
        "has_pace_sensitive_market": len(detected) > 0,
    }


def build_protocol_dna_fragments(
    *,
    input_text: str,
    entities: dict,
    evaluation: Any,
    blocks: list,
    nba_heuristics: Optional[dict] = None,
    context_data: Optional[dict] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Build the first explicit protocol-facing DNA fragment set from current runtime state.
    """
    return {
        "slip_structure": build_slip_structure_fragment(
            entities=entities,
            evaluation=evaluation,
            blocks=blocks,
        ),
        "team_schedule_context": build_team_schedule_context_fragment(
            nba_heuristics=nba_heuristics,
        ),
        "player_availability": build_player_availability_fragment(
            input_text=input_text,
            context_data=context_data,
            nba_heuristics=nba_heuristics,
        ),
        "team_lineup_stability": build_team_lineup_stability_fragment(
            context_data=context_data,
            nba_heuristics=nba_heuristics,
        ),
        "game_tempo_context": build_game_tempo_context_fragment(
            entities=entities,
            nba_heuristics=nba_heuristics,
        ),
        "market_sensitivity": build_market_sensitivity_fragment(
            entities=entities,
        ),
    }
