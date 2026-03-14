from __future__ import annotations

from types import SimpleNamespace

from app.db import get_engine, reset_engine
from app.models import Base
from app.services.calibration_analyzer import get_calibration_report
from app.services.evaluation_logger import log_evaluation_event


def _seed_eval(eval_id: str, confidence: int, raw_confidence: int, adjustment: int, bucket: str):
    normalized = SimpleNamespace(
        tier=SimpleNamespace(value="better"),
        input_text="Knicks ML + under 224.5",
        has_canonical_legs=True,
    )
    evaluation = SimpleNamespace(parlay_id=eval_id)
    log_evaluation_event(
        normalized=normalized,
        evaluation=evaluation,
        leg_count=2,
        dna_scoring={
            "score_model_version": "1.2.0",
            "scores": {
                "confidence": confidence,
                "fragility": 49,
                "edge": 2,
                "stability": 71,
            },
            "components": {
                "raw_confidence": raw_confidence,
                "calibration_adjustment": adjustment,
            },
            "calibration": {
                "bucket": bucket,
                "adjustment": adjustment,
            },
            "recommendation": "proceed_with_caution",
            "explanation": {},
        },
        triggered_protocols=[{"id": "pace_mismatch_v1"}],
        entities={"sport_guess": "nba", "markets_detected": ["moneyline", "total"]},
        primary_failure={"reason": "pace_mismatch"},
    )


def test_calibration_report_groups_recent_logs_by_bucket(tmp_path, monkeypatch):
    db_path = tmp_path / "calibration.sqlite"
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{db_path}")
    reset_engine()
    Base.metadata.create_all(bind=get_engine())

    _seed_eval("cal_eval_001", confidence=67, raw_confidence=71, adjustment=-4, bucket="65-69")
    _seed_eval("cal_eval_002", confidence=68, raw_confidence=70, adjustment=-2, bucket="65-69")
    _seed_eval("cal_eval_003", confidence=74, raw_confidence=74, adjustment=0, bucket="70-74")

    report = get_calibration_report(limit=10)

    assert report["summary"]["evaluations_analyzed"] == 3
    assert report["summary"]["adjusted_evaluations"] == 2
    assert report["bucket_count"] == 2

    first_bucket = report["buckets"][0]
    assert first_bucket["bucket"] == "65-69"
    assert first_bucket["count"] == 2
    assert first_bucket["avg_adjustment"] == -3.0
    assert first_bucket["avg_raw_confidence"] == 70.5
