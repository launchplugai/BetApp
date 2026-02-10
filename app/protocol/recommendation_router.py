"""
Recommendation Router - API endpoints for bet recommendations and parlays
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.services.auth import get_current_user_from_token
from app.models import get_session
from app.protocol.recommendation_models import Recommendation, Parlay
from app.protocol.recommendation_service import (
    generate_recommendations,
    create_parlay_from_recommendations,
    convert_parlay_to_bet
)
from app.protocol import service as protocol_service
from app.protocol import schemas

router = APIRouter(prefix="/api/protocols", tags=["recommendations"])
security = HTTPBearer()


def get_db():
    """Get database session."""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Recommendation Endpoints
# =============================================================================

@router.get("/{protocol_id}/recommendations", response_model=List[dict])
async def get_recommendations(
    protocol_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get AI-generated bet recommendations for a protocol.
    
    Generates fresh recommendations based on current snapshot data.
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get protocol
    protocol = protocol_service.get_protocol_detail(db, protocol_id, user.id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    # Get user tier for recommendation quality
    user_tier = getattr(user, 'tier', 'GOOD')
    
    # Generate recommendations
    recommendations = generate_recommendations(db, protocol, user_tier)
    
    return [r.to_dict() for r in recommendations]


@router.post("/{protocol_id}/recommendations/refresh")
async def refresh_recommendations(
    protocol_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Generate fresh recommendations (archive old ones).
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    protocol = protocol_service.get_protocol_detail(db, protocol_id, user.id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    # Archive old recommendations
    old_recs = db.query(Recommendation).filter(
        Recommendation.protocol_id == protocol_id,
        Recommendation.status == "active"
    ).all()
    
    for rec in old_recs:
        rec.status = "expired"
    
    db.commit()
    
    # Generate new ones
    user_tier = getattr(user, 'tier', 'GOOD')
    recommendations = generate_recommendations(db, protocol, user_tier)
    
    return {
        "success": True,
        "recommendations": [r.to_dict() for r in recommendations],
        "archived_count": len(old_recs)
    }


# =============================================================================
# Parlay Builder Endpoints
# =============================================================================

class ParlayCreateRequest(BaseModel):
    """Request to create a parlay."""
    recommendation_ids: List[str]
    title: Optional[str] = None


@router.post("/{protocol_id}/build-parlay", response_model=dict)
async def build_parlay(
    protocol_id: str,
    request: ParlayCreateRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Build a parlay from selected recommendations.
    
    Creates a shareable parlay preview that can be converted to a bet.
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Verify protocol exists and user owns it
    protocol = protocol_service.get_protocol_detail(db, protocol_id, user.id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    try:
        parlay = create_parlay_from_recommendations(
            db=db,
            user_id=user.id,
            recommendation_ids=request.recommendation_ids,
            title=request.title
        )
        
        return {
            "success": True,
            "parlay": parlay.to_dict(),
            "share_url": f"/parlay/{parlay.share_token}"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Parlay Preview & Sharing
# =============================================================================

@router.get("/parlays/{parlay_id}/preview", response_model=dict)
async def get_parlay_preview(
    parlay_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get detailed preview of a parlay with analysis.
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    parlay = db.query(Parlay).filter(
        Parlay.id == parlay_id,
        Parlay.user_id == user.id
    ).first()
    
    if not parlay:
        raise HTTPException(status_code=404, detail="Parlay not found")
    
    # Get full recommendation details
    recommendations = db.query(Recommendation).filter(
        Recommendation.id.in_(parlay.recommendation_ids)
    ).all()
    
    # Increment view count
    parlay.view_count += 1
    db.commit()
    
    return {
        "parlay": parlay.to_dict(),
        "recommendations": [r.to_dict() for r in recommendations],
        "analysis": {
            "total_legs": len(recommendations),
            "avg_confidence": sum(r.confidence for r in recommendations) / len(recommendations),
            "risk_level": _calculate_risk_level(recommendations),
            "share_url": f"/parlay/{parlay.share_token}"
        }
    }


@router.get("/parlays/share/{share_token}", response_model=dict)
async def get_shared_parlay(share_token: str, db: Session = Depends(get_db)):
    """
    Get public preview of a shared parlay (no auth required).
    
    Allows sharing parlays with others who can view but not modify.
    """
    parlay = db.query(Parlay).filter(Parlay.share_token == share_token).first()
    
    if not parlay or parlay.status != "draft":
        raise HTTPException(status_code=404, detail="Parlay not found")
    
    # Get recommendations (limited details for public)
    recommendations = db.query(Recommendation).filter(
        Recommendation.id.in_(parlay.recommendation_ids)
    ).all()
    
    # Increment view count
    parlay.view_count += 1
    db.commit()
    
    return {
        "title": parlay.title,
        "description": parlay.description,
        "total_odds": parlay.total_odds,
        "implied_probability": parlay.implied_probability,
        "picks": [
            {
                "description": r.description,
                "confidence": r.confidence,
                "bet_type": r.bet_type
            }
            for r in recommendations
        ],
        "view_count": parlay.view_count,
        "created_at": parlay.created_at.isoformat() if parlay.created_at else None
    }


# =============================================================================
# Copy to Bet
# =============================================================================

class CopyToBetRequest(BaseModel):
    """Request to convert parlay to bet."""
    wager: int  # Amount in cents


@router.post("/parlays/{parlay_id}/copy-to-bet", response_model=dict)
async def copy_parlay_to_bet(
    parlay_id: str,
    request: CopyToBetRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Convert a parlay preview to an actual bet.
    
    Imports the parlay into the user's bet builder.
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    parlay = db.query(Parlay).filter(
        Parlay.id == parlay_id,
        Parlay.user_id == user.id
    ).first()
    
    if not parlay:
        raise HTTPException(status_code=404, detail="Parlay not found")
    
    # Get recommendations for bet creation
    recommendations = db.query(Recommendation).filter(
        Recommendation.id.in_(parlay.recommendation_ids)
    ).all()
    
    # Build bet data
    bet_data = {
        "input_text": parlay.description,
        "legs": [
            {
                "entity": r.description,
                "market": r.bet_type,
                "value": None,
                "odds": -110  # Placeholder
            }
            for r in recommendations
        ],
        "wager": request.wager,
        "total_odds": parlay.total_odds,
        "potential_payout": _calculate_payout(request.wager, parlay.total_odds)
    }
    
    # Mark parlay as converted
    bet_id = convert_parlay_to_bet(db, parlay, {"bet_id": "pending"})
    
    return {
        "success": True,
        "message": "Parlay ready for bet submission",
        "bet_data": bet_data,
        "parlay_id": parlay.id
    }


# =============================================================================
# Helpers
# =============================================================================

def _calculate_risk_level(recommendations: List[Recommendation]) -> str:
    """Calculate risk level from recommendations."""
    avg_confidence = sum(r.confidence for r in recommendations) / len(recommendations)
    
    if avg_confidence >= 70:
        return "low"
    elif avg_confidence >= 55:
        return "medium"
    else:
        return "high"


def _calculate_payout(wager: int, odds: int) -> int:
    """Calculate potential payout from American odds."""
    if odds > 0:
        return wager + int(wager * odds / 100)
    else:
        return wager + int(wager * 100 / abs(odds))
