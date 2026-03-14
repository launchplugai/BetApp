"""Outcome enrichment for governed evaluation logs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Iterable

from app.db import session_scope
from app.repositories.governance import BetRepository, EvaluationLogRepository


_RESULT_MAP = {
    "won": "win",
    "lost": "loss",
    "void": "void",
    "push": "push",
}


def _normalized_slip_signature(input_text: str) -> str:
    normalized = (input_text or "").lower().strip()
    if not normalized:
        return ""
    for delimiter in (",", " and "):
        normalized = normalized.replace(delimiter, " + ")
    parts = [" ".join(part.split()) for part in normalized.split("+") if part.strip()]
    return " | ".join(sorted(parts))


def _bet_signature_candidates(bet) -> set[str]:
    candidates: set[str] = set()
    if getattr(bet, "input_text", None):
        signature = _normalized_slip_signature(bet.input_text)
        if signature:
            candidates.add(signature)

    legs = getattr(bet, "legs", None) or []
    if legs:
        leg_parts = []
        for leg in legs:
            if not isinstance(leg, dict):
                continue
            entity = str(leg.get("entity", "")).strip().lower()
            market = str(leg.get("market", "")).strip().lower()
            value = str(leg.get("value", "")).strip().lower()
            selection = str(leg.get("selection", "")).strip().lower()
            leg_parts.append(" ".join(part for part in (entity, market, value or selection) if part))
        if leg_parts:
            candidates.add(" | ".join(sorted(" ".join(part.split()) for part in leg_parts if part)))
    return candidates


def _find_matching_bet(*, bet_repository: BetRepository, input_text: str, input_signature: str, search_limit: int) -> object | None:
    bet = bet_repository.find_latest_by_input_text(input_text)
    if bet and bet.status != "pending":
        return bet

    if not input_signature:
        return None

    for candidate in bet_repository.list_recent_settled(limit=search_limit):
        if input_signature in _bet_signature_candidates(candidate):
            return candidate
    return None


def enrich_evaluation_log_outcomes(limit: int = 200) -> dict:
    """
    Backfill governed evaluation logs with settled outcomes from stored bets.

    Current matching strategy prefers explicit linkage, then falls back:
    - only logs without `final_result`
    - match using explicit `evaluation_id` on saved bets when present
    - then exact `input_text` captured in log metadata
    - apply only when the corresponding bet has a non-pending status
    """
    matched = 0
    updated = 0

    with session_scope() as session:
        evaluation_repository = EvaluationLogRepository(session)
        bet_repository = BetRepository(session)

        for record in evaluation_repository.list_unsettled(limit=limit):
            meta = record.meta or {}
            input_text = meta.get("input_text")
            input_signature = meta.get("input_signature") or _normalized_slip_signature(input_text or "")
            if not input_text and not input_signature:
                continue

            bet = bet_repository.find_latest_by_evaluation_id(record.evaluation_id)
            if not bet:
                bet = _find_matching_bet(
                    bet_repository=bet_repository,
                    input_text=input_text or "",
                    input_signature=input_signature,
                    search_limit=max(limit * 3, 200),
                )
            if not bet or bet.status == "pending":
                continue

            matched += 1
            final_result = _RESULT_MAP.get(bet.status, "unknown")
            if record.final_result == final_result:
                continue

            record.bet_id = record.bet_id or bet.id
            record.final_result = final_result
            record.settlement_timestamp = bet.settled_at or datetime.now(UTC)
            if bet.status == "won":
                record.legs_won = record.legs
                record.legs_lost = 0
            elif bet.status == "lost":
                record.legs_won = 0
                record.legs_lost = record.legs
            else:
                record.legs_won = None
                record.legs_lost = None
            updated += 1

    return {
        "matched_bets": matched,
        "updated_logs": updated,
    }
