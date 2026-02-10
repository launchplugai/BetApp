"""
Bets API for S18-D: Bet History Persistence + Submission.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from pydantic import BaseModel

from app.services.auth import get_current_user_from_token
from app.models import Bet, get_session

log = logging.getLogger(__name__)

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


# =============================================================================
# Bet Submission (Priority 1)
# =============================================================================

class BetLegInput(BaseModel):
    """Input schema for a bet leg."""
    entity: str
    market: str
    value: Optional[str] = None
    odds: int
    selection: str


class CreateBetRequest(BaseModel):
    """Request schema for creating a bet."""
    input_text: str
    legs: List[BetLegInput]
    wager: int  # Amount in cents (e.g., 10000 = $100.00)
    total_odds: Optional[int] = None
    potential_payout: Optional[int] = None
    # Optional: include DNA analysis results
    verdict: Optional[str] = None
    confidence: Optional[int] = None


class CreateBetResponse(BaseModel):
    """Response schema for bet creation."""
    success: bool
    bet_id: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None


@router.post("/", response_model=CreateBetResponse)
async def create_bet(
    request: CreateBetRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Create a new bet (Priority 1 - Core Loop).
    
    Stores bet in database with "pending" status.
    Returns bet ID for tracking.
    """
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Validate wager
    if request.wager <= 0:
        return CreateBetResponse(
            success=False,
            error="Wager must be greater than 0"
        )
    
    if request.wager > 1000000:  # Max $10,000
        return CreateBetResponse(
            success=False,
            error="Wager exceeds maximum allowed ($10,000)"
        )
    
    # Validate legs
    if not request.legs or len(request.legs) == 0:
        return CreateBetResponse(
            success=False,
            error="Bet must have at least one leg"
        )
    
    if len(request.legs) > 10:  # Max 10 legs
        return CreateBetResponse(
            success=False,
            error="Maximum 10 legs allowed per bet"
        )
    
    # Calculate payout if not provided
    potential_payout = request.potential_payout
    if potential_payout is None and request.total_odds:
        # Simple payout calculation: wager * (odds/100 + 1) for positive odds
        # This is simplified - real sportsbooks have complex calculations
        if request.total_odds > 0:
            potential_payout = int(request.wager * (request.total_odds / 100 + 1))
        else:
            potential_payout = int(request.wager * (100 / abs(request.total_odds) + 1))
    
    # Check and deduct balance
    db = get_session()
    
    if user.balance < request.wager:
        return CreateBetResponse(
            success=False,
            error=f"Insufficient balance. Available: ${user.balance/100:.2f}, Required: ${request.wager/100:.2f}"
        )
    
    try:
        # Deduct wager from balance
        user.balance -= request.wager
        
        bet = Bet(
            user_id=user.id,
            input_text=request.input_text,
            legs=[leg.dict() for leg in request.legs],
            wager=request.wager,
            total_odds=request.total_odds,
            potential_payout=potential_payout or request.wager,
            status="pending",
            verdict=request.verdict,
            confidence=request.confidence
        )
        
        db.add(bet)
        db.commit()
        db.refresh(bet)
        
        log.info(
            "BET_CREATED",
            extra={
                "bet_id": bet.id,
                "user_id": user.id,
                "wager": request.wager,
                "legs_count": len(request.legs),
            }
        )
        
        return CreateBetResponse(
            success=True,
            bet_id=bet.id,
            message=f"Bet created successfully. ID: {bet.id}"
        )
        
    except Exception as e:
        db.rollback()
        log.error("BET_CREATION_FAILED", extra={"error": str(e), "user_id": user.id})
        return CreateBetResponse(
            success=False,
            error=f"Failed to create bet: {str(e)}"
        )
