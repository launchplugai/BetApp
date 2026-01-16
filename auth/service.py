# auth/service.py
"""
Authentication service.

Handles:
- User registration and lookup
- Password verification
- Session creation and validation
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from auth.models import User, Session
from auth.password import hash_password, verify_password, is_password_strong
from persistence.db import get_db, init_db

_logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Base authentication error."""
    pass


class UserExistsError(AuthError):
    """User with this email already exists."""
    pass


class WeakPasswordError(AuthError):
    """Password doesn't meet strength requirements."""
    pass


class InvalidCredentialsError(AuthError):
    """Invalid email or password."""
    pass


class SessionExpiredError(AuthError):
    """Session has expired."""
    pass


def create_user(email: str, password: str, tier: str = "GOOD") -> User:
    """
    Create a new user account.

    Args:
        email: User's email address
        password: Plain text password
        tier: Subscription tier (default: GOOD)

    Returns:
        Created User object

    Raises:
        UserExistsError: If email already registered
        WeakPasswordError: If password doesn't meet requirements
    """
    init_db()

    # Validate password strength
    is_strong, error_msg = is_password_strong(password)
    if not is_strong:
        raise WeakPasswordError(error_msg)

    # Normalize email
    email = email.lower().strip()

    # Check if user exists
    if get_user_by_email(email):
        raise UserExistsError(f"User with email {email} already exists")

    # Hash password and create user
    password_hash = hash_password(password)
    user = User.new(email=email, password_hash=password_hash, tier=tier)

    # Persist to database
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO users (id, email, password_hash, tier, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user.id,
                user.email,
                user.password_hash,
                user.tier,
                user.created_at.isoformat(),
                user.updated_at.isoformat(),
            ),
        )

    _logger.info(f"Created user: {email}")
    return user


def get_user_by_email(email: str) -> Optional[User]:
    """
    Get user by email address.

    Args:
        email: Email to look up

    Returns:
        User if found, None otherwise
    """
    init_db()
    email = email.lower().strip()

    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,),
        )
        row = cursor.fetchone()

    if not row:
        return None

    return _row_to_user(row)


def get_user_by_id(user_id: str) -> Optional[User]:
    """
    Get user by ID.

    Args:
        user_id: User ID to look up

    Returns:
        User if found, None otherwise
    """
    init_db()

    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        )
        row = cursor.fetchone()

    if not row:
        return None

    return _row_to_user(row)


def _row_to_user(row) -> User:
    """Convert a database row to a User object."""
    tier_updated_at = None
    if row["tier_updated_at"]:
        tier_updated_at = datetime.fromisoformat(row["tier_updated_at"])

    return User(
        id=row["id"],
        email=row["email"],
        password_hash=row["password_hash"],
        tier=row["tier"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        stripe_customer_id=row["stripe_customer_id"],
        stripe_subscription_id=row["stripe_subscription_id"],
        tier_updated_at=tier_updated_at,
    )


def authenticate_user(email: str, password: str) -> User:
    """
    Authenticate user with email and password.

    Args:
        email: User's email
        password: Plain text password

    Returns:
        Authenticated User object

    Raises:
        InvalidCredentialsError: If credentials are invalid
    """
    user = get_user_by_email(email)

    if not user:
        _logger.warning(f"Login attempt for non-existent user: {email}")
        raise InvalidCredentialsError("Invalid email or password")

    if not verify_password(password, user.password_hash):
        _logger.warning(f"Invalid password for user: {email}")
        raise InvalidCredentialsError("Invalid email or password")

    _logger.info(f"User authenticated: {email}")
    return user


def update_user_tier(user_id: str, tier: str) -> bool:
    """
    Update a user's subscription tier.

    Args:
        user_id: User ID
        tier: New tier (GOOD, BETTER, BEST)

    Returns:
        True if updated, False if user not found
    """
    init_db()
    tier = tier.upper()

    if tier not in ("GOOD", "BETTER", "BEST"):
        raise ValueError(f"Invalid tier: {tier}")

    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE users SET tier = ?, updated_at = ?
            WHERE id = ?
            """,
            (tier, datetime.utcnow().isoformat(), user_id),
        )
        return cursor.rowcount > 0


def create_session(
    user_id: str,
    duration_days: int = 7,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Session:
    """
    Create a new session for a user.

    Args:
        user_id: User ID
        duration_days: Session duration in days
        ip_address: Client IP (optional)
        user_agent: Client user agent (optional)

    Returns:
        Created Session object
    """
    init_db()

    session = Session.new(
        user_id=user_id,
        duration_days=duration_days,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, user_id, created_at, expires_at, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session.id,
                session.user_id,
                session.created_at.isoformat(),
                session.expires_at.isoformat(),
                session.ip_address,
                session.user_agent,
            ),
        )

    _logger.debug(f"Created session for user: {user_id}")
    return session


def get_session(session_id: str) -> Optional[Session]:
    """
    Get session by ID.

    Args:
        session_id: Session ID

    Returns:
        Session if found and valid, None otherwise
    """
    init_db()

    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = cursor.fetchone()

    if not row:
        return None

    session = Session(
        id=row["id"],
        user_id=row["user_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        expires_at=datetime.fromisoformat(row["expires_at"]),
        ip_address=row["ip_address"],
        user_agent=row["user_agent"],
    )

    # Check if expired
    if not session.is_valid:
        # Clean up expired session
        invalidate_session(session_id)
        return None

    return session


def invalidate_session(session_id: str) -> bool:
    """
    Invalidate (delete) a session.

    Args:
        session_id: Session ID to invalidate

    Returns:
        True if deleted, False if not found
    """
    init_db()

    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,),
        )
        return cursor.rowcount > 0


def invalidate_user_sessions(user_id: str) -> int:
    """
    Invalidate all sessions for a user.

    Args:
        user_id: User ID

    Returns:
        Number of sessions invalidated
    """
    init_db()

    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM sessions WHERE user_id = ?",
            (user_id,),
        )
        return cursor.rowcount


def get_current_user(session_id: Optional[str]) -> Optional[User]:
    """
    Get the current user from a session ID.

    This is the main entry point for auth middleware.

    Args:
        session_id: Session ID from cookie

    Returns:
        User if session is valid, None otherwise
    """
    if not session_id:
        return None

    session = get_session(session_id)
    if not session:
        return None

    return get_user_by_id(session.user_id)


def cleanup_expired_sessions() -> int:
    """
    Remove expired sessions from database.

    Should be called periodically (e.g., daily cron).

    Returns:
        Number of sessions cleaned up
    """
    init_db()

    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM sessions WHERE expires_at < ?",
            (datetime.utcnow().isoformat(),),
        )
        count = cursor.rowcount

    if count > 0:
        _logger.info(f"Cleaned up {count} expired sessions")

    return count
