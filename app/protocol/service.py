"""
Protocol Service - Business logic for protocols
"""

from sqlalchemy.orm import Session
from typing import Optional, List

from app.protocol.models import Protocol, ProtocolItem, ProtocolTarget
from app.protocol.sports_integration import get_protocol_snapshot, generate_natural_language_summary


def create_protocol(
    db: Session,
    user_id: str,
    sport: str,
    title: str,
    context: dict,
    targets: Optional[List[dict]] = None,
    description: Optional[str] = None,
    rules: Optional[list] = None,
    visibility: str = "private"
) -> Protocol:
    """
    Create a new protocol with optional targets.
    """
    protocol = Protocol(
        user_id=user_id,
        sport=sport,
        title=title,
        description=description,
        status="draft",
        rules=rules or [],
        visibility=visibility,
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
    """
    return get_protocol_snapshot(protocol, user_tier)


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
    description: Optional[str] = None,
    status: Optional[str] = None,
    rules: Optional[list] = None,
    enabled: Optional[bool] = None,
    visibility: Optional[str] = None,
    context: Optional[dict] = None
) -> Protocol:
    """Update protocol fields."""
    if title is not None:
        protocol.title = title

    if description is not None:
        protocol.description = description

    if status is not None:
        protocol.status = status

    if rules is not None:
        protocol.rules = rules

    if enabled is not None:
        protocol.enabled = enabled

    if visibility is not None:
        protocol.visibility = visibility

    if context is not None:
        current = protocol.context or {}
        current.update(context)
        protocol.context = current

    db.commit()
    db.refresh(protocol)
    return protocol


def archive_protocol(db: Session, protocol: Protocol) -> None:
    """Archive (soft delete) a protocol."""
    protocol.status = "archived"
    db.commit()


def generate_protocol_feed(
    db: Session,
    protocol: Protocol,
    limit: int = 20
) -> list:
    """
    Generate protocol feed - match protocol rules against available games.

    Returns a list of FeedCandidate-shaped dicts. Currently returns candidates
    from protocol targets; will be enriched with rule-based matching as
    the odds/games APIs mature.
    """
    candidates = []
    rules = protocol.rules or []

    for target in list(protocol.targets)[:limit]:
        if target.target_type == "game":
            matched_rule_names = [r.get("name", "unnamed") for r in rules]
            candidates.append({
                "game_id": target.external_id,
                "sport": protocol.sport,
                "match_reason": f"Game target in protocol '{protocol.title}'",
                "suggested_legs": [],
                "alignment_score": 1.0 if not rules else 0.5,
                "matched_rules": matched_rule_names,
                "action_payload": {
                    "protocol_id": protocol.id,
                    "game_id": target.external_id,
                    "sport": protocol.sport,
                }
            })

    return candidates


def generate_snapshot_v2(db: Session, protocol: Protocol) -> dict:
    """
    Generate snapshot v2 - performance summary, rule hit rates, top drivers.
    """
    items = list(protocol.items)[:50]
    snapshots = [i for i in items if i.type == "stats_snapshot"]

    rule_names = [r.get("name", "unnamed") for r in (protocol.rules or [])]
    rule_hits = {name: 0.0 for name in rule_names}

    recent_matches = []
    for snap in snapshots[:10]:
        payload = snap.payload or {}
        recent_matches.append({
            "item_id": snap.id,
            "created_at": snap.created_at.isoformat() if snap.created_at else "",
            "summary": payload.get("summary", {}),
        })
        for rule_name in payload.get("matched_rules", []):
            if rule_name in rule_hits:
                rule_hits[rule_name] += 1

    total = len(snapshots) or 1
    rule_hit_rates = {k: round(v / total, 2) for k, v in rule_hits.items()}
    top_drivers = list(rule_hits.keys())[:5]

    return {
        "recent_matches": recent_matches,
        "performance": {
            "total_snapshots": len(snapshots),
            "total_items": len(items),
            "sport": protocol.sport,
        },
        "rule_hit_rates": rule_hit_rates,
        "top_drivers": top_drivers,
    }
