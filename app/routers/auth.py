"""
Authentication API endpoints for S18.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.services.auth import (
    register_user,
    authenticate_user,
    get_current_user_from_token,
    create_access_token,
    update_user_tier,
    validate_refresh_token,
    blacklist_access_token,
    revoke_refresh_token,
    revoke_all_user_refresh_tokens,
    get_user_from_refresh_token,
)
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    success: bool
    user: Optional[dict] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token: Optional[str] = None  # Legacy compatibility
    error: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    tier: str
    session_expires_at: Optional[str] = None  # S18-E: Session expiry


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    logout_all: bool = False  # Logout from all devices


# =============================================================================
# Routes
# =============================================================================

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register a new user account."""
    user, access_token, refresh_token, error = register_user(
        email=request.email,
        password=request.password,
        name=request.name
    )
    
    if error:
        return AuthResponse(success=False, error=error)
    
    return AuthResponse(
        success=True,
        user=user.to_dict(),
        access_token=access_token,
        refresh_token=refresh_token,
        token=access_token  # Legacy compatibility
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login with email/password."""
    user, access_token, refresh_token, error = authenticate_user(
        email=request.email,
        password=request.password
    )
    
    if error:
        return AuthResponse(success=False, error=error)
    
    return AuthResponse(
        success=True,
        user=user.to_dict(),
        access_token=access_token,
        refresh_token=refresh_token,
        token=access_token  # Legacy compatibility
    )


@router.get("/me", response_model=UserResponse)
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user info with session expiry (S18-E)."""
    from app.services.auth import decode_token
    from datetime import datetime
    
    token = credentials.credentials
    user = get_current_user_from_token(token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get expiry from token
    payload = decode_token(token)
    exp_timestamp = payload.get("exp") if payload else None
    session_expires_at = None
    
    if exp_timestamp:
        session_expires_at = datetime.utcfromtimestamp(exp_timestamp).isoformat() + "Z"
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        tier=user.tier,
        session_expires_at=session_expires_at
    )


@router.post("/refresh")
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token (S18-E).
    
    Validates refresh token and issues new access token.
    """
    user = validate_refresh_token(request.refresh_token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    # Create new access token
    new_access_token, _ = create_access_token({"sub": user.id})
    
    return {
        "success": True,
        "access_token": new_access_token,
        "token": new_access_token  # Legacy compatibility
    }


@router.post("/logout")
async def logout(
    request: LogoutRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout and invalidate tokens (S18-E).
    
    Blacklists access token and revokes refresh token(s).
    """
    access_token = credentials.credentials
    user = get_current_user_from_token(access_token)

    # Always revoke the provided refresh token when present, even if the access
    # token is already expired or otherwise invalid.
    refresh_token_revoked = False
    refresh_token_user = None
    if request.refresh_token:
        refresh_token_user = get_user_from_refresh_token(request.refresh_token)
        refresh_token_revoked = revoke_refresh_token(request.refresh_token)

    effective_user = user or refresh_token_user

    # Revoke refresh token(s)
    if request.logout_all:
        if not effective_user:
            return {"success": True, "message": "Logged out"}

        if user:
            blacklist_access_token(access_token, reason="logout")

        revoked_count = revoke_all_user_refresh_tokens(effective_user.id)
        return {
            "success": True,
            "message": f"Logged out from all devices ({revoked_count} sessions)"
        }

    if user:
        blacklist_access_token(access_token, reason="logout")

    if request.refresh_token:
        message = "Logged out successfully" if refresh_token_revoked else "Logged out"
        return {"success": True, "message": message}

    return {"success": True, "message": "Logged out (access token invalidated)"}


# =============================================================================
# Tier Upgrade (Mock for now)
# =============================================================================

class UpgradeRequest(BaseModel):
    tier: str  # BETTER, BEST


@router.post("/upgrade")
async def upgrade_tier(
    request: UpgradeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Upgrade user tier (mock - no real payment)."""
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    if request.tier not in ["BETTER", "BEST"]:
        raise HTTPException(status_code=400, detail="Invalid tier")
    
    # Mock upgrade (in real app, verify payment first)
    success = update_user_tier(user.id, request.tier)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to upgrade tier")
    
    return {
        "success": True,
        "message": f"Upgraded to {request.tier}",
        "tier": request.tier
    }
