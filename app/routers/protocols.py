"""
Protocol API endpoints - Phase 1: Database Persistence.
User-linked protocols with full CRUD.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.services.auth import get_current_user_from_token
from app.models import Protocol, get_session

router = APIRouter(prefix="/api/protocols", tags=["protocols"])
security = HTTPBearer()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class CreateProtocolRequest(BaseModel):
    """Request to create a protocol."""
    game_id: str
    league: str
    home_team: str
    away_team: str
    name: Optional[str] = None
    markets_watched: List[str] = ["spread", "total", "moneyline"]
    legs_snapshot: Optional[List[dict]] = None


class ProtocolResponse(BaseModel):
    """Protocol response."""
    id: str
    game_id: str
    league: str
    home_team: str
    away_team: str
    name: Optional[str]
    markets_watched: List[str]
    legs_snapshot: Optional[List[dict]]
    is_active: bool
    created_at: str
    last_updated: str


class ProtocolListResponse(BaseModel):
    """List of protocols."""
    protocols: List[ProtocolResponse]
    total: int


class UpdateProtocolRequest(BaseModel):
    """Request to update a protocol."""
    name: Optional[str] = None
    markets_watched: Optional[List[str]] = None
    is_active: Optional[bool] = None


# =============================================================================
# Routes
# =============================================================================

@router.post("/", response_model=ProtocolResponse)
async def create_protocol(
    request: CreateProtocolRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Create a new protocol linked to the authenticated user.
    
    Protocols track games for suggestions and monitoring.
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    protocol = Protocol(
        user_id=user.id,
        game_id=request.game_id,
        league=request.league,
        home_team=request.home_team,
        away_team=request.away_team,
        name=request.name or f"{request.away_team} @ {request.home_team}",
        markets_watched=request.markets_watched,
        legs_snapshot=request.legs_snapshot,
        is_active=1,
        created_at=datetime.utcnow(),
        last_updated=datetime.utcnow()
    )
    
    db.add(protocol)
    db.commit()
    db.refresh(protocol)
    
    return ProtocolResponse(
        id=protocol.id,
        game_id=protocol.game_id,
        league=protocol.league,
        home_team=protocol.home_team,
        away_team=protocol.away_team,
        name=protocol.name,
        markets_watched=protocol.markets_watched or [],
        legs_snapshot=protocol.legs_snapshot,
        is_active=bool(protocol.is_active),
        created_at=protocol.created_at.isoformat() if protocol.created_at else "",
        last_updated=protocol.last_updated.isoformat() if protocol.last_updated else ""
    )


@router.get("/", response_model=ProtocolListResponse)
async def list_protocols(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    active_only: bool = Query(True, description="Only return active protocols"),
    limit: int = Query(50, ge=1, le=100)
):
    """
    Get all protocols for the authenticated user.
    
    Query params:
        - active_only: Filter to active protocols (default: true)
        - limit: Max protocols to return (default: 50)
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    query = db.query(Protocol).filter(Protocol.user_id == user.id)
    
    if active_only:
        query = query.filter(Protocol.is_active == 1)
    
    protocols = query.order_by(Protocol.last_updated.desc()).limit(limit).all()
    total = query.count()
    
    return ProtocolListResponse(
        protocols=[
            ProtocolResponse(
                id=p.id,
                game_id=p.game_id,
                league=p.league,
                home_team=p.home_team,
                away_team=p.away_team,
                name=p.name,
                markets_watched=p.markets_watched or [],
                legs_snapshot=p.legs_snapshot,
                is_active=bool(p.is_active),
                created_at=p.created_at.isoformat() if p.created_at else "",
                last_updated=p.last_updated.isoformat() if p.last_updated else ""
            )
            for p in protocols
        ],
        total=total
    )


@router.get("/{protocol_id}", response_model=ProtocolResponse)
async def get_protocol(
    protocol_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a specific protocol by ID."""
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    protocol = db.query(Protocol).filter(
        Protocol.id == protocol_id,
        Protocol.user_id == user.id
    ).first()
    
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    return ProtocolResponse(
        id=protocol.id,
        game_id=protocol.game_id,
        league=protocol.league,
        home_team=protocol.home_team,
        away_team=protocol.away_team,
        name=protocol.name,
        markets_watched=protocol.markets_watched or [],
        legs_snapshot=protocol.legs_snapshot,
        is_active=bool(protocol.is_active),
        created_at=protocol.created_at.isoformat() if protocol.created_at else "",
        last_updated=protocol.last_updated.isoformat() if protocol.last_updated else ""
    )


@router.patch("/{protocol_id}", response_model=ProtocolResponse)
async def update_protocol(
    protocol_id: str,
    request: UpdateProtocolRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a protocol (name, markets, or active status)."""
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    protocol = db.query(Protocol).filter(
        Protocol.id == protocol_id,
        Protocol.user_id == user.id
    ).first()
    
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    # Update fields
    if request.name is not None:
        protocol.name = request.name
    if request.markets_watched is not None:
        protocol.markets_watched = request.markets_watched
    if request.is_active is not None:
        protocol.is_active = 1 if request.is_active else 0
    
    protocol.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(protocol)
    
    return ProtocolResponse(
        id=protocol.id,
        game_id=protocol.game_id,
        league=protocol.league,
        home_team=protocol.home_team,
        away_team=protocol.away_team,
        name=protocol.name,
        markets_watched=protocol.markets_watched or [],
        legs_snapshot=protocol.legs_snapshot,
        is_active=bool(protocol.is_active),
        created_at=protocol.created_at.isoformat() if protocol.created_at else "",
        last_updated=protocol.last_updated.isoformat() if protocol.last_updated else ""
    )


@router.delete("/{protocol_id}")
async def delete_protocol(
    protocol_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete (archive) a protocol."""
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    protocol = db.query(Protocol).filter(
        Protocol.id == protocol_id,
        Protocol.user_id == user.id
    ).first()
    
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    # Soft delete - mark as inactive
    protocol.is_active = 0
    protocol.last_updated = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": f"Protocol {protocol_id} archived"}
