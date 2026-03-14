"""Tests for odds router provider status and cache behavior."""

from fastapi.testclient import TestClient

from app.main import app
from app.routers.odds import _cache


client = TestClient(app)


def test_provider_status_reports_mode_and_cache():
    """Provider status returns provider mode and cache summary."""
    _cache.clear()

    response = client.get("/api/provider/status")

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] in {"mock", "oddsapi"}
    assert "odds_provider" in data
    assert "score_provider" in data
    assert "cache" in data
    assert data["cache"]["entries"] == 0


def test_odds_diagnostics_reports_cache_miss_then_hit():
    """Diagnostics should reflect cache state before and after odds fetch."""
    _cache.clear()
    game_id = "lal-gsw-2026-02-09"

    before = client.get(f"/api/odds/{game_id}/diagnostics")
    assert before.status_code == 200
    assert before.json()["cache_hit"] is False

    odds_response = client.get(f"/api/odds/{game_id}")
    assert odds_response.status_code == 200
    assert isinstance(odds_response.json(), list)

    after = client.get(f"/api/odds/{game_id}/diagnostics")
    assert after.status_code == 200
    payload = after.json()
    assert payload["cache_hit"] is True
    assert payload["cache"]["ttl_seconds"] == 30
    assert payload["provider"] == "mock"
    assert odds_response.headers["X-Data-Provider"] == "mock"
    assert odds_response.headers["X-Data-Mode"] == "mock"
    assert odds_response.headers["X-Data-Cache-Hit"] == "false"


def test_score_endpoint_caches_null_responses():
    """Score endpoint should cache null values instead of refetching immediately."""
    _cache.clear()
    game_id = "unknown-game-id"

    first = client.get(f"/api/score/{game_id}")
    assert first.status_code == 200
    assert first.json() is None
    assert first.headers["X-Data-Provider"] == "mock"
    assert first.headers["X-Data-Cache-Hit"] == "false"

    cache_meta = _cache.describe(f"score:{game_id}")
    assert cache_meta is not None
    assert cache_meta["ttl_seconds"] == 10


def test_games_endpoint_exposes_freshness_headers():
    """Games endpoint should expose provider and cache headers."""
    _cache.clear()

    first = client.get("/api/games?sport=NBA")
    assert first.status_code == 200
    assert first.headers["X-Data-Provider"] == "mock"
    assert first.headers["X-Data-Mode"] == "mock"
    assert first.headers["X-Data-Cache-Hit"] == "false"
    assert "X-Data-Stored-At" in first.headers

    second = client.get("/api/games?sport=NBA")
    assert second.status_code == 200
    assert second.headers["X-Data-Cache-Hit"] == "true"
