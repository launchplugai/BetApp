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
    update_user_tier
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
    token: Optional[str] = None
    error: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    tier: str


# =============================================================================
# Routes
# =============================================================================

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register a new user account."""
    user, error = register_user(
        email=request.email,
        password=request.password,
        name=request.name
    )
    
    if error:
        return AuthResponse(success=False, error=error)
    
    # Create JWT token
    token = create_access_token({"sub": user.id})
    
    return AuthResponse(
        success=True,
        user=user.to_dict(),
        token=token
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Login with email/password."""
    user, error = authenticate_user(
        email=request.email,
        password=request.password
    )
    
    if error:
        return AuthResponse(success=False, error=error)
    
    # Create JWT token
    token = create_access_token({"sub": user.id})
    
    return AuthResponse(
        success=True,
        user=user.to_dict(),
        token=token
    )


@router.get("/me", response_model=UserResponse)
async def get_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user info."""
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        tier=user.tier
    )


@router.post("/refresh")
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Refresh JWT token."""
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Create new token
    new_token = create_access_token({"sub": user.id})
    
    return {"token": new_token}


@router.post("/logout")
async def logout():
    """Logout (client-side token deletion)."""
    # JWT tokens are stateless, so we just tell client to delete it
    return {"success": True, "message": "Logged out successfully"}


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
