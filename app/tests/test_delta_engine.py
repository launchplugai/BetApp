# app/tests/test_delta_engine.py
"""
Tests for Change Delta Engine (Ticket 38B-B)

Tests verify:
1. No delta on first evaluation (no previous snapshot)
2. Leg removal detected and described
3. Leg addition detected and described
4. Correlation flag changes detected
5. Volatility source changes detected
6. Multiple simultaneous changes handled
7. No-op re-evaluation (identical snapshots)
8. Deterministic sentence generation
"""
import pytest

from app.delta_engine import (
    compute_snapshot_delta,
    store_snapshot_for_session,
    get_previous_snapshot_for_session,
)


# =============================================================================
# Test First Evaluation (No Previous Snapshot)
# =============================================================================


class TestFirstEvaluation:
    """Test behavior when no previous snapshot exists."""

    def test_no_delta_on_first_evaluation(self):
        """First evaluation produces no delta."""
        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "ml"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": ["totals"],
        }

        delta = compute_snapshot_delta(previous=None, current=current)

        assert delta.has_delta is False
        assert delta.delta_sentence is None
        assert delta.changes_detected == ()


# =============================================================================
# Test Leg Removal
# =============================================================================


class TestLegRemoval:
    """Test leg removal detection."""

    def test_single_leg_removed(self):
        """Single leg removal detected."""
        previous = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "ml"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert "removed 1 leg" in delta.delta_sentence
        assert "leg_removed:1" in delta.changes_detected

    def test_multiple_legs_removed(self):
        """Multiple legs removal detected."""
        previous = {
            "leg_count": 4,
            "leg_ids": ["id1", "id2", "id3", "id4"],
            "leg_types": ["spread", "total", "ml", "player_prop"],
            "props": 1,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert "removed 2 legs" in delta.delta_sentence
        assert "leg_removed:2" in delta.changes_detected


# =============================================================================
# Test Leg Addition
# =============================================================================


class TestLegAddition:
    """Test leg addition detection."""

    def test_single_leg_added(self):
        """Single leg addition detected."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "ml"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert "added 1 leg" in delta.delta_sentence
        assert "leg_added:1" in delta.changes_detected

    def test_multiple_legs_added(self):
        """Multiple legs addition detected."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 4,
            "leg_ids": ["id1", "id2", "id3", "id4"],
            "leg_types": ["spread", "total", "ml", "player_prop"],
            "props": 1,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": ["player_prop"],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert "added 2 legs" in delta.delta_sentence
        assert "leg_added:2" in delta.changes_detected


# =============================================================================
# Test Correlation Flag Changes
# =============================================================================


class TestCorrelationFlagChanges:
    """Test correlation flag detection."""

    def test_correlation_flag_added(self):
        """Correlation flag addition detected."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": ["same_game"],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert "same_game correlation" in delta.delta_sentence
        assert "correlation_added:same_game" in delta.changes_detected

    def test_correlation_flag_removed(self):
        """Correlation flag removal detected."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": ["same_game"],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert "removed same_game correlation" in delta.delta_sentence
        assert "correlation_removed:same_game" in delta.changes_detected


# =============================================================================
# Test Volatility Source Changes
# =============================================================================


class TestVolatilitySourceChanges:
    """Test volatility source detection."""

    def test_volatility_source_added(self):
        """Volatility source addition detected."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "ml"],
            "props": 0,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "ml", "player_prop"],
            "props": 1,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": ["player_prop"],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert "player prop" in delta.delta_sentence
        assert any("volatility_added:player_prop" in c for c in delta.changes_detected)

    def test_volatility_source_removed(self):
        """Volatility source removal detected."""
        previous = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "ml", "player_prop"],
            "props": 1,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": ["player_prop"],
        }

        current = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "ml"],
            "props": 0,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert "removed player prop" in delta.delta_sentence


# =============================================================================
# Test Multiple Simultaneous Changes
# =============================================================================


class TestMultipleChanges:
    """Test multiple simultaneous changes."""

    def test_leg_removal_and_correlation_added(self):
        """Leg removal + correlation addition."""
        previous = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "ml"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": ["same_game"],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert "removed 1 leg" in delta.delta_sentence
        assert "same_game correlation" in delta.delta_sentence
        assert len(delta.changes_detected) >= 2

    def test_leg_addition_and_volatility_added(self):
        """Leg addition + volatility source addition."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "ml"],
            "props": 0,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "ml", "player_prop"],
            "props": 1,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": ["player_prop"],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert "added 1 leg" in delta.delta_sentence
        assert len(delta.changes_detected) >= 2


# =============================================================================
# Test No-Op Re-Evaluation
# =============================================================================


class TestNoOpReEvaluation:
    """Test identical snapshots (no changes)."""

    def test_identical_snapshots_no_delta(self):
        """Identical snapshots produce no delta."""
        snapshot = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "ml"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": ["totals"],
        }

        delta = compute_snapshot_delta(previous=snapshot, current=snapshot)

        assert delta.has_delta is False
        assert delta.delta_sentence is None
        assert delta.changes_detected == ()


# =============================================================================
# Test Deterministic Sentence Generation
# =============================================================================


class TestDeterministicSentences:
    """Test sentence generation is deterministic."""

    def test_same_changes_same_sentence(self):
        """Same changes produce same sentence."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "ml"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta1 = compute_snapshot_delta(previous, current)
        delta2 = compute_snapshot_delta(previous, current)

        assert delta1.delta_sentence == delta2.delta_sentence
        assert delta1.changes_detected == delta2.changes_detected


# =============================================================================
# Test Session Storage
# =============================================================================


class TestSessionStorage:
    """Test snapshot storage and retrieval."""

    def test_store_and_retrieve_snapshot(self):
        """Snapshot can be stored and retrieved."""
        session_id = "test_session_123"
        snapshot = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "ml"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        store_snapshot_for_session(session_id, snapshot)
        retrieved = get_previous_snapshot_for_session(session_id)

        assert retrieved == snapshot

    def test_retrieve_nonexistent_session(self):
        """Retrieving nonexistent session returns None."""
        retrieved = get_previous_snapshot_for_session("nonexistent_session")

        assert retrieved is None


# =============================================================================
# Edge Case Tests (Ticket 38B-B2)
# =============================================================================


class TestEdgeCaseMultipleSimultaneousChanges:
    """Test complex scenarios with multiple simultaneous changes."""

    def test_three_changes_at_once(self):
        """Three simultaneous changes: leg removal + correlation added + volatility added."""
        previous = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "ml", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id4"],
            "leg_types": ["spread", "ml", "player_prop"],
            "props": 1,
            "totals": 0,
            "correlation_flags": ["same_game"],
            "volatility_sources": ["player_prop"],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        assert delta.delta_sentence is not None
        # Should contain all three change types
        assert len(delta.changes_detected) >= 3

    def test_leg_addition_removal_simultaneously(self):
        """Legs added and removed at the same time (net zero but composition changed)."""
        previous = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "ml", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id4"],
            "leg_types": ["spread", "ml", "player_prop"],
            "props": 1,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": ["player_prop"],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        # Leg count unchanged but composition changed
        assert "leg_replaced" in str(delta.changes_detected)


class TestOrderPreservedButContentChanged:
    """Test when order is preserved but leg content changes."""

    def test_same_position_different_leg(self):
        """Leg at same position but different leg_id (replacement)."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 2,
            "leg_ids": ["id1", "id3"],  # id2 replaced with id3
            "leg_types": ["spread", "ml"],
            "props": 0,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        assert delta.has_delta is True
        # Should detect replacement (leg_ids changed)
        assert "leg_replaced" in str(delta.changes_detected)


class TestNoOpReEvaluationEdgeCases:
    """Test no-op re-evaluations with edge cases."""

    def test_completely_identical_snapshots(self):
        """Completely identical snapshots down to every field."""
        snapshot = {
            "leg_count": 4,
            "leg_ids": ["id1", "id2", "id3", "id4"],
            "leg_types": ["spread", "total", "ml", "player_prop"],
            "props": 1,
            "totals": 1,
            "correlation_flags": ["same_game"],
            "volatility_sources": ["player_prop", "totals"],
        }

        delta = compute_snapshot_delta(previous=snapshot, current=snapshot)

        assert delta.has_delta is False
        assert delta.delta_sentence is None
        assert len(delta.changes_detected) == 0

    def test_empty_arrays_preserved(self):
        """Empty arrays in both snapshots still produce no delta."""
        snapshot = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "ml"],
            "props": 0,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous=snapshot, current=snapshot)

        assert delta.has_delta is False
        assert delta.delta_sentence is None


class TestMissingOptionalFields:
    """Test defensive handling of missing optional fields."""

    def test_missing_correlation_flags(self):
        """Snapshot missing correlation_flags field."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            # Missing: "correlation_flags"
            "volatility_sources": [],
        }

        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "ml"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        # Should handle missing field gracefully
        assert delta.has_delta is True
        assert "added 1 leg" in delta.delta_sentence

    def test_missing_volatility_sources(self):
        """Snapshot missing volatility_sources field."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            # Missing: "volatility_sources"
        }

        current = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        # Should handle missing field gracefully (no delta)
        assert delta.has_delta is False

    def test_missing_leg_ids(self):
        """Snapshot missing leg_ids field."""
        previous = {
            "leg_count": 2,
            # Missing: "leg_ids"
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "ml"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        # Should detect leg count change even without leg_ids
        assert delta.has_delta is True
        assert "added 1 leg" in delta.delta_sentence


class TestUnexpectedSnapshotShapes:
    """Test defensive handling of unexpected snapshot shapes."""

    def test_extra_fields_ignored(self):
        """Extra fields in snapshot are ignored."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "ml"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
            "extra_field": "should be ignored",
            "another_field": 12345,
        }

        delta = compute_snapshot_delta(previous, current)

        # Should work despite extra fields
        assert delta.has_delta is True
        assert "added 1 leg" in delta.delta_sentence

    def test_empty_snapshot(self):
        """Empty snapshot handled gracefully."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 0,
            "leg_ids": [],
            "leg_types": [],
            "props": 0,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        delta = compute_snapshot_delta(previous, current)

        # Should detect all legs removed
        assert delta.has_delta is True
        assert "removed 2 legs" in delta.delta_sentence


class TestDeterministicEdgeCases:
    """Test determinism in edge cases."""

    def test_same_changes_different_order(self):
        """Same changes produce same result regardless of internal order."""
        previous = {
            "leg_count": 2,
            "leg_ids": ["id1", "id2"],
            "leg_types": ["spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": [],
            "volatility_sources": [],
        }

        current = {
            "leg_count": 3,
            "leg_ids": ["id1", "id2", "id3"],
            "leg_types": ["spread", "total", "player_prop"],
            "props": 1,
            "totals": 1,
            "correlation_flags": ["same_game"],
            "volatility_sources": ["player_prop"],
        }

        # Run delta multiple times
        delta1 = compute_snapshot_delta(previous, current)
        delta2 = compute_snapshot_delta(previous, current)
        delta3 = compute_snapshot_delta(previous, current)

        # All should be identical
        assert delta1.delta_sentence == delta2.delta_sentence == delta3.delta_sentence
        assert delta1.changes_detected == delta2.changes_detected == delta3.changes_detected
