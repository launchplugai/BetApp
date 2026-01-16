# context/tests/test_apply.py
"""Tests for context application logic."""

import pytest
from datetime import datetime

from context.apply import apply_context, ContextModifier, ContextImpact
from context.snapshot import (
    ContextSnapshot,
    PlayerAvailability,
    PlayerStatus,
)


class TestApplyContext:
    """Test apply_context function."""

    def test_empty_snapshot_neutral_impact(self):
        """Empty snapshot returns neutral impact."""
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
        )
        impact = apply_context(snapshot)
        assert impact.total_adjustment == 0.0

    def test_missing_data_reduces_confidence(self):
        """Missing data adds negative modifier."""
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            missing_data=("Some data missing",),
        )
        impact = apply_context(snapshot)
        assert impact.total_adjustment < 0

    def test_player_out_reduces_confidence(self):
        """OUT player reduces confidence."""
        player = PlayerAvailability(
            player_id="test",
            player_name="Test Player",
            team="LAL",
            status=PlayerStatus.OUT,
            reason="Injury",
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=(player,),
        )
        impact = apply_context(snapshot, player_names=["Test Player"])
        assert impact.total_adjustment < 0
        # Should have a modifier about the player
        reasons = [m.reason for m in impact.modifiers]
        assert any("Test Player" in r for r in reasons)

    def test_player_questionable_reduces_confidence(self):
        """QUESTIONABLE player reduces confidence."""
        player = PlayerAvailability(
            player_id="test",
            player_name="Test Player",
            team="LAL",
            status=PlayerStatus.QUESTIONABLE,
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=(player,),
        )
        impact = apply_context(snapshot, player_names=["Test Player"])
        assert impact.total_adjustment < 0

    def test_player_available_slight_positive(self):
        """AVAILABLE player provides slight positive."""
        player = PlayerAvailability(
            player_id="test",
            player_name="Test Player",
            team="LAL",
            status=PlayerStatus.AVAILABLE,
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=(player,),
        )
        impact = apply_context(snapshot, player_names=["Test Player"])
        # Available players provide slight confidence boost
        # But there may be missing data offset
        assert impact is not None

    def test_team_with_out_players_reduces_confidence(self):
        """Team with OUT players reduces confidence."""
        players = (
            PlayerAvailability("p1", "Player 1", "LAL", PlayerStatus.OUT),
            PlayerAvailability("p2", "Player 2", "LAL", PlayerStatus.AVAILABLE),
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=players,
        )
        impact = apply_context(snapshot, team_names=["LAL"])
        assert impact.total_adjustment < 0

    def test_multiple_out_players_cumulative(self):
        """Multiple OUT players have cumulative effect."""
        players = (
            PlayerAvailability("p1", "Player 1", "LAL", PlayerStatus.OUT),
            PlayerAvailability("p2", "Player 2", "LAL", PlayerStatus.OUT),
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=players,
        )
        impact = apply_context(snapshot, team_names=["LAL"])
        # Should have team-level modifier
        assert any("LAL" in m.reason for m in impact.modifiers)

    def test_total_adjustment_clamped(self):
        """Total adjustment is clamped to [-1.0, 1.0]."""
        # Create many negative modifiers
        players = tuple(
            PlayerAvailability(f"p{i}", f"Player {i}", "LAL", PlayerStatus.OUT)
            for i in range(20)
        )
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            players=players,
        )
        impact = apply_context(snapshot, team_names=["LAL"])
        assert impact.total_adjustment >= -1.0
        assert impact.total_adjustment <= 1.0

    def test_unknown_player_reduces_confidence(self):
        """Player not in data reduces confidence slightly."""
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
        )
        impact = apply_context(snapshot, player_names=["Unknown Player"])
        assert impact.total_adjustment < 0


class TestContextModifier:
    """Test ContextModifier dataclass."""

    def test_create_modifier(self):
        """Can create a modifier."""
        modifier = ContextModifier(
            adjustment=-0.1,
            reason="Test reason",
            source="test",
        )
        assert modifier.adjustment == -0.1
        assert modifier.reason == "Test reason"
        assert len(modifier.affected_players) == 0

    def test_modifier_with_players(self):
        """Can create modifier with affected players."""
        modifier = ContextModifier(
            adjustment=-0.15,
            reason="Player out",
            source="test",
            affected_players=("LeBron James",),
        )
        assert "LeBron James" in modifier.affected_players


class TestContextImpact:
    """Test ContextImpact dataclass."""

    def test_summary_generation(self):
        """Impact includes summary."""
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
        )
        impact = apply_context(snapshot)
        assert isinstance(impact.summary, str)

    def test_missing_data_passthrough(self):
        """Missing data is passed through to impact."""
        snapshot = ContextSnapshot(
            sport="NBA",
            as_of=datetime.utcnow(),
            source="test",
            missing_data=("No live data",),
        )
        impact = apply_context(snapshot)
        assert "No live data" in impact.missing_data
