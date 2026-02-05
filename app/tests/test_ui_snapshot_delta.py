# app/tests/test_ui_snapshot_delta.py
"""
Tests for Ticket 38B-C1: UI Wiring for Snapshot + Delta

Verifies:
1. Structural snapshot panel is present in HTML
2. Delta sentence is displayed when has_delta is true
3. Delta sentence is hidden when has_delta is false (first evaluation)
4. Snapshot data is properly rendered

Design:
- Tests API responses to verify structure and delta fields
- Tests HTML rendering of new UI elements
- Minimal layout testing (no CSS/design verification)
"""
import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with Leading Light enabled."""
    os.environ["LEADING_LIGHT_ENABLED"] = "true"
    from app.main import app
    return TestClient(app)


# =============================================================================
# Tests: Structural Snapshot in HTML
# =============================================================================


class TestSnapshotPanelHTML:
    """Tests for structural snapshot panel presence in HTML."""

    def test_snapshot_panel_present_in_html(self, client):
        """App page contains snapshot panel element."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert 'id="snapshot-panel"' in html
        assert 'id="snapshot-content"' in html
        assert 'Structural Snapshot' in html

    def test_snapshot_panel_is_details_element(self, client):
        """Snapshot panel is a <details> element (collapsed by default)."""
        response = client.get("/app")
        html = response.text
        # Verify it's a details element
        assert '<details class="snapshot-panel"' in html


class TestDeltaSentenceHTML:
    """Tests for delta sentence element presence in HTML."""

    def test_delta_sentence_element_present(self, client):
        """App page contains delta sentence element."""
        response = client.get("/app")
        assert response.status_code == 200
        html = response.text
        assert 'id="delta-sentence"' in html

    def test_delta_sentence_has_hidden_class_initially(self, client):
        """Delta sentence element starts hidden (JS reveals it when needed)."""
        response = client.get("/app")
        html = response.text
        # Should contain the element with hidden class
        assert 'class="delta-sentence hidden"' in html


# =============================================================================
# Tests: API Response Structure
# =============================================================================


class TestSnapshotDeltaAPIResponse:
    """Tests for snapshot and delta fields in evaluation API response."""

    def test_evaluation_includes_structure_field(self, client):
        """Evaluation response includes structure snapshot."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure field exists
        assert "structure" in data
        structure = data["structure"]
        
        # Verify structure contract fields
        assert "leg_count" in structure
        assert "leg_ids" in structure
        assert "leg_types" in structure
        assert "props" in structure
        assert "totals" in structure
        assert "correlation_flags" in structure
        assert "volatility_sources" in structure
        
        # Verify values are reasonable
        assert structure["leg_count"] >= 1
        assert isinstance(structure["leg_ids"], list)
        assert isinstance(structure["leg_types"], list)
        assert isinstance(structure["props"], int)
        assert isinstance(structure["totals"], int)

    def test_first_evaluation_has_no_delta(self, client):
        """First evaluation has delta but with has_delta=False."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        
        # Verify delta field exists
        assert "delta" in data
        delta = data["delta"]
        
        # First evaluation should have no delta
        assert "has_delta" in delta
        assert delta["has_delta"] is False
        assert delta.get("delta_sentence") is None
        assert "changes_detected" in delta
        assert delta["changes_detected"] == []

    def test_structure_contract_leg_types(self, client):
        """Structure snapshot leg_types matches expected bet types."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML + Celtics -5.5",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        structure = data["structure"]
        
        # Should have 2 legs
        assert structure["leg_count"] == 2
        
        # Should have spread and ml types
        assert "spread" in structure["leg_types"]
        assert "ml" in structure["leg_types"]


# =============================================================================
# Tests: UI Rendering Logic (Client-Side)
# =============================================================================


class TestSnapshotRenderingContract:
    """Tests for snapshot rendering requirements."""

    def test_snapshot_includes_all_required_fields(self, client):
        """Snapshot API response includes all fields needed for UI rendering."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5 + Celtics ML + Over 220.5",
            "tier": "best"
        })
        assert response.status_code == 200
        data = response.json()
        structure = data["structure"]
        
        # Fields required for UI display (per Ticket 38B-C1)
        required_fields = [
            "leg_count",
            "leg_ids",
            "leg_types",
            "props",
            "totals",
            "correlation_flags",
            "volatility_sources"
        ]
        
        for field in required_fields:
            assert field in structure, f"Missing required field: {field}"

    def test_delta_sentence_rendering_contract(self, client):
        """Delta API response includes all fields needed for UI rendering."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers -5.5",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        delta = data["delta"]
        
        # Fields required for UI display (per Ticket 38B-C1)
        assert "has_delta" in delta
        assert "delta_sentence" in delta or delta["has_delta"] is False
        assert "changes_detected" in delta
        
        # When has_delta is False, delta_sentence should be None
        if not delta["has_delta"]:
            assert delta["delta_sentence"] is None


# =============================================================================
# Tests: Snapshot Content Structure
# =============================================================================


class TestSnapshotContentValues:
    """Tests for snapshot content value correctness."""

    def test_snapshot_counts_props_correctly(self, client):
        """Snapshot correctly identifies player props."""
        response = client.post("/app/evaluate", json={
            "input": "LeBron O27.5 pts + AD O10 reb + Lakers ML",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        structure = data["structure"]
        
        # Should have 3 legs total
        assert structure["leg_count"] == 3
        
        # Should have 2 props (LeBron pts + AD reb)
        assert structure["props"] == 2

    def test_snapshot_counts_totals_correctly(self, client):
        """Snapshot correctly identifies totals."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers vs Celtics O220.5 + Nuggets vs Heat U210",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        structure = data["structure"]
        
        # Should have 2 totals
        assert structure["totals"] == 2

    def test_snapshot_detects_same_game_correlation(self, client):
        """Snapshot detects same_game correlation flag."""
        response = client.post("/app/evaluate", json={
            "input": "Lakers ML + LeBron O27.5 pts",
            "tier": "good"
        })
        assert response.status_code == 200
        data = response.json()
        structure = data["structure"]
        
        # Should have same_game correlation (Lakers + LeBron same game)
        assert "same_game" in structure["correlation_flags"]
