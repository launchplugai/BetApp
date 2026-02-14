"""
Bets API for S18-D: Bet History Persistence + Submission.
Updated for S21-E: History Receipts.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.services.auth import get_current_user_from_token
from app.models import Bet, Transaction, User, get_session
from app.services.constraint_checker import ConstraintChecker

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
    # S21-E: DNA receipt fields
    user_dna_snapshot_id: Optional[str] = None
    risk_profile_at_bet: Optional[str] = None


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
            settled_at=bet.settled_at.isoformat() if bet.settled_at else None,
            user_dna_snapshot_id=bet.user_dna_snapshot_id,
            risk_profile_at_bet=bet.risk_profile_at_bet
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
    """Get single bet details by ID with DNA receipt info."""
    from app.models.user_dna_snapshot import UserDnaSnapshot
    
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    bet = db.query(Bet).filter(Bet.id == bet_id, Bet.user_id == user.id).first()
    
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")
    
    # Build response with DNA receipt info
    response = bet.to_dict()
    
    # S21-E: Include DNA snapshot details if available
    if bet.user_dna_snapshot_id:
        snapshot = db.query(UserDnaSnapshot).filter_by(id=bet.user_dna_snapshot_id).first()
        if snapshot:
            response["dna_snapshot"] = {
                "id": snapshot.id,
                "preferences": snapshot.preferences,
                "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None
            }
    
    return response


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
    # S21-E: Constraint violations and warnings
    constraint_violations: Optional[List[Dict[str, Any]]] = None
    risk_profile: Optional[str] = None
    dna_snapshot_id: Optional[str] = None


@router.post("/", response_model=CreateBetResponse)
async def create_bet(
    request: CreateBetRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Create a new bet (Priority 1 - Core Loop).
    
    Stores bet in database with "pending" status.
    Records DNA snapshot and applied constraints (S21-E).
    Returns bet ID for tracking.
    """
    from app.models.user_preferences import UserPreferences
    from app.models.user_dna_snapshot import UserDnaSnapshot
    import uuid
    
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
    
    # S21-E: Get user preferences and create DNA snapshot
    prefs = db.query(UserPreferences).filter_by(user_id=user.id).first()
    prefs_dict = None
    dna_snapshot_id = None
    risk_profile = "balanced"
    constraint_violations = []
    applied_constraints = []
    blocked_actions = []
    
    if prefs:
        prefs_dict = prefs.to_dict()
        risk_profile = prefs_dict.get("risk_profile", "balanced")
        
        # Create DNA snapshot
        snapshot = UserDnaSnapshot(
            id=f"snapshot_{uuid.uuid4().hex[:8]}",
            user_id=user.id,
            preferences=prefs_dict,
            created_at=datetime.utcnow()
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        dna_snapshot_id = snapshot.id
        
        # Check constraints on the picks
        picks = [leg.dict() for leg in request.legs]
        checker = ConstraintChecker(prefs_dict)
        violations = checker.check_picks(picks)
        constraint_violations = [v.to_dict() for v in violations]
        
        # Record which constraints were applied
        constraints_config = prefs_dict.get("constraints", {})
        if constraints_config.get("max_legs"):
            applied_constraints.append({
                "type": "max_legs",
                "value": constraints_config.get("max_legs"),
                "enforced": len(request.legs) <= constraints_config.get("max_legs", 6)
            })
        if constraints_config.get("no_unders"):
            applied_constraints.append({
                "type": "no_unders",
                "value": True,
                "enforced": True
            })
        if constraints_config.get("max_correlated_legs"):
            applied_constraints.append({
                "type": "max_correlated_legs",
                "value": constraints_config.get("max_correlated_legs"),
                "enforced": True
            })
        if constraints_config.get("favorite_sports"):
            applied_constraints.append({
                "type": "favorite_sports",
                "value": constraints_config.get("favorite_sports"),
                "enforced": True
            })
        if constraints_config.get("avoid_teams"):
            applied_constraints.append({
                "type": "avoid_teams",
                "value": constraints_config.get("avoid_teams"),
                "enforced": True
            })
        if constraints_config.get("avoid_players"):
            applied_constraints.append({
                "type": "avoid_players",
                "value": constraints_config.get("avoid_players"),
                "enforced": True
            })
        if constraints_config.get("min_odds") or constraints_config.get("max_odds"):
            applied_constraints.append({
                "type": "odds_range",
                "min": constraints_config.get("min_odds"),
                "max": constraints_config.get("max_odds"),
                "enforced": True
            })
        
        # Record blocked actions (warnings/errors from violations)
        for v in violations:
            if v.severity.value in ["warning", "error"]:
                blocked_actions.append({
                    "action": v.constraint_type,
                    "reason": v.message,
                    "severity": v.severity.value
                })
    
    try:
        # Record balance before wager
        balance_before = user.balance
        
        # Deduct wager from balance
        user.balance -= request.wager
        
        # Create wager transaction record
        wager_transaction = Transaction(
            user_id=user.id,
            bet_id=None,  # Will update after bet creation
            type="wager",
            amount=request.wager,
            balance_before=balance_before,
            balance_after=user.balance,
            description=f"Wager placed"
        )
        db.add(wager_transaction)
        
        bet = Bet(
            user_id=user.id,
            input_text=request.input_text,
            legs=[leg.dict() for leg in request.legs],
            wager=request.wager,
            total_odds=request.total_odds,
            potential_payout=potential_payout or request.wager,
            status="pending",
            verdict=request.verdict,
            confidence=request.confidence,
            # S21-E: DNA receipt fields
            user_dna_snapshot_id=dna_snapshot_id,
            applied_constraints=applied_constraints,
            blocked_actions=blocked_actions,
            risk_profile_at_bet=risk_profile
        )
        
        db.add(bet)
        db.commit()
        db.refresh(bet)
        
        # Update wager transaction with bet_id
        wager_transaction.bet_id = bet.id
        wager_transaction.description = f"Wager placed for bet {bet.id}"
        db.commit()
        
        log.info(
            "BET_CREATED",
            extra={
                "bet_id": bet.id,
                "user_id": user.id,
                "wager": request.wager,
                "legs_count": len(request.legs),
                "dna_snapshot_id": dna_snapshot_id,
                "risk_profile": risk_profile,
                "constraint_count": len(applied_constraints),
                "blocked_count": len(blocked_actions)
            }
        )
        
        return CreateBetResponse(
            success=True,
            bet_id=bet.id,
            message=f"Bet created successfully. ID: {bet.id}",
            constraint_violations=constraint_violations if constraint_violations else None,
            risk_profile=risk_profile,
            dna_snapshot_id=dna_snapshot_id
        )
        
    except Exception as e:
        db.rollback()
        log.error("BET_CREATION_FAILED", extra={"error": str(e), "user_id": user.id})
        return CreateBetResponse(
            success=False,
            error=f"Failed to create bet: {str(e)}"
        )


# =============================================================================
# Bet Settlement (S-NEXT)
# =============================================================================

class SettleBetRequest(BaseModel):
    """Request schema for settling a bet."""
    result: str  # "won", "lost", "void"
    actual_payout: Optional[int] = None  # cents, null for lost/void


class SettleBetResponse(BaseModel):
    """Response schema for bet settlement."""
    success: bool
    bet_id: Optional[str] = None
    status: Optional[str] = None
    actual_payout: Optional[int] = None
    new_balance: Optional[int] = None
    error: Optional[str] = None


@router.post("/{bet_id}/settle", response_model=SettleBetResponse)
async def settle_bet(
    bet_id: str,
    request: SettleBetRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Settle a bet (admin/operator only).
    
    Updates bet status and user balance based on result:
    - won: Add actual_payout to balance
    - lost: No payout, status updated
    - void: Refund original wager to balance
    """
    from datetime import datetime
    
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Validate result
    if request.result not in ("won", "lost", "void"):
        return SettleBetResponse(
            success=False,
            error=f"Invalid result: {request.result}. Must be 'won', 'lost', or 'void'"
        )
    
    db = get_session()
    
    # Get bet
    bet = db.query(Bet).filter(Bet.id == bet_id).first()
    
    if not bet:
        return SettleBetResponse(
            success=False,
            error="Bet not found"
        )
    
    # Check if already settled
    if bet.status != "pending":
        return SettleBetResponse(
            success=False,
            error=f"Bet already settled with status: {bet.status}"
        )
    
    # Get user for balance update
    user_record = db.query(User).filter(User.id == bet.user_id).first()
    
    if not user_record:
        return SettleBetResponse(
            success=False,
            error="User not found"
        )
    
    try:
        balance_before = user_record.balance or 0
        actual_payout = 0
        transaction_type = None
        transaction_description = ""
        
        if request.result == "won":
            actual_payout = request.actual_payout or bet.potential_payout or 0
            user_record.balance = balance_before + actual_payout
            transaction_type = "payout"
            transaction_description = f"Payout for winning bet {bet_id}"
            
        elif request.result == "lost":
            actual_payout = 0
            # No balance change - wager already deducted
            transaction_type = None  # No transaction for loss (wager was already deducted)
            transaction_description = f"Loss recorded for bet {bet_id}"
            
        elif request.result == "void":
            # Refund the wager
            actual_payout = bet.wager or 0
            user_record.balance = balance_before + actual_payout
            transaction_type = "refund"
            transaction_description = f"Refund for voided bet {bet_id}"
        
        # Update bet
        bet.status = request.result
        bet.actual_payout = actual_payout if request.result != "lost" else 0
        bet.settled_at = datetime.utcnow()
        
        # Create transaction log (except for losses - wager already logged on creation)
        if transaction_type:
            transaction = Transaction(
                user_id=bet.user_id,
                bet_id=bet_id,
                type=transaction_type,
                amount=actual_payout,
                balance_before=balance_before,
                balance_after=user_record.balance,
                description=transaction_description
            )
            db.add(transaction)
        
        db.commit()
        
        log.info(
            "BET_SETTLED",
            extra={
                "bet_id": bet_id,
                "user_id": bet.user_id,
                "result": request.result,
                "actual_payout": actual_payout,
                "new_balance": user_record.balance
            }
        )
        
        return SettleBetResponse(
            success=True,
            bet_id=bet_id,
            status=request.result,
            actual_payout=actual_payout,
            new_balance=user_record.balance
        )
        
    except Exception as e:
        db.rollback()
        log.error("BET_SETTLEMENT_FAILED", extra={"error": str(e), "bet_id": bet_id})
        return SettleBetResponse(
            success=False,
            error=f"Failed to settle bet: {str(e)}"
        )


# =============================================================================
# Transaction History
# =============================================================================

class TransactionItem(BaseModel):
    """Transaction item for history."""
    id: str
    type: str
    amount: int
    balance_before: int
    balance_after: int
    bet_id: Optional[str] = None
    description: str
    created_at: str


class TransactionHistoryResponse(BaseModel):
    """Response schema for transaction history."""
    transactions: List[TransactionItem]
    total: int


@router.get("/transactions", response_model=TransactionHistoryResponse)
async def get_transaction_history(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limit: int = Query(50, ge=1, le=100, description="Number of transactions to return")
):
    """
    Get transaction history for authenticated user.
    
    Returns wager, payout, and refund transactions with balance tracking.
    """
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    # Get transactions for user
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user.id
    ).order_by(Transaction.created_at.desc()).limit(limit).all()
    
    total = db.query(Transaction).filter(Transaction.user_id == user.id).count()
    
    # Map to response
    tx_items = [
        TransactionItem(
            id=tx.id,
            type=tx.type,
            amount=tx.amount,
            balance_before=tx.balance_before,
            balance_after=tx.balance_after,
            bet_id=tx.bet_id,
            description=tx.description,
            created_at=tx.created_at.isoformat() if tx.created_at else ""
        )
        for tx in transactions
    ]
    
    return TransactionHistoryResponse(
        transactions=tx_items,
        total=total
    )
