"""Shared auth dependencies for internal/admin surfaces."""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer()


def _admin_email_allowlist() -> set[str]:
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def require_internal_admin_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Require a valid authenticated user with internal/admin access."""
    from app.services.auth import get_current_user_from_token

    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    allowlisted = user.email.lower() in _admin_email_allowlist()
    if user.tier != "BEST" and not allowlisted:
        raise HTTPException(
            status_code=403,
            detail="Internal access requires BEST tier or allowlisted admin email",
        )

    return user
