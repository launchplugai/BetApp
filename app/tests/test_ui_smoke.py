import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.mark.parametrize("screen", ["dashboard", "protocol"])
def test_ui_smoke(screen):
    response = client.get(f"/app?screen={screen}")
    assert response.status_code == 200
    assert "<h1>Screen not found</h1>" not in response.text