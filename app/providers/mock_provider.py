"""
S19-A: Mock Provider Implementation

Returns hardcoded mock data in normalized canonical format.
Preserves existing mock data behavior.
"""

from typing import List, Optional
from datetime import datetime, timedelta

from app.providers import (
    OddsProvider,
    ScoreProvider,
    Sport,
    Game,
    MarketOdds,
    Selection,
    LiveScore
)


class MockOddsProvider(OddsProvider):
    """Mock odds provider with hardcoded data."""
    
    def get_sports(self) -> List[Sport]:
        """Return available sports (mock data)."""
        return [
            Sport(id="NBA", label="NBA", active=True),
            Sport(id="NFL", label="NFL", active=True),
            Sport(id="NHL", label="NHL", active=True),
            Sport(id="MLB", label="MLB", active=False),
            Sport(id="SOCCER", label="Soccer", active=False),
        ]
    
    def get_games(self, sport: str) -> List[Game]:
        """Return mock games for a sport."""
        if sport.upper() == "NBA":
            return self._get_nba_games()
        elif sport.upper() == "NFL":
            return self._get_nfl_games()
        elif sport.upper() == "NHL":
            return self._get_nhl_games()
        else:
            return []
    
    def get_odds(self, game_id: str) -> List[MarketOdds]:
        """Return mock odds for a game."""
        # Basic odds for any game
        if "nba" in game_id.lower() or "lal" in game_id.lower():
            return self._get_nba_odds()
        elif "nfl" in game_id.lower() or "chiefs" in game_id.lower():
            return self._get_nfl_odds()
        elif "nhl" in game_id.lower():
            return self._get_nhl_odds()
        else:
            return []
    
    def _get_nba_games(self) -> List[Game]:
        """Mock NBA games."""
        now = datetime.utcnow()
        
        return [
            Game(
                id="lal-gsw-2026-02-09",
                league="NBA",
                home="Lakers",
                away="Warriors",
                start_time=(now + timedelta(hours=2)).isoformat() + "Z",
                status="SCHEDULED"
            ),
            Game(
                id="mia-bos-2026-02-09",
                league="NBA",
                home="Heat",
                away="Celtics",
                start_time=(now + timedelta(hours=4)).isoformat() + "Z",
                status="SCHEDULED"
            ),
            Game(
                id="dal-phx-2026-02-09",
                league="NBA",
                home="Mavericks",
                away="Suns",
                start_time=(now + timedelta(hours=5)).isoformat() + "Z",
                status="SCHEDULED"
            ),
        ]
    
    def _get_nfl_games(self) -> List[Game]:
        """Mock NFL games."""
        now = datetime.utcnow()
        
        return [
            Game(
                id="chiefs-bills-2026-02-09",
                league="NFL",
                home="Chiefs",
                away="Bills",
                start_time=(now + timedelta(hours=3)).isoformat() + "Z",
                status="SCHEDULED"
            ),
        ]
    
    def _get_nhl_games(self) -> List[Game]:
        """Mock NHL games."""
        now = datetime.utcnow()
        
        return [
            Game(
                id="tor-mtl-2026-02-09",
                league="NHL",
                home="Maple Leafs",
                away="Canadiens",
                start_time=(now + timedelta(hours=6)).isoformat() + "Z",
                status="SCHEDULED"
            ),
        ]
    
    def _get_nba_odds(self) -> List[MarketOdds]:
        """Mock NBA odds including player props."""
        return [
            MarketOdds(
                market="spread",
                selections=[
                    Selection(label="Lakers -4.5", line=-4.5, odds=-110),
                    Selection(label="Warriors +4.5", line=4.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="total",
                selections=[
                    Selection(label="Over 220.5", line=220.5, odds=-110),
                    Selection(label="Under 220.5", line=220.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="moneyline",
                selections=[
                    Selection(label="Lakers ML", line=None, odds=-180),
                    Selection(label="Warriors ML", line=None, odds=+150),
                ]
            ),
            MarketOdds(
                market="player_prop",
                selections=[
                    Selection(label="LeBron James O27.5 PTS", line=27.5, odds=-110),
                    Selection(label="LeBron James U27.5 PTS", line=27.5, odds=-110),
                    Selection(label="Anthony Davis O23.5 PTS", line=23.5, odds=-110),
                    Selection(label="Anthony Davis U23.5 PTS", line=23.5, odds=-110),
                    Selection(label="Stephen Curry O28.5 PTS", line=28.5, odds=-110),
                    Selection(label="Stephen Curry U28.5 PTS", line=28.5, odds=-110),
                    Selection(label="LeBron James O8.5 AST", line=8.5, odds=-115),
                    Selection(label="LeBron James U8.5 AST", line=8.5, odds=-105),
                    Selection(label="Anthony Davis O10.5 REB", line=10.5, odds=-120),
                    Selection(label="Anthony Davis U10.5 REB", line=10.5, odds=+100),
                    Selection(label="Stephen Curry O4.5 3PM", line=4.5, odds=-130),
                    Selection(label="Stephen Curry U4.5 3PM", line=4.5, odds=+110),
                ]
            ),
        ]
    
    def _get_nfl_odds(self) -> List[MarketOdds]:
        """Mock NFL odds."""
        return [
            MarketOdds(
                market="spread",
                selections=[
                    Selection(label="Chiefs -3.0", line=-3.0, odds=-110),
                    Selection(label="Bills +3.0", line=3.0, odds=-110),
                ]
            ),
            MarketOdds(
                market="total",
                selections=[
                    Selection(label="Over 48.5", line=48.5, odds=-110),
                    Selection(label="Under 48.5", line=48.5, odds=-110),
                ]
            ),
            MarketOdds(
                market="moneyline",
                selections=[
                    Selection(label="Chiefs ML", line=None, odds=-150),
                    Selection(label="Bills ML", line=None, odds=+130),
                ]
            ),
        ]
    
    def _get_nhl_odds(self) -> List[MarketOdds]:
        """Mock NHL odds."""
        return [
            MarketOdds(
                market="puck_line",
                selections=[
                    Selection(label="Maple Leafs -1.5", line=-1.5, odds=+140),
                    Selection(label="Canadiens +1.5", line=1.5, odds=-170),
                ]
            ),
            MarketOdds(
                market="total",
                selections=[
                    Selection(label="Over 6.5", line=6.5, odds=-115),
                    Selection(label="Under 6.5", line=6.5, odds=-105),
                ]
            ),
            MarketOdds(
                market="moneyline",
                selections=[
                    Selection(label="Maple Leafs ML", line=None, odds=-130),
                    Selection(label="Canadiens ML", line=None, odds=+110),
                ]
            ),
        ]


class MockScoreProvider(ScoreProvider):
    """Mock score provider with live game simulation."""
    
    def get_score(self, game_id: str) -> Optional[LiveScore]:
        """Return mock live score."""
        # Only return score for "live" games (mock simulation)
        if "lal" in game_id.lower():
            return LiveScore(
                game_id=game_id,
                home_score=102,
                away_score=98,
                period="4th",
                clock="5:23",
                status="LIVE"
            )
        
        # Return None for games that aren't "live"
        return None
