# context/tests/test_nba_provider.py
"""Tests for NBA availability provider with mocked HTTP responses."""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

import httpx

from context.providers.nba_availability import (
    NBAAvailabilityProvider,
    get_nba_availability,
    _parse_status,
    _parse_team,
    _fetch_from_nba_official,
    _fetch_from_espn,
    _fetch_live_data,
    _get_sample_players,
)
from context.snapshot import PlayerStatus


# =============================================================================
# Mock Response Data
# =============================================================================

MOCK_NBA_RESPONSE = [
    {
        "team": "Los Angeles Lakers",
        "injuries": [
            {"player": "LeBron James", "status": "probable", "description": "Left ankle"},
            {"player": "Anthony Davis", "status": "out", "injury": "Right knee"},
        ]
    },
    {
        "team": "Boston Celtics",
        "injuries": [
            {"player": "Jayson Tatum", "status": "questionable", "description": "Right wrist"},
        ]
    }
]

MOCK_ESPN_RESPONSE = {
    "teams": [
        {
            "team": {"abbreviation": "LAL"},
            "injuries": [
                {
                    "athlete": {"displayName": "LeBron James"},
                    "status": "probable",
                    "type": {"description": "Left ankle"}
                }
            ]
        },
        {
            "team": {"abbreviation": "MIL"},
            "injuries": [
                {
                    "athlete": {"displayName": "Giannis Antetokounmpo"},
                    "status": "out",
                    "type": {"description": "Right knee"}
                }
            ]
        }
    ]
}


# =============================================================================
# Helper Tests
# =============================================================================


class TestParseStatus:
    """Test status string parsing."""

    def test_out(self):
        assert _parse_status("out") == PlayerStatus.OUT

    def test_doubtful(self):
        assert _parse_status("doubtful") == PlayerStatus.DOUBTFUL

    def test_questionable(self):
        assert _parse_status("questionable") == PlayerStatus.QUESTIONABLE

    def test_probable(self):
        assert _parse_status("probable") == PlayerStatus.PROBABLE

    def test_available(self):
        assert _parse_status("available") == PlayerStatus.AVAILABLE

    def test_gtd(self):
        """Game-time decision maps to questionable."""
        assert _parse_status("gtd") == PlayerStatus.QUESTIONABLE

    def test_day_to_day(self):
        assert _parse_status("day-to-day") == PlayerStatus.QUESTIONABLE

    def test_case_insensitive(self):
        assert _parse_status("OUT") == PlayerStatus.OUT
        assert _parse_status("Questionable") == PlayerStatus.QUESTIONABLE

    def test_unknown_status(self):
        assert _parse_status("injured-reserve") == PlayerStatus.UNKNOWN

    def test_empty_string(self):
        assert _parse_status("") == PlayerStatus.UNKNOWN


class TestParseTeam:
    """Test team name parsing."""

    def test_full_name(self):
        assert _parse_team("Los Angeles Lakers") == "LAL"
        assert _parse_team("Boston Celtics") == "BOS"

    def test_la_clippers(self):
        assert _parse_team("LA Clippers") == "LAC"
        assert _parse_team("Los Angeles Clippers") == "LAC"

    def test_unknown_team(self):
        """Unknown team returns first 3 chars."""
        assert _parse_team("Unknown Team") == "UNK"


# =============================================================================
# Provider Tests with Mocked HTTP
# =============================================================================


class TestNBAOfficialFetch:
    """Test _fetch_from_nba_official with mocked responses."""

    @patch("context.providers.nba_availability.httpx.Client")
    def test_successful_fetch(self, mock_client_class):
        """Successful API response returns player list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_NBA_RESPONSE

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        players = _fetch_from_nba_official(timeout=10)

        assert players is not None
        assert len(players) == 3
        assert players[0].player_name == "LeBron James"
        assert players[0].team == "LAL"
        assert players[0].status == PlayerStatus.PROBABLE

    @patch("context.providers.nba_availability.httpx.Client")
    def test_non_200_response(self, mock_client_class):
        """Non-200 response returns None."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        players = _fetch_from_nba_official(timeout=10)
        assert players is None

    @patch("context.providers.nba_availability.httpx.Client")
    def test_timeout(self, mock_client_class):
        """Timeout returns None."""
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        players = _fetch_from_nba_official(timeout=10)
        assert players is None

    @patch("context.providers.nba_availability.httpx.Client")
    def test_request_error(self, mock_client_class):
        """Request error returns None."""
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.RequestError("Connection failed")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        players = _fetch_from_nba_official(timeout=10)
        assert players is None


class TestESPNFetch:
    """Test _fetch_from_espn with mocked responses."""

    @patch("context.providers.nba_availability.httpx.Client")
    def test_successful_fetch(self, mock_client_class):
        """Successful ESPN response returns player list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_ESPN_RESPONSE

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        players = _fetch_from_espn(timeout=10)

        assert players is not None
        assert len(players) == 2
        assert players[0].player_name == "LeBron James"
        assert players[1].player_name == "Giannis Antetokounmpo"


class TestLiveDataFetch:
    """Test _fetch_live_data with multiple sources."""

    @patch("context.providers.nba_availability._fetch_from_espn")
    @patch("context.providers.nba_availability._fetch_from_nba_official")
    def test_nba_official_success(self, mock_nba, mock_espn):
        """When NBA official succeeds, ESPN is not called."""
        mock_nba.return_value = [MagicMock()]  # Non-empty list

        players, source, missing = _fetch_live_data(10)

        assert source == "nba-official"
        assert len(missing) == 0
        mock_espn.assert_not_called()

    @patch("context.providers.nba_availability._fetch_from_espn")
    @patch("context.providers.nba_availability._fetch_from_nba_official")
    def test_fallback_to_espn(self, mock_nba, mock_espn):
        """When NBA official fails, falls back to ESPN."""
        mock_nba.return_value = None
        mock_espn.return_value = [MagicMock()]  # Non-empty list

        players, source, missing = _fetch_live_data(10)

        assert source == "espn-injuries"
        assert "NBA official API unavailable" in missing

    @patch("context.providers.nba_availability._fetch_from_espn")
    @patch("context.providers.nba_availability._fetch_from_nba_official")
    def test_all_sources_fail(self, mock_nba, mock_espn):
        """When all sources fail, returns None with missing notes."""
        mock_nba.return_value = None
        mock_espn.return_value = None

        players, source, missing = _fetch_live_data(10)

        assert players is None
        assert source == "none"
        assert "NBA official API unavailable" in missing
        assert "ESPN API unavailable" in missing


# =============================================================================
# Provider Class Tests
# =============================================================================


class TestNBAAvailabilityProvider:
    """Test NBAAvailabilityProvider class."""

    def test_sample_mode_default(self):
        """Default mode uses sample data."""
        provider = NBAAvailabilityProvider(use_live_data=False)
        snapshot = provider.fetch()

        assert snapshot is not None
        assert snapshot.source == "sample-data"
        assert snapshot.player_count > 0

    @patch("context.providers.nba_availability._fetch_live_data")
    def test_live_mode_success(self, mock_fetch):
        """Live mode with successful fetch."""
        mock_fetch.return_value = (
            _get_sample_players(),
            "nba-official",
            [],
        )

        provider = NBAAvailabilityProvider(use_live_data=True)
        snapshot = provider.fetch()

        assert snapshot is not None
        assert snapshot.source == "nba-official"
        assert snapshot.confidence_hint == 0.5

    @patch("context.providers.nba_availability._fetch_live_data")
    def test_live_mode_failure_fallback(self, mock_fetch):
        """Live mode falls back to sample on failure."""
        mock_fetch.return_value = (
            None,
            "none",
            ["NBA official API unavailable", "ESPN API unavailable"],
        )

        provider = NBAAvailabilityProvider(use_live_data=True)
        snapshot = provider.fetch()

        assert snapshot is not None
        assert snapshot.source == "sample-fallback"
        assert snapshot.confidence_hint == -0.3
        assert "Using sample data as fallback" in snapshot.missing_data

    def test_graceful_degradation_on_exception(self):
        """Provider handles unexpected exceptions gracefully."""
        provider = NBAAvailabilityProvider(use_live_data=False)

        # Mock internal method to raise
        with patch.object(provider, "_fetch_sample", side_effect=Exception("Test error")):
            snapshot = provider.fetch()

        assert snapshot is not None
        assert snapshot.source == "error-fallback"
        assert "availability_source_unreachable" in snapshot.missing_data
        assert snapshot.confidence_hint == -0.5

    def test_env_var_config(self):
        """Provider reads config from environment."""
        with patch.dict("os.environ", {
            "NBA_AVAILABILITY_LIVE": "true",
            "NBA_AVAILABILITY_TIMEOUT": "5",
        }):
            provider = NBAAvailabilityProvider()
            assert provider._use_live_data is True
            assert provider._timeout == 5


class TestConvenienceFunction:
    """Test get_nba_availability convenience function."""

    def test_returns_snapshot(self):
        """Convenience function returns snapshot."""
        snapshot = get_nba_availability(use_live=False)
        assert snapshot is not None
        assert snapshot.sport == "NBA"


# =============================================================================
# Cache Integration Tests
# =============================================================================


class TestCacheIntegration:
    """Test provider behavior with service caching."""

    def test_provider_always_available(self):
        """Provider should always report as available (graceful degradation)."""
        provider = NBAAvailabilityProvider(use_live_data=False)
        assert provider.is_available() is True

        provider_live = NBAAvailabilityProvider(use_live_data=True)
        assert provider_live.is_available() is True

    def test_snapshot_has_required_fields(self):
        """Snapshot has all fields needed by cache."""
        provider = NBAAvailabilityProvider(use_live_data=False)
        snapshot = provider.fetch()

        assert hasattr(snapshot, "sport")
        assert hasattr(snapshot, "as_of")
        assert hasattr(snapshot, "source")
        assert hasattr(snapshot, "players")
        assert hasattr(snapshot, "missing_data")
        assert hasattr(snapshot, "confidence_hint")
