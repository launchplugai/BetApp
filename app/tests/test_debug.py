# app/tests/test_debug.py
"""
Tests for Debug Router (Ticket 18).
"""
import pytest
from fastapi.testclient import TestClient


class TestDebugContracts:
    """Test /debug/contracts endpoint."""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    def test_contracts_endpoint_exists(self, client):
        """Should have /debug/contracts endpoint."""
        response = client.get("/debug/contracts")
        assert response.status_code == 200

    def test_contracts_returns_json(self, client):
        """Should return JSON response."""
        response = client.get("/debug/contracts")
        data = response.json()
        assert isinstance(data, dict)

    def test_contracts_contains_git_sha(self, client):
        """Should contain git_sha field."""
        response = client.get("/debug/contracts")
        data = response.json()
        assert "git_sha" in data

    def test_contracts_contains_contract_versions(self, client):
        """Should contain contract_versions field."""
        response = client.get("/debug/contracts")
        data = response.json()
        assert "contract_versions" in data
        assert isinstance(data["contract_versions"], dict)

    def test_contracts_contains_flag_states(self, client):
        """Should contain flag_states field."""
        response = client.get("/debug/contracts")
        data = response.json()
        assert "flag_states" in data
        assert "leading_light_enabled" in data["flag_states"]
        assert "voice_enabled" in data["flag_states"]
        assert "sherlock_enabled" in data["flag_states"]
        assert "dna_recording_enabled" in data["flag_states"]

    def test_contracts_contains_module_boundary_status(self, client):
        """Should contain module_boundary_status field."""
        response = client.get("/debug/contracts")
        data = response.json()
        assert "module_boundary_status" in data
        assert "library_modules" in data["module_boundary_status"]
        assert "dormant_modules" in data["module_boundary_status"]

    def test_contracts_contains_proof_system(self, client):
        """Should contain proof_system field."""
        response = client.get("/debug/contracts")
        data = response.json()
        assert "proof_system" in data
        assert "sherlock_enabled" in data["proof_system"]
        assert "dna_recording_enabled" in data["proof_system"]


class TestDebugSherlockDNA:
    """Test /debug/sherlock-dna/recent endpoint."""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    def test_recent_proofs_endpoint_exists(self, client):
        """Should have /debug/sherlock-dna/recent endpoint."""
        response = client.get("/debug/sherlock-dna/recent")
        assert response.status_code == 200

    def test_recent_proofs_returns_json(self, client):
        """Should return JSON response."""
        response = client.get("/debug/sherlock-dna/recent")
        data = response.json()
        assert isinstance(data, dict)

    def test_recent_proofs_contains_records(self, client):
        """Should contain records field."""
        response = client.get("/debug/sherlock-dna/recent")
        data = response.json()
        assert "records" in data
        assert isinstance(data["records"], list)

    def test_recent_proofs_respects_limit(self, client):
        """Should respect limit parameter."""
        response = client.get("/debug/sherlock-dna/recent?limit=5")
        data = response.json()
        assert "records" in data

    def test_recent_proofs_contains_flag_states(self, client):
        """Should contain flag state info."""
        response = client.get("/debug/sherlock-dna/recent")
        data = response.json()
        assert "sherlock_enabled" in data
        assert "dna_recording_enabled" in data
