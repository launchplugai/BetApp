from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from app.db import get_engine, reset_engine, session_scope
from app.models import Base, Bet
from app.services.evaluation_logger import log_evaluation_event
from app.services.outcome_resolver import enrich_evaluation_log_outcomes
from app.services.calibration_analyzer import get_calibration_report


def _log_eval(eval_id: str, input_text: str, confidence: int, bucket: str):
    normalized = SimpleNamespace(
        tier=SimpleNamespace(value="better"),
        input_text=input_text,
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
                "raw_confidence": confidence + 4,
                "calibration_adjustment": -4,
            },
            "calibration": {
                "bucket": bucket,
                "adjustment": -4,
            },
            "recommendation": "proceed_with_caution",
            "explanation": {},
        },
        triggered_protocols=[{"id": "pace_mismatch_v1"}],
        entities={"sport_guess": "nba", "markets_detected": ["moneyline", "total"]},
        primary_failure={"reason": "pace_mismatch"},
    )


def test_outcome_resolver_enriches_logs_and_calibration_report_tracks_win_rate(tmp_path, monkeypatch):
    db_path = tmp_path / "outcomes.sqlite"
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{db_path}")
    reset_engine()
    Base.metadata.create_all(bind=get_engine())

    _log_eval("out_eval_001", "Knicks ML + under 224.5", 67, "65-69")
    with session_scope() as session:
        session.add(
            Bet(
                id="bet_resolved_001",
                user_id="user_test",
                input_text="Knicks ML + under 224.5",
                status="won",
                wager=1000,
                actual_payout=1900,
                created_at=datetime.now(UTC),
                settled_at=datetime.now(UTC),
            )
        )

    enrich_result = enrich_evaluation_log_outcomes(limit=20)
    assert enrich_result["matched_bets"] == 1
    assert enrich_result["updated_logs"] == 1

    report = get_calibration_report(limit=20)
    assert report["summary"]["settled_evaluations"] == 1
    assert report["buckets"][0]["settled_count"] == 1
    assert report["buckets"][0]["win_rate"] == 100.0


def test_outcome_resolver_matches_reordered_slip_signature(tmp_path, monkeypatch):
    db_path = tmp_path / "outcomes_signature.sqlite"
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{db_path}")
    reset_engine()
    Base.metadata.create_all(bind=get_engine())

    _log_eval("out_eval_002", "Lakers ML + Celtics -5.5", 68, "65-69")
    with session_scope() as session:
        session.add(
            Bet(
                id="bet_resolved_002",
                user_id="user_test",
                input_text="celtics -5.5, lakers ml",
                legs=[
                    {"entity": "Celtics", "market": "spread", "value": "-5.5", "selection": "Celtics -5.5"},
                    {"entity": "Lakers", "market": "moneyline", "value": "", "selection": "Lakers ML"},
                ],
                status="lost",
                wager=1000,
                actual_payout=0,
                created_at=datetime.now(UTC),
                settled_at=datetime.now(UTC),
            )
        )

    enrich_result = enrich_evaluation_log_outcomes(limit=20)
    assert enrich_result["matched_bets"] == 1
    assert enrich_result["updated_logs"] == 1

    report = get_calibration_report(limit=20)
    assert report["summary"]["settled_evaluations"] == 1
    assert report["buckets"][0]["win_rate"] == 0.0


def test_outcome_resolver_prefers_explicit_evaluation_id_link(tmp_path, monkeypatch):
    db_path = tmp_path / "outcomes_explicit.sqlite"
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{db_path}")
    reset_engine()
    Base.metadata.create_all(bind=get_engine())

    _log_eval("out_eval_003", "Original slip text", 72, "70-74")
    with session_scope() as session:
        session.add(
            Bet(
                id="bet_resolved_003",
                user_id="user_test",
                evaluation_id="out_eval_003",
                input_text="completely different saved bet text",
                legs=[],
                status="won",
                wager=1000,
                actual_payout=2100,
                created_at=datetime.now(UTC),
                settled_at=datetime.now(UTC),
            )
        )

    enrich_result = enrich_evaluation_log_outcomes(limit=20)
    assert enrich_result["matched_bets"] == 1
    assert enrich_result["updated_logs"] == 1

    report = get_calibration_report(limit=20)
    assert report["summary"]["settled_evaluations"] == 1
    assert report["buckets"][0]["win_rate"] == 100.0
