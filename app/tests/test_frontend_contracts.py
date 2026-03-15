import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.history_store import create_history_item, get_history_store
from app.main import app


@pytest.fixture
def client():
    os.environ["LEADING_LIGHT_ENABLED"] = "true"
    return TestClient(app)


class TestEvaluateContract:
    def test_app_evaluate_exposes_top_level_evaluation_id(self, client):
        response = client.post(
            "/app/evaluate",
            json={
                "input": "Lakers ML + Celtics ML",
                "tier": "good",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "evaluationId" in data
        assert data["evaluationId"] == data["evaluation"]["parlayId"]

    def test_app_evaluate_exposes_builder_handoff_contract(self, client):
        response = client.post(
            "/app/evaluate",
            json={
                "input": "Lakers ML + Celtics ML + Knicks ML + Suns ML + Heat ML",
                "tier": "best",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "builderHandoff" in data

        handoff = data["builderHandoff"]
        assert handoff["evaluationId"] == data["evaluationId"]
        assert handoff["inputText"] == data["input"]["betText"]
        assert handoff["tier"] == data["input"]["tier"]
        assert "primaryFailure" in handoff
        assert "deltaPreview" in handoff
        assert "signalInfo" in handoff
        assert "protocolContextNote" in handoff


class TestOcrReviewContract:
    def test_ocr_review_returns_parsed_legs_without_evaluation(self, client):
        with patch("app.routers.ocr._parse_bet_slip_image", return_value="Jalen Brunson 8+ assists\nKnicks ML"):
            response = client.post(
                "/api/ocr/review",
                files={"image": ("slip.png", b"fake-image-bytes", "image/png")},
            )

        assert response.status_code == 200
        data = response.json()

        assert data["source"] == "image"
        assert data["fileName"] == "slip.png"
        assert data["rawText"] == "Jalen Brunson 8+ assists\nKnicks ML"
        assert isinstance(data["detectedLegs"], list)
        assert len(data["detectedLegs"]) == 2
        assert "evaluation" not in data
        assert "evaluationId" not in data
        assert "requestId" in data
        assert 0.0 <= data["confidence"] <= 1.0
        assert isinstance(data["requiresReview"], bool)
        assert data["detectedLegs"][0]["legId"].startswith("leg_")
        assert data["detectedLegs"][0]["source"] == "ocr"
        assert data["detectedLegs"][0]["clarity"] in {"clear", "review", "ambiguous"}


class TestHistoryContracts:
    def test_history_list_alias_returns_frontend_safe_shape(self, client):
        store = get_history_store()
        store.clear()
        store.add(
            create_history_item(
                {
                    "signalInfo": {
                        "signal": "yellow",
                        "label": "Fixable",
                        "grade": "C",
                        "fragilityScore": 63,
                    }
                },
                "Lakers ML + Celtics ML",
            )
        )

        response = client.get("/app/history")

        assert response.status_code == 200
        data = response.json()
        assert "requestId" in data
        assert isinstance(data["items"], list)
        assert data["count"] >= 1
        assert "createdAt" in data["items"][0]
        assert "inputText" in data["items"][0]

    def test_history_detail_alias_returns_replay_payload(self, client):
        store = get_history_store()
        store.clear()
        item = create_history_item(
            {
                "evaluationId": "eval_789",
                "input": {"betText": "Lakers ML + LeBron over 25.5", "tier": "best"},
                "signalInfo": {
                    "signal": "yellow",
                    "label": "Fixable",
                    "grade": "C",
                    "fragilityScore": 63,
                },
                "builderHandoff": {
                    "evaluationId": "eval_789",
                    "inputText": "Lakers ML + LeBron over 25.5",
                    "tier": "best",
                    "protocolContextNote": "Schedule, availability, and pace context was checked before this read.",
                },
            },
            "Lakers ML + LeBron over 25.5",
        )
        store.add(item)

        response = client.get(f"/app/history/{item.id}")

        assert response.status_code == 200
        data = response.json()
        assert "requestId" in data
        assert data["item"]["id"] == item.id
        assert "replay" in data["item"]
        assert data["item"]["replay"]["evaluationId"] == "eval_789"
        assert data["item"]["replay"]["builderHandoff"]["protocolContextNote"] is not None
