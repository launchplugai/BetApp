# auth/__init__.py
"""
Authentication module.

Provides:
- User model with email/password auth
- Session management with HTTP-only cookies
- Password hashing with bcrypt
"""

from auth.models import User, Session
from auth.service import (
    create_user,
    authenticate_user,
    create_session,
    get_session,
    invalidate_session,
    get_current_user,
)

__all__ = [
    "User",
    "Session",
    "create_user",
    "authenticate_user",
    "create_session",
    "get_session",
    "invalidate_session",
    "get_current_user",
]
