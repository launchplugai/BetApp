from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.db import get_engine, reset_engine, session_scope
from app.models import Base, LearningProposal, PromotionAuditRecord
from app.services.evaluation_logger import get_evaluation_log_summary, log_evaluation_event
from app.services.governance_registry import get_learning_control_summary
from app.services.model_registry import get_active_model_versions, get_governance_summary


@pytest.fixture
def isolated_app_db(tmp_path, monkeypatch):
    db_path = tmp_path / "governance.sqlite"
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{db_path}")
    reset_engine()
    Base.metadata.create_all(bind=get_engine())
    try:
        yield
    finally:
        reset_engine()


def test_model_registry_seeds_default_versions(isolated_app_db):
    versions = get_active_model_versions()

    assert versions == {
        "dna_model_version": "dna_v1.0.0",
        "protocol_library_version": "pl_v1.0.0",
        "calibration_version": "cal_v1.0.0",
        "recommendation_version": "rec_v1.0.0",
    }

    summary = get_governance_summary()
    assert summary["total_registry_entries"] >= 4
    assert summary["production_entries"] >= 4
    assert summary["app_database_backend"] == "sqlite"


def test_evaluation_logger_writes_once_per_evaluation(isolated_app_db):
    normalized = SimpleNamespace(
        tier=SimpleNamespace(value="better"),
        input_text="Lakers ML + over 228.5",
        has_canonical_legs=True,
    )
    evaluation = SimpleNamespace(parlay_id="eval_test_001")
    dna_scoring = {
        "score_model_version": "1.2.0",
        "scores": {
            "confidence": 74,
            "fragility": 58,
            "edge": 3,
            "stability": 69,
        },
        "components": {
            "raw_confidence": 78,
            "calibration_adjustment": -4,
        },
        "calibration": {
            "bucket": "70-74",
            "adjustment": -4,
        },
        "recommendation": "consider_simplifying",
        "explanation": {"summary": "Structurally solid but a bit fragile."},
    }
    triggered_protocols = [{"id": "fatigue_b2b_v1"}, {"id": "pace_mismatch_v1"}]
    entities = {"sport_guess": "nba", "markets_detected": ["moneyline", "total"]}

    log_evaluation_event(
        normalized=normalized,
        evaluation=evaluation,
        leg_count=2,
        dna_scoring=dna_scoring,
        triggered_protocols=triggered_protocols,
        entities=entities,
        primary_failure={"reason": "leg_count_risk"},
    )
    log_evaluation_event(
        normalized=normalized,
        evaluation=evaluation,
        leg_count=2,
        dna_scoring=dna_scoring,
        triggered_protocols=triggered_protocols,
        entities=entities,
        primary_failure={"reason": "leg_count_risk"},
    )

    summary = get_evaluation_log_summary()
    assert summary["total_logs"] == 1
    assert summary["recent_evaluations"][0]["evaluation_id"] == "eval_test_001"
    assert summary["recent_evaluations"][0]["sport"] == "NBA"
    assert summary["recent_evaluations"][0]["market_type"] == "parlay"
    assert summary["recent_evaluations"][0]["recommendation_type"] == "consider_simplifying"
    assert summary["recent_evaluations"][0]["raw_confidence"] == 78
    assert summary["recent_evaluations"][0]["calibration_adjustment"] == -4
    assert summary["recent_evaluations"][0]["confidence_bucket"] == "70-74"
    assert summary["calibration_summary"]["recent_count"] == 1
    assert summary["calibration_summary"]["recent_adjusted_count"] == 1
    assert summary["calibration_summary"]["average_adjustment"] == -4.0


def test_learning_control_summary_uses_repository_counts(isolated_app_db):
    with session_scope() as session:
        session.add(
            LearningProposal(
                id="prop_001",
                proposal_type="protocol_tuning",
                status="pending_review",
                target={"entityType": "protocol", "entityId": "fatigue_b2b_v1"},
                current_value=-8,
                proposed_value=-10,
                reason="Observed underestimation of B2B penalty.",
                evidence={"sampleSize": 500},
                allowed_range=[-12, -4],
                model_scope=["NBA"],
                review={"required": True},
            )
        )
        session.add(
            PromotionAuditRecord(
                id="prom_001",
                proposal_id="prop_001",
                approved_by="admin_user",
                old_version="pl_v1.0.0",
                new_version="pl_v1.0.1",
                rollback_version="pl_v1.0.0",
                notes="Approved after holdout validation.",
            )
        )

    summary = get_learning_control_summary()
    assert summary["proposal_counts"]["pending_review"] == 1
    assert summary["promotion_count"] == 1
    assert summary["recent_promotions"][0]["proposal_id"] == "prop_001"
