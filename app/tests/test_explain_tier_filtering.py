# app/tests/test_explain_tier_filtering.py
"""
Tests for explain wrapper tier filtering in /evaluate/text and /evaluate/image endpoints.

Verifies that:
- GOOD plan returns empty explain dict
- BETTER plan returns summary only
- BEST plan returns full explain (summary + alerts + recommended_next_step)
- evaluation.metrics and evaluation.recommendation are ALWAYS present
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# =============================================================================
# /evaluate/text endpoint tier filtering
# =============================================================================


def test_evaluate_text_good_plan_explain_filtering():
    """GOOD plan should return empty explain dict."""
    response = client.post(
        "/leading-light/evaluate/text",
        json={
            "bet_text": "Chiefs -3.5",
            "plan": "good",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify explain is empty
    assert "explain" in data
    assert data["explain"] == {}

    # Verify interpretation still present
    assert "interpretation" in data
    assert "fragility" in data["interpretation"]

    # Verify evaluation metrics still present
    assert "evaluation" in data
    assert "metrics" in data["evaluation"]
    assert "final_fragility" in data["evaluation"]["metrics"]
    assert "recommendation" in data["evaluation"]


def test_evaluate_text_free_plan_maps_to_good():
    """FREE plan should map to GOOD and return empty explain."""
    response = client.post(
        "/leading-light/evaluate/text",
        json={
            "bet_text": "Chiefs -3.5",
            "plan": "free",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify explain is empty (free -> good)
    assert data["explain"] == {}


def test_evaluate_text_better_plan_explain_filtering():
    """BETTER plan should return summary only."""
    response = client.post(
        "/leading-light/evaluate/text",
        json={
            "bet_text": "Chiefs -3.5 + Lakers ML",
            "plan": "better",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify explain contains summary only
    assert "explain" in data
    assert "summary" in data["explain"]
    assert isinstance(data["explain"]["summary"], list)

    # Verify alerts and recommended_next_step are NOT present
    assert "alerts" not in data["explain"]
    assert "recommended_next_step" not in data["explain"]

    # Verify evaluation metrics still present
    assert "evaluation" in data
    assert "metrics" in data["evaluation"]
    assert "recommendation" in data["evaluation"]


def test_evaluate_text_best_plan_explain_filtering():
    """BEST plan should return full explain wrapper."""
    response = client.post(
        "/leading-light/evaluate/text",
        json={
            "bet_text": "Chiefs -3.5 + Lakers ML + Over 220.5",
            "plan": "best",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify explain contains all fields
    assert "explain" in data
    assert "summary" in data["explain"]
    assert "alerts" in data["explain"]
    assert "recommended_next_step" in data["explain"]

    # Verify data types
    assert isinstance(data["explain"]["summary"], list)
    assert isinstance(data["explain"]["alerts"], list)
    assert isinstance(data["explain"]["recommended_next_step"], str)

    # Verify evaluation metrics still present
    assert "evaluation" in data
    assert "metrics" in data["evaluation"]
    assert "recommendation" in data["evaluation"]


# =============================================================================
# /evaluate/image endpoint tier filtering (using mock image)
# =============================================================================


@pytest.fixture
def mock_image_bytes():
    """Create a minimal mock image file for testing."""
    # 1x1 PNG image (smallest valid PNG)
    return (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )


def test_evaluate_image_good_plan_explain_filtering(mock_image_bytes, monkeypatch):
    """GOOD plan should return empty explain dict for image endpoint."""
    # Mock the vision API call
    async def mock_parse_image(image_bytes):
        return "Chiefs -3.5"

    from app.routers import leading_light
    monkeypatch.setattr(leading_light, "_parse_bet_slip_image", mock_parse_image)

    response = client.post(
        "/leading-light/evaluate/image",
        files={"image": ("test.png", mock_image_bytes, "image/png")},
        data={"plan": "good"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify explain is empty
    assert "explain" in data
    assert data["explain"] == {}

    # Verify interpretation still present
    assert "interpretation" in data
    assert "fragility" in data["interpretation"]

    # Verify evaluation metrics still present
    assert "evaluation" in data
    assert "metrics" in data["evaluation"]


def test_evaluate_image_better_plan_explain_filtering(mock_image_bytes, monkeypatch):
    """BETTER plan should return summary only for image endpoint."""
    # Mock the vision API call
    async def mock_parse_image(image_bytes):
        return "Chiefs -3.5 + Lakers ML"

    from app.routers import leading_light
    monkeypatch.setattr(leading_light, "_parse_bet_slip_image", mock_parse_image)

    response = client.post(
        "/leading-light/evaluate/image",
        files={"image": ("test.png", mock_image_bytes, "image/png")},
        data={"plan": "better"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify explain contains summary only
    assert "explain" in data
    assert "summary" in data["explain"]
    assert "alerts" not in data["explain"]
    assert "recommended_next_step" not in data["explain"]


def test_evaluate_image_best_plan_explain_filtering(mock_image_bytes, monkeypatch):
    """BEST plan should return full explain wrapper for image endpoint."""
    # Mock the vision API call
    async def mock_parse_image(image_bytes):
        return "Chiefs -3.5 + Lakers ML + Over 220.5"

    from app.routers import leading_light
    monkeypatch.setattr(leading_light, "_parse_bet_slip_image", mock_parse_image)

    response = client.post(
        "/leading-light/evaluate/image",
        files={"image": ("test.png", mock_image_bytes, "image/png")},
        data={"plan": "best"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify explain contains all fields
    assert "explain" in data
    assert "summary" in data["explain"]
    assert "alerts" in data["explain"]
    assert "recommended_next_step" in data["explain"]
