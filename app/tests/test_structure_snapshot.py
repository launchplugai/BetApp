# app/tests/test_structure_snapshot.py
"""
Tests for Structural Snapshot Generator (Ticket 38B-A)

Tests verify:
1. Snapshot generation is deterministic
2. Order is preserved (canonical leg order)
3. Correct counting of leg types
4. Correlation flags detected
5. Volatility sources detected
6. Canonical legs take precedence over blocks
"""
import pytest
from uuid import uuid4

from core.models.leading_light import BetBlock, BetType, ContextModifiers, ContextModifier
from app.structure_snapshot import (
    generate_structure_snapshot,
    generate_leg_id,
    detect_correlation_flags,
    detect_volatility_sources,
)


# Helper to create test blocks
def create_test_block(
    bet_type: BetType,
    selection: str = "test",
    sport: str = "basketball",
    game_id: str = "game1",
    player_id: str | None = None,
    team_id: str | None = None,
    base_fragility: float = 0.5,
) -> BetBlock:
    """Create a test BetBlock with minimal required fields."""
    # Create empty context modifiers (no context applied)
    empty_modifier = ContextModifier(applied=False, delta=0.0)
    context_modifiers = ContextModifiers(
        weather=empty_modifier,
        injury=empty_modifier,
        trade=empty_modifier,
        role=empty_modifier,
    )
    
    return BetBlock.create(
        sport=sport,
        game_id=game_id,
        bet_type=bet_type,
        selection=selection,
        base_fragility=base_fragility,
        context_modifiers=context_modifiers,
        correlation_tags=[],
        player_id=player_id,
        team_id=team_id,
    )


# =============================================================================
# Test Leg ID Generation (Deterministic)
# =============================================================================


class TestLegIdGeneration:
    """Test deterministic leg ID generation."""

    def test_same_block_same_id(self):
        """Same block content produces same ID."""
        block = create_test_block(
            bet_type=BetType.SPREAD,
            selection="-5.5",
            team_id="Lakers",
        )

        id1 = generate_leg_id(block)
        id2 = generate_leg_id(block)

        assert id1 == id2
        assert len(id1) == 16  # First 16 chars of SHA-256

    def test_different_block_different_id(self):
        """Different block content produces different ID."""
        block1 = create_test_block(
            bet_type=BetType.SPREAD,
            selection="-5.5",
            team_id="Lakers",
        )
        block2 = create_test_block(
            bet_type=BetType.SPREAD,
            selection="-3.5",
            team_id="Celtics",
        )

        id1 = generate_leg_id(block1)
        id2 = generate_leg_id(block2)

        assert id1 != id2


# =============================================================================
# Test Correlation Flags
# =============================================================================


class TestCorrelationFlags:
    """Test correlation flag detection."""

    def test_no_correlation_single_leg(self):
        """Single leg has no correlation flags."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", team_id="Lakers"),
        ]

        flags = detect_correlation_flags(blocks)

        assert flags == ()

    def test_same_game_detected(self):
        """Same-game correlation detected when game_id appears twice."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", game_id="LAL_BOS", team_id="Lakers"),
            create_test_block(bet_type=BetType.TOTAL, selection="o220.5", game_id="LAL_BOS", team_id="Lakers"),
        ]

        flags = detect_correlation_flags(blocks)

        assert "same_game" in flags

    def test_no_same_game_different_games(self):
        """No same-game flag when all game_ids different."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", game_id="LAL_BOS", team_id="Lakers"),
            create_test_block(bet_type=BetType.SPREAD, selection="-3.5", game_id="MIA_NYK", team_id="Celtics"),
        ]

        flags = detect_correlation_flags(blocks)

        assert "same_game" not in flags


# =============================================================================
# Test Volatility Sources
# =============================================================================


class TestVolatilitySources:
    """Test volatility source detection."""

    def test_player_prop_detected(self):
        """Player prop detected as volatility source."""
        blocks = [
            create_test_block(bet_type=BetType.PLAYER_PROP, selection="o25.5", player_id="LeBron James"),
        ]

        sources = detect_volatility_sources(blocks)

        assert "player_prop" in sources

    def test_totals_detected(self):
        """Totals detected as volatility source."""
        blocks = [
            create_test_block(bet_type=BetType.TOTAL, selection="o220.5", game_id="LAL_BOS"),
        ]

        sources = detect_volatility_sources(blocks)

        assert "totals" in sources

    def test_team_total_detected(self):
        """Team totals detected as volatility source."""
        blocks = [
            create_test_block(bet_type=BetType.TEAM_TOTAL, selection="o110.5", team_id="Lakers"),
        ]

        sources = detect_volatility_sources(blocks)

        assert "totals" in sources

    def test_no_volatility_spread_only(self):
        """No volatility sources for spread-only parlay."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", game_id="game1", team_id="Lakers"),
            create_test_block(bet_type=BetType.SPREAD, selection="-3.5", game_id="game2", team_id="Celtics"),
        ]

        sources = detect_volatility_sources(blocks)

        assert len(sources) == 0

    def test_multiple_sources(self):
        """Multiple volatility sources detected."""
        blocks = [
            create_test_block(bet_type=BetType.PLAYER_PROP, selection="o25.5", player_id="LeBron James"),
            create_test_block(bet_type=BetType.TOTAL, selection="o220.5", game_id="LAL_BOS"),
        ]

        sources = detect_volatility_sources(blocks)

        assert "player_prop" in sources
        assert "totals" in sources


# =============================================================================
# Test Snapshot Generation
# =============================================================================


class TestSnapshotGeneration:
    """Test full snapshot generation."""

    def test_single_leg_snapshot(self):
        """Single leg snapshot generated correctly."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", team_id="Lakers"),
        ]

        snapshot = generate_structure_snapshot(blocks)

        assert snapshot.leg_count == 1
        assert len(snapshot.leg_ids) == 1
        assert len(snapshot.leg_types) == 1
        assert snapshot.leg_types[0] == "spread"
        assert snapshot.props == 0
        assert snapshot.totals == 0

    def test_multi_leg_snapshot(self):
        """Multi-leg snapshot generated correctly."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", game_id="game1", team_id="Lakers"),
            create_test_block(bet_type=BetType.SPREAD, selection="-3.5", game_id="game2", team_id="Celtics"),
            create_test_block(bet_type=BetType.TOTAL, selection="o210.5", game_id="game3", team_id="Heat"),
        ]

        snapshot = generate_structure_snapshot(blocks)

        assert snapshot.leg_count == 3
        assert len(snapshot.leg_ids) == 3
        assert len(snapshot.leg_types) == 3
        assert snapshot.leg_types == ("spread", "spread", "total")
        assert snapshot.props == 0
        assert snapshot.totals == 1

    def test_props_counted(self):
        """Player props counted correctly."""
        blocks = [
            create_test_block(bet_type=BetType.PLAYER_PROP, selection="o25.5", player_id="LeBron James"),
            create_test_block(bet_type=BetType.PLAYER_PROP, selection="o22.5", player_id="Anthony Davis"),
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", team_id="Lakers"),
        ]

        snapshot = generate_structure_snapshot(blocks)

        assert snapshot.props == 2
        assert snapshot.leg_count == 3

    def test_totals_counted(self):
        """Totals and team totals counted correctly."""
        blocks = [
            create_test_block(bet_type=BetType.TOTAL, selection="o220.5", game_id="game1"),
            create_test_block(bet_type=BetType.TEAM_TOTAL, selection="o110.5", team_id="Lakers"),
            create_test_block(bet_type=BetType.SPREAD, selection="-3.5", team_id="Celtics"),
        ]

        snapshot = generate_structure_snapshot(blocks)

        assert snapshot.totals == 2
        assert snapshot.leg_count == 3

    def test_order_preserved(self):
        """Leg order preserved in snapshot."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", game_id="game1", team_id="First"),
            create_test_block(bet_type=BetType.TOTAL, selection="o220.5", game_id="game2", team_id="Second"),
            create_test_block(bet_type=BetType.ML, selection="ML", game_id="game3", team_id="Third"),
        ]

        snapshot = generate_structure_snapshot(blocks)

        # Leg types should match block order
        assert snapshot.leg_types == ("spread", "total", "ml")

        # Leg IDs should be in same order as blocks
        id1 = generate_leg_id(blocks[0])
        id2 = generate_leg_id(blocks[1])
        id3 = generate_leg_id(blocks[2])

        assert snapshot.leg_ids == (id1, id2, id3)

    def test_canonical_legs_override(self):
        """Canonical legs take precedence over blocks."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", team_id="Lakers"),
        ]

        canonical_legs = [
            {"leg_id": "canonical_id_1", "market": "spread", "entity": "Lakers"},
            {"leg_id": "canonical_id_2", "market": "total", "entity": "Celtics"},
        ]

        snapshot = generate_structure_snapshot(blocks, canonical_legs=canonical_legs)

        assert snapshot.leg_count == 2  # From canonical legs, not blocks
        assert snapshot.leg_ids == ("canonical_id_1", "canonical_id_2")
        assert snapshot.leg_types == ("spread", "total")

    def test_snapshot_to_dict(self):
        """Snapshot converts to dict correctly."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", game_id="game1", team_id="Lakers"),
            create_test_block(bet_type=BetType.TOTAL, selection="o220.5", game_id="game2", team_id="Celtics"),
        ]

        snapshot = generate_structure_snapshot(blocks)
        snapshot_dict = snapshot.to_dict()

        assert snapshot_dict["leg_count"] == 2
        assert isinstance(snapshot_dict["leg_ids"], list)
        assert isinstance(snapshot_dict["leg_types"], list)
        assert isinstance(snapshot_dict["correlation_flags"], list)
        assert isinstance(snapshot_dict["volatility_sources"], list)
        assert "leg_count" in snapshot_dict
        assert "props" in snapshot_dict
        assert "totals" in snapshot_dict

    def test_deterministic_snapshot(self):
        """Same blocks produce same snapshot."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", game_id="game1", team_id="Lakers"),
            create_test_block(bet_type=BetType.TOTAL, selection="o220.5", game_id="game2", team_id="Celtics"),
        ]

        snapshot1 = generate_structure_snapshot(blocks)
        snapshot2 = generate_structure_snapshot(blocks)

        assert snapshot1.to_dict() == snapshot2.to_dict()


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests with multiple scenarios."""

    def test_complex_parlay(self):
        """Complex parlay with all leg types."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", game_id="game1", team_id="Lakers"),
            create_test_block(bet_type=BetType.PLAYER_PROP, selection="o25.5", game_id="game2", player_id="LeBron James"),
            create_test_block(bet_type=BetType.TOTAL, selection="o220.5", game_id="game3"),
            create_test_block(bet_type=BetType.ML, selection="ML", game_id="game4", team_id="Celtics"),
        ]

        snapshot = generate_structure_snapshot(blocks)

        assert snapshot.leg_count == 4
        assert snapshot.props == 1
        assert snapshot.totals == 1
        assert "player_prop" in snapshot.volatility_sources
        assert "totals" in snapshot.volatility_sources

    def test_same_game_parlay(self):
        """Same-game parlay detected."""
        blocks = [
            create_test_block(bet_type=BetType.SPREAD, selection="-5.5", game_id="LAL_BOS", team_id="Lakers"),
            create_test_block(bet_type=BetType.TEAM_TOTAL, selection="o110.5", game_id="LAL_BOS", team_id="Lakers"),
        ]

        snapshot = generate_structure_snapshot(blocks)

        assert "same_game" in snapshot.correlation_flags
