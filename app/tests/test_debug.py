# app/tests/test_debug.py
"""
Tests for Debug Router (Ticket 18).
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models import User


@pytest.fixture
def best_user():
    return User(
        id="user_debug_best",
        email="debug-best@example.com",
        password_hash="hashed_password",
        name="Debug Best",
        tier="BEST",
    )


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer valid_token"}


class TestDebugContracts:
    """Test /debug/contracts endpoint."""

    @pytest.fixture
    def client(self):
        from app.main import app
        return TestClient(app)

    def test_contracts_requires_auth(self, client):
        """Debug contracts should require auth."""
        response = client.get("/debug/contracts")
        assert response.status_code == 401

    @patch("app.services.auth.get_current_user_from_token")
    def test_contracts_endpoint_exists(self, mock_get_current_user, client, best_user, auth_headers):
        """Should have /debug/contracts endpoint for internal users."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/contracts", headers=auth_headers)
        assert response.status_code == 200

    @patch("app.services.auth.get_current_user_from_token")
    def test_contracts_returns_json(self, mock_get_current_user, client, best_user, auth_headers):
        """Should return JSON response."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/contracts", headers=auth_headers)
        data = response.json()
        assert isinstance(data, dict)

    @patch("app.services.auth.get_current_user_from_token")
    def test_contracts_contains_git_sha(self, mock_get_current_user, client, best_user, auth_headers):
        """Should contain git_sha field in build object."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/contracts", headers=auth_headers)
        data = response.json()
        # API schema updated: git_sha is now nested in build object
        assert "build" in data, "Response should contain build object"
        assert "git_sha" in data["build"], "build object should contain git_sha"

    @patch("app.services.auth.get_current_user_from_token")
    def test_contracts_contains_contract_versions(self, mock_get_current_user, client, best_user, auth_headers):
        """Should contain contracts field (was contract_versions)."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/contracts", headers=auth_headers)
        data = response.json()
        # API schema updated: renamed from contract_versions to contracts
        assert "contracts" in data
        assert isinstance(data["contracts"], dict)

    @patch("app.services.auth.get_current_user_from_token")
    def test_contracts_contains_flag_states(self, mock_get_current_user, client, best_user, auth_headers):
        """Should contain flags field (was flag_states)."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/contracts", headers=auth_headers)
        data = response.json()
        # API schema updated: renamed from flag_states to flags
        assert "flags" in data
        assert "leading_light_enabled" in data["flags"]
        assert "voice_enabled" in data["flags"]
        assert "sherlock_enabled" in data["flags"]
        assert "dna_recording_enabled" in data["flags"]

    @pytest.mark.xfail(reason="Feature removed from API: module_boundary_status no longer exposed")
    @patch("app.services.auth.get_current_user_from_token")
    def test_contracts_contains_module_boundary_status(self, mock_get_current_user, client, best_user, auth_headers):
        """Should contain module_boundary_status field."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/contracts", headers=auth_headers)
        data = response.json()
        assert "module_boundary_status" in data
        assert "library_modules" in data["module_boundary_status"]
        assert "dormant_modules" in data["module_boundary_status"]

    @pytest.mark.xfail(reason="Feature removed from API: proof_system no longer exposed")
    @patch("app.services.auth.get_current_user_from_token")
    def test_contracts_contains_proof_system(self, mock_get_current_user, client, best_user, auth_headers):
        """Should contain proof_system field."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/contracts", headers=auth_headers)
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

    def test_recent_proofs_requires_auth(self, client):
        """Debug proof records should require auth."""
        response = client.get("/debug/sherlock-dna/recent")
        assert response.status_code == 401

    @patch("app.services.auth.get_current_user_from_token")
    def test_recent_proofs_endpoint_exists(self, mock_get_current_user, client, best_user, auth_headers):
        """Should have /debug/sherlock-dna/recent endpoint."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/sherlock-dna/recent", headers=auth_headers)
        assert response.status_code == 200

    @patch("app.services.auth.get_current_user_from_token")
    def test_recent_proofs_returns_json(self, mock_get_current_user, client, best_user, auth_headers):
        """Should return JSON response."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/sherlock-dna/recent", headers=auth_headers)
        data = response.json()
        assert isinstance(data, dict)

    @patch("app.services.auth.get_current_user_from_token")
    def test_recent_proofs_contains_records(self, mock_get_current_user, client, best_user, auth_headers):
        """Should contain records field."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/sherlock-dna/recent", headers=auth_headers)
        data = response.json()
        assert "records" in data
        assert isinstance(data["records"], list)

    @patch("app.services.auth.get_current_user_from_token")
    def test_recent_proofs_respects_limit(self, mock_get_current_user, client, best_user, auth_headers):
        """Should respect limit parameter."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/sherlock-dna/recent?limit=5", headers=auth_headers)
        data = response.json()
        assert "records" in data

    @patch("app.services.auth.get_current_user_from_token")
    def test_recent_proofs_contains_flag_states(self, mock_get_current_user, client, best_user, auth_headers):
        """Should contain flag state info."""
        mock_get_current_user.return_value = best_user
        response = client.get("/debug/sherlock-dna/recent", headers=auth_headers)
        data = response.json()
        assert "sherlock_enabled" in data
        assert "dna_recording_enabled" in data
