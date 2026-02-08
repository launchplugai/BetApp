"""
Mock API routes for S16 UI development.
Replace with real database queries as backend is built.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List

router = APIRouter(prefix="/api/mock", tags=["mock"])

from app.mock_data import MOCK_GAMES, MOCK_ODDS, MOCK_USER, SPORTS

@router.get("/sports")
async def get_sports():
    """Get all sports."""
    return {"sports": SPORTS}

@router.get("/games")
async def get_games(sport: Optional[str] = None, status: Optional[str] = None):
    """Get games filtered by sport and/or status."""
    games = []
    if sport and sport in MOCK_GAMES:
        games = MOCK_GAMES[sport]
    else:
        for sport_games in MOCK_GAMES.values():
            games.extend(sport_games)
    
    if status:
        games = [g for g in games if g["status"] == status]
    
    return {"games": games}

@router.get("/games/{game_id}")
async def get_game(game_id: str):
    """Get specific game details."""
    for sport_games in MOCK_GAMES.values():
        for game in sport_games:
            if game["id"] == game_id:
                return game
    raise HTTPException(status_code=404, detail="Game not found")

@router.get("/odds/{game_id}")
async def get_odds(game_id: str):
    """Get odds for a specific game."""
    if game_id in MOCK_ODDS:
        return {"game_id": game_id, "odds": MOCK_ODDS[game_id]}
    raise HTTPException(status_code=404, detail="Odds not found")

@router.post("/slip/calculate")
async def calculate_slip(legs: List[dict]):
    """Calculate parlay odds and payout."""
    # Simple calculation: convert American odds to decimal and multiply
    total_decimal = 1.0
    for leg in legs:
        odds = leg.get("odds", -110)
        if odds > 0:
            decimal = (odds / 100) + 1
        else:
            decimal = (100 / abs(odds)) + 1
        total_decimal *= decimal
    
    # Convert back to American
    if total_decimal > 2.0:
        total_odds = int((total_decimal - 1) * 100)
    else:
        total_odds = int(-100 / (total_decimal - 1))
    
    return {
        "legs": legs,
        "total_odds": total_odds,
        "total_decimal": round(total_decimal, 2)
    }

@router.get("/user/me")
async def get_current_user():
    """Get current user profile."""
    return MOCK_USER

@router.get("/user/bets")
async def get_user_bets(status: Optional[str] = None):
    """Get user's bets."""
    bets = MOCK_USER.get("active_bets", [])
    if status:
        bets = [b for b in bets if b["status"] == status]
    return {"bets": bets}

@router.get("/user/stats")
async def get_user_stats():
    """Get user statistics."""
    return {
        "win_rate": MOCK_USER["win_rate"],
        "total_bets": MOCK_USER["total_bets"],
        "balance": MOCK_USER["balance"]
    }
