# auth/tests/test_auth.py
"""
Comprehensive tests for authentication module.

Tests:
- User model
- Session model
- Password hashing
- User service (CRUD, auth)
- Session service (create, validate, invalidate)
"""

from __future__ import annotations

import os
import pytest
from datetime import datetime, timedelta

# Set test database before imports
os.environ["DNA_DB_PATH"] = ":memory:"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_database():
    """Reset database before each test."""
    from persistence.db import reset_db, init_db, _local, _init_lock
    import persistence.db as db_module

    # Reset the initialized flag
    with _init_lock:
        db_module._initialized = False

    # Clear thread-local connection
    if hasattr(_local, "connection") and _local.connection:
        _local.connection.close()
        _local.connection = None

    # Initialize fresh
    init_db()
    yield
    reset_db()


# =============================================================================
# Model Tests
# =============================================================================


class TestUserModel:
    """Tests for User model."""

    def test_user_new_generates_id(self):
        """User.new() generates a unique ID."""
        from auth.models import User

        user = User.new(email="test@example.com", password_hash="hash123")
        assert user.id is not None
        assert len(user.id) == 36  # UUID format

    def test_user_new_normalizes_email(self):
        """User.new() normalizes email to lowercase."""
        from auth.models import User

        user = User.new(email="  TEST@Example.COM  ", password_hash="hash")
        assert user.email == "test@example.com"

    def test_user_new_default_tier(self):
        """User.new() defaults to GOOD tier."""
        from auth.models import User

        user = User.new(email="test@example.com", password_hash="hash")
        assert user.tier == "GOOD"

    def test_user_new_custom_tier(self):
        """User.new() accepts custom tier."""
        from auth.models import User

        user = User.new(email="test@example.com", password_hash="hash", tier="best")
        assert user.tier == "BEST"

    def test_user_to_dict_excludes_password(self):
        """User.to_dict() excludes password hash."""
        from auth.models import User

        user = User.new(email="test@example.com", password_hash="secret_hash")
        d = user.to_dict()

        assert "password_hash" not in d
        assert "email" in d
        assert d["email"] == "test@example.com"


class TestSessionModel:
    """Tests for Session model."""

    def test_session_new_generates_id(self):
        """Session.new() generates a unique ID."""
        from auth.models import Session

        session = Session.new(user_id="user-123")
        assert session.id is not None
        assert len(session.id) == 36  # UUID format

    def test_session_new_sets_expiry(self):
        """Session.new() sets expiry 7 days ahead by default."""
        from auth.models import Session

        session = Session.new(user_id="user-123")
        now = datetime.utcnow()

        # Should be approximately 7 days ahead (allowing for test timing)
        diff = session.expires_at - now
        assert 6 <= diff.days <= 7

    def test_session_new_custom_duration(self):
        """Session.new() accepts custom duration."""
        from auth.models import Session

        session = Session.new(user_id="user-123", duration_days=30)
        now = datetime.utcnow()

        # Should be approximately 30 days ahead (allowing for test timing)
        diff = session.expires_at - now
        assert 29 <= diff.days <= 30

    def test_session_is_valid_true_for_new(self):
        """New session is valid."""
        from auth.models import Session

        session = Session.new(user_id="user-123")
        assert session.is_valid is True

    def test_session_is_valid_false_for_expired(self):
        """Expired session is not valid."""
        from auth.models import Session

        session = Session(
            id="session-123",
            user_id="user-123",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        assert session.is_valid is False

    def test_session_stores_metadata(self):
        """Session stores IP and user agent."""
        from auth.models import Session

        session = Session.new(
            user_id="user-123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Mozilla/5.0"


# =============================================================================
# Password Tests
# =============================================================================


class TestPasswordHashing:
    """Tests for password hashing."""

    def test_hash_password_creates_hash(self):
        """hash_password creates a bcrypt hash."""
        from auth.password import hash_password

        hashed = hash_password("mypassword123")
        assert hashed is not None
        assert hashed.startswith("$2b$")  # bcrypt prefix
        assert len(hashed) == 60  # bcrypt hash length

    def test_hash_password_different_hashes(self):
        """hash_password creates different hashes for same password."""
        from auth.password import hash_password

        hash1 = hash_password("mypassword123")
        hash2 = hash_password("mypassword123")
        assert hash1 != hash2  # Different salts

    def test_hash_password_empty_raises(self):
        """hash_password raises on empty password."""
        from auth.password import hash_password

        with pytest.raises(ValueError, match="empty"):
            hash_password("")

    def test_verify_password_correct(self):
        """verify_password returns True for correct password."""
        from auth.password import hash_password, verify_password

        hashed = hash_password("correctpassword")
        assert verify_password("correctpassword", hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password returns False for wrong password."""
        from auth.password import hash_password, verify_password

        hashed = hash_password("correctpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty_returns_false(self):
        """verify_password returns False for empty inputs."""
        from auth.password import verify_password

        assert verify_password("", "somehash") is False
        assert verify_password("password", "") is False

    def test_is_password_strong_valid(self):
        """is_password_strong accepts valid passwords."""
        from auth.password import is_password_strong

        valid, _ = is_password_strong("Password1")
        assert valid is True

    def test_is_password_strong_too_short(self):
        """is_password_strong rejects short passwords."""
        from auth.password import is_password_strong

        valid, msg = is_password_strong("Pass1")
        assert valid is False
        assert "8 characters" in msg

    def test_is_password_strong_no_letter(self):
        """is_password_strong rejects passwords without letters."""
        from auth.password import is_password_strong

        valid, msg = is_password_strong("12345678")
        assert valid is False
        assert "letter" in msg

    def test_is_password_strong_no_digit(self):
        """is_password_strong rejects passwords without digits."""
        from auth.password import is_password_strong

        valid, msg = is_password_strong("PasswordOnly")
        assert valid is False
        assert "digit" in msg


# =============================================================================
# User Service Tests
# =============================================================================


class TestUserService:
    """Tests for user service functions."""

    def test_create_user_success(self):
        """create_user creates a new user."""
        from auth.service import create_user

        user = create_user("test@example.com", "password123")
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.tier == "GOOD"

    def test_create_user_custom_tier(self):
        """create_user accepts custom tier."""
        from auth.service import create_user

        user = create_user("test@example.com", "password123", tier="BEST")
        assert user.tier == "BEST"

    def test_create_user_duplicate_raises(self):
        """create_user raises for duplicate email."""
        from auth.service import create_user, UserExistsError

        create_user("test@example.com", "password123")

        with pytest.raises(UserExistsError):
            create_user("test@example.com", "differentpass1")

    def test_create_user_weak_password_raises(self):
        """create_user raises for weak password."""
        from auth.service import create_user, WeakPasswordError

        with pytest.raises(WeakPasswordError):
            create_user("test@example.com", "weak")

    def test_get_user_by_email_found(self):
        """get_user_by_email returns user when found."""
        from auth.service import create_user, get_user_by_email

        create_user("test@example.com", "password123")
        user = get_user_by_email("test@example.com")

        assert user is not None
        assert user.email == "test@example.com"

    def test_get_user_by_email_not_found(self):
        """get_user_by_email returns None when not found."""
        from auth.service import get_user_by_email

        user = get_user_by_email("nonexistent@example.com")
        assert user is None

    def test_get_user_by_id_found(self):
        """get_user_by_id returns user when found."""
        from auth.service import create_user, get_user_by_id

        created = create_user("test@example.com", "password123")
        user = get_user_by_id(created.id)

        assert user is not None
        assert user.id == created.id

    def test_get_user_by_id_not_found(self):
        """get_user_by_id returns None when not found."""
        from auth.service import get_user_by_id

        user = get_user_by_id("nonexistent-id")
        assert user is None

    def test_authenticate_user_success(self):
        """authenticate_user returns user for valid credentials."""
        from auth.service import create_user, authenticate_user

        create_user("test@example.com", "password123")
        user = authenticate_user("test@example.com", "password123")

        assert user is not None
        assert user.email == "test@example.com"

    def test_authenticate_user_wrong_password(self):
        """authenticate_user raises for wrong password."""
        from auth.service import create_user, authenticate_user, InvalidCredentialsError

        create_user("test@example.com", "password123")

        with pytest.raises(InvalidCredentialsError):
            authenticate_user("test@example.com", "wrongpassword")

    def test_authenticate_user_nonexistent(self):
        """authenticate_user raises for nonexistent user."""
        from auth.service import authenticate_user, InvalidCredentialsError

        with pytest.raises(InvalidCredentialsError):
            authenticate_user("nonexistent@example.com", "anypassword")

    def test_update_user_tier_success(self):
        """update_user_tier updates the tier."""
        from auth.service import create_user, update_user_tier, get_user_by_id

        user = create_user("test@example.com", "password123")
        assert user.tier == "GOOD"

        updated = update_user_tier(user.id, "BEST")
        assert updated is True

        refreshed = get_user_by_id(user.id)
        assert refreshed.tier == "BEST"

    def test_update_user_tier_invalid(self):
        """update_user_tier raises for invalid tier."""
        from auth.service import create_user, update_user_tier

        user = create_user("test@example.com", "password123")

        with pytest.raises(ValueError):
            update_user_tier(user.id, "INVALID_TIER")


# =============================================================================
# Session Service Tests
# =============================================================================


class TestSessionService:
    """Tests for session service functions."""

    def test_create_session_success(self):
        """create_session creates a session."""
        from auth.service import create_user, create_session

        user = create_user("test@example.com", "password123")
        session = create_session(user.id)

        assert session.id is not None
        assert session.user_id == user.id
        assert session.is_valid is True

    def test_create_session_with_metadata(self):
        """create_session stores metadata."""
        from auth.service import create_user, create_session

        user = create_user("test@example.com", "password123")
        session = create_session(
            user.id,
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0",
        )

        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "TestAgent/1.0"

    def test_get_session_valid(self):
        """get_session returns valid session."""
        from auth.service import create_user, create_session, get_session

        user = create_user("test@example.com", "password123")
        created = create_session(user.id)

        session = get_session(created.id)
        assert session is not None
        assert session.id == created.id

    def test_get_session_not_found(self):
        """get_session returns None for nonexistent session."""
        from auth.service import get_session

        session = get_session("nonexistent-session-id")
        assert session is None

    def test_invalidate_session_success(self):
        """invalidate_session deletes the session."""
        from auth.service import create_user, create_session, invalidate_session, get_session

        user = create_user("test@example.com", "password123")
        session = create_session(user.id)

        deleted = invalidate_session(session.id)
        assert deleted is True

        # Session should no longer exist
        assert get_session(session.id) is None

    def test_invalidate_session_not_found(self):
        """invalidate_session returns False for nonexistent."""
        from auth.service import invalidate_session

        deleted = invalidate_session("nonexistent-id")
        assert deleted is False

    def test_invalidate_user_sessions(self):
        """invalidate_user_sessions removes all user sessions."""
        from auth.service import (
            create_user,
            create_session,
            invalidate_user_sessions,
            get_session,
        )

        user = create_user("test@example.com", "password123")
        s1 = create_session(user.id)
        s2 = create_session(user.id)
        s3 = create_session(user.id)

        count = invalidate_user_sessions(user.id)
        assert count == 3

        # All sessions should be gone
        assert get_session(s1.id) is None
        assert get_session(s2.id) is None
        assert get_session(s3.id) is None

    def test_get_current_user_with_session(self):
        """get_current_user returns user for valid session."""
        from auth.service import create_user, create_session, get_current_user

        user = create_user("test@example.com", "password123")
        session = create_session(user.id)

        current = get_current_user(session.id)
        assert current is not None
        assert current.id == user.id

    def test_get_current_user_no_session(self):
        """get_current_user returns None for no session."""
        from auth.service import get_current_user

        assert get_current_user(None) is None
        assert get_current_user("") is None

    def test_get_current_user_invalid_session(self):
        """get_current_user returns None for invalid session."""
        from auth.service import get_current_user

        assert get_current_user("invalid-session-id") is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestAuthIntegration:
    """Integration tests for full auth flow."""

    def test_full_auth_flow(self):
        """Test complete signup -> login -> logout flow."""
        from auth.service import (
            create_user,
            authenticate_user,
            create_session,
            get_session,
            invalidate_session,
            get_current_user,
        )

        # 1. Signup
        user = create_user("newuser@example.com", "Password123")
        assert user.id is not None

        # 2. Login
        auth_user = authenticate_user("newuser@example.com", "Password123")
        assert auth_user.id == user.id

        # 3. Create session
        session = create_session(auth_user.id)
        assert session.is_valid is True

        # 4. Get current user from session
        current = get_current_user(session.id)
        assert current is not None
        assert current.email == "newuser@example.com"

        # 5. Logout (invalidate session)
        invalidate_session(session.id)
        assert get_session(session.id) is None

        # 6. Current user is None after logout
        assert get_current_user(session.id) is None

    def test_user_tier_flow(self):
        """Test tier upgrade flow."""
        from auth.service import create_user, update_user_tier, get_user_by_id

        # Start with GOOD tier
        user = create_user("user@example.com", "Password123", tier="GOOD")
        assert user.tier == "GOOD"

        # Upgrade to BETTER
        update_user_tier(user.id, "BETTER")
        user = get_user_by_id(user.id)
        assert user.tier == "BETTER"

        # Upgrade to BEST
        update_user_tier(user.id, "BEST")
        user = get_user_by_id(user.id)
        assert user.tier == "BEST"
