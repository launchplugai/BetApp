import pytest
from fastapi.testclient import TestClient
from app.models import init_db
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def _ensure_tables():
    """Create database tables before tests run."""
    init_db()


def test_create_protocol_no_auth():
    """Protocol creation works without auth token."""
    resp = client.post("/api/protocols", json={
        "sport": "nba",
        "title": "Test Protocol",
        "context": {},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["sport"] == "nba"
    assert data["title"] == "Test Protocol"
    assert "id" in data


def test_list_protocols_no_auth():
    """Protocol listing works without auth token."""
    resp = client.get("/api/protocols")
    assert resp.status_code == 200
    data = resp.json()
    assert "protocols" in data
    assert isinstance(data["protocols"], list)
