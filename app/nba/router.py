"""
NBA Data API Router

REST endpoints for protocols to access heuristics and analytics.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel

from app.nba.models import Base, DimTeam, DimGame
from app.nba.heuristics import NBAHeuristics, get_comprehensive_edge
from app.nba.cache import get_cache, NBACache
from app.nba.database import get_db_session

router = APIRouter(prefix="/api/nba", tags=["nba-analytics"])


# =============================================================================
# Response Models
# =============================================================================

class RestAdvantage(BaseModel):
    days_rest: int
    advantage_points: float
    fatigue_score: float
    games_in_7_days: int


class TankStatus(BaseModel):
    is_tanking: bool
    confidence: float
    signals: dict


class InjuryImpact(BaseModel):
    injured_players: list
    total_war_lost: float
    severity: str
    injury_count: int


class PlayoffContext(BaseModel):
    current_seed: Optional[int]
    games_back: Optional[float]
    clinch_number: Optional[int]
    elimination_number: Optional[int]
    position_battles: list
    leverage_index: float


class MatchupAnalysis(BaseModel):
    head_to_head: dict
    recent_form: dict
    style_clash: dict


class ComprehensiveEdge(BaseModel):
    """Full heuristics response for a matchup."""
    rest_advantage: dict
    tank_status: dict
    injury_impact: dict
    playoff_context: dict
    matchup_analysis: dict
    cached: bool = False
    cache_expires_in: Optional[int] = None


class TeamInfo(BaseModel):
    team_id: int
    abbreviation: str
    nickname: str
    city: str
    full_name: str


class GameInfo(BaseModel):
    game_id: str
    game_date: str
    home_team: str
    away_team: str
    status: str
    home_score: Optional[int]
    away_score: Optional[int]


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/teams", response_model=List[TeamInfo])
async def get_teams():
    """
    Get all NBA teams.
    
    Cached for 24h (teams don't change often).
    """
    cache = get_cache()
    cache_key = "teams:all"
    
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    db = get_db_session()
    try:
        teams = db.query(DimTeam).filter_by(active=True).all()
        result = [
            TeamInfo(
                team_id=t.team_id,
                abbreviation=t.abbreviation,
                nickname=t.nickname,
                city=t.city,
                full_name=t.full_name
            )
            for t in teams
        ]
        cache.set_historical(cache_key, result)
        return result
    finally:
        db.close()


@router.get("/games/today", response_model=List[GameInfo])
async def get_todays_games():
    """
    Get today's NBA games.
    
    Cached for 5 minutes.
    """
    cache = get_cache()
    today = date.today().isoformat()
    cache_key = f"games:date:{today}"
    
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    db = get_db_session()
    try:
        games = db.query(DimGame).filter(
            DimGame.game_date == date.today()
        ).all()
        
        result = []
        for g in games:
            home_team = db.query(DimTeam).filter_by(team_id=g.home_team_id).first()
            away_team = db.query(DimTeam).filter_by(team_id=g.away_team_id).first()
            
            result.append(GameInfo(
                game_id=g.game_id,
                game_date=g.game_date.isoformat(),
                home_team=home_team.abbreviation if home_team else str(g.home_team_id),
                away_team=away_team.abbreviation if away_team else str(g.away_team_id),
                status=g.status,
                home_score=g.home_score,
                away_score=g.away_score
            ))
        
        cache.set_fresh(cache_key, result)
        return result
    finally:
        db.close()


@router.get("/edge/{team_a_abbrev}/{team_b_abbrev}", response_model=ComprehensiveEdge)
async def get_edge(
    team_a_abbrev: str,
    team_b_abbrev: str,
    game_date: Optional[str] = Query(None, description="Game date (YYYY-MM-DD), defaults to today")
):
    """
    Get comprehensive edge analysis for a matchup.
    
    This is the main endpoint protocols will call.
    
    Returns:
    - Rest advantage
    - Tank status for both teams
    - Injury impact for both teams
    - Playoff context for both teams
    - Matchup analysis (H2H, recent form, style clash)
    """
    cache = get_cache()
    
    # Parse date
    if game_date:
        try:
            target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = date.today()
    
    db = get_db_session()
    try:
        # Look up teams
        team_a = db.query(DimTeam).filter_by(
            abbreviation=team_a_abbrev.upper()
        ).first()
        team_b = db.query(DimTeam).filter_by(
            abbreviation=team_b_abbrev.upper()
        ).first()
        
        if not team_a:
            raise HTTPException(404, f"Team not found: {team_a_abbrev}")
        if not team_b:
            raise HTTPException(404, f"Team not found: {team_b_abbrev}")
        
        # Check cache
        cache_key = NBACache.key_heuristics(
            team_a.team_id, 
            team_b.team_id, 
            target_date.isoformat()
        )
        
        cached = cache.get(cache_key)
        if cached:
            return ComprehensiveEdge(
                **cached,
                cached=True,
                cache_expires_in=300  # Approximate
            )
        
        # Calculate fresh
        season = f"{target_date.year}-{str(target_date.year + 1)[-2:]}"
        
        result = get_comprehensive_edge(
            db,
            team_a.team_id,
            team_b.team_id,
            target_date,
            season
        )
        
        # Cache it
        cache.set_fresh(cache_key, result)
        
        return ComprehensiveEdge(
            **result,
            cached=False
        )
    finally:
        db.close()


@router.get("/rest/{team_abbrev}")
async def get_rest_advantage(
    team_abbrev: str,
    game_date: Optional[str] = Query(None, description="Game date (YYYY-MM-DD)")
):
    """
    Get rest advantage for a single team.
    """
    if game_date:
        target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
    else:
        target_date = date.today()
    
    db = get_db_session()
    try:
        team = db.query(DimTeam).filter_by(
            abbreviation=team_abbrev.upper()
        ).first()
        
        if not team:
            raise HTTPException(404, f"Team not found: {team_abbrev}")
        
        heuristics = NBAHeuristics(db)
        return heuristics.calculate_rest_advantage(team.team_id, target_date)
    finally:
        db.close()


@router.get("/tank/{team_abbrev}")
async def get_tank_status(
    team_abbrev: str,
    game_date: Optional[str] = Query(None)
):
    """
    Get tank detection analysis for a team.
    """
    if game_date:
        target_date = datetime.strptime(game_date, "%Y-%m-%d").date()
    else:
        target_date = date.today()
    
    season = f"{target_date.year}-{str(target_date.year + 1)[-2:]}"
    
    db = get_db_session()
    try:
        team = db.query(DimTeam).filter_by(
            abbreviation=team_abbrev.upper()
        ).first()
        
        if not team:
            raise HTTPException(404, f"Team not found: {team_abbrev}")
        
        heuristics = NBAHeuristics(db)
        return heuristics.detect_tanking(team.team_id, season, target_date)
    finally:
        db.close()


@router.get("/injuries/{team_abbrev}")
async def get_injuries(
    team_abbrev: str
):
    """
    Get injury impact analysis for a team.
    """
    cache = get_cache()
    
    db = get_db_session()
    try:
        team = db.query(DimTeam).filter_by(
            abbreviation=team_abbrev.upper()
        ).first()
        
        if not team:
            raise HTTPException(404, f"Team not found: {team_abbrev}")
        
        cache_key = NBACache.key_injuries(team.team_id)
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        heuristics = NBAHeuristics(db)
        result = heuristics.calculate_injury_impact(team.team_id, date.today())
        
        cache.set_fresh(cache_key, result)
        return result
    finally:
        db.close()


@router.get("/standings/{team_abbrev}")
async def get_standings(
    team_abbrev: str
):
    """
    Get playoff context and standings for a team.
    """
    target_date = date.today()
    season = f"{target_date.year}-{str(target_date.year + 1)[-2:]}"
    
    db = get_db_session()
    try:
        team = db.query(DimTeam).filter_by(
            abbreviation=team_abbrev.upper()
        ).first()
        
        if not team:
            raise HTTPException(404, f"Team not found: {team_abbrev}")
        
        heuristics = NBAHeuristics(db)
        return heuristics.get_playoff_context(team.team_id, season, target_date)
    finally:
        db.close()


@router.get("/matchup/{team_a_abbrev}/{team_b_abbrev}")
async def get_matchup_history(
    team_a_abbrev: str,
    team_b_abbrev: str
):
    """
    Get matchup history and analysis between two teams.
    """
    target_date = date.today()
    season = f"{target_date.year}-{str(target_date.year + 1)[-2:]}"
    
    db = get_db_session()
    try:
        team_a = db.query(DimTeam).filter_by(
            abbreviation=team_a_abbrev.upper()
        ).first()
        team_b = db.query(DimTeam).filter_by(
            abbreviation=team_b_abbrev.upper()
        ).first()
        
        if not team_a:
            raise HTTPException(404, f"Team not found: {team_a_abbrev}")
        if not team_b:
            raise HTTPException(404, f"Team not found: {team_b_abbrev}")
        
        heuristics = NBAHeuristics(db)
        return heuristics.analyze_matchup(team_a.team_id, team_b.team_id, season)
    finally:
        db.close()


@router.get("/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics.
    
    Useful for monitoring and optimization.
    """
    cache = get_cache()
    return cache.get_stats()


@router.post("/cache/clear")
async def clear_cache():
    """
    Clear all cache entries.
    
    Use for debugging/testing.
    """
    cache = get_cache()
    count = cache.clear()
    return {"cleared": count}
