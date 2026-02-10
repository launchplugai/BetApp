"""
Protocol Service - Business logic for protocols
"""

from sqlalchemy.orm import Session
from typing import Optional, List

from app.protocol.models import Protocol, ProtocolItem, ProtocolTarget


def create_protocol(
    db: Session,
    user_id: str,
    sport: str,
    title: str,
    context: dict,
    targets: Optional[List[dict]] = None
) -> Protocol:
    """
    Create a new protocol with optional targets.
    
    Args:
        db: Database session
        user_id: Owner user ID
        sport: Sport code (nba, nfl, etc.)
        title: Protocol title
        context: Configuration dict
        targets: Optional list of target dicts
        
    Returns:
        Created Protocol
    """
    protocol = Protocol(
        user_id=user_id,
        sport=sport,
        title=title,
        status="draft",
        context=context or {}
    )
    db.add(protocol)
    db.flush()  # Get protocol.id
    
    # Add targets if provided
    if targets:
        for t in targets:
            db.add(ProtocolTarget(
                protocol_id=protocol.id,
                target_type=t["target_type"],
                provider=t["provider"],
                external_id=t["external_id"],
                meta=t.get("meta", {})
            ))
    
    db.commit()
    db.refresh(protocol)
    return protocol


def create_stats_snapshot(
    db: Session,
    protocol: Protocol,
    user_id: str,
    user_tier: str = "GOOD"
) -> ProtocolItem:
    """
    Create a stats snapshot from NBA analytics system.
    
    Args:
        db: Database session
        protocol: Protocol to snapshot
        user_id: Requesting user (for permission check)
        user_tier: User tier (GOOD/BETTER/BEST) for data depth
        
    Returns:
        Created ProtocolItem
        
    Raises:
        PermissionError: If user doesn't own protocol
        ValueError: If no game target found for snapshot
    """
    if protocol.user_id != user_id:
        raise PermissionError("Not your protocol")
    
    # Find game target
    game_target = None
    for target in protocol.targets:
        if target.target_type == "game":
            game_target = target
            break
    
    if not game_target:
        raise ValueError("No game target found for snapshot")
    
    # Pull from NBA analytics system with tier-based depth
    snapshot = _get_protocol_snapshot(protocol, game_target, user_tier)
    
    item = ProtocolItem(
        protocol_id=protocol.id,
        type="stats_snapshot",
        payload=snapshot
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _get_protocol_snapshot(protocol: Protocol, game_target: ProtocolTarget, user_tier: str = "GOOD") -> dict:
    """
    Get snapshot data from NBA analytics system.
    
    Tier-based depth:
    - GOOD: Basic game info
    - BETTER: + team stats, recent form
    - BEST: + player stats, injuries, advanced metrics
    
    Phase 1-C: Implement actual NBA data pull
    """
    base = {
        "game_id": game_target.external_id,
        "provider": game_target.provider,
        "tier": user_tier,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if user_tier == "GOOD":
        base["data"] = {"level": "basic", "teams": [], "note": "Basic game info"}
    elif user_tier == "BETTER":
        base["data"] = {"level": "enhanced", "teams": [], "recent_form": {}, "note": "Team stats + form"}
    else:  # BEST
        base["data"] = {"level": "full", "teams": [], "players": [], "injuries": [], "advanced": {}, "note": "Full analytics"}
    
    return base


def get_user_protocols(
    db: Session,
    user_id: str,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Protocol]:
    """
    Get protocols for a user.
    
    Args:
        db: Database session
        user_id: User ID
        status: Optional status filter
        limit: Max results
        
    Returns:
        List of Protocols
    """
    query = db.query(Protocol).filter(Protocol.user_id == user_id)
    
    if status:
        query = query.filter(Protocol.status == status)
    
    return query.order_by(Protocol.updated_at.desc()).limit(limit).all()


def get_protocol_detail(
    db: Session,
    protocol_id: str,
    user_id: str
) -> Optional[Protocol]:
    """
    Get protocol detail with permission check.
    
    Args:
        db: Database session
        protocol_id: Protocol ID
        user_id: Requesting user
        
    Returns:
        Protocol or None if not found/not owned
    """
    return db.query(Protocol).filter(
        Protocol.id == protocol_id,
        Protocol.user_id == user_id
    ).first()


def update_protocol(
    db: Session,
    protocol: Protocol,
    title: Optional[str] = None,
    status: Optional[str] = None,
    context: Optional[dict] = None
) -> Protocol:
    """
    Update protocol fields.
    
    Args:
        db: Database session
        protocol: Protocol to update
        title: New title (optional)
        status: New status (optional)
        context: Context updates (optional, merged)
        
    Returns:
        Updated Protocol
    """
    if title is not None:
        protocol.title = title
    
    if status is not None:
        protocol.status = status
    
    if context is not None:
        # Merge context updates
        current = protocol.context or {}
        current.update(context)
        protocol.context = current
    
    db.commit()
    db.refresh(protocol)
    return protocol


def archive_protocol(db: Session, protocol: Protocol) -> None:
    """
    Archive (soft delete) a protocol.
    
    Args:
        db: Database session
        protocol: Protocol to archive
    """
    protocol.status = "archived"
    db.commit()
