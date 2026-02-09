"""
Dashboard API for S18-B.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.services.auth import get_current_user_from_token
from app.services.stats import get_user_stats, get_recent_bets
from app.services.protocol_tracker import tracker

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
security = HTTPBearer()


@router.get("/")
async def get_dashboard(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Get dashboard data for authenticated user.
    
    Returns:
        {
            user: {...},
            stats: {...},
            active_protocols: [...],
            recent_bets: [...]
        }
    """
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Get stats
    stats = get_user_stats(user.id)
    
    # Get recent bets
    recent_bets = get_recent_bets(user.id, limit=5)
    
    # Get active protocols (all for now, TODO: filter by user)
    active_protocols = tracker.list_active_protocols(max_age_hours=24)
    active_protocols_data = [
        {
            "protocol_id": p.protocol_id,
            "game_id": p.game_id,
            "league": p.league,
            "teams": p.teams,
            "status": p.current_score.status if p.current_score else "UNKNOWN",
            "created_at": p.created_at.isoformat()
        }
        for p in active_protocols[:3]  # Limit to 3
    ]
    
    return {
        "user": user.to_dict(),
        "stats": stats,
        "active_protocols": active_protocols_data,
        "recent_bets": recent_bets
    }
