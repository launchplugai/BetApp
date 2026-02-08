"""
Mock provider implementation for development and testing.
Returns data from mock_data.py with simulated latency.
"""

import asyncio
from datetime import datetime
from typing import List, Optional

from app.providers.base import (
    OddsProvider, ScoreProvider,
    OddsResponse, ScoreResponse,
    MarketsData, MarketLine, PlayerProp,
    ScoreData
)
from app.mock_data import MOCK_GAMES, MOCK_ODDS


class MockOddsProvider(OddsProvider):
    """
    Mock odds provider using in-memory data.
    Simulates realistic API latency (50-200ms).
    """
    
    def __init__(self, latency_ms: int = 100):
        self.latency_ms = latency_ms
    
    @property
    def source_name(self) -> str:
        return "mock"
    
    async def get_odds(self, game_id: str) -> OddsResponse:
        """Get odds for a single game."""
        # Simulate network latency
        await asyncio.sleep(self.latency_ms / 1000)
        
        if game_id not in MOCK_ODDS:
            raise ValueError(f"Game {game_id} not found in mock data")
        
        raw_odds = MOCK_ODDS[game_id]
        markets = self._normalize_markets(raw_odds)
        
        return OddsResponse(
            game_id=game_id,
            timestamp=datetime.utcnow(),
            markets=markets
        )
    
    async def get_odds_batch(self, game_ids: List[str]) -> List[OddsResponse]:
        """Get odds for multiple games."""
        results = []
        for game_id in game_ids:
            try:
                odds = await self.get_odds(game_id)
                results.append(odds)
            except ValueError:
                continue
        return results
    
    def _normalize_markets(self, raw_odds: dict) -> MarketsData:
        """Convert raw mock data to standardized MarketsData."""
        markets = MarketsData()
        
        # Spread
        if "spread" in raw_odds:
            markets.spread = {
                "home": MarketLine(
                    line=raw_odds["spread"]["home"]["line"],
                    odds=raw_odds["spread"]["home"]["odds"]
                ),
                "away": MarketLine(
                    line=raw_odds["spread"]["away"]["line"],
                    odds=raw_odds["spread"]["away"]["odds"]
                )
            }
        
        # Total
        if "total" in raw_odds:
            markets.total = {
                "over": MarketLine(
                    line=raw_odds["total"]["over"]["line"],
                    odds=raw_odds["total"]["over"]["odds"]
                ),
                "under": MarketLine(
                    line=raw_odds["total"]["under"]["line"],
                    odds=raw_odds["total"]["under"]["odds"]
                )
            }
        
        # Moneyline
        if "moneyline" in raw_odds:
            markets.moneyline = {
                "home": {"odds": raw_odds["moneyline"]["home"]["odds"]},
                "away": {"odds": raw_odds["moneyline"]["away"]["odds"]}
            }
        
        # Player Props
        if "player_props" in raw_odds:
            markets.player_props = [
                PlayerProp(
                    player=p["player"],
                    prop=p["prop"],
                    line=p["line"],
                    over_odds=p["over_odds"],
                    under_odds=p["under_odds"]
                )
                for p in raw_odds["player_props"]
            ]
        
        return markets


class MockScoreProvider(ScoreProvider):
    """
    Mock score provider using in-memory data.
    Simulates realistic API latency (50-200ms).
    """
    
    def __init__(self, latency_ms: int = 80):
        self.latency_ms = latency_ms
    
    @property
    def source_name(self) -> str:
        return "mock"
    
    async def get_score(self, game_id: str) -> ScoreResponse:
        """Get score for a single game."""
        await asyncio.sleep(self.latency_ms / 1000)
        
        # Find game in mock data
        game = self._find_game(game_id)
        if not game:
            raise ValueError(f"Game {game_id} not found")
        
        return self._normalize_score(game_id, game)
    
    async def get_scores_batch(self, game_ids: List[str]) -> List[ScoreResponse]:
        """Get scores for multiple games."""
        results = []
        for game_id in game_ids:
            try:
                score = await self.get_score(game_id)
                results.append(score)
            except ValueError:
                continue
        return results
    
    def _find_game(self, game_id: str) -> Optional[dict]:
        """Find game in mock data by ID."""
        for sport, games in MOCK_GAMES.items():
            for game in games:
                if game["id"] == game_id:
                    return game
        return None
    
    def _normalize_score(self, game_id: str, game: dict) -> ScoreResponse:
        """Convert raw game data to ScoreResponse."""
        status = game.get("status", "UPCOMING").upper()
        
        # Build clock string
        clock = None
        if status == "LIVE":
            if game.get("quarter"):
                clock = f"Q{game['quarter']} {game.get('time_remaining', '')}"
            elif game.get("period"):
                clock = f"{game['period']} {game.get('time_remaining', '')}"
        
        # Build score
        score = None
        if game.get("home_score") is not None and game.get("away_score") is not None:
            score = ScoreData(
                home=game["home_score"],
                away=game["away_score"]
            )
        
        return ScoreResponse(
            game_id=game_id,
            status=status,
            clock=clock,
            score=score,
            quarter=game.get("quarter"),
            period=game.get("period")
        )
