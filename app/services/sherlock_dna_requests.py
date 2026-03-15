"""
Thin Sherlock-facing request layer over current DNA fragments.

This does not move protocol reasoning into Sherlock yet. It creates a bounded
request/response shape so protocol and future Sherlock code can stop reaching
into ad hoc runtime state directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.services.dna_fragments import build_protocol_dna_fragments


@dataclass(frozen=True)
class FragmentRequirement:
    fragment_type: str
    rationale: str
    required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fragment_type": self.fragment_type,
            "rationale": self.rationale,
            "required": self.required,
        }


@dataclass(frozen=True)
class SherlockDNARequest:
    request_id: str
    protocol_bundle_id: str
    sport: str
    requirements: List[FragmentRequirement]
    assumptions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "protocol_bundle_id": self.protocol_bundle_id,
            "sport": self.sport,
            "requirements": [item.to_dict() for item in self.requirements],
            "assumptions": self.assumptions,
        }


@dataclass(frozen=True)
class SherlockDNAResponse:
    request: SherlockDNARequest
    fragments: Dict[str, Dict[str, Any]]
    missing_fragments: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": self.request.to_dict(),
            "fragments": self.fragments,
            "missing_fragments": self.missing_fragments,
        }


def build_nba_protocol_context_request() -> SherlockDNARequest:
    """
    First Sherlock-facing request bundle for active NBA Tier 1 protocol reasoning.
    """
    return SherlockDNARequest(
        request_id=f"req_{uuid4().hex[:12]}",
        protocol_bundle_id="nba_fatigue_injury_pace_v1",
        sport="nba",
        requirements=[
            FragmentRequirement(
                fragment_type="team_schedule_context",
                rationale="Assess rest, back-to-back state, and schedule stress.",
            ),
            FragmentRequirement(
                fragment_type="player_availability",
                rationale="Assess player injury and availability instability.",
            ),
            FragmentRequirement(
                fragment_type="game_tempo_context",
                rationale="Assess pace environment and same-game tempo sensitivity.",
            ),
            FragmentRequirement(
                fragment_type="market_sensitivity",
                rationale="Assess whether slip markets are tempo-sensitive.",
            ),
        ],
        assumptions=[
            "Protocols require structured context fragments, not raw backend internals.",
            "This request is additive and does not replace core evaluation logic.",
        ],
    )


def resolve_sherlock_dna_request(
    request: SherlockDNARequest,
    *,
    available_fragments: Dict[str, Dict[str, Any]],
) -> SherlockDNAResponse:
    resolved: Dict[str, Dict[str, Any]] = {}
    missing: List[str] = []

    for requirement in request.requirements:
        fragment = available_fragments.get(requirement.fragment_type)
        if fragment:
            resolved[requirement.fragment_type] = fragment
        elif requirement.required:
            missing.append(requirement.fragment_type)

    return SherlockDNAResponse(
        request=request,
        fragments=resolved,
        missing_fragments=missing,
    )


def build_nba_protocol_context_response(
    *,
    input_text: str,
    entities: dict,
    evaluation: Any,
    blocks: list,
    nba_heuristics: Optional[dict] = None,
    context_data: Optional[dict] = None,
    dna_fragments: Optional[Dict[str, Dict[str, Any]]] = None,
) -> SherlockDNAResponse:
    request = build_nba_protocol_context_request()
    fragments = dna_fragments or build_protocol_dna_fragments(
        input_text=input_text,
        entities=entities,
        evaluation=evaluation,
        blocks=blocks,
        nba_heuristics=nba_heuristics,
        context_data=context_data,
    )
    return resolve_sherlock_dna_request(request, available_fragments=fragments)
