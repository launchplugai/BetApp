"""
Protocol Router - API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional

from app.services.auth import get_current_user_from_token
from app.models import get_session
from app.protocol.models import Protocol
from app.protocol import schemas
from app.protocol import service

router = APIRouter(prefix="/api/protocols", tags=["protocols"])
security = HTTPBearer()


def get_db():
    """Get database session."""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=schemas.ProtocolOut)
async def create_protocol(
    payload: schemas.ProtocolCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Create a new protocol.
    
    Creates a protocol workspace with optional targets (games/teams/players).
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Convert targets to dicts for service
    targets = None
    if payload.targets:
        targets = [t.model_dump() for t in payload.targets]
    
    protocol = service.create_protocol(
        db=db,
        user_id=user.id,
        sport=payload.sport,
        title=payload.title,
        context=payload.context or {},
        targets=targets
    )
    
    return _protocol_to_out(protocol)


@router.get("", response_model=schemas.ProtocolListOut)
async def list_protocols(
    status: Optional[str] = Query(None, description="Filter by status: draft|active|archived"),
    limit: int = Query(50, ge=1, le=100),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    List user's protocols.
    
    Returns protocols owned by the authenticated user.
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    protocols = service.get_user_protocols(
        db=db,
        user_id=user.id,
        status=status,
        limit=limit
    )
    
    return schemas.ProtocolListOut(
        protocols=[_protocol_to_out(p) for p in protocols],
        total=len(protocols)
    )


@router.get("/{protocol_id}", response_model=schemas.ProtocolDetailOut)
async def get_protocol(
    protocol_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get protocol detail with targets and recent items.
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    protocol = service.get_protocol_detail(db, protocol_id, user.id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    return _protocol_to_detail_out(protocol)


@router.patch("/{protocol_id}", response_model=schemas.ProtocolOut)
async def update_protocol(
    protocol_id: str,
    payload: schemas.ProtocolUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Update protocol (title, status, context).
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    protocol = service.get_protocol_detail(db, protocol_id, user.id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    updated = service.update_protocol(
        db=db,
        protocol=protocol,
        title=payload.title,
        status=payload.status,
        context=payload.context
    )
    
    return _protocol_to_out(updated)


@router.delete("/{protocol_id}")
async def archive_protocol(
    protocol_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Archive (soft delete) a protocol.
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    protocol = service.get_protocol_detail(db, protocol_id, user.id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    service.archive_protocol(db, protocol)
    
    return {"success": True, "message": f"Protocol {protocol_id} archived"}


@router.post("/{protocol_id}/snapshot", response_model=schemas.SnapshotOut)
async def create_snapshot(
    protocol_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Create a stats snapshot from NBA analytics system.
    
    Pulls current stats for the protocol's game target and stores as item.
    Data depth depends on user tier (GOOD/BETTER/BEST).
    """
    user = get_current_user_from_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    protocol = service.get_protocol_detail(db, protocol_id, user.id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    # Get user tier for data depth
    user_tier = getattr(user, 'tier', 'GOOD')
    
    try:
        item = service.create_stats_snapshot(db, protocol, user.id, user_tier)
        return schemas.SnapshotOut(
            item_id=item.id,
            type=item.type,
            summary=item.payload,
            created_at=item.created_at.isoformat() if item.created_at else ""
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# Helpers
# =============================================================================

def _protocol_to_out(protocol: Protocol) -> schemas.ProtocolOut:
    """Convert Protocol to ProtocolOut."""
    return schemas.ProtocolOut(
        id=protocol.id,
        sport=protocol.sport,
        title=protocol.title,
        status=protocol.status,
        context=protocol.context or {},
        created_at=protocol.created_at.isoformat() if protocol.created_at else "",
        updated_at=protocol.updated_at.isoformat() if protocol.updated_at else "",
        target_count=protocol.targets.count() if hasattr(protocol.targets, 'count') else len(list(protocol.targets)),
        item_count=protocol.items.count() if hasattr(protocol.items, 'count') else len(list(protocol.items))
    )


def _protocol_to_detail_out(protocol: Protocol) -> schemas.ProtocolDetailOut:
    """Convert Protocol to ProtocolDetailOut with targets and items."""
    targets = [
        schemas.ProtocolTargetOut(
            id=t.id,
            target_type=t.target_type,
            provider=t.provider,
            external_id=t.external_id,
            meta=t.meta or {},
            created_at=t.created_at.isoformat() if t.created_at else ""
        )
        for t in protocol.targets
    ]
    
    # Get 10 most recent items
    recent_items = [
        schemas.ProtocolItemOut(
            id=i.id,
            type=i.type,
            payload=i.payload or {},
            created_at=i.created_at.isoformat() if i.created_at else ""
        )
        for i in list(protocol.items)[:10]
    ]
    
    return schemas.ProtocolDetailOut(
        id=protocol.id,
        sport=protocol.sport,
        title=protocol.title,
        status=protocol.status,
        context=protocol.context or {},
        created_at=protocol.created_at.isoformat() if protocol.created_at else "",
        updated_at=protocol.updated_at.isoformat() if protocol.updated_at else "",
        target_count=len(targets),
        item_count=protocol.items.count() if hasattr(protocol.items, 'count') else len(list(protocol.items)),
        targets=targets,
        recent_items=recent_items
    )
