"""
Runtime protocol registry and Tier 1 protocol evaluation.

This is the bridge between the canonical protocol docs and the current
application runtime. It starts with the launch protocols only and uses data
already available inside the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from app.services.dna_fragments import build_protocol_dna_fragments
from app.services.sherlock_dna_requests import build_nba_protocol_context_response


@dataclass(frozen=True)
class ProtocolImpact:
    stability_delta: int = 0
    fragility_delta: int = 0
    edge_delta: int = 0
    volatility_delta: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "stability_delta": self.stability_delta,
            "fragility_delta": self.fragility_delta,
            "edge_delta": self.edge_delta,
            "volatility_delta": self.volatility_delta,
        }


@dataclass(frozen=True)
class TriggeredProtocol:
    id: str
    name: str
    category: str
    trigger_confidence: float
    impact: ProtocolImpact
    evidence: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "trigger_confidence": self.trigger_confidence,
            "impact": self.impact.to_dict(),
            "evidence": self.evidence,
        }


def _contains_injury_language(text: str) -> bool:
    text_lower = text.lower()
    return any(
        token in text_lower
        for token in (
            "questionable",
            "game-time decision",
            "gtd",
            "doubtful",
            "probable",
            "injury",
        )
    )


def _extract_nba_rest_evidence_from_fragment(schedule_fragment: Optional[dict]) -> List[str]:
    if not schedule_fragment:
        return []
    evidence: List[str] = []
    summary = schedule_fragment.get("context_summary", "")
    flags = schedule_fragment.get("risk_flags", []) or []

    if "back-to-back" in summary.lower() or " 0d " in f" {summary.lower()} ":
        evidence.append(summary)

    for flag in flags:
        lower = flag.lower()
        if "back-to-back" in lower or "0d" in lower:
            evidence.append(flag)

    return evidence


def _extract_nba_rest_evidence(nba_heuristics: Optional[dict]) -> List[str]:
    if not nba_heuristics:
        return []
    return _extract_nba_rest_evidence_from_fragment(
        {
            "context_summary": nba_heuristics.get("context_summary", ""),
            "risk_flags": nba_heuristics.get("risk_flags", []) or [],
        }
    )


def _rest_trigger_confidence(rest_evidence: List[str]) -> float:
    combined = " | ".join(rest_evidence).lower()
    if "both teams on back-to-back" in combined:
        return 0.93
    if " 0d " in f" {combined} " or "back-to-back" in combined:
        return 0.88
    return 0.84


def _extract_injury_evidence(input_text: str, nba_heuristics: Optional[dict]) -> List[str]:
    evidence: List[str] = []

    if _contains_injury_language(input_text):
        evidence.append("Input references injury or availability uncertainty.")

    if nba_heuristics:
        summary = nba_heuristics.get("context_summary", "")
        flags = nba_heuristics.get("risk_flags", []) or []

        if "injur" in summary.lower():
            evidence.append(summary)

        for flag in flags:
            if "injur" in flag.lower() or "questionable" in flag.lower():
                evidence.append(flag)

    deduped: List[str] = []
    seen = set()
    for item in evidence:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _extract_context_injury_evidence_from_fragment(player_availability_fragment: Optional[dict]) -> List[str]:
    if not player_availability_fragment:
        return []
    evidence: List[str] = []
    modifiers = player_availability_fragment.get("negative_modifiers", []) or []
    missing_data = player_availability_fragment.get("missing_data", []) or []

    for modifier in modifiers:
        adjustment = float(modifier.get("adjustment", 0.0) or 0.0)
        reason = modifier.get("reason")
        if adjustment < 0 and reason:
            evidence.append(reason)

    for missing_item in missing_data:
        lower = str(missing_item).lower()
        if any(token in lower for token in ("availability", "injur", "unreachable", "fallback")):
            evidence.append(str(missing_item))

    deduped: List[str] = []
    seen = set()
    for item in evidence:
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _extract_context_injury_evidence(context_data: Optional[dict]) -> List[str]:
    if not context_data:
        return []
    impact = context_data.get("impact", {}) or {}
    return _extract_context_injury_evidence_from_fragment(
        {
            "negative_modifiers": impact.get("modifiers", []) or [],
            "missing_data": context_data.get("missing_data", []) or [],
        }
    )


def _build_pace_mismatch_evidence_from_fragments(
    tempo_fragment: Optional[dict],
    market_sensitivity_fragment: Optional[dict],
) -> List[str]:
    evidence: List[str] = []
    same_game_count = int((tempo_fragment or {}).get("same_game_count", 0) or 0)
    markets = (tempo_fragment or {}).get("markets_detected", []) or []
    pace_sensitive_markets = (market_sensitivity_fragment or {}).get("pace_sensitive_markets", []) or []
    pace_sensitive_count = len(pace_sensitive_markets)

    if same_game_count >= 2 and pace_sensitive_count > 0:
        evidence.append("Slip stacks same-game pace-sensitive markets.")
    if same_game_count >= 3:
        evidence.append(f"{same_game_count} legs from one game raise tempo sensitivity.")
    if "total" in markets and pace_sensitive_count >= 2:
        evidence.append("Totals paired with same-game props increase tempo exposure.")

    context_summary = (tempo_fragment or {}).get("context_summary", "")
    if "pace" in context_summary.lower():
        evidence.append(context_summary)

    return evidence


def _build_pace_mismatch_evidence(entities: dict, nba_heuristics: Optional[dict]) -> List[str]:
    if not entities and not nba_heuristics:
        return []
    return _build_pace_mismatch_evidence_from_fragments(
        {
            "same_game_count": (entities or {}).get("same_game_indicator", {}).get("same_game_count", 0),
            "context_summary": (nba_heuristics or {}).get("context_summary", ""),
        },
        {
            "pace_sensitive_markets": [
                market
                for market in ((entities or {}).get("markets_detected", []) or [])
                if market in {"total", "points", "assists", "rebounds", "threes", "pra", "pr", "ra", "pa"}
            ]
        },
    )


def _pace_trigger_confidence_from_fragments(
    tempo_fragment: Optional[dict],
    market_sensitivity_fragment: Optional[dict],
    evidence: List[str],
) -> float:
    if not evidence:
        return 0.0

    same_game_count = int((tempo_fragment or {}).get("same_game_count", 0) or 0)
    pace_sensitive_count = len((market_sensitivity_fragment or {}).get("pace_sensitive_markets", []) or [])
    context_summary = (tempo_fragment or {}).get("context_summary", "")

    if same_game_count >= 3 and pace_sensitive_count >= 2:
        return 0.78
    if same_game_count >= 2 and pace_sensitive_count >= 1:
        return 0.70
    if "pace" in context_summary.lower():
        return 0.66
    return 0.62


def _pace_trigger_confidence(entities: dict, nba_heuristics: Optional[dict], evidence: List[str]) -> float:
    return _pace_trigger_confidence_from_fragments(
        {
            "same_game_count": (entities or {}).get("same_game_indicator", {}).get("same_game_count", 0),
            "context_summary": (nba_heuristics or {}).get("context_summary", ""),
        },
        {
            "pace_sensitive_markets": [
                market
                for market in ((entities or {}).get("markets_detected", []) or [])
                if market in {"total", "points", "assists", "rebounds", "threes", "pra", "pr", "ra", "pa"}
            ]
        },
        evidence,
    )


def _correlation_protocol_impact(correlation_count: int, correlation_penalty: float) -> ProtocolImpact:
    fragility_delta = 6
    if correlation_count >= 2:
        fragility_delta += 2
    if correlation_count >= 3:
        fragility_delta += 2
    if correlation_penalty >= 8:
        fragility_delta += 2
    if correlation_penalty >= 12:
        fragility_delta += 2
    return ProtocolImpact(fragility_delta=min(fragility_delta, 14))


def _correlation_trigger_confidence(correlation_count: int, correlation_penalty: float) -> float:
    if correlation_count >= 3 or correlation_penalty >= 12:
        return 0.95
    if correlation_count >= 2 or correlation_penalty >= 8:
        return 0.92
    return 0.88


def evaluate_tier1_protocols(
    *,
    input_text: str,
    blocks: list,
    entities: dict,
    evaluation: Any,
    nba_heuristics: Optional[dict] = None,
    context_data: Optional[dict] = None,
    dna_fragments: Optional[dict] = None,
) -> List[TriggeredProtocol]:
    """
    Evaluate launch-priority protocols using deterministic runtime data.
    """
    protocols: List[TriggeredProtocol] = []
    fragments = dna_fragments or build_protocol_dna_fragments(
        input_text=input_text,
        entities=entities,
        evaluation=evaluation,
        blocks=blocks,
        nba_heuristics=nba_heuristics,
        context_data=context_data,
    )
    slip_structure = fragments.get("slip_structure", {}) or {}
    schedule_fragment = fragments.get("team_schedule_context", {}) or {}
    player_availability = fragments.get("player_availability", {}) or {}
    tempo_fragment = fragments.get("game_tempo_context", {}) or {}
    market_sensitivity = fragments.get("market_sensitivity", {}) or {}
    nba_protocol_context = build_nba_protocol_context_response(
        input_text=input_text,
        entities=entities,
        evaluation=evaluation,
        blocks=blocks,
        nba_heuristics=nba_heuristics,
        context_data=context_data,
        dna_fragments=fragments,
    )
    nba_fragments = nba_protocol_context.fragments
    schedule_fragment = nba_fragments.get("team_schedule_context", schedule_fragment) or {}
    player_availability = nba_fragments.get("player_availability", player_availability) or {}
    tempo_fragment = nba_fragments.get("game_tempo_context", tempo_fragment) or {}
    market_sensitivity = nba_fragments.get("market_sensitivity", market_sensitivity) or {}

    leg_count = int(slip_structure.get("leg_count", len(blocks or [])) or 0)

    rest_evidence = _extract_nba_rest_evidence_from_fragment(schedule_fragment)
    if rest_evidence:
        protocols.append(
            TriggeredProtocol(
                id="fatigue_back_to_back",
                name="Back-to-Back Fatigue",
                category="schedule_fatigue",
                trigger_confidence=_rest_trigger_confidence(rest_evidence),
                impact=ProtocolImpact(stability_delta=-8, fragility_delta=5),
                evidence=rest_evidence,
            )
        )

    if leg_count > 4:
        extra_legs = leg_count - 4
        protocols.append(
            TriggeredProtocol(
                id="structure_leg_count_risk",
                name="Leg Count Risk",
                category="structural_parlay",
                trigger_confidence=1.0,
                impact=ProtocolImpact(fragility_delta=8 * extra_legs),
                evidence=[
                    f"Parlay contains {leg_count} legs.",
                    "Parlay complexity increases failure probability.",
                ],
            )
        )

    correlations = getattr(evaluation, "correlations", []) or []
    correlation_count = int(slip_structure.get("correlation_count", len(correlations)) or 0)
    correlation_penalty = float(
        slip_structure.get(
            "correlation_penalty",
            getattr(evaluation.metrics, "correlation_penalty", 0.0),
        )
        or 0.0
    )
    if correlations or correlation_penalty > 0:
        evidence = []
        if correlations:
            evidence.append(f"{correlation_count} correlated leg pair(s) detected.")
        if correlation_penalty > 0:
            evidence.append(f"Correlation penalty applied: +{correlation_penalty:.1f}.")
        if correlation_count >= 3 or correlation_penalty >= 12:
            evidence.append("Correlation stack is severe enough to materially weaken the slip.")
        elif correlation_count >= 2 or correlation_penalty >= 8:
            evidence.append("Multiple dependencies are stacking across the slip.")
        evidence.append("Multiple legs depend on the same game conditions.")
        protocols.append(
            TriggeredProtocol(
                id="structure_correlation_risk",
                name="Correlation Risk",
                category="structural_parlay",
                trigger_confidence=_correlation_trigger_confidence(correlation_count, correlation_penalty),
                impact=_correlation_protocol_impact(correlation_count, correlation_penalty),
                evidence=evidence,
            )
        )

    pace_evidence = _build_pace_mismatch_evidence_from_fragments(tempo_fragment, market_sensitivity)
    if pace_evidence:
        protocols.append(
            TriggeredProtocol(
                id="matchup_pace_mismatch",
                name="Pace Mismatch",
                category="matchup",
                trigger_confidence=_pace_trigger_confidence_from_fragments(
                    tempo_fragment,
                    market_sensitivity,
                    pace_evidence,
                ),
                impact=ProtocolImpact(volatility_delta=5),
                evidence=pace_evidence + ["Possession tempo mismatch increases scoring variance."],
            )
        )

    injury_evidence = _extract_injury_evidence(input_text, nba_heuristics)
    context_injury_evidence = _extract_context_injury_evidence_from_fragment(player_availability)
    if context_injury_evidence:
        injury_evidence.extend(context_injury_evidence)
    if injury_evidence:
        deduped_injury_evidence: List[str] = []
        seen = set()
        for item in injury_evidence:
            if item and item not in seen:
                seen.add(item)
                deduped_injury_evidence.append(item)
        protocols.append(
            TriggeredProtocol(
                id="matchup_injury_instability",
                name="Injury Instability",
                category="matchup",
                trigger_confidence=0.89 if context_injury_evidence else 0.77,
                impact=ProtocolImpact(stability_delta=-7, fragility_delta=5),
                evidence=deduped_injury_evidence,
            )
        )

    return protocols


def summarize_protocol_impacts(protocols: Iterable[TriggeredProtocol]) -> Dict[str, int]:
    return {
        "stability_penalty": sum(abs(min(0, p.impact.stability_delta)) for p in protocols),
        "fragility_penalty": sum(max(0, p.impact.fragility_delta) for p in protocols),
        "edge_bonus": sum(max(0, p.impact.edge_delta) for p in protocols),
        "volatility_penalty": sum(max(0, p.impact.volatility_delta) for p in protocols),
    }
