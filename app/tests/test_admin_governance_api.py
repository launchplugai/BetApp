from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import get_engine, reset_engine, session_scope
from app.models import Base, LearningProposal, ModelRegistryEntry, User
from app.services.evaluation_logger import log_evaluation_event


@pytest.fixture
def isolated_admin_db(tmp_path, monkeypatch):
    db_path = tmp_path / "admin-governance.sqlite"
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{db_path}")
    reset_engine()
    Base.metadata.create_all(bind=get_engine())
    try:
        yield
    finally:
        reset_engine()


@pytest.fixture
def client(isolated_admin_db):
    from app.main import app

    return TestClient(app)


@pytest.fixture
def best_user():
    return User(
        id="user_best_001",
        email="best@example.com",
        password_hash="hashed_password",
        name="Best User",
        tier="BEST",
    )


@pytest.fixture
def good_user():
    return User(
        id="user_good_001",
        email="good@example.com",
        password_hash="hashed_password",
        name="Good User",
        tier="GOOD",
    )


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer valid_token"}


def seed_evaluation_log():
    normalized = SimpleNamespace(
        tier=SimpleNamespace(value="better"),
        input_text="Knicks ML + under 224.5",
        has_canonical_legs=True,
    )
    evaluation = SimpleNamespace(parlay_id="admin_eval_001")
    dna_scoring = {
        "score_model_version": "1.2.0",
        "scores": {
            "confidence": 67,
            "fragility": 49,
            "edge": 2,
            "stability": 71,
        },
        "components": {
            "raw_confidence": 71,
            "calibration_adjustment": -4,
        },
        "calibration": {
            "bucket": "65-69",
            "adjustment": -4,
        },
        "recommendation": "proceed_with_caution",
        "explanation": {"summary": "Decent setup with moderate downside risk."},
    }

    log_evaluation_event(
        normalized=normalized,
        evaluation=evaluation,
        leg_count=2,
        dna_scoring=dna_scoring,
        triggered_protocols=[{"id": "pace_mismatch_v1"}],
        entities={"sport_guess": "nba", "markets_detected": ["moneyline", "total"]},
        primary_failure={"reason": "pace_mismatch"},
    )


def seed_proposal():
    with session_scope() as session:
        session.add(
            LearningProposal(
                id="prop_admin_001",
                proposal_type="protocol_tuning",
                status="pending_review",
                target={
                    "entityType": "protocol_library",
                    "entityId": "fatigue_b2b_v1",
                    "entityName": "Protocol Library",
                },
                current_value={"stabilityPenalty": -8},
                proposed_value={"stabilityPenalty": -10},
                reason="Observed underestimation of fatigue risk.",
                evidence={"sampleSize": 912, "holdoutImprovement": 0.04},
                allowed_range=[-12, -4],
                model_scope=["NBA"],
                review={"required": True},
            )
        )
        session.add(
            ModelRegistryEntry(
                entity_type="protocol_library",
                entity_name="Protocol Library",
                version="pl_v1.0.0",
                status="production",
                scope=["global"],
                meta={"seeded": True},
            )
        )


@patch("app.services.auth.get_current_user_from_token")
def test_admin_governance_summary_endpoint(mock_get_current_user, client, best_user, auth_headers):
    mock_get_current_user.return_value = best_user
    seed_evaluation_log()

    response = client.get("/api/admin/governance/summary", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "governance" in data
    assert "evaluation_logs" in data
    assert "learning_control" in data
    assert data["evaluation_logs"]["total_logs"] == 1


@patch("app.services.auth.get_current_user_from_token")
def test_admin_governance_evaluations_endpoint(mock_get_current_user, client, best_user, auth_headers):
    mock_get_current_user.return_value = best_user
    seed_evaluation_log()

    response = client.get("/api/admin/governance/evaluations?limit=5", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "recent_evaluations" in data
    assert len(data["recent_evaluations"]) == 1
    assert data["recent_evaluations"][0]["evaluation_id"] == "admin_eval_001"
    assert data["recent_evaluations"][0]["sport"] == "NBA"
    assert data["recent_evaluations"][0]["raw_confidence"] == 71
    assert data["recent_evaluations"][0]["calibration_adjustment"] == -4
    assert data["recent_evaluations"][0]["confidence_bucket"] == "65-69"
    assert data["calibration_summary"]["average_adjustment"] == -4.0


@patch("app.services.auth.get_current_user_from_token")
def test_admin_governance_calibration_report_endpoint(mock_get_current_user, client, best_user, auth_headers):
    mock_get_current_user.return_value = best_user
    seed_evaluation_log()

    response = client.get("/api/admin/governance/calibration-report?limit=50", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["summary"]["evaluations_analyzed"] >= 1
    assert len(data["buckets"]) >= 1


@patch("app.services.auth.get_current_user_from_token")
def test_admin_governance_outcome_enrichment_endpoint(mock_get_current_user, client, best_user, auth_headers):
    mock_get_current_user.return_value = best_user

    response = client.post("/api/admin/governance/outcomes/enrich?limit=25", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "matched_bets" in data
    assert "updated_logs" in data


@patch("app.services.auth.get_current_user_from_token")
def test_admin_governance_proposals_list_and_detail(mock_get_current_user, client, best_user, auth_headers):
    mock_get_current_user.return_value = best_user
    seed_proposal()

    list_response = client.get("/api/admin/governance/proposals?status=pending_review", headers=auth_headers)
    assert list_response.status_code == 200
    proposals = list_response.json()["proposals"]
    assert len(proposals) == 1
    assert proposals[0]["id"] == "prop_admin_001"

    detail_response = client.get("/api/admin/governance/proposals/prop_admin_001", headers=auth_headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "pending_review"


@patch("app.services.auth.get_current_user_from_token")
def test_admin_governance_version_hint(mock_get_current_user, client, best_user, auth_headers):
    mock_get_current_user.return_value = best_user
    seed_proposal()

    response = client.get(
        "/api/admin/governance/version-hint?entity_type=protocol_library",
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["entity_type"] == "protocol_library"
    assert data["current_version"] == "pl_v1.0.0"
    assert data["suggested_version"] == "pl_v1.0.1"
    assert data["rollback_version"] == "pl_v1.0.0"


@patch("app.services.auth.get_current_user_from_token")
def test_admin_governance_proposal_approval(mock_get_current_user, client, best_user, auth_headers):
    mock_get_current_user.return_value = best_user
    seed_proposal()

    response = client.post(
        "/api/admin/governance/proposals/prop_admin_001/approve",
        headers=auth_headers,
        json={
            "approved_by": "admin_user_1",
            "old_version": "pl_v1.0.0",
            "new_version": "pl_v1.0.1",
            "rollback_version": "pl_v1.0.0",
            "notes": "Approved after review.",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["proposal"]["status"] == "promoted"
    assert data["promotion"]["new_version"] == "pl_v1.0.1"
    assert data["registry_entry"]["version"] == "pl_v1.0.1"

    promotions_response = client.get("/api/admin/governance/promotions?limit=5", headers=auth_headers)
    assert promotions_response.status_code == 200
    promotions = promotions_response.json()["promotions"]
    assert len(promotions) == 1
    assert promotions[0]["proposal_id"] == "prop_admin_001"


@patch("app.services.auth.get_current_user_from_token")
def test_admin_governance_promotion_rollback(mock_get_current_user, client, best_user, auth_headers):
    mock_get_current_user.return_value = best_user
    seed_proposal()

    approve_response = client.post(
        "/api/admin/governance/proposals/prop_admin_001/approve",
        headers=auth_headers,
        json={
            "approved_by": "admin_user_1",
            "old_version": "pl_v1.0.0",
            "new_version": "pl_v1.0.1",
            "rollback_version": "pl_v1.0.0",
            "notes": "Approved after review.",
        },
    )
    assert approve_response.status_code == 200
    promotion_id = approve_response.json()["promotion"]["id"]

    rollback_response = client.post(
        f"/api/admin/governance/promotions/{promotion_id}/rollback",
        headers=auth_headers,
        json={
            "rolled_back_by": "admin_user_2",
            "notes": "Rollback after validation drift.",
        },
    )
    assert rollback_response.status_code == 200

    data = rollback_response.json()
    assert data["rollback_promotion"]["old_version"] == "pl_v1.0.1"
    assert data["rollback_promotion"]["new_version"] == "pl_v1.0.0"
    assert data["registry_entry"]["version"] == "pl_v1.0.0"

    promotions_response = client.get("/api/admin/governance/promotions?limit=5", headers=auth_headers)
    assert promotions_response.status_code == 200
    promotions = promotions_response.json()["promotions"]
    assert len(promotions) == 2


def test_admin_governance_requires_auth(client):
    response = client.get("/api/admin/governance/summary")
    assert response.status_code == 401


@patch("app.services.auth.get_current_user_from_token")
def test_admin_governance_rejects_non_admin_user(mock_get_current_user, client, good_user, auth_headers):
    mock_get_current_user.return_value = good_user

    response = client.get("/api/admin/governance/summary", headers=auth_headers)
    assert response.status_code == 403


@patch("app.services.auth.get_current_user_from_token")
def test_admin_governance_allows_allowlisted_email(mock_get_current_user, client, good_user, auth_headers, monkeypatch):
    mock_get_current_user.return_value = good_user
    monkeypatch.setenv("ADMIN_EMAILS", "good@example.com")

    response = client.get("/api/admin/governance/summary", headers=auth_headers)
    assert response.status_code == 200
