"""
Bets API for S18-D: Bet History Persistence.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from pydantic import BaseModel

from app.services.auth import get_current_user_from_token
from app.models import Bet, get_session

router = APIRouter(prefix="/api/bets", tags=["bets"])
security = HTTPBearer()


# =============================================================================
# Response Schemas
# =============================================================================

class BetLeg(BaseModel):
    entity: str
    market: str
    value: Optional[str]
    odds: Optional[int]


class BetHistoryItem(BaseModel):
    id: str
    input_text: str
    legs: List[BetLeg]
    wager: int
    total_odds: Optional[int]
    potential_payout: int
    status: str  # pending, won, lost, void
    actual_payout: Optional[int]
    verdict: Optional[str]
    confidence: Optional[int]
    created_at: str
    settled_at: Optional[str]


class BetHistoryResponse(BaseModel):
    bets: List[BetHistoryItem]
    total: int
    page: int
    per_page: int


# =============================================================================
# Routes
# =============================================================================

@router.get("/history", response_model=BetHistoryResponse)
async def get_bet_history(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    status: Optional[str] = Query(None, description="Filter by status: pending, won, lost, void"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=50, description="Items per page")
):
    """
    Get bet history for authenticated user.
    
    Query params:
        - status: Filter by status (pending, won, lost, void)
        - page: Page number (default 1)
        - per_page: Items per page (default 10, max 50)
    
    Returns:
        {
            "bets": [...],
            "total": 100,
            "page": 1,
            "per_page": 10
        }
    """
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    # Build query
    query = db.query(Bet).filter(Bet.user_id == user.id)
    
    if status:
        query = query.filter(Bet.status == status.lower())
    
    # Get total count
    total = query.count()
    
    # Pagination
    offset = (page - 1) * per_page
    bets = query.order_by(Bet.created_at.desc()).offset(offset).limit(per_page).all()
    
    # Map to response format
    bet_items = []
    for bet in bets:
        # Parse legs from JSON
        legs = bet.legs or []
        leg_items = [
            BetLeg(
                entity=leg.get("entity", ""),
                market=leg.get("market", ""),
                value=leg.get("value"),
                odds=leg.get("odds")
            )
            for leg in legs
        ]
        
        bet_items.append(BetHistoryItem(
            id=bet.id,
            input_text=bet.input_text,
            legs=leg_items,
            wager=bet.wager or 0,
            total_odds=bet.total_odds,
            potential_payout=bet.potential_payout or 0,
            status=bet.status or "pending",
            actual_payout=bet.actual_payout,
            verdict=bet.verdict,
            confidence=bet.confidence,
            created_at=bet.created_at.isoformat() if bet.created_at else "",
            settled_at=bet.settled_at.isoformat() if bet.settled_at else None
        ))
    
    return BetHistoryResponse(
        bets=bet_items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/{bet_id}")
async def get_bet_detail(
    bet_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get single bet details by ID."""
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    bet = db.query(Bet).filter(Bet.id == bet_id, Bet.user_id == user.id).first()
    
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    return bet.to_dict()
