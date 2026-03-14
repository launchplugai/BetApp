"""Evaluation logging service for governed learning and auditability."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from app.db import session_scope
from app.repositories.governance import EvaluationLogRepository
from app.services.model_registry import get_active_model_versions

log = logging.getLogger(__name__)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _normalized_slip_signature(input_text: str) -> str:
    normalized = (input_text or "").lower().strip()
    if not normalized:
        return ""
    for delimiter in (",", " and "):
        normalized = normalized.replace(delimiter, " + ")
    parts = [" ".join(part.split()) for part in normalized.split("+") if part.strip()]
    return " | ".join(sorted(parts))


def log_evaluation_event(
    *,
    normalized: Any,
    evaluation: Any,
    leg_count: int,
    dna_scoring: Optional[dict],
    triggered_protocols: Optional[list],
    entities: Optional[dict],
    primary_failure: Optional[dict],
) -> None:
    """
    Persist a canonical evaluation log.

    Best-effort only. Logging must never break the evaluation request.
    """
    versions = get_active_model_versions()
    scores = (dna_scoring or {}).get("scores", {})
    protocols = triggered_protocols or []
    sport_guess = (entities or {}).get("sport_guess", "unknown")
    markets = (entities or {}).get("markets_detected", []) or []

    market_type = "single"
    if leg_count > 1 or getattr(normalized, "has_canonical_legs", False) or (len(markets) > 1):
        market_type = "parlay"

    recommendation_type = (dna_scoring or {}).get("recommendation") or "proceed_with_caution"
    recommendation_details = {
        "primary_failure": primary_failure or {},
        "explanation": (dna_scoring or {}).get("explanation", {}),
    }
    score_components = (dna_scoring or {}).get("components", {}) or {}
    calibration = (dna_scoring or {}).get("calibration", {}) or {}
    metadata = {
        "tier": getattr(normalized.tier, "value", str(getattr(normalized, "tier", "good"))),
        "input_length": len(getattr(normalized, "input_text", "")),
        "input_text": getattr(normalized, "input_text", ""),
        "input_signature": _normalized_slip_signature(getattr(normalized, "input_text", "")),
        "score_model_version": (dna_scoring or {}).get("score_model_version"),
        "raw_confidence": _safe_int(score_components.get("raw_confidence"), _safe_int(scores.get("confidence"), default=0)),
        "calibration_adjustment": _safe_int(
            calibration.get("adjustment"),
            _safe_int(score_components.get("calibration_adjustment"), default=0),
        ),
        "confidence_bucket": calibration.get("bucket"),
    }

    try:
        with session_scope() as session:
            repository = EvaluationLogRepository(session)
            existing = repository.get_by_evaluation_id(str(evaluation.parlay_id))
            if existing:
                return

            repository.create(
                evaluation_id=str(evaluation.parlay_id),
                bet_id=None,
                user_id=None,
                timestamp=datetime.now(UTC),
                sport=(sport_guess or "unknown").upper(),
                market_type=market_type,
                bet_type="mixed" if len(markets) > 1 else (markets[0] if markets else "unknown"),
                legs=max(1, int(leg_count)),
                stake=None,
                odds_snapshot={},
                best_book=None,
                edge_score=_safe_int(scores.get("edge"), default=0),
                confidence_score=_safe_int(scores.get("confidence"), default=0),
                fragility_score=_safe_int(scores.get("fragility"), default=0),
                stability_score=_safe_int(scores.get("stability"), default=0),
                dna_mode="CORE_PLUS_PROTOCOLS",
                triggered_protocols=[p.get("id") for p in protocols if p.get("id")],
                recommendation_type=recommendation_type,
                recommendation_details=recommendation_details,
                user_action="view_only",
                final_result=None,
                legs_won=None,
                legs_lost=None,
                settlement_timestamp=None,
                dna_model_version=versions["dna_model_version"],
                protocol_library_version=versions["protocol_library_version"],
                calibration_version=versions["calibration_version"],
                recommendation_version=versions["recommendation_version"],
                meta=metadata,
            )
    except Exception as exc:  # pragma: no cover - best-effort path
        log.warning("Evaluation logging failed: %s", exc)


def get_recent_evaluation_logs(limit: int = 5) -> list[dict]:
    """Return recent evaluation logs in an admin/debug friendly shape."""
    with session_scope() as session:
        repository = EvaluationLogRepository(session)
        recent_logs = repository.list_recent(limit=limit)
        return [
            {
                "metadata": item.meta or {},
                "evaluation_id": item.evaluation_id,
                "timestamp": item.timestamp.isoformat() if item.timestamp else None,
                "sport": item.sport,
                "market_type": item.market_type,
                "bet_type": item.bet_type,
                "legs": item.legs,
                "confidence_score": item.confidence_score,
                "raw_confidence": (item.meta or {}).get("raw_confidence"),
                "calibration_adjustment": (item.meta or {}).get("calibration_adjustment"),
                "confidence_bucket": (item.meta or {}).get("confidence_bucket"),
                "score_model_version": (item.meta or {}).get("score_model_version"),
                "fragility_score": item.fragility_score,
                "stability_score": item.stability_score,
                "recommendation_type": item.recommendation_type,
                "triggered_protocols": item.triggered_protocols or [],
            }
            for item in recent_logs
        ]


def get_evaluation_log_summary() -> Dict[str, object]:
    """Return lightweight evaluation log metrics for introspection."""
    with session_scope() as session:
        repository = EvaluationLogRepository(session)
        total_logs = repository.count_all()
    recent_evaluations = get_recent_evaluation_logs(limit=5)
    calibration_adjustments = [
        item["calibration_adjustment"]
        for item in recent_evaluations
        if isinstance(item.get("calibration_adjustment"), int)
    ]
    return {
        "total_logs": total_logs,
        "recent_evaluations": recent_evaluations,
        "calibration_summary": {
            "recent_count": len(recent_evaluations),
            "recent_adjusted_count": sum(1 for item in calibration_adjustments if item != 0),
            "average_adjustment": round(sum(calibration_adjustments) / len(calibration_adjustments), 2)
            if calibration_adjustments
            else 0.0,
        },
    }
