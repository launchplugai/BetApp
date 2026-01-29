"""
League and Team Data for v1 UI.

4 major leagues, ~120 teams total.
Structured data eliminates text parsing.
"""

LEAGUES = {
    "NBA": {
        "name": "NBA",
        "sport": "basketball",
        "teams": {
            "ATL": "Atlanta Hawks",
            "BOS": "Boston Celtics",
            "BKN": "Brooklyn Nets",
            "CHA": "Charlotte Hornets",
            "CHI": "Chicago Bulls",
            "CLE": "Cleveland Cavaliers",
            "DAL": "Dallas Mavericks",
            "DEN": "Denver Nuggets",
            "DET": "Detroit Pistons",
            "GSW": "Golden State Warriors",
            "HOU": "Houston Rockets",
            "IND": "Indiana Pacers",
            "LAC": "LA Clippers",
            "LAL": "LA Lakers",
            "MEM": "Memphis Grizzlies",
            "MIA": "Miami Heat",
            "MIL": "Milwaukee Bucks",
            "MIN": "Minnesota Timberwolves",
            "NOP": "New Orleans Pelicans",
            "NYK": "New York Knicks",
            "OKC": "Oklahoma City Thunder",
            "ORL": "Orlando Magic",
            "PHI": "Philadelphia 76ers",
            "PHX": "Phoenix Suns",
            "POR": "Portland Trail Blazers",
            "SAC": "Sacramento Kings",
            "SAS": "San Antonio Spurs",
            "TOR": "Toronto Raptors",
            "UTA": "Utah Jazz",
            "WAS": "Washington Wizards",
        },
    },
    "NFL": {
        "name": "NFL",
        "sport": "football",
        "teams": {
            "ARI": "Arizona Cardinals",
            "ATL": "Atlanta Falcons",
            "BAL": "Baltimore Ravens",
            "BUF": "Buffalo Bills",
            "CAR": "Carolina Panthers",
            "CHI": "Chicago Bears",
            "CIN": "Cincinnati Bengals",
            "CLE": "Cleveland Browns",
            "DAL": "Dallas Cowboys",
            "DEN": "Denver Broncos",
            "DET": "Detroit Lions",
            "GB": "Green Bay Packers",
            "HOU": "Houston Texans",
            "IND": "Indianapolis Colts",
            "JAX": "Jacksonville Jaguars",
            "KC": "Kansas City Chiefs",
            "LV": "Las Vegas Raiders",
            "LAC": "Los Angeles Chargers",
            "LAR": "Los Angeles Rams",
            "MIA": "Miami Dolphins",
            "MIN": "Minnesota Vikings",
            "NE": "New England Patriots",
            "NO": "New Orleans Saints",
            "NYG": "New York Giants",
            "NYJ": "New York Jets",
            "PHI": "Philadelphia Eagles",
            "PIT": "Pittsburgh Steelers",
            "SF": "San Francisco 49ers",
            "SEA": "Seattle Seahawks",
            "TB": "Tampa Bay Buccaneers",
            "TEN": "Tennessee Titans",
            "WAS": "Washington Commanders",
        },
    },
    "MLB": {
        "name": "MLB",
        "sport": "baseball",
        "teams": {
            "ARI": "Arizona Diamondbacks",
            "ATL": "Atlanta Braves",
            "BAL": "Baltimore Orioles",
            "BOS": "Boston Red Sox",
            "CHC": "Chicago Cubs",
            "CHW": "Chicago White Sox",
            "CIN": "Cincinnati Reds",
            "CLE": "Cleveland Guardians",
            "COL": "Colorado Rockies",
            "DET": "Detroit Tigers",
            "HOU": "Houston Astros",
            "KC": "Kansas City Royals",
            "LAA": "Los Angeles Angels",
            "LAD": "Los Angeles Dodgers",
            "MIA": "Miami Marlins",
            "MIL": "Milwaukee Brewers",
            "MIN": "Minnesota Twins",
            "NYM": "New York Mets",
            "NYY": "New York Yankees",
            "OAK": "Oakland Athletics",
            "PHI": "Philadelphia Phillies",
            "PIT": "Pittsburgh Pirates",
            "SD": "San Diego Padres",
            "SF": "San Francisco Giants",
            "SEA": "Seattle Mariners",
            "STL": "St. Louis Cardinals",
            "TB": "Tampa Bay Rays",
            "TEX": "Texas Rangers",
            "TOR": "Toronto Blue Jays",
            "WAS": "Washington Nationals",
        },
    },
    "NHL": {
        "name": "NHL",
        "sport": "hockey",
        "teams": {
            "ANA": "Anaheim Ducks",
            "ARI": "Arizona Coyotes",
            "BOS": "Boston Bruins",
            "BUF": "Buffalo Sabres",
            "CGY": "Calgary Flames",
            "CAR": "Carolina Hurricanes",
            "CHI": "Chicago Blackhawks",
            "COL": "Colorado Avalanche",
            "CBJ": "Columbus Blue Jackets",
            "DAL": "Dallas Stars",
            "DET": "Detroit Red Wings",
            "EDM": "Edmonton Oilers",
            "FLA": "Florida Panthers",
            "LA": "Los Angeles Kings",
            "MIN": "Minnesota Wild",
            "MTL": "Montreal Canadiens",
            "NSH": "Nashville Predators",
            "NJ": "New Jersey Devils",
            "NYI": "New York Islanders",
            "NYR": "New York Rangers",
            "OTT": "Ottawa Senators",
            "PHI": "Philadelphia Flyers",
            "PIT": "Pittsburgh Penguins",
            "SJ": "San Jose Sharks",
            "SEA": "Seattle Kraken",
            "STL": "St. Louis Blues",
            "TB": "Tampa Bay Lightning",
            "TOR": "Toronto Maple Leafs",
            "VAN": "Vancouver Canucks",
            "VGK": "Vegas Golden Knights",
            "WAS": "Washington Capitals",
            "WPG": "Winnipeg Jets",
        },
    },
}

# Bet types available for selection
BET_TYPES = {
    "spread": {"label": "Spread", "needs_line": True, "needs_direction": True},
    "ml": {"label": "Moneyline", "needs_line": False, "needs_direction": False},
    "total": {"label": "Total (O/U)", "needs_line": True, "needs_direction": True},
    "player_prop": {"label": "Player Prop", "needs_line": True, "needs_player": True},
    "team_total": {"label": "Team Total", "needs_line": True, "needs_direction": True},
}


def get_teams_for_league(league: str) -> dict:
    """Get teams dict for a league."""
    if league not in LEAGUES:
        return {}
    return LEAGUES[league]["teams"]


def get_team_name(league: str, abbrev: str) -> str:
    """Get full team name from abbreviation."""
    teams = get_teams_for_league(league)
    return teams.get(abbrev, abbrev)


def format_leg(league: str, team: str, bet_type: str, line: str = "", direction: str = "") -> str:
    """
    Format a leg for display and evaluation.

    Returns canonical format like:
    - "LAL -5.5" (spread)
    - "LAL ML" (moneyline)
    - "LAL/BOS o220.5" (total)
    """
    team_name = get_team_name(league, team)

    if bet_type == "spread":
        sign = "+" if direction == "plus" else "-"
        return f"{team_name} {sign}{line}"
    elif bet_type == "ml":
        return f"{team_name} ML"
    elif bet_type == "total":
        ou = "o" if direction == "over" else "u"
        return f"{team_name} {ou}{line}"
    elif bet_type == "team_total":
        ou = "o" if direction == "over" else "u"
        return f"{team_name} TT {ou}{line}"
    elif bet_type == "player_prop":
        return f"{team_name} prop {line}"
    else:
        return f"{team_name} {bet_type} {line}"
