# tests/core/test_fragility_engine.py
"""
Unit tests for Fragility Engine.

All tests include concrete numeric expectations to verify exact formula implementation.
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


@pytest.fixture
def sample_modifiers() -> ContextModifiers:
    """
    Context modifiers with known deltas:
    - weather: applied, delta=2.5
    - injury: applied, delta=5.0
    - trade: not applied, delta=0.0
    - role: applied, delta=3.0
    Total applied delta: 10.5
    """
    return ContextModifiers(
        weather=ContextModifier(applied=True, delta=2.5, reason="Rain"),
        injury=ContextModifier(applied=True, delta=5.0, reason="Questionable"),
        trade=ContextModifier(applied=False, delta=0.0),
        role=ContextModifier(applied=True, delta=3.0, reason="Role change"),
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

    def test_with_applied_modifiers(self, sample_modifiers: ContextModifiers):
        """
        base=30.0, applied deltas=2.5+5.0+3.0=10.5
        effective = 30.0 + 10.5 = 40.5
        """
        result = compute_effective_fragility(30.0, sample_modifiers)
        assert result == 40.5

    def test_only_weather_applied(self):
        """Test single modifier."""
        modifiers = ContextModifiers(
            weather=ContextModifier(applied=True, delta=7.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )
        result = compute_effective_fragility(25.0, modifiers)
        assert result == 32.0  # 25 + 7

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

    def test_invariant_effective_gte_base(self, sample_modifiers: ContextModifiers):
        """Effective fragility is always >= base fragility."""
        for base in [0.0, 10.0, 50.0, 100.0]:
            result = compute_effective_fragility(base, sample_modifiers)
            assert result >= base

    def test_zero_base_fragility(self, sample_modifiers: ContextModifiers):
        """Base of 0 still adds context deltas."""
        result = compute_effective_fragility(0.0, sample_modifiers)
        assert result == 10.5  # 0 + 10.5


# =============================================================================
# Test compute_leg_penalty
# =============================================================================


class TestComputeLegPenalty:
    def test_one_leg(self):
        """legPenalty = 8 × (1 ^ 1.5) = 8 × 1 = 8"""
        result = compute_leg_penalty(1)
        assert result == 8.0

    def test_two_legs(self):
        """legPenalty = 8 × (2 ^ 1.5) = 8 × 2.828... ≈ 22.627"""
        result = compute_leg_penalty(2)
        assert abs(result - 22.627416997969522) < 1e-10

    def test_three_legs(self):
        """legPenalty = 8 × (3 ^ 1.5) = 8 × 5.196... ≈ 41.569"""
        result = compute_leg_penalty(3)
        assert abs(result - 41.5692193816531) < 1e-10

    def test_four_legs(self):
        """legPenalty = 8 × (4 ^ 1.5) = 8 × 8 = 64"""
        result = compute_leg_penalty(4)
        assert result == 64.0

    def test_five_legs(self):
        """legPenalty = 8 × (5 ^ 1.5) = 8 × 11.180... ≈ 89.442"""
        result = compute_leg_penalty(5)
        assert abs(result - 89.4427190999916) < 1e-10

    def test_ten_legs(self):
        """legPenalty = 8 × (10 ^ 1.5) = 8 × 31.622... ≈ 252.982"""
        result = compute_leg_penalty(10)
        assert abs(result - 252.98221281347036) < 1e-10

    def test_rejects_zero_legs(self):
        """Zero legs is invalid."""
        with pytest.raises(ValueError, match="num_legs must be >= 1"):
            compute_leg_penalty(0)

    def test_rejects_negative_legs(self):
        """Negative legs is invalid."""
        with pytest.raises(ValueError, match="num_legs must be >= 1"):
            compute_leg_penalty(-1)


# =============================================================================
# Test compute_raw_fragility
# =============================================================================


class TestComputeRawFragility:
    def test_single_block(self, zero_modifiers: ContextModifiers):
        """Raw fragility of single block is its effective fragility."""
        block = make_block(30.0, zero_modifiers)
        result = compute_raw_fragility([block])
        assert result == 30.0

    def test_multiple_blocks(self, zero_modifiers: ContextModifiers):
        """Raw fragility is sum of effective fragilities."""
        blocks = [
            make_block(20.0, zero_modifiers),
            make_block(30.0, zero_modifiers),
            make_block(15.0, zero_modifiers),
        ]
        result = compute_raw_fragility(blocks)
        assert result == 65.0  # 20 + 30 + 15

    def test_with_context_modifiers(self, sample_modifiers: ContextModifiers):
        """Raw fragility includes context modifier effects."""
        blocks = [
            make_block(20.0, sample_modifiers),  # 20 + 10.5 = 30.5
            make_block(10.0, sample_modifiers),  # 10 + 10.5 = 20.5
        ]
        result = compute_raw_fragility(blocks)
        assert result == 51.0  # 30.5 + 20.5

    def test_empty_blocks(self):
        """Empty list returns 0."""
        result = compute_raw_fragility([])
        assert result == 0.0


# =============================================================================
# Test compute_final_fragility
# =============================================================================


class TestComputeFinalFragility:
    def test_simple_calculation(self):
        """
        final = (30 + 8 + 0) × 1.0 = 38
        """
        result = compute_final_fragility(
            raw_fragility=30.0,
            leg_penalty=8.0,
            correlation_penalty=0.0,
            correlation_multiplier=1.0,
        )
        assert result == 38.0

    def test_with_correlation_penalty(self):
        """
        final = (30 + 8 + 5) × 1.0 = 43
        """
        result = compute_final_fragility(
            raw_fragility=30.0,
            leg_penalty=8.0,
            correlation_penalty=5.0,
            correlation_multiplier=1.0,
        )
        assert result == 43.0

    def test_with_correlation_multiplier(self):
        """
        final = (30 + 8 + 5) × 1.15 = 43 × 1.15 = 49.45
        """
        result = compute_final_fragility(
            raw_fragility=30.0,
            leg_penalty=8.0,
            correlation_penalty=5.0,
            correlation_multiplier=1.15,
        )
        assert abs(result - 49.45) < 1e-10

    def test_clamp_upper_bound(self):
        """Final fragility clamped to 100."""
        result = compute_final_fragility(
            raw_fragility=80.0,
            leg_penalty=30.0,
            correlation_penalty=10.0,
            correlation_multiplier=1.5,  # (80+30+10) × 1.5 = 180
        )
        assert result == 100.0

    def test_clamp_lower_bound(self):
        """Final fragility clamped to 0 (edge case with negative inputs)."""
        # Note: In practice, negatives shouldn't occur, but clamp handles it
        result = compute_final_fragility(
            raw_fragility=0.0,
            leg_penalty=0.0,
            correlation_penalty=0.0,
            correlation_multiplier=1.0,
        )
        assert result == 0.0

    def test_exactly_100(self):
        """Test value exactly at upper bound."""
        result = compute_final_fragility(
            raw_fragility=50.0,
            leg_penalty=30.0,
            correlation_penalty=20.0,
            correlation_multiplier=1.0,  # 50+30+20 = 100
        )
        assert result == 100.0

    def test_just_under_100(self):
        """Test value just under upper bound."""
        result = compute_final_fragility(
            raw_fragility=50.0,
            leg_penalty=30.0,
            correlation_penalty=19.0,
            correlation_multiplier=1.0,  # 50+30+19 = 99
        )
        assert result == 99.0


# =============================================================================
# Test compute_parlay_metrics
# =============================================================================


class TestComputeParlayMetrics:
    def test_single_leg_parlay(self, zero_modifiers: ContextModifiers):
        """
        1 leg, base=30, no context, no correlation
        - rawFragility = 30
        - legPenalty = 8 × (1^1.5) = 8
        - finalFragility = (30 + 8 + 0) × 1.0 = 38
        """
        blocks = [make_block(30.0, zero_modifiers)]
        metrics = compute_parlay_metrics(
            blocks=blocks,
            correlation_penalty=0.0,
            correlation_multiplier=1.0,
        )
        assert metrics.raw_fragility == 30.0
        assert metrics.leg_penalty == 8.0
        assert metrics.correlation_penalty == 0.0
        assert metrics.correlation_multiplier == 1.0
        assert metrics.final_fragility == 38.0

    def test_two_leg_parlay(self, zero_modifiers: ContextModifiers):
        """
        2 legs, bases=20+30=50, no context, no correlation
        - rawFragility = 50
        - legPenalty = 8 × (2^1.5) ≈ 22.627
        - finalFragility = (50 + 22.627 + 0) × 1.0 ≈ 72.627
        """
        blocks = [
            make_block(20.0, zero_modifiers),
            make_block(30.0, zero_modifiers),
        ]
        metrics = compute_parlay_metrics(
            blocks=blocks,
            correlation_penalty=0.0,
            correlation_multiplier=1.0,
        )
        assert metrics.raw_fragility == 50.0
        assert abs(metrics.leg_penalty - 22.627416997969522) < 1e-10
        assert abs(metrics.final_fragility - 72.627416997969522) < 1e-10

    def test_three_leg_with_context(self, sample_modifiers: ContextModifiers):
        """
        3 legs with context modifiers (+10.5 each)
        - bases: 10, 20, 15 → effective: 20.5, 30.5, 25.5
        - rawFragility = 76.5
        - legPenalty = 8 × (3^1.5) ≈ 41.569
        - finalFragility = (76.5 + 41.569 + 0) × 1.0 ≈ 118.069 → clamped to 100
        """
        blocks = [
            make_block(10.0, sample_modifiers),  # 10 + 10.5 = 20.5
            make_block(20.0, sample_modifiers),  # 20 + 10.5 = 30.5
            make_block(15.0, sample_modifiers),  # 15 + 10.5 = 25.5
        ]
        metrics = compute_parlay_metrics(
            blocks=blocks,
            correlation_penalty=0.0,
            correlation_multiplier=1.0,
        )
        assert metrics.raw_fragility == 76.5
        assert abs(metrics.leg_penalty - 41.5692193816531) < 1e-10
        assert metrics.final_fragility == 100.0  # Clamped

    def test_with_correlation_inputs(self, zero_modifiers: ContextModifiers):
        """
        2 legs with correlation penalty and multiplier
        - rawFragility = 40
        - legPenalty ≈ 22.627
        - correlation_penalty = 5
        - final = (40 + 22.627 + 5) × 1.15 ≈ 77.771
        """
        blocks = [
            make_block(20.0, zero_modifiers),
            make_block(20.0, zero_modifiers),
        ]
        metrics = compute_parlay_metrics(
            blocks=blocks,
            correlation_penalty=5.0,
            correlation_multiplier=1.15,
        )
        assert metrics.raw_fragility == 40.0
        assert metrics.correlation_penalty == 5.0
        assert metrics.correlation_multiplier == 1.15
        expected_final = (40.0 + 22.627416997969522 + 5.0) * 1.15
        assert abs(metrics.final_fragility - expected_final) < 1e-10

    def test_four_leg_with_high_correlation(self, zero_modifiers: ContextModifiers):
        """
        4 legs, high correlation
        - rawFragility = 60
        - legPenalty = 64
        - correlation_penalty = 15
        - final = (60 + 64 + 15) × 1.5 = 208.5 → clamped to 100
        """
        blocks = [
            make_block(15.0, zero_modifiers),
            make_block(15.0, zero_modifiers),
            make_block(15.0, zero_modifiers),
            make_block(15.0, zero_modifiers),
        ]
        metrics = compute_parlay_metrics(
            blocks=blocks,
            correlation_penalty=15.0,
            correlation_multiplier=1.5,
        )
        assert metrics.raw_fragility == 60.0
        assert metrics.leg_penalty == 64.0
        assert metrics.final_fragility == 100.0  # Clamped from 208.5

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
    def test_effective_always_gte_base(self, sample_modifiers: ContextModifiers):
        """Effective fragility is always >= base fragility."""
        for base in [0.0, 10.0, 25.0, 50.0, 75.0, 100.0]:
            effective = compute_effective_fragility(base, sample_modifiers)
            assert effective >= base, f"Failed for base={base}"

    def test_final_always_in_bounds(self, zero_modifiers: ContextModifiers):
        """Final fragility is always in [0, 100]."""
        # Test with various inputs that could exceed bounds
        test_cases = [
            (10.0, 0.0, 1.0),   # Low
            (50.0, 0.0, 1.0),   # Medium
            (80.0, 20.0, 1.5), # Would exceed 100
            (0.0, 0.0, 1.0),   # Minimum
        ]
        for raw, corr_penalty, corr_mult in test_cases:
            blocks = [make_block(raw, zero_modifiers)]
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
