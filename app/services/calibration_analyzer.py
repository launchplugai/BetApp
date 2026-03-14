"""Lightweight calibration analysis over governed evaluation logs."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from app.db import session_scope
from app.repositories.governance import EvaluationLogRepository


def _bucket_label(score: int) -> str:
    floor = max(0, min(95, (int(score) // 5) * 5))
    return f"{floor}-{floor + 4}"


def get_calibration_report(limit: int = 200) -> Dict[str, object]:
    """
    Build a lightweight bucketed calibration report from recent evaluations.

    This is not a settled-outcome calibration curve yet. It summarizes how the
    scoring layer is distributing and adjusting confidence so the admin control
    plane can review the current behavior.
    """
    with session_scope() as session:
        repository = EvaluationLogRepository(session)
        records = [
            {
                "confidence_score": item.confidence_score,
                "sport": item.sport,
                "final_result": item.final_result,
                "meta": item.meta or {},
            }
            for item in repository.list_recent(limit=limit)
        ]

    buckets: dict[str, dict] = defaultdict(
        lambda: {
            "count": 0,
            "avg_confidence": 0.0,
            "avg_raw_confidence": 0.0,
            "avg_adjustment": 0.0,
            "settled_count": 0,
            "win_count": 0,
            "sports": set(),
        }
    )

    for record in records:
        meta = record.get("meta") or {}
        confidence = int(record.get("confidence_score") or 0)
        raw_confidence = int(meta.get("raw_confidence", confidence) or confidence)
        adjustment = int(meta.get("calibration_adjustment", 0) or 0)
        label = meta.get("confidence_bucket") or _bucket_label(confidence)

        bucket = buckets[label]
        bucket["count"] += 1
        bucket["avg_confidence"] += confidence
        bucket["avg_raw_confidence"] += raw_confidence
        bucket["avg_adjustment"] += adjustment
        if record.get("final_result") in {"win", "loss"}:
            bucket["settled_count"] += 1
            if record["final_result"] == "win":
                bucket["win_count"] += 1
        if record.get("sport"):
            bucket["sports"].add(record["sport"])

    bucket_rows: List[dict] = []
    total_adjustment = 0
    total_adjusted = 0
    for label in sorted(buckets.keys(), key=lambda item: int(item.split("-")[0])):
        bucket = buckets[label]
        count = bucket["count"]
        avg_adjustment = round(bucket["avg_adjustment"] / count, 2) if count else 0.0
        bucket_rows.append(
            {
                "bucket": label,
                "count": count,
                "avg_confidence": round(bucket["avg_confidence"] / count, 2) if count else 0.0,
                "avg_raw_confidence": round(bucket["avg_raw_confidence"] / count, 2) if count else 0.0,
                "avg_adjustment": avg_adjustment,
                "settled_count": bucket["settled_count"],
                "win_rate": round((bucket["win_count"] / bucket["settled_count"]) * 100, 2) if bucket["settled_count"] else None,
                "sports": sorted(bucket["sports"]),
            }
        )
        total_adjustment += bucket["avg_adjustment"]
        total_adjusted += sum(1 for _ in range(count) if avg_adjustment != 0)

    return {
        "window_size": len(records),
        "bucket_count": len(bucket_rows),
        "buckets": bucket_rows,
        "summary": {
            "evaluations_analyzed": len(records),
            "adjusted_evaluations": sum(1 for record in records if int((record.get("meta") or {}).get("calibration_adjustment", 0) or 0) != 0),
            "settled_evaluations": sum(1 for record in records if record.get("final_result") in {"win", "loss"}),
            "avg_adjustment": round(
                sum(int((record.get("meta") or {}).get("calibration_adjustment", 0) or 0) for record in records) / len(records),
                2,
            )
            if records
            else 0.0,
        },
    }
