"""Auth API regression tests."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import User
from app.services.auth import get_password_hash, verify_password


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create mock user for auth tests."""
    return User(
        id="user_auth123",
        email="auth@example.com",
        password_hash="hashed_password",
        name="Auth User",
        tier="GOOD",
    )


class TestLogoutRegression:
    """Regression coverage for logout token invalidation behavior."""

    @patch("app.routers.auth.revoke_refresh_token")
    @patch("app.routers.auth.get_user_from_refresh_token")
    @patch("app.routers.auth.get_current_user_from_token")
    def test_logout_revokes_refresh_token_when_access_token_invalid(
        self,
        mock_get_current_user,
        mock_get_user_from_refresh,
        mock_revoke_refresh_token,
        client,
        mock_user,
    ):
        """Refresh token should still be revoked when access token is expired."""
        mock_get_current_user.return_value = None
        mock_get_user_from_refresh.return_value = mock_user
        mock_revoke_refresh_token.return_value = True

        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer expired_token"},
            json={"refresh_token": "refresh_123"},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        mock_revoke_refresh_token.assert_called_once_with("refresh_123")

    @patch("app.routers.auth.blacklist_access_token")
    @patch("app.routers.auth.revoke_refresh_token")
    @patch("app.routers.auth.revoke_all_user_refresh_tokens")
    @patch("app.routers.auth.get_user_from_refresh_token")
    @patch("app.routers.auth.get_current_user_from_token")
    def test_logout_all_uses_refresh_token_identity_when_access_token_invalid(
        self,
        mock_get_current_user,
        mock_get_user_from_refresh,
        mock_revoke_all,
        mock_revoke_refresh_token,
        mock_blacklist,
        client,
        mock_user,
    ):
        """Logout-all still works when the access token is already invalid."""
        mock_get_current_user.return_value = None
        mock_get_user_from_refresh.return_value = mock_user
        mock_revoke_all.return_value = 3
        mock_revoke_refresh_token.return_value = True

        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer expired_token"},
            json={"refresh_token": "refresh_123", "logout_all": True},
        )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "3 sessions" in response.json()["message"]
        mock_revoke_refresh_token.assert_called_once_with("refresh_123")
        mock_revoke_all.assert_called_once_with(mock_user.id)
        mock_blacklist.assert_not_called()


class TestPasswordHashing:
    """Regression coverage for direct bcrypt password hashing."""

    def test_password_hash_round_trip(self):
        password = "Sup3rSecret!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert hashed.startswith("$2")
        assert verify_password(password, hashed) is True

    def test_verify_password_rejects_invalid_hash(self):
        assert verify_password("anything", "not-a-bcrypt-hash") is False
