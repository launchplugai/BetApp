"""
The Odds API provider for live sports data.
https://the-odds-api.com/ — Free tier: 500 requests/month

Maps their response format to our internal OddsProvider/ScoreProvider interfaces.
Falls back gracefully when API key is missing or quota exceeded.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from app.providers.base import (
    OddsProvider, ScoreProvider,
    OddsResponse, ScoreResponse,
    MarketsData, MarketLine, PlayerProp,
    ScoreData
)

logger = logging.getLogger(__name__)

# The Odds API sport keys mapped to our internal sport IDs
SPORT_KEY_MAP = {
    "nba": "basketball_nba",
    "nfl": "americanfootball_nfl",
    "mlb": "baseball_mlb",
    "nhl": "icehockey_nhl",
    "soccer": "soccer_epl",
    "soccer_mls": "soccer_usa_mls",
    "soccer_ucl": "soccer_uefa_champs_league",
    "mma": "mma_mixed_martial_arts",
}

# Reverse map
SPORT_KEY_REVERSE = {v: k for k, v in SPORT_KEY_MAP.items()}


class OddsAPIProvider(OddsProvider):
    """
    Live odds provider using The Odds API.
    Free tier: 500 requests/month.
    """

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key or os.environ.get("ODDS_API_KEY", "")
        self.base_url = "https://api.the-odds-api.com/v4"
        self.timeout = timeout
        self._remaining_requests = None

    @property
    def source_name(self) -> str:
        return "odds_api"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def get_upcoming_games(self, sport: str = "nba", regions: str = "us") -> list:
        """Fetch upcoming/live games for a sport with odds."""
        sport_key = SPORT_KEY_MAP.get(sport, sport)
        url = f"{self.base_url}/sports/{sport_key}/odds/"
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": "spreads,totals,h2h",
            "oddsFormat": "american",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                self._remaining_requests = resp.headers.get("x-requests-remaining")
                logger.info(f"Odds API requests remaining: {self._remaining_requests}")

                if resp.status_code == 401:
                    logger.error("Odds API: Invalid API key")
                    return []
                if resp.status_code == 429:
                    logger.warning("Odds API: Quota exceeded")
                    return []
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"Odds API fetch failed: {e}")
            return []

    async def get_live_scores(self, sport: str = "nba") -> list:
        """Fetch live scores for a sport."""
        sport_key = SPORT_KEY_MAP.get(sport, sport)
        url = f"{self.base_url}/sports/{sport_key}/scores/"
        params = {
            "apiKey": self.api_key,
            "daysFrom": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, params=params)
                self._remaining_requests = resp.headers.get("x-requests-remaining")
                if resp.status_code != 200:
                    return []
                return resp.json()
        except Exception as e:
            logger.error(f"Odds API scores fetch failed: {e}")
            return []

    def normalize_games(self, raw_games: list, sport: str) -> list:
        """Convert Odds API game format to our internal game format."""
        games = []
        for g in raw_games:
            game_id = g.get("id", "")
            home_team = g.get("home_team", "")
            away_team = g.get("away_team", "")
            commence = g.get("commence_time", "")

            # Determine status
            completed = g.get("completed", False)
            if completed:
                status = "final"
            elif g.get("scores"):
                status = "live"
            else:
                status = "upcoming"

            # Extract best odds from bookmakers
            odds = self._extract_best_odds(g.get("bookmakers", []))

            game = {
                "id": game_id,
                "sport": sport,
                "home_team": {
                    "name": home_team,
                    "code": self._team_code(home_team),
                    "logo": get_team_logo(home_team, sport),
                },
                "away_team": {
                    "name": away_team,
                    "code": self._team_code(away_team),
                    "logo": get_team_logo(away_team, sport),
                },
                "home_score": None,
                "away_score": None,
                "start_time": commence,
                "status": status,
                "odds": odds,
                "source": "live",
            }

            # Add scores if available
            scores = g.get("scores")
            if scores:
                for s in scores:
                    if s.get("name") == home_team:
                        game["home_score"] = int(s.get("score", 0)) if s.get("score") else None
                    elif s.get("name") == away_team:
                        game["away_score"] = int(s.get("score", 0)) if s.get("score") else None

            games.append(game)
        return games

    def _extract_best_odds(self, bookmakers: list) -> dict:
        """Extract odds from first available bookmaker (usually FanDuel/DraftKings)."""
        preferred = ["fanduel", "draftkings", "betmgm", "pointsbetus"]
        selected = None

        for pref in preferred:
            for bm in bookmakers:
                if bm.get("key") == pref:
                    selected = bm
                    break
            if selected:
                break

        if not selected and bookmakers:
            selected = bookmakers[0]

        if not selected:
            return {}

        odds = {}
        for market in selected.get("markets", []):
            key = market.get("key")
            outcomes = market.get("outcomes", [])

            if key == "spreads":
                home_out = next((o for o in outcomes if o.get("name") == "home" or outcomes.index(o) == 0), None)
                away_out = next((o for o in outcomes if o.get("name") == "away" or outcomes.index(o) == 1), None)
                if home_out and away_out:
                    odds["spread"] = {
                        "home": {"line": home_out.get("point", 0), "odds": home_out.get("price", -110)},
                        "away": {"line": away_out.get("point", 0), "odds": away_out.get("price", -110)},
                    }
            elif key == "totals":
                over = next((o for o in outcomes if o.get("name") == "Over"), None)
                under = next((o for o in outcomes if o.get("name") == "Under"), None)
                if over and under:
                    odds["total"] = {
                        "over": {"line": over.get("point", 0), "odds": over.get("price", -110)},
                        "under": {"line": under.get("point", 0), "odds": under.get("price", -110)},
                    }
            elif key == "h2h":
                if len(outcomes) >= 2:
                    odds["moneyline"] = {
                        "home": {"odds": outcomes[0].get("price", -110)},
                        "away": {"odds": outcomes[1].get("price", 100)},
                    }

        return odds

    def _team_code(self, team_name: str) -> str:
        """Generate a short team code from name."""
        code = TEAM_CODES.get(team_name)
        if code:
            return code
        # Fallback: first 3 chars uppercase
        parts = team_name.split()
        return parts[-1][:3].upper() if parts else team_name[:3].upper()

    async def get_odds(self, game_id: str) -> OddsResponse:
        """Get odds for a single game (not efficient for Odds API, use batch)."""
        return OddsResponse(
            game_id=game_id,
            timestamp=datetime.now(timezone.utc),
            markets=MarketsData()
        )

    async def get_odds_batch(self, game_ids: List[str]) -> List[OddsResponse]:
        return []


class OddsAPIScoreProvider(ScoreProvider):
    """Live score provider using The Odds API."""

    def __init__(self, api_key: Optional[str] = None):
        self.odds_provider = OddsAPIProvider(api_key=api_key)

    @property
    def source_name(self) -> str:
        return "odds_api"

    async def get_score(self, game_id: str) -> ScoreResponse:
        return ScoreResponse(game_id=game_id, status="UNKNOWN")

    async def get_scores_batch(self, game_ids: List[str]) -> List[ScoreResponse]:
        return []


# =============================================================================
# Team Logo CDN — ESPN public logo URLs
# =============================================================================

def get_team_logo(team_name: str, sport: str = "nba") -> str:
    """Get team logo URL from ESPN CDN."""
    espn_id = TEAM_ESPN_IDS.get(team_name)
    if espn_id:
        sport_path = ESPN_SPORT_PATHS.get(sport, "basketball/nba")
        return f"https://a.espncdn.com/i/teamlogos/{sport_path}/500/{espn_id}.png"
    # Fallback: generic sport icon
    return ""


def get_league_logo(sport: str) -> str:
    """Get league logo URL."""
    return LEAGUE_LOGOS.get(sport, "")


ESPN_SPORT_PATHS = {
    "nba": "nba",
    "nfl": "nfl",
    "mlb": "mlb",
    "nhl": "nhl",
    "soccer": "soccer/eng.1",
}

# ESPN team IDs for logo CDN
TEAM_ESPN_IDS = {
    # NBA
    "Los Angeles Lakers": "lal",
    "Lakers": "lal",
    "Golden State Warriors": "gs",
    "Warriors": "gs",
    "Boston Celtics": "bos",
    "Celtics": "bos",
    "Miami Heat": "mia",
    "Heat": "mia",
    "Denver Nuggets": "den",
    "Nuggets": "den",
    "Phoenix Suns": "phx",
    "Suns": "phx",
    "Milwaukee Bucks": "mil",
    "Bucks": "mil",
    "Philadelphia 76ers": "phi",
    "76ers": "phi",
    "New York Knicks": "ny",
    "Knicks": "ny",
    "Brooklyn Nets": "bkn",
    "Nets": "bkn",
    "Chicago Bulls": "chi",
    "Bulls": "chi",
    "Dallas Mavericks": "dal",
    "Mavericks": "dal",
    "Memphis Grizzlies": "mem",
    "Grizzlies": "mem",
    "Cleveland Cavaliers": "cle",
    "Cavaliers": "cle",
    "Sacramento Kings": "sac",
    "Kings": "sac",
    "Minnesota Timberwolves": "min",
    "Timberwolves": "min",
    "Oklahoma City Thunder": "okc",
    "Thunder": "okc",
    "New Orleans Pelicans": "no",
    "Pelicans": "no",
    "Atlanta Hawks": "atl",
    "Hawks": "atl",
    "Toronto Raptors": "tor",
    "Raptors": "tor",
    "Indiana Pacers": "ind",
    "Pacers": "ind",
    "Portland Trail Blazers": "por",
    "Trail Blazers": "por",
    "Utah Jazz": "utah",
    "Jazz": "utah",
    "San Antonio Spurs": "sa",
    "Spurs": "sa",
    "Charlotte Hornets": "cha",
    "Hornets": "cha",
    "Detroit Pistons": "det",
    "Pistons": "det",
    "Orlando Magic": "orl",
    "Magic": "orl",
    "Washington Wizards": "wsh",
    "Wizards": "wsh",
    "Houston Rockets": "hou",
    "Rockets": "hou",
    "LA Clippers": "lac",
    "Clippers": "lac",
    # NFL
    "Kansas City Chiefs": "kc",
    "Chiefs": "kc",
    "Buffalo Bills": "buf",
    "Bills": "buf",
    "San Francisco 49ers": "sf",
    "49ers": "sf",
    "Baltimore Ravens": "bal",
    "Ravens": "bal",
    "Detroit Lions": "det",
    "Lions": "det",
    "Dallas Cowboys": "dal",
    "Cowboys": "dal",
    "Philadelphia Eagles": "phi",
    "Eagles": "phi",
    "Miami Dolphins": "mia",
    "Dolphins": "mia",
    "Cincinnati Bengals": "cin",
    "Bengals": "cin",
    "Houston Texans": "hou",
    "Texans": "hou",
    "Jacksonville Jaguars": "jax",
    "Jaguars": "jax",
    "Pittsburgh Steelers": "pit",
    "Steelers": "pit",
    "Green Bay Packers": "gb",
    "Packers": "gb",
    "New York Giants": "nyg",
    "Giants": "nyg",
    "New York Jets": "nyj",
    "Jets": "nyj",
    "Los Angeles Rams": "lar",
    "Rams": "lar",
    "Los Angeles Chargers": "lac",
    "Chargers": "lac",
    "Seattle Seahawks": "sea",
    "Seahawks": "sea",
    "New England Patriots": "ne",
    "Patriots": "ne",
    "Tampa Bay Buccaneers": "tb",
    "Buccaneers": "tb",
    "Minnesota Vikings": "min",
    "Vikings": "min",
    "Chicago Bears": "chi",
    "Bears": "chi",
    "Denver Broncos": "den",
    "Broncos": "den",
    "Cleveland Browns": "cle",
    "Browns": "cle",
    "Las Vegas Raiders": "lv",
    "Raiders": "lv",
    "Tennessee Titans": "ten",
    "Titans": "ten",
    "Indianapolis Colts": "ind",
    "Colts": "ind",
    "Arizona Cardinals": "ari",
    "Cardinals": "ari",
    "Carolina Panthers": "car",
    "Panthers": "car",
    "Atlanta Falcons": "atl",
    "Falcons": "atl",
    "New Orleans Saints": "no",
    "Saints": "no",
    "Washington Commanders": "wsh",
    "Commanders": "wsh",
    # NHL
    "New York Rangers": "nyr",
    "Rangers": "nyr",
    "Boston Bruins": "bos",
    "Bruins": "bos",
    "Toronto Maple Leafs": "tor",
    "Maple Leafs": "tor",
    "Edmonton Oilers": "edm",
    "Oilers": "edm",
    "Florida Panthers": "fla",
    "Colorado Avalanche": "col",
    "Avalanche": "col",
    "Dallas Stars": "dal",
    "Stars": "dal",
    "Carolina Hurricanes": "car",
    "Hurricanes": "car",
    "Vegas Golden Knights": "vgk",
    "Golden Knights": "vgk",
    "Winnipeg Jets": "wpg",
    # MLB
    "New York Yankees": "nyy",
    "Yankees": "nyy",
    "Los Angeles Dodgers": "lad",
    "Dodgers": "lad",
    "Atlanta Braves": "atl",
    "Braves": "atl",
    "Houston Astros": "hou",
    "Astros": "hou",
    "Boston Red Sox": "bos",
    "Red Sox": "bos",
    "Chicago Cubs": "chc",
    "Cubs": "chc",
    "Philadelphia Phillies": "phi",
    "Phillies": "phi",
    "San Diego Padres": "sd",
    "Padres": "sd",
    "Texas Rangers": "tex",
    "St. Louis Cardinals": "stl",
    "New York Mets": "nym",
    "Mets": "nym",
}

TEAM_CODES = {
    # NBA short codes
    "Los Angeles Lakers": "LAL", "Lakers": "LAL",
    "Golden State Warriors": "GSW", "Warriors": "GSW",
    "Boston Celtics": "BOS", "Celtics": "BOS",
    "Miami Heat": "MIA", "Heat": "MIA",
    "Denver Nuggets": "DEN", "Nuggets": "DEN",
    "Phoenix Suns": "PHX", "Suns": "PHX",
    "Milwaukee Bucks": "MIL", "Bucks": "MIL",
    "Philadelphia 76ers": "PHI", "76ers": "PHI",
    "New York Knicks": "NYK", "Knicks": "NYK",
    "Brooklyn Nets": "BKN", "Nets": "BKN",
    "Dallas Mavericks": "DAL", "Mavericks": "DAL",
    "Oklahoma City Thunder": "OKC", "Thunder": "OKC",
    "Cleveland Cavaliers": "CLE", "Cavaliers": "CLE",
    "Minnesota Timberwolves": "MIN", "Timberwolves": "MIN",
    "Sacramento Kings": "SAC", "Kings": "SAC",
    # NFL
    "Kansas City Chiefs": "KC", "Chiefs": "KC",
    "Buffalo Bills": "BUF", "Bills": "BUF",
    "San Francisco 49ers": "SF", "49ers": "SF",
    "Baltimore Ravens": "BAL", "Ravens": "BAL",
    "Philadelphia Eagles": "PHI", "Eagles": "PHI",
    # NHL
    "New York Rangers": "NYR", "Rangers": "NYR",
    "Boston Bruins": "BOS", "Bruins": "BOS",
}

LEAGUE_LOGOS = {
    "nba": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nba.png&w=100&h=100",
    "nfl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=100&h=100",
    "mlb": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/mlb.png&w=100&h=100",
    "nhl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nhl.png&w=100&h=100",
    "soccer": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/eng.1.png&w=100&h=100",
    "mma": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/ufc.png&w=100&h=100",
}
