"""
Mock API routes for S16 UI development.
Replace with real database queries as backend is built.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List

from app.providers import ProviderFactory

router = APIRouter(prefix="/api/mock", tags=["mock"])

from app.mock_data import MOCK_GAMES, MOCK_ODDS, MOCK_USER, SPORTS, MOCK_PROTOCOLS

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
    """Get odds for a specific game using provider."""
    provider = ProviderFactory.get_odds_provider("mock")
    try:
        odds = await provider.get_odds(game_id)
        return {"game_id": game_id, "odds": MOCK_ODDS[game_id], "normalized": odds.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/scores/{game_id}")
async def get_score(game_id: str):
    """Get live score for a specific game."""
    provider = ProviderFactory.get_score_provider("mock")
    try:
        score = await provider.get_score(game_id)
        return score.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

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


# S16: Protocol endpoints

@router.get("/protocols/available")
async def get_available_protocols(league: Optional[str] = None):
    """Get available protocols for event selection.
    
    Returns ProtocolContext objects for games available to bet on.
    """
    protocols = []
    
    if league and league.lower() in MOCK_PROTOCOLS:
        protocols = MOCK_PROTOCOLS[league.lower()]
    else:
        # Return all protocols if no league specified
        for league_protocols in MOCK_PROTOCOLS.values():
            protocols.extend(league_protocols)
    
    return {
        "protocols": protocols,
        "count": len(protocols),
        "league": league
    }


@router.get("/protocols/{protocol_id}")
async def get_protocol(protocol_id: str):
    """Get specific protocol by ID."""
    for league_protocols in MOCK_PROTOCOLS.values():
        for protocol in league_protocols:
            if protocol["protocolId"] == protocol_id:
                return protocol
    raise HTTPException(status_code=404, detail="Protocol not found")


@router.get("/markets/{game_id}")
async def get_markets(game_id: str):
    """Get betting markets for a specific game.
    
    Used by parlay builder to display available bets.
    """
    # Map game_id to odds key
    odds_key = None
    for sport, games in MOCK_GAMES.items():
        for game in games:
            if game["id"] == game_id:
                odds_key = game_id
                break
    
    if not odds_key or odds_key not in MOCK_ODDS:
        raise HTTPException(status_code=404, detail="Markets not found")
    
    return {
        "game_id": game_id,
        "markets": MOCK_ODDS[odds_key]
    }
