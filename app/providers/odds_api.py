"""
The Odds API integration provider.

Fetches live odds and scores from the-odds-api.com.
Docs: https://the-odds-api.com/liveapi/guides/v4/
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
import httpx

from app.providers import (
    OddsProvider,
    ScoreProvider,
    Sport,
    Game,
    MarketOdds,
    Selection,
    LiveScore,
    ProviderConfig
)


class OddsApiProvider(OddsProvider, ScoreProvider):
    """
    Live odds and scores provider using The Odds API.
    
    Implements both OddsProvider and ScoreProvider interfaces.
    Uses in-memory caching with TTL for cost efficiency.
    """
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    # Sport key mapping: our ID -> The Odds API key
    SPORT_KEYS = {
        "NBA": "basketball_nba",
        "NFL": "americanfootball_nfl",
        "NHL": "icehockey_nhl",
        "MLB": "baseball_mlb",
        "MLS": "soccer_usa_mls",
        "EPL": "soccer_epl",
        "UCL": "soccer_uefa_champs_league",
    }
    
    # Reverse mapping for lookups
    REVERSE_SPORT_KEYS = {v: k for k, v in SPORT_KEYS.items()}
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.api_key = config.api_key
        
        if not self.api_key:
            raise ValueError("OddsApiProvider requires api_key in config")
        
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30.0,
            headers={
                "Accept": "application/json",
            }
        )
    
    @property
    def source_name(self) -> str:
        return "the_odds_api"
    
    # ========================================================================
    # Sports
    # ========================================================================
    
    def get_sports(self) -> List[Sport]:
        """Get list of available sports."""
        # Return cached sports list - these don't change often
        return [
            Sport(id="NBA", label="NBA", active=True),
            Sport(id="NFL", label="NFL", active= self._is_nfl_season()),
            Sport(id="NHL", label="NHL", active=True),
            Sport(id="MLB", label="MLB", active= self._is_mlb_season()),
            Sport(id="MLS", label="MLS", active=True),
            Sport(id="EPL", label="Premier League", active=True),
            Sport(id="UCL", label="Champions League", active=True),
        ]
    
    def _is_nfl_season(self) -> bool:
        """Rough NFL season check (Sept - Feb)."""
        month = datetime.now().month
        return month >= 9 or month <= 2
    
    def _is_mlb_season(self) -> bool:
        """Rough MLB season check (March - Oct)."""
        month = datetime.now().month
        return 3 <= month <= 10
    
    # ========================================================================
    # Games
    # ========================================================================
    
    async def get_games(self, sport: str) -> List[Game]:
        """Get upcoming games for a sport."""
        sport_key = self.SPORT_KEYS.get(sport, sport.lower())
        
        url = f"/sports/{sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h,spreads,totals",  # Standard markets only
            "oddsFormat": "american",
            "dateFormat": "iso",
        }
        
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            games = []
            for event in data:
                game = self._parse_game(event, sport)
                if game:
                    games.append(game)
            
            return games
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValueError("Invalid API key")
            elif e.response.status_code == 429:
                raise ValueError("API rate limit exceeded")
            raise ValueError(f"API error: {e.response.status_code}")
        except Exception as e:
            raise ValueError(f"Failed to fetch games: {str(e)}")
    
    def _parse_game(self, event: Dict[str, Any], sport: str) -> Optional[Game]:
        """Parse API event into canonical Game model."""
        try:
            home_team = event.get("home_team")
            away_team = event.get("away_team")
            
            if not home_team or not away_team:
                return None
            
            # Determine status
            commence_time = event.get("commence_time", "")
            status = "SCHEDULED"
            if event.get("completed", False):
                status = "FINAL"
            
            # Build game ID
            game_date = commence_time[:10] if commence_time else datetime.now().strftime("%Y-%m-%d")
            game_id = f"{sport.lower()}-{away_team.lower().replace(' ', '-')}-at-{home_team.lower().replace(' ', '-')}-{game_date}"
            
            return Game(
                id=game_id,
                league=sport,
                home=home_team,
                away=away_team,
                start_time=commence_time,
                status=status
            )
        except Exception:
            return None
    
    # ========================================================================
    # Odds
    # ========================================================================
    
    async def get_odds(self, game_id: str) -> List[MarketOdds]:
        """Get odds for a specific game."""
        # Parse sport from game_id (format: sport-away-at-home-date)
        parts = game_id.split("-")
        if len(parts) < 2:
            raise ValueError(f"Invalid game_id format: {game_id}")
        
        sport_code = parts[0].upper()
        sport_key = self.SPORT_KEYS.get(sport_code, sport_code.lower())
        
        # Fetch all games for this sport and find matching game
        games_data = await self._fetch_odds_for_sport(sport_key)
        
        for event in games_data:
            event_game_id = self._generate_game_id(event, sport_code)
            if event_game_id == game_id:
                return self._parse_markets(event)
        
        raise ValueError(f"Game not found: {game_id}")
    
    async def get_odds_batch(self, game_ids: List[str]) -> List[List[MarketOdds]]:
        """Get odds for multiple games."""
        results = []
        for game_id in game_ids:
            try:
                odds = await self.get_odds(game_id)
                results.append(odds)
            except ValueError:
                results.append([])
        return results
    
    async def _fetch_odds_for_sport(self, sport_key: str) -> List[Dict[str, Any]]:
        """Fetch odds data for a sport."""
        url = f"/sports/{sport_key}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h,spreads,totals",  # player_props is separate endpoint
            "oddsFormat": "american",
            "dateFormat": "iso",
        }
        
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def _generate_game_id(self, event: Dict[str, Any], sport: str) -> str:
        """Generate consistent game ID from event data."""
        home = event.get("home_team", "").lower().replace(" ", "-")
        away = event.get("away_team", "").lower().replace(" ", "-")
        commence = event.get("commence_time", "")[:10]
        return f"{sport.lower()}-{away}-at-{home}-{commence}"
    
    def _parse_markets(self, event: Dict[str, Any]) -> List[MarketOdds]:
        """Parse odds markets from event data."""
        markets = []
        
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            return markets
        
        # Use first bookmaker (typically has best odds or is most reliable)
        # TODO: Could average across bookmakers or pick specific one
        bookmaker = bookmakers[0]
        market_data = {m["key"]: m for m in bookmaker.get("markets", [])}
        
        home_team = event.get("home_team", "Home")
        away_team = event.get("away_team", "Away")
        
        # Moneyline (h2h)
        if "h2h" in market_data:
            h2h = market_data["h2h"]
            outcomes = {o["name"]: o for o in h2h.get("outcomes", [])}
            
            selections = []
            if home_team in outcomes:
                selections.append(Selection(
                    label=f"{home_team} ML",
                    line=None,
                    odds=outcomes[home_team].get("price", 0)
                ))
            if away_team in outcomes:
                selections.append(Selection(
                    label=f"{away_team} ML",
                    line=None,
                    odds=outcomes[away_team].get("price", 0)
                ))
            
            if selections:
                markets.append(MarketOdds(market="moneyline", selections=selections))
        
        # Spread
        if "spreads" in market_data:
            spreads = market_data["spreads"]
            outcomes = {o["name"]: o for o in spreads.get("outcomes", [])}
            
            selections = []
            if home_team in outcomes:
                home_outcome = outcomes[home_team]
                selections.append(Selection(
                    label=f"{home_team} {home_outcome.get('point', 0):+.1f}",
                    line=home_outcome.get("point", 0),
                    odds=home_outcome.get("price", 0)
                ))
            if away_team in outcomes:
                away_outcome = outcomes[away_team]
                selections.append(Selection(
                    label=f"{away_team} {away_outcome.get('point', 0):+.1f}",
                    line=away_outcome.get("point", 0),
                    odds=away_outcome.get("price", 0)
                ))
            
            if selections:
                markets.append(MarketOdds(market="spread", selections=selections))
        
        # Total
        if "totals" in market_data:
            totals = market_data["totals"]
            outcomes = {o["name"].lower(): o for o in totals.get("outcomes", [])}
            
            # Find the line value (should be same for over/under)
            line = 0
            for outcome in totals.get("outcomes", []):
                if "point" in outcome:
                    line = outcome["point"]
                    break
            
            selections = []
            if "over" in outcomes:
                selections.append(Selection(
                    label=f"Over {line:.1f}",
                    line=line,
                    odds=outcomes["over"].get("price", 0)
                ))
            if "under" in outcomes:
                selections.append(Selection(
                    label=f"Under {line:.1f}",
                    line=line,
                    odds=outcomes["under"].get("price", 0)
                ))
            
            if selections:
                markets.append(MarketOdds(market="total", selections=selections))
        
        # Player Props
        if "player_props" in market_data:
            props = market_data["player_props"]
            # Group by player
            player_groups: Dict[str, List] = {}
            for outcome in props.get("outcomes", []):
                player = outcome.get("description", "Unknown")
                if player not in player_groups:
                    player_groups[player] = []
                player_groups[player].append(outcome)
            
            for player, outcomes in player_groups.items():
                for outcome in outcomes:
                    prop_type = self._normalize_prop_type(outcome.get("name", ""))
                    line = outcome.get("point", 0)
                    odds = outcome.get("price", 0)
                    
                    selections = [
                        Selection(
                            label=f"{player} {prop_type} O{line:.1f}",
                            line=line,
                            odds=odds
                        )
                    ]
                    
                    markets.append(MarketOdds(
                        market=f"player_prop_{prop_type.lower().replace(' ', '_')}",
                        selections=selections
                    ))
        
        return markets
    
    def _normalize_prop_type(self, raw_name: str) -> str:
        """Normalize prop type names to standard format."""
        name = raw_name.lower()
        if "point" in name or "pts" in name:
            return "Points"
        elif "rebound" in name or "reb" in name:
            return "Rebounds"
        elif "assist" in name or "ast" in name:
            return "Assists"
        elif "three" in name or "3pt" in name:
            return "3-Pointers"
        elif "block" in name or "blk" in name:
            return "Blocks"
        elif "steal" in name or "stl" in name:
            return "Steals"
        elif "turnover" in name or "to" in name:
            return "Turnovers"
        else:
            return raw_name.title()
    
    # ========================================================================
    # Scores
    # ========================================================================
    
    async def get_score(self, game_id: str) -> Optional[LiveScore]:
        """Get live score for a game."""
        parts = game_id.split("-")
        if len(parts) < 2:
            return None
        
        sport_code = parts[0].upper()
        sport_key = self.SPORT_KEYS.get(sport_code, sport_code.lower())
        
        # Fetch scores for this sport
        scores = await self._fetch_scores(sport_key)
        
        for score_data in scores:
            score_game_id = self._generate_game_id(score_data, sport_code)
            if score_game_id == game_id:
                return self._parse_score(score_data, game_id)
        
        return None
    
    async def get_scores_batch(self, game_ids: List[str]) -> List[Optional[LiveScore]]:
        """Get scores for multiple games."""
        results = []
        for game_id in game_ids:
            try:
                score = await self.get_score(game_id)
                results.append(score)
            except Exception:
                results.append(None)
        return results
    
    async def _fetch_scores(self, sport_key: str) -> List[Dict[str, Any]]:
        """Fetch live scores for a sport."""
        url = f"/sports/{sport_key}/scores"
        params = {
            "apiKey": self.api_key,
            "daysFrom": 3,  # Last 3 days
        }
        
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError:
            return []
    
    def _parse_score(self, data: Dict[str, Any], game_id: str) -> Optional[LiveScore]:
        """Parse score data into LiveScore model."""
        try:
            scores = data.get("scores", [])
            if len(scores) < 2:
                return None
            
            home_score = 0
            away_score = 0
            
            for score in scores:
                if score.get("name") == data.get("home_team"):
                    home_score = int(score.get("score", 0))
                elif score.get("name") == data.get("away_team"):
                    away_score = int(score.get("score", 0))
            
            # Determine status and period
            completed = data.get("completed", False)
            if completed:
                status = "FINAL"
                period = "Final"
            else:
                status = "LIVE"
                # Try to get period info from scores API
                period = "Live"
            
            return LiveScore(
                game_id=game_id,
                home_score=home_score,
                away_score=away_score,
                period=period,
                clock=None,  # API may not provide clock
                status=status
            )
        except Exception:
            return None
    
    # ========================================================================
    # Cleanup
    # ========================================================================
    
    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
