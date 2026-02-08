# Mock Data for DNA Bet Engine UI
# S16: Placeholder data until backend APIs are ready

import uuid
from datetime import datetime, timedelta

def generate_protocol_id():
    """Generate a unique protocol ID."""
    return f"proto_{uuid.uuid4().hex[:8]}"

# ProtocolContext schema for S16
# {
#   "protocolId": "uuid",
#   "league": "NBA",
#   "gameId": "lal-gsw-2026-02-08",
#   "teams": ["Lakers", "Warriors"],
#   "status": "LIVE",
#   "clock": "Q3 8:42",
#   "score": {"home": 88, "away": 82},
#   "marketsAvailable": ["spread", "total", "player_props"]
# }

MOCK_PROTOCOLS = {
    "nba": [
        {
            "protocolId": generate_protocol_id(),
            "league": "NBA",
            "gameId": "lal-gsw-2026-02-08",
            "teams": ["Lakers", "Warriors"],
            "status": "LIVE",
            "clock": "Q3 8:42",
            "score": {"home": 88, "away": 82},
            "marketsAvailable": ["spread", "total", "moneyline", "player_props"],
            "featured": True,
            "aiInsight": "Lakers spread has 82% probability"
        },
        {
            "protocolId": generate_protocol_id(),
            "league": "NBA",
            "gameId": "bos-mia-2026-02-09",
            "teams": ["Celtics", "Heat"],
            "status": "UPCOMING",
            "clock": None,
            "score": None,
            "marketsAvailable": ["spread", "total", "moneyline"],
            "featured": False,
            "aiInsight": "Celtics strong home advantage"
        },
        {
            "protocolId": generate_protocol_id(),
            "league": "NBA",
            "gameId": "den-phx-2026-02-09",
            "teams": ["Nuggets", "Suns"],
            "status": "UPCOMING",
            "clock": None,
            "score": None,
            "marketsAvailable": ["spread", "total", "moneyline", "player_props"],
            "featured": False,
            "aiInsight": "High total expected"
        }
    ],
    "nfl": [
        {
            "protocolId": generate_protocol_id(),
            "league": "NFL",
            "gameId": "kc-buf-2026-02-11",
            "teams": ["Chiefs", "Bills"],
            "status": "UPCOMING",
            "clock": None,
            "score": None,
            "marketsAvailable": ["spread", "total", "moneyline", "player_props"],
            "featured": True,
            "aiInsight": "Chiefs home field advantage significant"
        }
    ],
    "nhl": [
        {
            "protocolId": generate_protocol_id(),
            "league": "NHL",
            "gameId": "nyr-bos-2026-02-08",
            "teams": ["Rangers", "Bruins"],
            "status": "LIVE",
            "clock": "2nd 14:32",
            "score": {"home": 2, "away": 1},
            "marketsAvailable": ["puck_line", "total", "moneyline"],
            "featured": False,
            "aiInsight": "Low scoring game developing"
        }
    ]
}

# Legacy games data (kept for compatibility)
MOCK_GAMES = {
    "nba": [
        {
            "id": "nba_001",
            "sport": "nba",
            "home_team": {"name": "Lakers", "code": "LAL", "color": "#552583"},
            "away_team": {"name": "Warriors", "code": "GSW", "color": "#1D428A"},
            "home_score": 88,
            "away_score": 82,
            "start_time": "2024-02-08T19:30:00Z",
            "status": "live",
            "quarter": "Q3",
            "time_remaining": "8:42"
        },
        {
            "id": "nba_002", 
            "sport": "nba",
            "home_team": {"name": "Celtics", "code": "BOS", "color": "#007A33"},
            "away_team": {"name": "Heat", "code": "MIA", "color": "#98002E"},
            "home_score": None,
            "away_score": None,
            "start_time": "2024-02-09T01:30:00Z",
            "status": "upcoming",
            "quarter": None,
            "time_remaining": None
        },
        {
            "id": "nba_003",
            "sport": "nba",
            "home_team": {"name": "Nuggets", "code": "DEN", "color": "#0E2240"},
            "away_team": {"name": "Suns", "code": "PHX", "color": "#1D1160"},
            "home_score": None,
            "away_score": None,
            "start_time": "2024-02-09T02:00:00Z",
            "status": "upcoming",
            "quarter": None,
            "time_remaining": None
        }
    ],
    "nfl": [
        {
            "id": "nfl_001",
            "sport": "nfl",
            "home_team": {"name": "Chiefs", "code": "KC", "color": "#E31837"},
            "away_team": {"name": "Bills", "code": "BUF", "color": "#00338D"},
            "home_score": None,
            "away_score": None,
            "start_time": "2024-02-11T23:30:00Z",
            "status": "upcoming",
            "quarter": None,
            "time_remaining": None
        }
    ],
    "nhl": [
        {
            "id": "nhl_001",
            "sport": "nhl",
            "home_team": {"name": "Rangers", "code": "NYR", "color": "#0038A8"},
            "away_team": {"name": "Bruins", "code": "BOS", "color": "#FFB81C"},
            "home_score": 2,
            "away_score": 1,
            "start_time": "2024-02-08T00:00:00Z",
            "status": "live",
            "period": "2nd",
            "time_remaining": "14:32"
        }
    ]
}

MOCK_ODDS = {
    "nba_001": {
        "spread": {
            "home": {"line": -4.5, "odds": -110},
            "away": {"line": 4.5, "odds": -110}
        },
        "total": {
            "over": {"line": 224.5, "odds": -108},
            "under": {"line": 224.5, "odds": -108}
        },
        "moneyline": {
            "home": {"odds": -190},
            "away": {"odds": 158}
        },
        "player_props": [
            {"player": "LeBron James", "prop": "points", "line": 27.5, "over_odds": -115, "under_odds": -115},
            {"player": "LeBron James", "prop": "rebounds", "line": 8.5, "over_odds": -110, "under_odds": -110},
            {"player": "Stephen Curry", "prop": "points", "line": 26.5, "over_odds": -115, "under_odds": -115},
            {"player": "Stephen Curry", "prop": "threes", "line": 4.5, "over_odds": -120, "under_odds": -110},
            {"player": "Anthony Davis", "prop": "points", "line": 24.5, "over_odds": -115, "under_odds": -115},
            {"player": "Anthony Davis", "prop": "blocks", "line": 2.5, "over_odds": -130, "under_odds": 110}
        ]
    },
    "nba_002": {
        "spread": {
            "home": {"line": -2.5, "odds": -110},
            "away": {"line": 2.5, "odds": -110}
        },
        "total": {
            "over": {"line": 212, "odds": -110},
            "under": {"line": 212, "odds": -110}
        },
        "moneyline": {
            "home": {"odds": -145},
            "away": {"odds": 125}
        }
    },
    "nfl_001": {
        "spread": {
            "home": {"line": -3.5, "odds": -110},
            "away": {"line": 3.5, "odds": -110}
        },
        "total": {
            "over": {"line": 47.5, "odds": -110},
            "under": {"line": 47.5, "odds": -110}
        },
        "moneyline": {
            "home": {"odds": -175},
            "away": {"odds": 145}
        },
        "player_props": [
            {"player": "Patrick Mahomes", "prop": "pass_yards", "line": 280.5, "over_odds": -115, "under_odds": -115},
            {"player": "Josh Allen", "prop": "pass_yards", "line": 265.5, "over_odds": -115, "under_odds": -115}
        ]
    }
}

MOCK_USER = {
    "id": "user_001",
    "name": "Ben Ross",
    "email": "ben@example.com",
    "tier": "elite",
    "balance": 12840.50,
    "win_rate": 0.685,
    "total_bets": 142,
    "active_bets": [
        {
            "id": "bet_001",
            "game_id": "nba_001",
            "legs": [
                {"market": "spread", "selection": "lakers", "line": -4.5, "odds": -110}
            ],
            "wager": 50.00,
            "potential_payout": 170.00,
            "status": "winning"
        },
        {
            "id": "bet_002",
            "game_id": "nfl_001",
            "legs": [
                {"market": "total", "selection": "over", "line": 47.5, "odds": -110}
            ],
            "wager": 100.00,
            "potential_payout": 190.91,
            "status": "pending"
        }
    ]
}

SPORTS = [
    {"id": "nba", "name": "NBA", "icon": "🏀", "active": True},
    {"id": "nfl", "name": "NFL", "icon": "🏈", "active": True},
    {"id": "mlb", "name": "MLB", "icon": "⚾", "active": False},
    {"id": "nhl", "name": "NHL", "icon": "🏒", "active": True},
    {"id": "soccer", "name": "Soccer", "icon": "⚽", "active": False},
    {"id": "mma", "name": "MMA", "icon": "🥊", "active": False}
]
