# tests/core/test_parlay_reducer.py
"""
Unit tests for Parlay State Reducer.

Tests the "spine" of the Parlay Builder - deterministic ParlayState construction.
"""
import pytest
from uuid import uuid4

from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextModifier,
    ContextModifiers,
    ParlayState,
)
from core.parlay_reducer import (
    build_parlay_state,
    add_block,
    remove_block,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def zero_modifiers() -> ContextModifiers:
    """Context modifiers with no applied changes."""
    return ContextModifiers(
        weather=ContextModifier(applied=False, delta=0.0),
        injury=ContextModifier(applied=False, delta=0.0),
        trade=ContextModifier(applied=False, delta=0.0),
        role=ContextModifier(applied=False, delta=0.0),
    )


@pytest.fixture
def high_fragility_modifiers() -> ContextModifiers:
    """Context modifiers that add significant fragility."""
    return ContextModifiers(
        weather=ContextModifier(applied=True, delta=15.0),
        injury=ContextModifier(applied=True, delta=20.0),
        trade=ContextModifier(applied=True, delta=10.0),
        role=ContextModifier(applied=True, delta=5.0),
    )


def make_block(
    bet_type: BetType = BetType.PLAYER_PROP,
    game_id: str = "game-1",
    player_id: str | None = None,
    base_fragility: float = 20.0,
    modifiers: ContextModifiers | None = None,
    correlation_tags: list[str] | None = None,
) -> BetBlock:
    """Helper to create a BetBlock for testing."""
    if modifiers is None:
        modifiers = ContextModifiers(
            weather=ContextModifier(applied=False, delta=0.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
    return BetBlock.create(
        sport="NFL",
        game_id=game_id,
        bet_type=bet_type,
        selection="Test Selection",
        base_fragility=base_fragility,
        context_modifiers=modifiers,
        correlation_tags=correlation_tags or [],
        player_id=player_id,
    )


# =============================================================================
# Test build_parlay_state
# =============================================================================


class TestBuildParlayState:
    def test_empty_parlay(self):
        """Empty parlay has zero metrics."""
        parlay = build_parlay_state([])

        assert parlay.blocks == ()
        assert parlay.correlations == ()
        assert parlay.metrics.raw_fragility == 0.0
        assert parlay.metrics.leg_penalty == 0.0
        assert parlay.metrics.correlation_penalty == 0.0
        assert parlay.metrics.correlation_multiplier == 1.0
        assert parlay.metrics.final_fragility == 0.0

    def test_single_block(self, zero_modifiers: ContextModifiers):
        """Single block parlay computes metrics correctly."""
        block = make_block(base_fragility=15.0, modifiers=zero_modifiers)
        parlay = build_parlay_state([block])

        assert len(parlay.blocks) == 1
        assert parlay.correlations == ()  # No correlations with single block
        assert parlay.metrics.leg_penalty == 8.0  # 8 × (1^1.5)
        # rawFragility = 15 + 8 + 0 = 23
        assert parlay.metrics.raw_fragility == 23.0
        assert parlay.metrics.final_fragility == 23.0

    def test_two_blocks_no_correlation(self, zero_modifiers: ContextModifiers):
        """Two uncorrelated blocks."""
        block1 = make_block(base_fragility=20.0, game_id="game-1", modifiers=zero_modifiers)
        block2 = make_block(base_fragility=20.0, game_id="game-2", modifiers=zero_modifiers)
        parlay = build_parlay_state([block1, block2])

        assert len(parlay.blocks) == 2
        assert parlay.correlations == ()
        assert parlay.metrics.correlation_penalty == 0.0
        assert parlay.metrics.correlation_multiplier == 1.0

    def test_parlay_id_preserved(self, zero_modifiers: ContextModifiers):
        """Parlay ID is preserved when provided."""
        custom_id = uuid4()
        block = make_block(modifiers=zero_modifiers)
        parlay = build_parlay_state([block], parlay_id=custom_id)

        assert parlay.parlay_id == custom_id

    def test_parlay_id_generated(self, zero_modifiers: ContextModifiers):
        """Parlay ID is generated when not provided."""
        block = make_block(modifiers=zero_modifiers)
        parlay = build_parlay_state([block])

        assert parlay.parlay_id is not None


# =============================================================================
# REQUIRED TEST VECTORS
# =============================================================================


class TestRequiredVectors:
    """Required test vectors from specification."""

    def test_vector_a_add_remove_recompute(self, zero_modifiers: ContextModifiers):
        """
        Test A: Add/remove recompute

        Start empty -> add Block1 -> add Block2 -> remove Block1
        Expected:
        - metrics reflect current blocks only
        - correlations recomputed (no references to removed block)
        - legPenalty updates with legs count
        """
        # Start empty
        parlay = build_parlay_state([])
        assert len(parlay.blocks) == 0
        assert parlay.metrics.leg_penalty == 0.0

        # Add Block1 (player prop, player-1)
        block1 = make_block(
            base_fragility=20.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        parlay = add_block(parlay, block1)
        assert len(parlay.blocks) == 1
        assert parlay.metrics.leg_penalty == 8.0  # 8 × (1^1.5) = 8

        # Add Block2 (player prop, player-1 - correlated with Block1)
        block2 = make_block(
            base_fragility=25.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        parlay = add_block(parlay, block2)
        assert len(parlay.blocks) == 2
        assert parlay.metrics.leg_penalty == 8.0 * (2 ** 1.5)  # ≈22.627
        assert parlay.metrics.correlation_penalty == 12.0  # same_player
        assert len(parlay.correlations) == 1

        # Verify correlation references both blocks
        corr = parlay.correlations[0]
        assert corr.block_a in (block1.block_id, block2.block_id)
        assert corr.block_b in (block1.block_id, block2.block_id)

        # Remove Block1
        parlay = remove_block(parlay, block1.block_id)
        assert len(parlay.blocks) == 1
        assert parlay.blocks[0].block_id == block2.block_id
        assert parlay.metrics.leg_penalty == 8.0  # Back to 1 leg
        assert parlay.metrics.correlation_penalty == 0.0  # No correlation with single block
        assert len(parlay.correlations) == 0  # No references to removed block

    def test_vector_b_correlation_integration(self, zero_modifiers: ContextModifiers):
        """
        Test B: Correlation integration

        Use 2 blocks that trigger same_player_multi_props (+12)
        Expected:
        - ParlayState.correlations has exactly 1 record
        - correlationPenalty=12
        - correlationMultiplier=1.0
        - finalFragility computed using penalty
        """
        block1 = make_block(
            bet_type=BetType.PLAYER_PROP,
            base_fragility=20.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        block2 = make_block(
            bet_type=BetType.PLAYER_PROP,
            base_fragility=20.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        parlay = build_parlay_state([block1, block2])

        # Correlation checks
        assert len(parlay.correlations) == 1
        assert parlay.correlations[0].penalty == 12.0
        assert parlay.correlations[0].type == "same_player_multi_props"

        # Metrics checks
        assert parlay.metrics.correlation_penalty == 12.0
        assert parlay.metrics.correlation_multiplier == 1.0  # ≤20 -> 1.0

        # finalFragility computation
        # sumBlocks = 20 + 20 = 40
        # legPenalty = 8 × (2^1.5) ≈ 22.627
        # rawFragility = 40 + 22.627 + 12 ≈ 74.627
        # finalFragility = 74.627 × 1.0 = 74.627
        expected_leg_penalty = 8.0 * (2 ** 1.5)
        expected_raw = 40.0 + expected_leg_penalty + 12.0
        assert abs(parlay.metrics.raw_fragility - expected_raw) < 1e-10
        assert abs(parlay.metrics.final_fragility - expected_raw) < 1e-10

    def test_vector_c_clamp_integration(self, high_fragility_modifiers: ContextModifiers):
        """
        Test C: Clamp integration

        Use blocks + correlations such that finalFragility > 100
        Expected:
        - finalFragility == 100
        """
        # High fragility blocks with correlations
        # base=30, modifiers add 50 -> effective=80 each
        block1 = make_block(
            bet_type=BetType.PLAYER_PROP,
            base_fragility=30.0,
            player_id="player-1",
            modifiers=high_fragility_modifiers,
        )
        block2 = make_block(
            bet_type=BetType.PLAYER_PROP,
            base_fragility=30.0,
            player_id="player-1",
            modifiers=high_fragility_modifiers,
        )
        block3 = make_block(
            bet_type=BetType.PLAYER_PROP,
            base_fragility=30.0,
            player_id="player-1",
            modifiers=high_fragility_modifiers,
        )

        parlay = build_parlay_state([block1, block2, block3])

        # effective = 30 + 50 = 80 each
        # sumBlocks = 240
        # legPenalty = 8 × (3^1.5) ≈ 41.569
        # correlationPenalty = 3 pairs × 12 = 36
        # multiplier = 1.3 (36 is in 36-50 range)
        # rawFragility = 240 + 41.569 + 36 ≈ 317.569
        # unclamped = 317.569 × 1.3 ≈ 412.84
        # clamped = 100

        assert parlay.metrics.final_fragility == 100.0

    def test_vector_d_determinism(self, zero_modifiers: ContextModifiers):
        """
        Test D: Determinism

        Build same parlay twice from same inputs
        Expected:
        - identical metrics and correlation outputs
        """
        block1 = make_block(
            bet_type=BetType.PLAYER_PROP,
            base_fragility=20.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        block2 = make_block(
            bet_type=BetType.PLAYER_PROP,
            base_fragility=25.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )

        # Use same parlay_id for comparison
        parlay_id = uuid4()

        parlay1 = build_parlay_state([block1, block2], parlay_id=parlay_id)
        parlay2 = build_parlay_state([block1, block2], parlay_id=parlay_id)

        # Metrics must be identical
        assert parlay1.metrics.raw_fragility == parlay2.metrics.raw_fragility
        assert parlay1.metrics.leg_penalty == parlay2.metrics.leg_penalty
        assert parlay1.metrics.correlation_penalty == parlay2.metrics.correlation_penalty
        assert parlay1.metrics.correlation_multiplier == parlay2.metrics.correlation_multiplier
        assert parlay1.metrics.final_fragility == parlay2.metrics.final_fragility

        # Correlations must be identical
        assert len(parlay1.correlations) == len(parlay2.correlations)
        for c1, c2 in zip(parlay1.correlations, parlay2.correlations):
            assert c1.block_a == c2.block_a
            assert c1.block_b == c2.block_b
            assert c1.type == c2.type
            assert c1.penalty == c2.penalty


# =============================================================================
# Test add_block
# =============================================================================


class TestAddBlock:
    def test_add_to_empty(self, zero_modifiers: ContextModifiers):
        """Add block to empty parlay."""
        parlay = build_parlay_state([])
        block = make_block(modifiers=zero_modifiers)

        new_parlay = add_block(parlay, block)

        assert len(new_parlay.blocks) == 1
        assert new_parlay.blocks[0].block_id == block.block_id

    def test_add_preserves_parlay_id(self, zero_modifiers: ContextModifiers):
        """Adding block preserves parlay ID."""
        parlay_id = uuid4()
        parlay = build_parlay_state([], parlay_id=parlay_id)
        block = make_block(modifiers=zero_modifiers)

        new_parlay = add_block(parlay, block)

        assert new_parlay.parlay_id == parlay_id

    def test_add_recomputes_all(self, zero_modifiers: ContextModifiers):
        """Adding block recomputes all derived fields."""
        block1 = make_block(base_fragility=20.0, modifiers=zero_modifiers)
        parlay = build_parlay_state([block1])

        # Verify initial state
        assert parlay.metrics.leg_penalty == 8.0

        block2 = make_block(base_fragility=30.0, modifiers=zero_modifiers)
        new_parlay = add_block(parlay, block2)

        # Leg penalty should update
        assert abs(new_parlay.metrics.leg_penalty - 8.0 * (2 ** 1.5)) < 1e-10

    def test_original_unchanged(self, zero_modifiers: ContextModifiers):
        """Original parlay is not modified."""
        block1 = make_block(modifiers=zero_modifiers)
        parlay = build_parlay_state([block1])
        original_len = len(parlay.blocks)

        block2 = make_block(modifiers=zero_modifiers)
        add_block(parlay, block2)

        # Original should be unchanged
        assert len(parlay.blocks) == original_len


# =============================================================================
# Test remove_block
# =============================================================================


class TestRemoveBlock:
    def test_remove_existing(self, zero_modifiers: ContextModifiers):
        """Remove existing block."""
        block1 = make_block(modifiers=zero_modifiers)
        block2 = make_block(modifiers=zero_modifiers)
        parlay = build_parlay_state([block1, block2])

        new_parlay = remove_block(parlay, block1.block_id)

        assert len(new_parlay.blocks) == 1
        assert new_parlay.blocks[0].block_id == block2.block_id

    def test_remove_not_found(self, zero_modifiers: ContextModifiers):
        """Remove non-existent block raises error."""
        block = make_block(modifiers=zero_modifiers)
        parlay = build_parlay_state([block])

        with pytest.raises(ValueError, match="not found"):
            remove_block(parlay, uuid4())

    def test_remove_preserves_parlay_id(self, zero_modifiers: ContextModifiers):
        """Removing block preserves parlay ID."""
        parlay_id = uuid4()
        block1 = make_block(modifiers=zero_modifiers)
        block2 = make_block(modifiers=zero_modifiers)
        parlay = build_parlay_state([block1, block2], parlay_id=parlay_id)

        new_parlay = remove_block(parlay, block1.block_id)

        assert new_parlay.parlay_id == parlay_id

    def test_remove_to_empty(self, zero_modifiers: ContextModifiers):
        """Remove last block results in empty parlay."""
        block = make_block(modifiers=zero_modifiers)
        parlay = build_parlay_state([block])

        new_parlay = remove_block(parlay, block.block_id)

        assert len(new_parlay.blocks) == 0
        assert new_parlay.metrics.raw_fragility == 0.0

    def test_remove_clears_correlations(self, zero_modifiers: ContextModifiers):
        """Removing block clears correlations involving that block."""
        block1 = make_block(
            bet_type=BetType.PLAYER_PROP,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        block2 = make_block(
            bet_type=BetType.PLAYER_PROP,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        parlay = build_parlay_state([block1, block2])

        # Should have correlation
        assert len(parlay.correlations) == 1

        new_parlay = remove_block(parlay, block1.block_id)

        # Correlation should be gone
        assert len(new_parlay.correlations) == 0

    def test_original_unchanged(self, zero_modifiers: ContextModifiers):
        """Original parlay is not modified."""
        block1 = make_block(modifiers=zero_modifiers)
        block2 = make_block(modifiers=zero_modifiers)
        parlay = build_parlay_state([block1, block2])
        original_len = len(parlay.blocks)

        remove_block(parlay, block1.block_id)

        # Original should be unchanged
        assert len(parlay.blocks) == original_len


# =============================================================================
# Test Order of Operations
# =============================================================================


class TestOrderOfOperations:
    def test_effective_fragility_used(self, zero_modifiers: ContextModifiers):
        """Effective fragility (with context) is used in computations."""
        modifiers = ContextModifiers(
            weather=ContextModifier(applied=True, delta=10.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        block = make_block(base_fragility=20.0, modifiers=modifiers)

        # effective = 20 + 10 = 30
        assert block.effective_fragility == 30.0

        parlay = build_parlay_state([block])

        # sumBlocks should use effective fragility
        # rawFragility = 30 + 8 + 0 = 38
        assert parlay.metrics.raw_fragility == 38.0

    def test_correlations_before_metrics(self, zero_modifiers: ContextModifiers):
        """Correlations are computed before metrics (penalty affects metrics)."""
        block1 = make_block(
            bet_type=BetType.PLAYER_PROP,
            base_fragility=20.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        block2 = make_block(
            bet_type=BetType.PLAYER_PROP,
            base_fragility=20.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        parlay = build_parlay_state([block1, block2])

        # Correlation penalty should be included in rawFragility
        # sumBlocks = 40, legPenalty ≈ 22.627, corrPenalty = 12
        # rawFragility should include all three
        assert parlay.metrics.correlation_penalty == 12.0
        assert parlay.metrics.raw_fragility > 40.0 + 12.0  # Includes leg penalty too
