"""
Protocol API endpoints for S17.
Manage tracked protocols (create, get, refresh, delete).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.protocol_tracker import tracker
from app.services.suggestion_engine import suggestion_engine, DNASuggestion
from app.providers import ProviderFactory

router = APIRouter(prefix="/api/protocols", tags=["protocols"])


class CreateProtocolRequest(BaseModel):
    """Request to create a protocol."""
    game_id: str
    league: str
    teams: List[str]
    markets_watched: List[str]
    legs: Optional[List[dict]] = None


class ProtocolResponse(BaseModel):
    """Protocol response."""
    protocol_id: str
    game_id: str
    league: str
    teams: List[str]
    created_at: str
    last_updated: str
    markets_watched: List[str]
    current_odds: Optional[dict] = None
    current_score: Optional[dict] = None
    legs_snapshot: Optional[List[dict]] = None


@router.post("/create", response_model=ProtocolResponse)
async def create_protocol(request: CreateProtocolRequest):
    """
    Create a new tracked protocol.
    
    Called when user enters builder screen.
    """
    protocol = tracker.create_protocol(
        game_id=request.game_id,
        league=request.league,
        teams=request.teams,
        markets_watched=request.markets_watched,
        legs=request.legs
    )
    
    return ProtocolResponse(
        protocol_id=protocol.protocol_id,
        game_id=protocol.game_id,
        league=protocol.league,
        teams=protocol.teams,
        created_at=protocol.created_at.isoformat(),
        last_updated=protocol.last_updated.isoformat(),
        markets_watched=protocol.markets_watched,
        legs_snapshot=protocol.legs_snapshot
    )


@router.get("/{protocol_id}", response_model=ProtocolResponse)
async def get_protocol(protocol_id: str):
    """Get protocol by ID."""
    protocol = tracker.get_protocol(protocol_id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    return ProtocolResponse(
        protocol_id=protocol.protocol_id,
        game_id=protocol.game_id,
        league=protocol.league,
        teams=protocol.teams,
        created_at=protocol.created_at.isoformat(),
        last_updated=protocol.last_updated.isoformat(),
        markets_watched=protocol.markets_watched,
        current_odds=protocol.current_odds.model_dump() if protocol.current_odds else None,
        current_score=protocol.current_score.model_dump() if protocol.current_score else None,
        legs_snapshot=protocol.legs_snapshot
    )


@router.get("/", response_model=List[ProtocolResponse])
async def list_active_protocols(max_age_hours: int = 24):
    """List all active protocols."""
    protocols = tracker.list_active_protocols(max_age_hours)
    
    return [
        ProtocolResponse(
            protocol_id=p.protocol_id,
            game_id=p.game_id,
            league=p.league,
            teams=p.teams,
            created_at=p.created_at.isoformat(),
            last_updated=p.last_updated.isoformat(),
            markets_watched=p.markets_watched,
            current_odds=p.current_odds.model_dump() if p.current_odds else None,
            current_score=p.current_score.model_dump() if p.current_score else None,
            legs_snapshot=p.legs_snapshot
        )
        for p in protocols
    ]


@router.post("/{protocol_id}/refresh", response_model=ProtocolResponse)
async def refresh_protocol(protocol_id: str):
    """
    Refresh odds and score for a protocol.
    
    Fetches latest data from providers and generates suggestions.
    """
    protocol = tracker.get_protocol(protocol_id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    old_odds = protocol.current_odds
    old_score = protocol.current_score
    
    # Refresh odds
    if "spread" in protocol.markets_watched or "total" in protocol.markets_watched:
        odds_provider = ProviderFactory.get_odds_provider("mock")
        try:
            new_odds = await odds_provider.get_odds(protocol.game_id)
            tracker.update_odds(protocol_id, new_odds)
            
            # Analyze odds changes
            suggestion_engine.analyze_odds_change(protocol_id, old_odds, new_odds)
        except Exception as e:
            print(f"Failed to refresh odds: {e}")
    
    # Refresh score
    score_provider = ProviderFactory.get_score_provider("mock")
    try:
        new_score = await score_provider.get_score(protocol.game_id)
        tracker.update_score(protocol_id, new_score)
        
        # Analyze score changes
        suggestion_engine.analyze_score_change(protocol_id, old_score, new_score)
    except Exception as e:
        print(f"Failed to refresh score: {e}")
    
    # Get updated protocol
    protocol = tracker.get_protocol(protocol_id)
    
    return ProtocolResponse(
        protocol_id=protocol.protocol_id,
        game_id=protocol.game_id,
        league=protocol.league,
        teams=protocol.teams,
        created_at=protocol.created_at.isoformat(),
        last_updated=protocol.last_updated.isoformat(),
        markets_watched=protocol.markets_watched,
        current_odds=protocol.current_odds.model_dump() if protocol.current_odds else None,
        current_score=protocol.current_score.model_dump() if protocol.current_score else None,
        legs_snapshot=protocol.legs_snapshot
    )


@router.delete("/{protocol_id}")
async def delete_protocol(protocol_id: str):
    """Delete a protocol."""
    success = tracker.delete_protocol(protocol_id)
    if not success:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    return {"status": "deleted", "protocol_id": protocol_id}


@router.get("/stats/summary")
async def get_stats():
    """Get tracker statistics."""
    return tracker.get_stats()


@router.post("/cleanup")
async def cleanup_expired(max_age_hours: int = 24):
    """Manually trigger cleanup of expired protocols."""
    expired_count = tracker.expire_old_protocols(max_age_hours)
    return {"expired_count": expired_count, "max_age_hours": max_age_hours}


# S17-C: Suggestion Endpoints

@router.get("/{protocol_id}/suggestions")
async def get_suggestions(protocol_id: str, unacknowledged_only: bool = False):
    """
    Get suggestions for a protocol.
    
    Args:
        protocol_id: Protocol ID
        unacknowledged_only: If true, only return unacknowledged suggestions
    """
    # Verify protocol exists
    protocol = tracker.get_protocol(protocol_id)
    if not protocol:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    suggestions = suggestion_engine.get_suggestions(protocol_id, unacknowledged_only)
    
    return {
        "protocol_id": protocol_id,
        "suggestions": [s.model_dump() for s in suggestions],
        "count": len(suggestions)
    }


@router.post("/suggestions/{suggestion_id}/acknowledge")
async def acknowledge_suggestion(suggestion_id: str):
    """
    Acknowledge (dismiss) a suggestion.
    
    User has seen and acted on (or ignored) the suggestion.
    """
    success = suggestion_engine.acknowledge_suggestion(suggestion_id)
    if not success:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    return {"status": "acknowledged", "suggestion_id": suggestion_id}
