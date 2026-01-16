# tests/core/test_fragility_engine.py
"""
Unit tests for Fragility Engine.

All tests include concrete numeric expectations to verify exact formula implementation.

Canonical Formulas:
- effectiveFragility = baseFragility + sum(applied context deltas)
- legPenalty = 8 × (legs ^ 1.5)
- sumBlocks = sum(block.effectiveFragility for all blocks)
- rawFragility = sumBlocks + legPenalty + correlationPenalty
- finalFragility = rawFragility × correlationMultiplier, clamped [0, 100]
"""
import pytest
from uuid import uuid4

from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextModifier,
    ContextModifiers,
    ParlayMetrics,
)
from core.fragility_engine import (
    compute_effective_fragility,
    compute_leg_penalty,
    compute_sum_blocks,
    compute_raw_fragility,
    compute_final_fragility,
    compute_parlay_metrics,
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


def make_block(
    base_fragility: float,
    modifiers: ContextModifiers,
) -> BetBlock:
    """Helper to create a BetBlock with computed effective fragility."""
    return BetBlock.create(
        sport="NBA",
        game_id="test-game",
        bet_type=BetType.PLAYER_PROP,
        selection="Test Selection",
        base_fragility=base_fragility,
        context_modifiers=modifiers,
        correlation_tags=[],
    )


# =============================================================================
# Test compute_effective_fragility
# =============================================================================


class TestComputeEffectiveFragility:
    def test_no_modifiers_applied(self, zero_modifiers: ContextModifiers):
        """With no modifiers, effective equals base."""
        result = compute_effective_fragility(30.0, zero_modifiers)
        assert result == 30.0

    def test_only_weather_applied(self):
        """Test single modifier: base=22, weather delta=6 → effective=28."""
        modifiers = ContextModifiers(
            weather=ContextModifier(applied=True, delta=6.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        result = compute_effective_fragility(22.0, modifiers)
        assert result == 28.0

    def test_only_injury_applied(self):
        """Test single modifier: base=16, injury delta=4 → effective=20."""
        modifiers = ContextModifiers(
            weather=ContextModifier(applied=False, delta=0.0),
            injury=ContextModifier(applied=True, delta=4.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        result = compute_effective_fragility(16.0, modifiers)
        assert result == 20.0

    def test_all_modifiers_applied(self):
        """Test all four modifiers applied."""
        modifiers = ContextModifiers(
            weather=ContextModifier(applied=True, delta=1.0),
            injury=ContextModifier(applied=True, delta=2.0),
            trade=ContextModifier(applied=True, delta=3.0),
            role=ContextModifier(applied=True, delta=4.0),
        )
        result = compute_effective_fragility(10.0, modifiers)
        assert result == 20.0  # 10 + 1 + 2 + 3 + 4

    def test_invariant_effective_gte_base(self, zero_modifiers: ContextModifiers):
        """Effective fragility is always >= base fragility."""
        for base in [0.0, 10.0, 50.0, 100.0]:
            result = compute_effective_fragility(base, zero_modifiers)
            assert result >= base

    def test_zero_base_fragility(self):
        """Base of 0 still adds context deltas."""
        modifiers = ContextModifiers(
            weather=ContextModifier(applied=True, delta=5.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        result = compute_effective_fragility(0.0, modifiers)
        assert result == 5.0


# =============================================================================
# Test compute_leg_penalty
# =============================================================================


class TestComputeLegPenalty:
    def test_one_leg(self):
        """legPenalty = 8 × (1 ^ 1.5) = 8 × 1 = 8"""
        result = compute_leg_penalty(1)
        assert result == 8.0

    def test_two_legs(self):
        """legPenalty = 8 × (2 ^ 1.5) = 8 × 2.82842712... = 22.62741699..."""
        result = compute_leg_penalty(2)
        # Spec value: 22.62741696
        assert abs(result - 22.62741699796952) < 1e-6

    def test_three_legs(self):
        """legPenalty = 8 × (3 ^ 1.5) = 8 × 5.196... ≈ 41.569"""
        result = compute_leg_penalty(3)
        assert abs(result - 41.5692193816531) < 1e-10

    def test_four_legs(self):
        """legPenalty = 8 × (4 ^ 1.5) = 8 × 8 = 64"""
        result = compute_leg_penalty(4)
        assert result == 64.0

    def test_rejects_zero_legs(self):
        """Zero legs is invalid."""
        with pytest.raises(ValueError, match="num_legs must be >= 1"):
            compute_leg_penalty(0)

    def test_rejects_negative_legs(self):
        """Negative legs is invalid."""
        with pytest.raises(ValueError, match="num_legs must be >= 1"):
            compute_leg_penalty(-1)


# =============================================================================
# Test compute_sum_blocks
# =============================================================================


class TestComputeSumBlocks:
    def test_single_block(self, zero_modifiers: ContextModifiers):
        """Sum of single block is its effective fragility."""
        block = make_block(15.0, zero_modifiers)
        result = compute_sum_blocks([block])
        assert result == 15.0

    def test_multiple_blocks(self, zero_modifiers: ContextModifiers):
        """Sum of effective fragilities: 28 + 20 = 48."""
        block1_mods = ContextModifiers(
            weather=ContextModifier(applied=True, delta=6.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        block2_mods = ContextModifiers(
            weather=ContextModifier(applied=False, delta=0.0),
            injury=ContextModifier(applied=True, delta=4.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        blocks = [
            make_block(22.0, block1_mods),  # 22 + 6 = 28
            make_block(16.0, block2_mods),  # 16 + 4 = 20
        ]
        result = compute_sum_blocks(blocks)
        assert result == 48.0

    def test_empty_blocks(self):
        """Empty list returns 0."""
        result = compute_sum_blocks([])
        assert result == 0.0


# =============================================================================
# Test compute_raw_fragility
# =============================================================================


class TestComputeRawFragility:
    def test_formula(self):
        """rawFragility = sumBlocks + legPenalty + correlationPenalty"""
        # sumBlocks=48, legPenalty=22.62741696, correlationPenalty=10
        result = compute_raw_fragility(
            sum_blocks=48.0,
            leg_penalty=22.62741696,
            correlation_penalty=10.0,
        )
        assert abs(result - 80.62741696) < 1e-6

    def test_no_correlation(self):
        """rawFragility with zero correlation penalty."""
        result = compute_raw_fragility(
            sum_blocks=15.0,
            leg_penalty=8.0,
            correlation_penalty=0.0,
        )
        assert result == 23.0


# =============================================================================
# Test compute_final_fragility
# =============================================================================


class TestComputeFinalFragility:
    def test_multiplier_1_0(self):
        """finalFragility = rawFragility × 1.0 (no change)"""
        result = compute_final_fragility(
            raw_fragility=80.62741696,
            correlation_multiplier=1.0,
        )
        assert abs(result - 80.62741696) < 1e-6

    def test_multiplier_1_5_with_clamp(self):
        """finalFragility = 80.62741696 × 1.5 = 120.94... → clamped to 100"""
        result = compute_final_fragility(
            raw_fragility=80.62741696,
            correlation_multiplier=1.5,
        )
        assert result == 100.0

    def test_clamp_lower_bound(self):
        """Final fragility clamped to 0."""
        result = compute_final_fragility(
            raw_fragility=0.0,
            correlation_multiplier=1.0,
        )
        assert result == 0.0

    def test_exactly_100(self):
        """Test value exactly at upper bound."""
        result = compute_final_fragility(
            raw_fragility=100.0,
            correlation_multiplier=1.0,
        )
        assert result == 100.0

    def test_just_under_100(self):
        """Test value just under upper bound."""
        result = compute_final_fragility(
            raw_fragility=99.0,
            correlation_multiplier=1.0,
        )
        assert result == 99.0


# =============================================================================
# REQUIRED TEST VECTORS (from spec)
# =============================================================================


class TestCanonicalVectors:
    """
    Test vectors from the specification.
    These are the canonical tests that MUST pass.
    """

    def test_vector_a_single_block_no_context(self):
        """
        Test A: Single block, no context

        1 block: baseFragility=15, all modifiers applied=false, deltas=0
        correlationPenalty=0, correlationMultiplier=1.0

        Expected:
        - block.effectiveFragility = 15
        - legs = 1
        - legPenalty = 8 × (1^1.5) = 8
        - sumBlocks = 15
        - rawFragility = 15 + 8 + 0 = 23
        - finalFragility = 23 × 1.0 = 23
        """
        modifiers = ContextModifiers(
            weather=ContextModifier(applied=False, delta=0.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        block = make_block(15.0, modifiers)

        # Verify effective fragility
        assert block.effective_fragility == 15.0

        # Compute metrics
        metrics = compute_parlay_metrics(
            blocks=[block],
            correlation_penalty=0.0,
            correlation_multiplier=1.0,
        )

        assert metrics.leg_penalty == 8.0
        assert metrics.raw_fragility == 23.0  # 15 + 8 + 0
        assert metrics.final_fragility == 23.0

    def test_vector_b_two_blocks_context_applied(self):
        """
        Test B: 2 blocks, context applied

        Block1: base=22, weather applied=true delta=6, others 0 → effective=28
        Block2: base=16, injury applied=true delta=4, others 0 → effective=20

        correlationPenalty=10, correlationMultiplier=1.0

        Expected:
        - legs = 2
        - legPenalty = 8 × (2^1.5) = 8 × 2.82842712 = 22.62741696
        - sumBlocks = 28 + 20 = 48
        - rawFragility = 48 + 22.62741696 + 10 = 80.62741696
        - finalFragility = 80.62741696 × 1.0 = 80.62741696 (no clamp)
        """
        block1_mods = ContextModifiers(
            weather=ContextModifier(applied=True, delta=6.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        block2_mods = ContextModifiers(
            weather=ContextModifier(applied=False, delta=0.0),
            injury=ContextModifier(applied=True, delta=4.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )

        block1 = make_block(22.0, block1_mods)
        block2 = make_block(16.0, block2_mods)

        # Verify effective fragilities
        assert block1.effective_fragility == 28.0
        assert block2.effective_fragility == 20.0

        # Compute metrics
        metrics = compute_parlay_metrics(
            blocks=[block1, block2],
            correlation_penalty=10.0,
            correlation_multiplier=1.0,
        )

        # legPenalty = 8 × 2^1.5
        expected_leg_penalty = 8.0 * (2 ** 1.5)
        assert abs(metrics.leg_penalty - expected_leg_penalty) < 1e-10

        # rawFragility = 48 + 22.62741696 + 10 = 80.62741696
        expected_raw = 48.0 + expected_leg_penalty + 10.0
        assert abs(metrics.raw_fragility - expected_raw) < 1e-10
        assert abs(metrics.raw_fragility - 80.62741699796952) < 1e-6

        # finalFragility = rawFragility × 1.0 (no clamp needed)
        assert abs(metrics.final_fragility - 80.62741699796952) < 1e-6

    def test_vector_c_clamp(self):
        """
        Test C: Clamp test

        Same as Test B but correlationMultiplier=1.5

        Expected:
        - rawFragility = 80.62741696
        - finalFragility = 80.62741696 × 1.5 = 120.94112544
        - Clamped finalFragility = 100
        """
        block1_mods = ContextModifiers(
            weather=ContextModifier(applied=True, delta=6.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        block2_mods = ContextModifiers(
            weather=ContextModifier(applied=False, delta=0.0),
            injury=ContextModifier(applied=True, delta=4.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )

        block1 = make_block(22.0, block1_mods)
        block2 = make_block(16.0, block2_mods)

        metrics = compute_parlay_metrics(
            blocks=[block1, block2],
            correlation_penalty=10.0,
            correlation_multiplier=1.5,
        )

        # rawFragility same as Test B
        assert abs(metrics.raw_fragility - 80.62741699796952) < 1e-6

        # finalFragility clamped to 100
        assert metrics.final_fragility == 100.0


# =============================================================================
# Test compute_parlay_metrics
# =============================================================================


class TestComputeParlayMetrics:
    def test_rejects_empty_blocks(self):
        """Empty blocks list is invalid."""
        with pytest.raises(ValueError, match="blocks cannot be empty"):
            compute_parlay_metrics(
                blocks=[],
                correlation_penalty=0.0,
                correlation_multiplier=1.0,
            )

    def test_rejects_invalid_multiplier(self, zero_modifiers: ContextModifiers):
        """Invalid correlation multiplier is rejected."""
        blocks = [make_block(30.0, zero_modifiers)]
        with pytest.raises(ValueError, match="correlation_multiplier must be one of"):
            compute_parlay_metrics(
                blocks=blocks,
                correlation_penalty=0.0,
                correlation_multiplier=1.25,  # Invalid
            )

    def test_all_valid_multipliers(self, zero_modifiers: ContextModifiers):
        """All valid multipliers are accepted."""
        blocks = [make_block(20.0, zero_modifiers)]
        for mult in [1.0, 1.15, 1.3, 1.5]:
            metrics = compute_parlay_metrics(
                blocks=blocks,
                correlation_penalty=0.0,
                correlation_multiplier=mult,
            )
            assert metrics.correlation_multiplier == mult


# =============================================================================
# Test Invariants
# =============================================================================


class TestFragilityEngineInvariants:
    def test_effective_always_gte_base(self, zero_modifiers: ContextModifiers):
        """Effective fragility is always >= base fragility."""
        modifiers = ContextModifiers(
            weather=ContextModifier(applied=True, delta=5.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        for base in [0.0, 10.0, 25.0, 50.0, 75.0, 100.0]:
            effective = compute_effective_fragility(base, modifiers)
            assert effective >= base, f"Failed for base={base}"

    def test_final_always_in_bounds(self, zero_modifiers: ContextModifiers):
        """Final fragility is always in [0, 100]."""
        test_cases = [
            (10.0, 0.0, 1.0),   # Low
            (50.0, 0.0, 1.0),   # Medium
            (80.0, 20.0, 1.5),  # Would exceed 100
            (0.0, 0.0, 1.0),    # Minimum
        ]
        for base, corr_penalty, corr_mult in test_cases:
            blocks = [make_block(base, zero_modifiers)]
            metrics = compute_parlay_metrics(
                blocks=blocks,
                correlation_penalty=corr_penalty,
                correlation_multiplier=corr_mult,
            )
            assert 0.0 <= metrics.final_fragility <= 100.0

    def test_leg_penalty_monotonic(self):
        """Leg penalty increases with more legs."""
        prev_penalty = 0.0
        for legs in range(1, 11):
            penalty = compute_leg_penalty(legs)
            assert penalty > prev_penalty, f"Penalty not increasing at {legs} legs"
            prev_penalty = penalty
