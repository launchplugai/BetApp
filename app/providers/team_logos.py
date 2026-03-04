"""
Team and league logo utilities.

Uses ESPN's public CDN for team logos. Falls back gracefully
when a team isn't recognized.
"""


def get_team_logo(team_name: str, sport: str = "nba") -> str:
    """Get team logo URL from ESPN CDN."""
    espn_id = TEAM_ESPN_IDS.get(team_name)
    if espn_id:
        sport_path = ESPN_SPORT_PATHS.get(sport.lower(), "nba")
        return f"https://a.espncdn.com/combiner/i?img=/i/teamlogos/{sport_path}/500/{espn_id}.png&w=100&h=100"
    return ""


def get_league_logo(sport: str) -> str:
    """Get league logo URL."""
    return LEAGUE_LOGOS.get(sport.lower(), "")


ESPN_SPORT_PATHS = {
    "nba": "nba",
    "nfl": "nfl",
    "mlb": "mlb",
    "nhl": "nhl",
    "soccer": "soccer/eng.1",
    "epl": "soccer/eng.1",
    "mls": "soccer/usa.1",
    "ucl": "soccer/uefa.champions",
}

LEAGUE_LOGOS = {
    "nba": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nba.png&w=100&h=100",
    "nfl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=100&h=100",
    "mlb": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/mlb.png&w=100&h=100",
    "nhl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nhl.png&w=100&h=100",
    "soccer": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/eng.1.png&w=100&h=100",
    "epl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/eng.1.png&w=100&h=100",
    "mls": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/usa.1.png&w=100&h=100",
    "ucl": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/uefa.champions.png&w=100&h=100",
    "mma": "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/ufc.png&w=100&h=100",
}

# ESPN team IDs — maps team names to ESPN logo slugs
TEAM_ESPN_IDS = {
    # NBA
    "Los Angeles Lakers": "lal", "Lakers": "lal",
    "Golden State Warriors": "gs", "Warriors": "gs",
    "Boston Celtics": "bos", "Celtics": "bos",
    "Miami Heat": "mia", "Heat": "mia",
    "Denver Nuggets": "den", "Nuggets": "den",
    "Phoenix Suns": "phx", "Suns": "phx",
    "Milwaukee Bucks": "mil", "Bucks": "mil",
    "Philadelphia 76ers": "phi", "76ers": "phi",
    "New York Knicks": "ny", "Knicks": "ny",
    "Brooklyn Nets": "bkn", "Nets": "bkn",
    "Chicago Bulls": "chi", "Bulls": "chi",
    "Dallas Mavericks": "dal", "Mavericks": "dal",
    "Memphis Grizzlies": "mem", "Grizzlies": "mem",
    "Cleveland Cavaliers": "cle", "Cavaliers": "cle",
    "Sacramento Kings": "sac", "Kings": "sac",
    "Minnesota Timberwolves": "min", "Timberwolves": "min",
    "Oklahoma City Thunder": "okc", "Thunder": "okc",
    "New Orleans Pelicans": "no", "Pelicans": "no",
    "Atlanta Hawks": "atl", "Hawks": "atl",
    "Toronto Raptors": "tor", "Raptors": "tor",
    "Indiana Pacers": "ind", "Pacers": "ind",
    "Portland Trail Blazers": "por", "Trail Blazers": "por",
    "Utah Jazz": "utah", "Jazz": "utah",
    "San Antonio Spurs": "sa", "Spurs": "sa",
    "Charlotte Hornets": "cha", "Hornets": "cha",
    "Detroit Pistons": "det", "Pistons": "det",
    "Orlando Magic": "orl", "Magic": "orl",
    "Washington Wizards": "wsh", "Wizards": "wsh",
    "Houston Rockets": "hou", "Rockets": "hou",
    "LA Clippers": "lac", "Clippers": "lac",
    # NFL
    "Kansas City Chiefs": "kc", "Chiefs": "kc",
    "Buffalo Bills": "buf", "Bills": "buf",
    "San Francisco 49ers": "sf", "49ers": "sf",
    "Baltimore Ravens": "bal", "Ravens": "bal",
    "Detroit Lions": "det", "Lions": "det",
    "Dallas Cowboys": "dal", "Cowboys": "dal",
    "Philadelphia Eagles": "phi", "Eagles": "phi",
    "Miami Dolphins": "mia", "Dolphins": "mia",
    "Cincinnati Bengals": "cin", "Bengals": "cin",
    "Houston Texans": "hou", "Texans": "hou",
    "Jacksonville Jaguars": "jax", "Jaguars": "jax",
    "Pittsburgh Steelers": "pit", "Steelers": "pit",
    "Green Bay Packers": "gb", "Packers": "gb",
    "New York Giants": "nyg", "Giants": "nyg",
    "New York Jets": "nyj",
    "Los Angeles Rams": "lar", "Rams": "lar",
    "Los Angeles Chargers": "lac", "Chargers": "lac",
    "Seattle Seahawks": "sea", "Seahawks": "sea",
    "New England Patriots": "ne", "Patriots": "ne",
    "Tampa Bay Buccaneers": "tb", "Buccaneers": "tb",
    "Minnesota Vikings": "min", "Vikings": "min",
    "Chicago Bears": "chi", "Bears": "chi",
    "Denver Broncos": "den", "Broncos": "den",
    "Cleveland Browns": "cle", "Browns": "cle",
    "Las Vegas Raiders": "lv", "Raiders": "lv",
    "Tennessee Titans": "ten", "Titans": "ten",
    "Indianapolis Colts": "ind", "Colts": "ind",
    "Arizona Cardinals": "ari", "Cardinals": "ari",
    "Carolina Panthers": "car", "Panthers": "car",
    "Atlanta Falcons": "atl", "Falcons": "atl",
    "New Orleans Saints": "no", "Saints": "no",
    "Washington Commanders": "wsh", "Commanders": "wsh",
    # NHL
    "New York Rangers": "nyr", "Rangers": "nyr",
    "Boston Bruins": "bos", "Bruins": "bos",
    "Toronto Maple Leafs": "tor", "Maple Leafs": "tor",
    "Edmonton Oilers": "edm", "Oilers": "edm",
    "Florida Panthers": "fla",
    "Colorado Avalanche": "col", "Avalanche": "col",
    "Dallas Stars": "dal", "Stars": "dal",
    "Carolina Hurricanes": "car", "Hurricanes": "car",
    "Vegas Golden Knights": "vgk", "Golden Knights": "vgk",
    "Winnipeg Jets": "wpg",
    # MLB
    "New York Yankees": "nyy", "Yankees": "nyy",
    "Los Angeles Dodgers": "lad", "Dodgers": "lad",
    "Atlanta Braves": "atl", "Braves": "atl",
    "Houston Astros": "hou", "Astros": "hou",
    "Boston Red Sox": "bos", "Red Sox": "bos",
    "Chicago Cubs": "chc", "Cubs": "chc",
    "Philadelphia Phillies": "phi", "Phillies": "phi",
    "San Diego Padres": "sd", "Padres": "sd",
    "Texas Rangers": "tex",
    "St. Louis Cardinals": "stl",
    "New York Mets": "nym", "Mets": "nym",
}
