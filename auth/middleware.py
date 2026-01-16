# auth/middleware.py
"""
FastAPI authentication middleware.

Provides:
- Session cookie handling
- User context injection into requests
- Helper dependencies for route handlers
"""

from __future__ import annotations

from typing import Optional
from fastapi import Request, Response, HTTPException, Depends
from fastapi.responses import RedirectResponse

from auth.models import User
from auth.service import get_current_user, create_session, invalidate_session

# Cookie configuration
SESSION_COOKIE_NAME = "dna_session"
SESSION_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def get_session_id(request: Request) -> Optional[str]:
    """Extract session ID from request cookies."""
    return request.cookies.get(SESSION_COOKIE_NAME)


def set_session_cookie(response: Response, session_id: str) -> None:
    """
    Set session cookie on response.

    Uses HTTP-only, secure settings for production.
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,  # Prevent JS access
        samesite="lax",  # CSRF protection
        secure=False,  # Set True in production with HTTPS
    )


def clear_session_cookie(response: Response) -> None:
    """Clear session cookie from response."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        samesite="lax",
    )


async def get_optional_user(request: Request) -> Optional[User]:
    """
    FastAPI dependency: Get current user if logged in.

    Returns None for anonymous users (no error).
    """
    session_id = get_session_id(request)
    return get_current_user(session_id)


async def get_required_user(request: Request) -> User:
    """
    FastAPI dependency: Get current user (required).

    Raises 401 if not logged in.
    """
    user = await get_optional_user(request)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )
    return user


async def get_user_tier(request: Request) -> str:
    """
    FastAPI dependency: Get user's tier.

    Returns 'GOOD' for anonymous users.
    """
    user = await get_optional_user(request)
    return user.tier if user else "GOOD"


def require_tier(minimum_tier: str):
    """
    Factory for tier requirement dependencies.

    Usage:
        @router.get("/premium")
        async def premium_feature(user: User = Depends(require_tier("BETTER"))):
            ...
    """
    tier_levels = {"GOOD": 1, "BETTER": 2, "BEST": 3}
    min_level = tier_levels.get(minimum_tier.upper(), 1)

    async def check_tier(user: User = Depends(get_required_user)) -> User:
        user_level = tier_levels.get(user.tier.upper(), 1)
        if user_level < min_level:
            raise HTTPException(
                status_code=403,
                detail=f"This feature requires {minimum_tier} tier or higher",
            )
        return user

    return check_tier


class AuthMiddleware:
    """
    Middleware that attaches user to request state.

    This allows any route handler to access request.state.user
    without using Depends().
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Create request to access cookies
            request = Request(scope, receive)
            session_id = get_session_id(request)
            user = get_current_user(session_id)

            # Store in scope for later access
            scope["state"] = scope.get("state", {})
            scope["state"]["user"] = user
            scope["state"]["user_id"] = user.id if user else None
            scope["state"]["tier"] = user.tier if user else "GOOD"

        await self.app(scope, receive, send)
