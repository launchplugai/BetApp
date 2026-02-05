# app/tests/test_parser_bet_type.py
"""
Tests for Ticket A1: Parser Bet_Type Correction

Verifies that common real-world betting text inputs produce
BetBlock objects with correct bet_type classification.

These tests use actual failing examples from integration tests.
"""
import pytest
from app.pipeline import _detect_leg_markets, _parse_bet_text
from core.models.leading_light import BetType


class TestPlayerPropAbbreviations:
    """Test that common player prop abbreviations are recognized."""

    def test_pts_abbreviation_detected(self):
        """'pts' should be recognized as player_prop."""
        legs = _detect_leg_markets("LeBron O27.5 pts")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP

    def test_reb_abbreviation_detected(self):
        """'reb' should be recognized as player_prop."""
        legs = _detect_leg_markets("AD O10 reb")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP

    def test_ast_abbreviation_detected(self):
        """'ast' should be recognized as player_prop."""
        legs = _detect_leg_markets("Jokic O8.5 ast")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP

    def test_multiple_props_recognized(self):
        """Multiple player props should all be detected correctly."""
        legs = _detect_leg_markets("LeBron O27.5 pts + AD O10 reb")
        assert len(legs) == 2
        assert all(leg["bet_type"] == BetType.PLAYER_PROP for leg in legs)

    def test_mixed_props_and_ml(self):
        """Mix of player props and moneyline should be detected correctly."""
        legs = _detect_leg_markets("LeBron O27.5 pts + AD O10 reb + Lakers ML")
        assert len(legs) == 3
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP
        assert legs[1]["bet_type"] == BetType.PLAYER_PROP
        assert legs[2]["bet_type"] == BetType.ML


class TestCommonPropPatterns:
    """Test that common prop patterns are recognized."""

    def test_o_number_pattern(self):
        """'O<number>' pattern should indicate player prop."""
        legs = _detect_leg_markets("Curry O5.5 3pm")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP

    def test_u_number_pattern(self):
        """'U<number>' pattern should indicate player prop."""
        legs = _detect_leg_markets("Butler U22.5 pts")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP

    def test_3pm_abbreviation(self):
        """'3pm' should be recognized as player prop."""
        legs = _detect_leg_markets("Curry O5.5 3pm")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP

    def test_blk_abbreviation(self):
        """'blk' should be recognized as player prop."""
        legs = _detect_leg_markets("Gobert O2.5 blk")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP

    def test_stl_abbreviation(self):
        """'stl' should be recognized as player prop."""
        legs = _detect_leg_markets("Holiday O1.5 stl")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP

    def test_to_abbreviation(self):
        """'to' (turnovers) should be recognized as player prop."""
        legs = _detect_leg_markets("Westbrook U3.5 to")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP


class TestMoneylineDetection:
    """Test that moneyline bets are correctly identified."""

    def test_ml_abbreviation(self):
        """'ML' should be recognized as moneyline."""
        legs = _detect_leg_markets("Lakers ML")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.ML

    def test_moneyline_full_word(self):
        """'moneyline' should be recognized as moneyline."""
        legs = _detect_leg_markets("Celtics moneyline")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.ML


class TestSpreadDetection:
    """Test that spread bets are correctly identified."""

    def test_negative_spread(self):
        """'-5.5' pattern should be recognized as spread."""
        legs = _detect_leg_markets("Lakers -5.5")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.SPREAD

    def test_positive_spread(self):
        """'+3.5' pattern should be recognized as spread."""
        legs = _detect_leg_markets("Celtics +3.5")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.SPREAD

    def test_spread_with_team_name(self):
        """Spread with team name should be detected."""
        legs = _detect_leg_markets("Lakers -5.5 + Celtics ML")
        assert len(legs) == 2
        assert legs[0]["bet_type"] == BetType.SPREAD
        assert legs[1]["bet_type"] == BetType.ML


class TestTotalDetection:
    """Test that total bets are correctly identified."""

    def test_over_keyword(self):
        """'over' keyword should be recognized as total."""
        legs = _detect_leg_markets("Lakers vs Celtics over 220.5")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.TOTAL

    def test_under_keyword(self):
        """'under' keyword should be recognized as total."""
        legs = _detect_leg_markets("Nuggets vs Heat under 210")
        assert len(legs) == 1
        assert legs[0]["bet_type"] == BetType.TOTAL


class TestRealWorldExamples:
    """Test using actual failing examples from integration tests."""

    def test_failing_example_1(self):
        """Test case from test_snapshot_counts_props_correctly."""
        legs = _detect_leg_markets("LeBron O27.5 pts + AD O10 reb + Lakers ML")
        
        # Should have 3 legs
        assert len(legs) == 3
        
        # First two should be player props
        assert legs[0]["bet_type"] == BetType.PLAYER_PROP
        assert legs[1]["bet_type"] == BetType.PLAYER_PROP
        
        # Last should be moneyline
        assert legs[2]["bet_type"] == BetType.ML

    def test_failing_example_2(self):
        """Test case from test_snapshot_counts_totals_correctly."""
        legs = _detect_leg_markets("Lakers vs Celtics O220.5 + Nuggets vs Heat U210")
        
        # Should have 2 totals
        assert len(legs) == 2
        assert all(leg["bet_type"] == BetType.TOTAL for leg in legs)

    def test_failing_example_3(self):
        """Test case from test_snapshot_detects_same_game_correlation."""
        legs = _detect_leg_markets("Lakers ML + LeBron O27.5 pts")
        
        # Should have 1 ML + 1 prop
        assert len(legs) == 2
        assert legs[0]["bet_type"] == BetType.ML
        assert legs[1]["bet_type"] == BetType.PLAYER_PROP


class TestBetBlockIntegration:
    """Test that _parse_bet_text produces correct BetBlock bet_type values."""

    def test_parse_produces_correct_bet_types(self):
        """Full parsing should produce BetBlocks with correct bet_type."""
        blocks = _parse_bet_text("LeBron O27.5 pts + AD O10 reb + Lakers ML")
        
        # Should have 3 blocks
        assert len(blocks) == 3
        
        # Check bet_type on actual BetBlock objects
        assert blocks[0].bet_type == BetType.PLAYER_PROP
        assert blocks[1].bet_type == BetType.PLAYER_PROP
        assert blocks[2].bet_type == BetType.ML
