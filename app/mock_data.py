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


# =============================================================================
# Protocol Context — Contextual intelligence data for the Protocol System
# =============================================================================
# Each game gets a protocol context containing the hidden forces
# that affect the bet beyond raw stats and odds.

MOCK_PROTOCOL_CONTEXTS = {
    "lal-gsw-2026-02-08": {
        "game_id": "lal-gsw-2026-02-08",
        "league": "NBA",
        "home_team": "Lakers",
        "away_team": "Warriors",
        # Schedule
        "is_back_to_back_home": False,
        "is_back_to_back_away": True,  # Warriors on B2B
        "home_rest_days": 2,
        "away_rest_days": 0,
        "home_travel_miles": 0,
        "away_travel_miles": 350,
        # Tactical
        "home_pace": 99.2,
        "away_pace": 101.8,
        "home_def_rating": 112.4,
        "away_def_rating": 109.1,
        # Roster
        "home_injuries": [
            {"player": "Anthony Davis", "status": "QUESTIONABLE", "injury": "knee", "is_star": True},
        ],
        "away_injuries": [],
        "home_lineup_changes": 1,
        "away_lineup_changes": 0,
        "home_starter_out": False,
        "away_starter_out": False,
        # Psychological
        "revenge_players": [],
        "home_streak": 3,
        "away_streak": -2,
        # Market
        "opening_spread": -3.5,
        "current_spread": -4.5,
        "public_bet_pct_home": 72.0,
        "sharp_money_side": "away",
        "line_movement": -1.0,
        # Officiating
        "ref_crew": "Scott Foster",
        "ref_foul_rate": 2.3,
        "ref_home_advantage": 1.8,
        # Environment
        "altitude_ft": 340,
        "is_playoff": False,
    },
    "bos-mia-2026-02-09": {
        "game_id": "bos-mia-2026-02-09",
        "league": "NBA",
        "home_team": "Celtics",
        "away_team": "Heat",
        "is_back_to_back_home": False,
        "is_back_to_back_away": False,
        "home_rest_days": 3,
        "away_rest_days": 2,
        "home_travel_miles": 0,
        "away_travel_miles": 1500,
        "home_pace": 100.5,
        "away_pace": 96.3,
        "home_def_rating": 106.8,
        "away_def_rating": 111.5,
        "home_injuries": [],
        "away_injuries": [
            {"player": "Jimmy Butler", "status": "OUT", "injury": "ankle", "is_star": True},
        ],
        "home_lineup_changes": 0,
        "away_lineup_changes": 2,
        "home_starter_out": False,
        "away_starter_out": True,
        "revenge_players": [],
        "home_streak": 5,
        "away_streak": -1,
        "opening_spread": -2.0,
        "current_spread": -2.5,
        "public_bet_pct_home": 68.0,
        "sharp_money_side": None,
        "line_movement": -0.5,
        "ref_crew": None,
        "ref_foul_rate": 0.0,
        "ref_home_advantage": 0.0,
        "altitude_ft": 20,
        "is_playoff": False,
    },
    "den-phx-2026-02-09": {
        "game_id": "den-phx-2026-02-09",
        "league": "NBA",
        "home_team": "Nuggets",
        "away_team": "Suns",
        "is_back_to_back_home": False,
        "is_back_to_back_away": True,
        "home_rest_days": 2,
        "away_rest_days": 0,
        "home_travel_miles": 0,
        "away_travel_miles": 600,
        "home_pace": 97.8,
        "away_pace": 100.1,
        "home_def_rating": 108.2,
        "away_def_rating": 113.7,
        "home_injuries": [],
        "away_injuries": [],
        "home_lineup_changes": 0,
        "away_lineup_changes": 0,
        "home_starter_out": False,
        "away_starter_out": False,
        "revenge_players": [
            {
                "player": "Kevin Durant",
                "former_team": "Suns",
                "current_team": "Nuggets",
                "games_since_trade": 3,
                "is_contentious": True,
            }
        ],
        "home_streak": 1,
        "away_streak": 0,
        "opening_spread": -6.0,
        "current_spread": -7.5,
        "public_bet_pct_home": 78.0,
        "sharp_money_side": "home",
        "line_movement": -1.5,
        "ref_crew": "Tony Brothers",
        "ref_foul_rate": 3.1,
        "ref_home_advantage": 2.4,
        "altitude_ft": 5280,  # Denver altitude
        "is_playoff": False,
    },
    "kc-buf-2026-02-11": {
        "game_id": "kc-buf-2026-02-11",
        "league": "NFL",
        "home_team": "Chiefs",
        "away_team": "Bills",
        "is_back_to_back_home": False,
        "is_back_to_back_away": False,
        "home_rest_days": 7,
        "away_rest_days": 7,
        "home_travel_miles": 0,
        "away_travel_miles": 1400,
        "home_pace": 0,
        "away_pace": 0,
        "home_def_rating": 0,
        "away_def_rating": 0,
        "home_injuries": [],
        "away_injuries": [],
        "home_lineup_changes": 0,
        "away_lineup_changes": 0,
        "home_starter_out": False,
        "away_starter_out": False,
        "revenge_players": [],
        "home_streak": 4,
        "away_streak": 2,
        "opening_spread": -3.0,
        "current_spread": -3.5,
        "public_bet_pct_home": 65.0,
        "sharp_money_side": None,
        "line_movement": -0.5,
        "ref_crew": None,
        "ref_foul_rate": 0.0,
        "ref_home_advantage": 0.0,
        "altitude_ft": 900,
        "is_playoff": False,
    },
}
