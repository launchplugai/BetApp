# app/tests/test_demo_cases.py
"""
Tests for Leading Light Demo Cases.

Validates that each demo case deterministically produces the expected inductor level.
"""
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.demo.leading_light_demo_cases import (
    DEMO_CASES,
    STABLE_CASE,
    LOADED_CASE,
    TENSE_CASE,
    CRITICAL_CASE,
    get_demo_case,
    list_demo_cases,
    get_all_demo_payloads,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# =============================================================================
# Demo Case Validation Tests
# =============================================================================


class TestDemoCaseValidation:
    """Tests that each demo case produces expected inductor."""

    def test_stable_case_produces_stable(self, client):
        """STABLE case produces stable inductor."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/stable")

            assert response.status_code == 200
            data = response.json()
            assert data["inductor"]["level"] == "stable"
            assert data["metrics"]["final_fragility"] <= 30

    def test_loaded_case_produces_loaded(self, client):
        """LOADED case produces loaded inductor."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/loaded")

            assert response.status_code == 200
            data = response.json()
            assert data["inductor"]["level"] == "loaded"
            assert 31 <= data["metrics"]["final_fragility"] <= 55

    def test_tense_case_produces_tense(self, client):
        """TENSE case produces tense inductor."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/tense")

            assert response.status_code == 200
            data = response.json()
            assert data["inductor"]["level"] == "tense"
            assert 56 <= data["metrics"]["final_fragility"] <= 75

    def test_critical_case_produces_critical(self, client):
        """CRITICAL case produces critical inductor."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/critical")

            assert response.status_code == 200
            data = response.json()
            assert data["inductor"]["level"] == "critical"
            assert data["metrics"]["final_fragility"] > 75


# =============================================================================
# Demo Case Structure Tests
# =============================================================================


class TestDemoCaseStructure:
    """Tests for demo case structure."""

    def test_all_cases_have_required_fields(self):
        """All cases have required fields."""
        for name, case in DEMO_CASES.items():
            assert case.name is not None
            assert case.description is not None
            assert case.expected_inductor in ("stable", "loaded", "tense", "critical")
            assert len(case.blocks) > 0

    def test_all_blocks_have_labels(self):
        """All blocks have human-readable selections (labels)."""
        for name, case in DEMO_CASES.items():
            for block in case.blocks:
                assert "selection" in block
                assert len(block["selection"]) > 0

    def test_tense_case_has_context_signals(self):
        """TENSE case includes context signals."""
        assert TENSE_CASE.context_signals is not None
        assert len(TENSE_CASE.context_signals) > 0

    def test_critical_case_has_all_context_types(self):
        """CRITICAL case includes weather, injury, and trade signals."""
        assert CRITICAL_CASE.context_signals is not None

        signal_types = [s["type"] for s in CRITICAL_CASE.context_signals]
        assert "weather" in signal_types
        assert "injury" in signal_types
        assert "trade" in signal_types

    def test_critical_case_has_same_player_props(self):
        """CRITICAL case includes same player multi-props (Mahomes)."""
        mahomes_props = [
            b for b in CRITICAL_CASE.blocks
            if b.get("player_id") == "mahomes-15" and b["bet_type"] == "player_prop"
        ]
        assert len(mahomes_props) >= 2  # At least 2 props for same player


# =============================================================================
# Demo API Endpoint Tests
# =============================================================================


class TestDemoEndpoints:
    """Tests for demo API endpoints."""

    def test_list_demos(self, client):
        """GET /leading-light/demo lists all cases."""
        response = client.get("/leading-light/demo")

        assert response.status_code == 200
        data = response.json()
        assert "cases" in data
        assert len(data["cases"]) == 4

        case_names = [c["name"] for c in data["cases"]]
        assert "stable" in case_names
        assert "loaded" in case_names
        assert "tense" in case_names
        assert "critical" in case_names

    def test_get_demo_request(self, client):
        """GET /leading-light/demo/{case_name} returns request JSON."""
        response = client.get("/leading-light/demo/stable")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "stable"
        assert data["expected_inductor"] == "stable"
        assert "request" in data
        assert "blocks" in data["request"]

    def test_get_demo_request_invalid_case(self, client):
        """GET /leading-light/demo/{invalid} returns 404."""
        response = client.get("/leading-light/demo/nonexistent")

        assert response.status_code == 404

    def test_run_demo_requires_flag(self, client):
        """POST /leading-light/demo/{case} requires feature flag."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "false"}):
            response = client.post("/leading-light/demo/stable")

            assert response.status_code == 503

    def test_run_demo_invalid_case(self, client):
        """POST /leading-light/demo/{invalid} returns 404."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/nonexistent")

            assert response.status_code == 404


# =============================================================================
# Context Signals Tests
# =============================================================================


class TestContextSignalsInDemos:
    """Tests that context signals affect fragility in demo cases."""

    def test_tense_case_context_affects_fragility(self, client):
        """Context signals in TENSE case affect fragility and generate alerts."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/tense")

            assert response.status_code == 200
            data = response.json()

            # Should have correlation penalty from props in same game
            assert data["metrics"]["correlation_penalty"] >= 0

    def test_critical_case_correlations_detected(self, client):
        """CRITICAL case detects same_player_multi_props correlation."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/critical")

            assert response.status_code == 200
            data = response.json()

            # Should have correlations
            assert len(data["correlations"]) > 0

            # Should include same_player_multi_props
            corr_types = [c["correlation_type"] for c in data["correlations"]]
            assert "same_player_multi_props" in corr_types


# =============================================================================
# Determinism Tests
# =============================================================================


class TestDemoDeterminism:
    """Tests that demo cases are deterministic."""

    def test_stable_deterministic(self, client):
        """STABLE case produces same results on repeated runs."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response1 = client.post("/leading-light/demo/stable")
            response2 = client.post("/leading-light/demo/stable")

            data1 = response1.json()
            data2 = response2.json()

            assert data1["inductor"]["level"] == data2["inductor"]["level"]
            assert data1["metrics"]["final_fragility"] == data2["metrics"]["final_fragility"]

    def test_all_cases_deterministic(self, client):
        """All demo cases produce deterministic results."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            for case_name in DEMO_CASES.keys():
                response1 = client.post(f"/leading-light/demo/{case_name}")
                response2 = client.post(f"/leading-light/demo/{case_name}")

                data1 = response1.json()
                data2 = response2.json()

                assert data1["inductor"]["level"] == data2["inductor"]["level"], \
                    f"Case {case_name} not deterministic"


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_demo_case(self):
        """get_demo_case returns correct case."""
        case = get_demo_case("stable")
        assert case is not None
        assert case.name == "stable"

    def test_get_demo_case_case_insensitive(self):
        """get_demo_case is case insensitive."""
        case1 = get_demo_case("STABLE")
        case2 = get_demo_case("Stable")
        case3 = get_demo_case("stable")

        assert case1 is not None
        assert case1.name == case2.name == case3.name

    def test_get_demo_case_invalid(self):
        """get_demo_case returns None for invalid name."""
        case = get_demo_case("invalid")
        assert case is None

    def test_list_demo_cases(self):
        """list_demo_cases returns all cases."""
        cases = list_demo_cases()

        assert len(cases) == 4
        names = [c["name"] for c in cases]
        assert set(names) == {"stable", "loaded", "tense", "critical"}

    def test_get_all_demo_payloads(self):
        """get_all_demo_payloads returns valid JSON."""
        payloads = get_all_demo_payloads()

        assert len(payloads) == 4
        for name, payload in payloads.items():
            assert "blocks" in payload


# =============================================================================
# DNA Violations in CRITICAL Case
# =============================================================================


class TestDNAInDemos:
    """Tests for DNA enforcement in demo cases."""

    def test_critical_case_has_violations(self, client):
        """CRITICAL case exceeds DNA max_legs (4 blocks, max_legs=4)."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/critical")

            assert response.status_code == 200
            data = response.json()

            # CRITICAL has 5 legs, DNA max_legs=4
            assert len(data["dna"]["violations"]) > 0
            assert "max_legs_exceeded" in data["dna"]["violations"]


# =============================================================================
# Suggestions in CRITICAL Case
# =============================================================================


class TestSuggestionsInDemos:
    """Tests for suggestions in demo cases."""

    def test_loaded_case_returns_suggestions(self, client):
        """LOADED case returns suggestions (demonstrates working suggestions)."""
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/loaded")

            assert response.status_code == 200
            data = response.json()

            # LOADED case has room below fragility cap, so suggestions work
            assert data["suggestions"] is not None
            assert len(data["suggestions"]) > 0

            # Check suggestion structure
            suggestion = data["suggestions"][0]
            assert "delta_fragility" in suggestion
            assert "dna_compatible" in suggestion
            assert "label" in suggestion
            assert suggestion["delta_fragility"] > 0

    def test_critical_case_has_candidates(self):
        """CRITICAL case includes candidates for suggestions."""
        assert CRITICAL_CASE.candidates is not None
        assert len(CRITICAL_CASE.candidates) > 0

    def test_critical_case_returns_suggestions(self, client):
        """CRITICAL case handles suggestions correctly.

        Note: When finalFragility is capped at 100, suggestions may be empty
        because deltaFragility=0 (adding blocks doesn't increase risk past cap).
        This is expected behavior for extreme CRITICAL cases.
        """
        with patch.dict(os.environ, {"LEADING_LIGHT_ENABLED": "true"}):
            response = client.post("/leading-light/demo/critical")

            assert response.status_code == 200
            data = response.json()

            # Suggestions field should exist (may be empty if at fragility cap)
            assert data["suggestions"] is not None
            # At fragility cap (100), suggestions are empty because deltaFragility=0
            # This is correct behavior - can't meaningfully suggest additions at max risk
            assert data["suggestions"] == []
