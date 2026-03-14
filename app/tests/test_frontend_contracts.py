import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

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
