"""
Preferences API router for user DNA management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from app.models import get_session
from app.models.user_preferences import UserPreferences
from app.models.user_dna_snapshot import UserDnaSnapshot
from app.services.constraint_checker import check_constraints_for_user, ConstraintChecker

router = APIRouter(prefix="/api/preferences", tags=["preferences"])
security = HTTPBearer()


# Pydantic schemas for API
class ConstraintsInput(BaseModel):
    no_unders: bool = False
    max_legs: int = 6
    max_correlated_legs: int = 2
    favorite_sports: List[str] = []
    min_odds: Optional[float] = None
    max_odds: Optional[float] = None
    avoid_teams: List[str] = []
    avoid_players: List[str] = []


class BankrollPolicyInput(BaseModel):
    unit_size_percent: float = 1.0
    max_units_per_bet: float = 3.0
    max_daily_exposure_units: float = 10.0
    bankroll_goal: Optional[float] = None
    goal_timeline_days: Optional[int] = None


class PreferencesInput(BaseModel):
    risk_profile: str = "balanced"
    bet_style: List[str] = ["props"]
    constraints: ConstraintsInput = ConstraintsInput()
    bankroll_policy: BankrollPolicyInput = BankrollPolicyInput()


class PreferencesResponse(BaseModel):
    id: str
    user_id: str
    risk_profile: str
    bet_style: List[str]
    constraints: Dict[str, Any]
    bankroll_policy: Dict[str, Any]
    version: int
    created_at: Optional[str]
    updated_at: Optional[str]


# Schema classes for default constraints (used when user has no preferences)
class ConstraintsSchema(BaseModel):
    no_unders: bool = False
    max_legs: int = 6
    max_correlated_legs: int = 2
    favorite_sports: List[str] = []
    min_odds: Optional[float] = None
    max_odds: Optional[float] = None
    avoid_teams: List[str] = []
    avoid_players: List[str] = []


class BankrollPolicySchema(BaseModel):
    unit_size_percent: float = 1.0
    max_units_per_bet: float = 3.0
    max_daily_exposure_units: float = 10.0
    bankroll_goal: Optional[float] = None
    goal_timeline_days: Optional[int] = None


def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Extract user ID from JWT token."""
    # This is a simplified version - integrate with your auth service
    token = credentials.credentials
    # TODO: Validate JWT and extract user_id
    # For now, return a mock user_id based on token
    return f"user_{token[:8]}"


@router.get("", response_model=PreferencesResponse)
async def get_preferences(user_id: str = Depends(get_current_user_id)):
    """Get current user preferences."""
    session = get_session()
    
    prefs = session.query(UserPreferences).filter_by(user_id=user_id).first()
    
    if not prefs:
        # Return default preferences
        return PreferencesResponse(
            id="default",
            user_id=user_id,
            risk_profile="balanced",
            bet_style=["props"],
            constraints=ConstraintsSchema().dict(),
            bankroll_policy=BankrollPolicySchema().dict(),
            version=1,
            created_at=None,
            updated_at=None
        )
    
    return PreferencesResponse(**prefs.to_dict())


@router.post("", response_model=PreferencesResponse)
async def create_or_update_preferences(
    input_data: PreferencesInput,
    user_id: str = Depends(get_current_user_id)
):
    """Create or update user preferences."""
    session = get_session()
    
    # Check if preferences exist
    prefs = session.query(UserPreferences).filter_by(user_id=user_id).first()
    
    if prefs:
        # Update existing
        prefs.risk_profile = input_data.risk_profile
        prefs.bet_style = input_data.bet_style
        prefs.constraints = input_data.constraints.dict()
        prefs.bankroll_policy = input_data.bankroll_policy.dict()
        prefs.version += 1
        prefs.updated_at = datetime.utcnow()
    else:
        # Create new
        prefs = UserPreferences(
            id=f"pref_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            risk_profile=input_data.risk_profile,
            bet_style=input_data.bet_style,
            constraints=input_data.constraints.dict(),
            bankroll_policy=input_data.bankroll_policy.dict(),
            version=1
        )
        session.add(prefs)
    
    session.commit()
    
    return PreferencesResponse(**prefs.to_dict())


@router.post("/check", response_model=Dict[str, Any])
async def check_constraints(
    picks: List[Dict[str, Any]],
    user_id: str = Depends(get_current_user_id)
):
    """Check picks against user constraints without saving."""
    session = get_session()
    
    # Get user preferences
    prefs = session.query(UserPreferences).filter_by(user_id=user_id).first()
    
    if not prefs:
        # Use defaults
        prefs_dict = {
            "risk_profile": "balanced",
            "bet_style": ["props"],
            "constraints": ConstraintsSchema().dict(),
            "bankroll_policy": BankrollPolicySchema().dict()
        }
    else:
        prefs_dict = prefs.to_dict()
    
    # Check constraints
    violations = check_constraints_for_user(picks, prefs_dict)
    
    return {
        "violations": violations,
        "violation_count": len(violations),
        "has_warnings": any(v["severity"] in ["warning", "error"] for v in violations),
        "preferences_summary": {
            "risk_profile": prefs_dict["risk_profile"],
            "max_legs": prefs_dict["constraints"].get("max_legs", 6)
        }
    }


@router.get("/summary")
async def get_preferences_summary(user_id: str = Depends(get_current_user_id)):
    """Get a summary of active constraints for display."""
    session = get_session()
    
    prefs = session.query(UserPreferences).filter_by(user_id=user_id).first()
    
    if not prefs:
        return {
            "has_preferences": False,
            "message": "Using default preferences",
            "summary": {
                "risk_profile": "balanced",
                "max_legs": 6,
                "max_correlated_legs": 2
            }
        }
    
    checker = ConstraintChecker(prefs.to_dict())
    
    return {
        "has_preferences": True,
        "summary": checker.get_constraint_summary()
    }


@router.get("/snapshots")
async def get_dna_snapshots(
    limit: int = 10,
    user_id: str = Depends(get_current_user_id)
):
    """Get recent DNA snapshots for auditing."""
    session = get_session()
    
    snapshots = session.query(UserDnaSnapshot)\
        .filter_by(user_id=user_id)\
        .order_by(UserDnaSnapshot.created_at.desc())\
        .limit(limit)\
        .all()
    
    return {
        "snapshots": [s.to_dict() for s in snapshots],
        "count": len(snapshots)
    }
