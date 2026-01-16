# context/tests/test_snapshot.py
"""Tests for ContextSnapshot schema."""

import pytest
from datetime import datetime

from context.snapshot import (
    ContextSnapshot,
    PlayerAvailability,
    PlayerStatus,
    empty_snapshot,
)


class TestPlayerStatus:
    """Test PlayerStatus enum."""

    def test_all_statuses_defined(self):
        """All required statuses should be defined."""
        assert PlayerStatus.AVAILABLE
        assert PlayerStatus.PROBABLE
        assert PlayerStatus.QUESTIONABLE
        assert PlayerStatus.DOUBTFUL
        assert PlayerStatus.OUT
        assert PlayerStatus.UNKNOWN


class TestPlayerAvailability:
    """Test PlayerAvailability dataclass."""

    def test_create_player(self):
        """Can create a player availability record."""
        player = PlayerAvailability(
            player_id="lebron-james",
            player_name="LeBron James",
            team="LAL",
            status=PlayerStatus.AVAILABLE,
        )
        assert player.player_name == "LeBron James"
        assert player.team == "LAL"
        assert player.status == PlayerStatus.AVAILABLE
        assert player.reason is None

    def test_create_with_reason(self):
        """Can create with injury reason."""
        player = PlayerAvailability(
            player_id="ad",
            player_name="Anthony Davis",
            team="LAL",
            status=PlayerStatus.QUESTIONABLE,
            reason="Right knee",
        )
        assert player.reason == "Right knee"

    def test_player_is_frozen(self):
        """PlayerAvailability should be immutable."""
        player = PlayerAvailability(
            player_id="test",
            player_name="Test Player",
            team="TST",
            status=PlayerStatus.AVAILABLE,
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            player.status = PlayerStatus.OUT


class TestContextSnapshot:
    """Test ContextSnapshot dataclass."""

    def test_create_minimal_snapshot(self):
        """Can create minimal snapshot."""
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test-source",
        )
        assert snapshot.sport == "NBA"
        assert snapshot.source == "test-source"
        assert snapshot.player_count == 0
        assert snapshot.confidence_hint == 0.0

    def test_create_with_players(self):
        """Can create snapshot with players."""
        player = PlayerAvailability(
            player_id="test",
            player_name="Test Player",
            team="TST",
            status=PlayerStatus.OUT,
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=(player,),
        )
        assert snapshot.player_count == 1

    def test_confidence_hint_clamped_high(self):
        """Confidence hint should be clamped to 1.0 max."""
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            confidence_hint=2.0,
        )
        assert snapshot.confidence_hint == 1.0

    def test_confidence_hint_clamped_low(self):
        """Confidence hint should be clamped to -1.0 min."""
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            confidence_hint=-2.0,
        )
        assert snapshot.confidence_hint == -1.0

    def test_get_player_by_name(self):
        """Can look up player by name."""
        player = PlayerAvailability(
            player_id="lebron",
            player_name="LeBron James",
            team="LAL",
            status=PlayerStatus.AVAILABLE,
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=(player,),
        )
        found = snapshot.get_player("LeBron James")
        assert found is not None
        assert found.player_name == "LeBron James"

    def test_get_player_case_insensitive(self):
        """Player lookup should be case insensitive."""
        player = PlayerAvailability(
            player_id="lebron",
            player_name="LeBron James",
            team="LAL",
            status=PlayerStatus.AVAILABLE,
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=(player,),
        )
        found = snapshot.get_player("lebron james")
        assert found is not None

    def test_get_player_not_found(self):
        """Returns None for unknown player."""
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
        )
        found = snapshot.get_player("Unknown Player")
        assert found is None

    def test_get_team_players(self):
        """Can get all players for a team."""
        players = (
            PlayerAvailability("p1", "Player 1", "LAL", PlayerStatus.AVAILABLE),
            PlayerAvailability("p2", "Player 2", "LAL", PlayerStatus.OUT),
            PlayerAvailability("p3", "Player 3", "BOS", PlayerStatus.AVAILABLE),
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=players,
        )
        lal_players = snapshot.get_team_players("LAL")
        assert len(lal_players) == 2

    def test_get_unavailable_players(self):
        """Can get OUT and DOUBTFUL players."""
        players = (
            PlayerAvailability("p1", "Player 1", "LAL", PlayerStatus.AVAILABLE),
            PlayerAvailability("p2", "Player 2", "LAL", PlayerStatus.OUT),
            PlayerAvailability("p3", "Player 3", "BOS", PlayerStatus.DOUBTFUL),
            PlayerAvailability("p4", "Player 4", "BOS", PlayerStatus.QUESTIONABLE),
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=players,
        )
        unavailable = snapshot.get_unavailable_players()
        assert len(unavailable) == 2

    def test_has_missing_data(self):
        """Check missing data flag."""
        snapshot_empty = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
        )
        assert not snapshot_empty.has_missing_data

        snapshot_missing = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            missing_data=("Some data missing",),
        )
        assert snapshot_missing.has_missing_data


class TestEmptySnapshot:
    """Test empty_snapshot factory function."""

    def test_creates_empty_snapshot(self):
        """Creates properly structured empty snapshot."""
        snapshot = empty_snapshot()
        assert snapshot.sport == "NBA"
        assert snapshot.source == "none"
        assert snapshot.player_count == 0
        assert snapshot.has_missing_data

    def test_custom_sport(self):
        """Can specify custom sport."""
        snapshot = empty_snapshot(sport="NFL")
        assert snapshot.sport == "NFL"
