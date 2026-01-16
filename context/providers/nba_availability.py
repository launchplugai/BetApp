# context/providers/nba_availability.py
"""
NBA Player Availability Provider

Sprint 3.1: Real data implementation with graceful fallback.

Fetches player injury/availability data from official NBA sources.
Falls back to sample data if live fetch fails.

Configuration via environment variables:
- NBA_AVAILABILITY_LIVE: Set to "true" to enable live data (default: false)
- NBA_AVAILABILITY_TIMEOUT: HTTP timeout in seconds (default: 10)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

import httpx

from context.providers.base import ContextProvider
from context.snapshot import (
    ContextSnapshot,
    PlayerAvailability,
    PlayerStatus,
    empty_snapshot,
)


_logger = logging.getLogger(__name__)

# NBA official injury report endpoint (used by nbainjuries package)
# Format: JSON with team-by-team injury data
NBA_INJURIES_BASE_URL = "https://official.nba.com/wp-json/nba-injury/v1/report"

# Alternative: ESPN API (as backup)
ESPN_INJURIES_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries"

# Team name to abbreviation mapping for parsing
_TEAM_ABBREV = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Clippers": "LAC",
    "LA Lakers": "LAL", "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM", "Miami Heat": "MIA", "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK", "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI", "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC", "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA", "Washington Wizards": "WAS",
}

# Status string to enum mapping
_STATUS_MAP = {
    "out": PlayerStatus.OUT,
    "doubtful": PlayerStatus.DOUBTFUL,
    "questionable": PlayerStatus.QUESTIONABLE,
    "probable": PlayerStatus.PROBABLE,
    "available": PlayerStatus.AVAILABLE,
    "day-to-day": PlayerStatus.QUESTIONABLE,
    "gtd": PlayerStatus.QUESTIONABLE,  # Game-time decision
}


def _get_config() -> tuple[bool, int]:
    """Get provider configuration from environment."""
    use_live = os.environ.get("NBA_AVAILABILITY_LIVE", "false").lower() == "true"
    timeout = int(os.environ.get("NBA_AVAILABILITY_TIMEOUT", "10"))
    return use_live, timeout


# =============================================================================
# Sample Data (fallback when live data unavailable)
# =============================================================================

_SAMPLE_AVAILABILITY_DATA = [
    ("lebron-james", "LeBron James", "LAL", PlayerStatus.PROBABLE, "Left ankle"),
    ("anthony-davis", "Anthony Davis", "LAL", PlayerStatus.QUESTIONABLE, "Right knee"),
    ("jaylen-brown", "Jaylen Brown", "BOS", PlayerStatus.AVAILABLE, None),
    ("jayson-tatum", "Jayson Tatum", "BOS", PlayerStatus.AVAILABLE, None),
    ("nikola-jokic", "Nikola Jokic", "DEN", PlayerStatus.AVAILABLE, None),
    ("jamal-murray", "Jamal Murray", "DEN", PlayerStatus.QUESTIONABLE, "Left hamstring"),
    ("giannis-antetokounmpo", "Giannis Antetokounmpo", "MIL", PlayerStatus.PROBABLE, "Right knee"),
    ("damian-lillard", "Damian Lillard", "MIL", PlayerStatus.OUT, "Right calf strain"),
    ("stephen-curry", "Stephen Curry", "GSW", PlayerStatus.AVAILABLE, None),
    ("klay-thompson", "Klay Thompson", "DAL", PlayerStatus.AVAILABLE, None),
    ("kevin-durant", "Kevin Durant", "PHX", PlayerStatus.DOUBTFUL, "Left ankle sprain"),
    ("devin-booker", "Devin Booker", "PHX", PlayerStatus.PROBABLE, "Left hamstring"),
    ("joel-embiid", "Joel Embiid", "PHI", PlayerStatus.OUT, "Left knee injury management"),
    ("tyrese-maxey", "Tyrese Maxey", "PHI", PlayerStatus.AVAILABLE, None),
    ("luka-doncic", "Luka Doncic", "DAL", PlayerStatus.QUESTIONABLE, "Right ankle"),
    ("kyrie-irving", "Kyrie Irving", "DAL", PlayerStatus.AVAILABLE, None),
]


def _get_sample_players() -> list[PlayerAvailability]:
    """Return sample player data as fallback."""
    now = datetime.utcnow()
    return [
        PlayerAvailability(
            player_id=pid,
            player_name=name,
            team=team,
            status=status,
            reason=reason,
            updated_at=now,
        )
        for pid, name, team, status, reason in _SAMPLE_AVAILABILITY_DATA
    ]


# =============================================================================
# Live Data Fetching
# =============================================================================


def _parse_status(status_str: str) -> PlayerStatus:
    """Parse status string to PlayerStatus enum."""
    if not status_str:
        return PlayerStatus.UNKNOWN
    normalized = status_str.lower().strip()
    return _STATUS_MAP.get(normalized, PlayerStatus.UNKNOWN)


def _parse_team(team_name: str) -> str:
    """Parse team name to abbreviation."""
    return _TEAM_ABBREV.get(team_name, team_name[:3].upper())


def _create_player_id(name: str) -> str:
    """Create a player ID from name."""
    return name.lower().replace(" ", "-").replace(".", "").replace("'", "")


def _fetch_from_nba_official(timeout: int) -> Optional[list[PlayerAvailability]]:
    """
    Fetch injury data from NBA official endpoint.

    Returns list of PlayerAvailability or None on failure.
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                NBA_INJURIES_BASE_URL,
                headers={
                    "User-Agent": "DNA-Matrix/1.0",
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                _logger.warning(f"NBA API returned {response.status_code}")
                return None

            data = response.json()
            players = []
            now = datetime.utcnow()

            # Parse NBA official format
            # Structure: list of team objects with injury arrays
            if isinstance(data, list):
                for team_data in data:
                    team_name = team_data.get("team", "")
                    team_abbr = _parse_team(team_name)
                    injuries = team_data.get("injuries", [])

                    for injury in injuries:
                        player_name = injury.get("player", "")
                        if not player_name:
                            continue

                        status_str = injury.get("status", "")
                        reason = injury.get("description", injury.get("injury", ""))

                        players.append(PlayerAvailability(
                            player_id=_create_player_id(player_name),
                            player_name=player_name,
                            team=team_abbr,
                            status=_parse_status(status_str),
                            reason=reason if reason else None,
                            updated_at=now,
                        ))

            return players if players else None

    except httpx.TimeoutException:
        _logger.warning("NBA API request timed out")
        return None
    except httpx.RequestError as e:
        _logger.warning(f"NBA API request failed: {e}")
        return None
    except Exception as e:
        _logger.warning(f"Failed to parse NBA API response: {e}")
        return None


def _fetch_from_espn(timeout: int) -> Optional[list[PlayerAvailability]]:
    """
    Fetch injury data from ESPN API (backup source).

    Returns list of PlayerAvailability or None on failure.
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(
                ESPN_INJURIES_URL,
                headers={
                    "User-Agent": "DNA-Matrix/1.0",
                    "Accept": "application/json",
                },
            )

            if response.status_code != 200:
                _logger.warning(f"ESPN API returned {response.status_code}")
                return None

            data = response.json()
            players = []
            now = datetime.utcnow()

            # Parse ESPN format
            # Structure: { "teams": [ { "team": {...}, "injuries": [...] } ] }
            teams = data.get("teams", [])
            for team_entry in teams:
                team_info = team_entry.get("team", {})
                team_abbr = team_info.get("abbreviation", "UNK")
                injuries = team_entry.get("injuries", [])

                for injury in injuries:
                    athlete = injury.get("athlete", {})
                    player_name = athlete.get("displayName", "")
                    if not player_name:
                        continue

                    status_str = injury.get("status", "")
                    injury_detail = injury.get("type", {})
                    reason = injury_detail.get("description", "")

                    players.append(PlayerAvailability(
                        player_id=_create_player_id(player_name),
                        player_name=player_name,
                        team=team_abbr,
                        status=_parse_status(status_str),
                        reason=reason if reason else None,
                        updated_at=now,
                    ))

            return players if players else None

    except httpx.TimeoutException:
        _logger.warning("ESPN API request timed out")
        return None
    except httpx.RequestError as e:
        _logger.warning(f"ESPN API request failed: {e}")
        return None
    except Exception as e:
        _logger.warning(f"Failed to parse ESPN API response: {e}")
        return None


def _fetch_live_data(timeout: int) -> tuple[Optional[list[PlayerAvailability]], str, list[str]]:
    """
    Attempt to fetch live data from available sources.

    Returns (players, source_name, missing_data_notes).
    """
    missing = []

    # Try NBA official first
    players = _fetch_from_nba_official(timeout)
    if players:
        return players, "nba-official", []

    missing.append("NBA official API unavailable")

    # Try ESPN as backup
    players = _fetch_from_espn(timeout)
    if players:
        return players, "espn-injuries", missing

    missing.append("ESPN API unavailable")

    # All sources failed
    return None, "none", missing


# =============================================================================
# Provider Class
# =============================================================================


class NBAAvailabilityProvider(ContextProvider):
    """
    NBA player availability provider with live data support.

    Configuration:
    - Set NBA_AVAILABILITY_LIVE=true to enable live fetching
    - Set NBA_AVAILABILITY_TIMEOUT=N for custom timeout (default: 10s)

    Graceful degradation:
    - If live fetch fails, returns snapshot with:
      - Sample data as fallback
      - missing_data noting the failure
      - confidence_hint = -0.3 (reduced confidence)
    """

    def __init__(self, use_live_data: Optional[bool] = None):
        """
        Initialize provider.

        Args:
            use_live_data: Override env var setting. None uses env var.
        """
        env_live, self._timeout = _get_config()
        self._use_live_data = use_live_data if use_live_data is not None else env_live
        self._source_name = "nba-availability"
        self._last_fetch_source: Optional[str] = None

    @property
    def sport(self) -> str:
        return "NBA"

    @property
    def source_name(self) -> str:
        if self._last_fetch_source:
            return self._last_fetch_source
        return self._source_name

    def fetch(self) -> Optional[ContextSnapshot]:
        """
        Fetch NBA player availability data.

        Returns ContextSnapshot with current availability status.
        Falls back to sample data if live fetch fails.
        """
        try:
            if self._use_live_data:
                return self._fetch_live()
            else:
                return self._fetch_sample()
        except Exception as e:
            _logger.error(f"Provider fetch failed: {e}")
            # Return graceful fallback
            return self._create_fallback_snapshot(str(e))

    def _fetch_live(self) -> ContextSnapshot:
        """Fetch from live data sources with fallback."""
        players, source, missing = _fetch_live_data(self._timeout)

        if players:
            self._last_fetch_source = source
            return ContextSnapshot(
                sport=self.sport,
                as_of=datetime.utcnow(),
                source=source,
                players=tuple(players),
                missing_data=tuple(missing),
                confidence_hint=0.5 if not missing else 0.3,
            )

        # Live fetch failed - use sample with degraded confidence
        _logger.warning("All live sources failed, using sample data fallback")
        self._last_fetch_source = "sample-fallback"

        return ContextSnapshot(
            sport=self.sport,
            as_of=datetime.utcnow(),
            source="sample-fallback",
            players=tuple(_get_sample_players()),
            missing_data=tuple(missing + ["Using sample data as fallback"]),
            confidence_hint=-0.3,  # Reduced confidence for stale data
        )

    def _fetch_sample(self) -> ContextSnapshot:
        """Fetch sample data (development mode)."""
        self._last_fetch_source = "sample-data"
        return ContextSnapshot(
            sport=self.sport,
            as_of=datetime.utcnow(),
            source="sample-data",
            players=tuple(_get_sample_players()),
            missing_data=("Using sample data (live API not enabled)",),
            confidence_hint=0.0,
        )

    def _create_fallback_snapshot(self, error: str) -> ContextSnapshot:
        """Create a fallback snapshot when everything fails."""
        self._last_fetch_source = "error-fallback"
        return ContextSnapshot(
            sport=self.sport,
            as_of=datetime.utcnow(),
            source="error-fallback",
            players=tuple(_get_sample_players()),
            missing_data=(
                "availability_source_unreachable",
                f"Error: {error}",
                "Using sample data as emergency fallback",
            ),
            confidence_hint=-0.5,  # Low confidence
        )

    def is_available(self) -> bool:
        """Check if provider is available."""
        # Provider is always available (graceful degradation ensures this)
        return True


# =============================================================================
# Convenience Functions
# =============================================================================


def get_nba_availability(use_live: Optional[bool] = None) -> Optional[ContextSnapshot]:
    """
    Fetch NBA availability snapshot using default provider.

    Args:
        use_live: Override live data setting. None uses env var.
    """
    provider = NBAAvailabilityProvider(use_live_data=use_live)
    return provider.fetch()
