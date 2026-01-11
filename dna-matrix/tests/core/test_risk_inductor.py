# tests/core/test_risk_inductor.py
"""
Tests for Risk Inductor Engine.

Tests the mapping of parlay metrics to risk inductors:
STABLE, LOADED, TENSE, CRITICAL.
"""
import random
from uuid import uuid4

import pytest

from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextModifier,
    ContextModifiers,
    DNAEnforcement,
    ParlayMetrics,
    ParlayState,
)
from core.risk_inductor import (
    CRITICAL_CORRELATION_PENALTY,
    CRITICAL_MIN_LEGS,
    THRESHOLD_LOADED,
    THRESHOLD_STABLE,
    THRESHOLD_TENSE,
    InductorResult,
    RiskInductor,
    resolve_inductor,
    resolve_inductor_from_metrics,
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
    """Helper to create a BetBlock."""
    return BetBlock(
        block_id=uuid4(),
        sport="NFL",
        game_id=f"game-{uuid4().hex[:8]}",
        bet_type=BetType.SPREAD,
        selection="Test Selection",
        base_fragility=base_fragility,
        context_modifiers=modifiers,
        correlation_tags=(),
        effective_fragility=base_fragility + modifiers.total_delta(),
        player_id=None,
        team_id=None,
    )


def make_parlay_state(
    num_legs: int,
    final_fragility: float,
    correlation_penalty: float = 0.0,
    modifiers: ContextModifiers | None = None,
) -> ParlayState:
    """Helper to create a ParlayState with specific metrics."""
    if modifiers is None:
        modifiers = ContextModifiers(
            weather=ContextModifier(applied=False, delta=0.0),
            injury=ContextModifier(applied=False, delta=0.0),
            trade=ContextModifier(applied=False, delta=0.0),
            role=ContextModifier(applied=False, delta=0.0),
        )

    blocks = tuple(make_block(10.0, modifiers) for _ in range(num_legs))

    # Determine correlation multiplier from penalty
    if correlation_penalty <= 20:
        multiplier = 1.0
    elif correlation_penalty <= 35:
        multiplier = 1.15
    elif correlation_penalty <= 50:
        multiplier = 1.3
    else:
        multiplier = 1.5

    default_enforcement = DNAEnforcement(
        max_legs=10,
        fragility_tolerance=100.0,
        stake_cap=1000.0,
        violations=(),
    )

    return ParlayState(
        parlay_id=uuid4(),
        blocks=blocks,
        correlations=(),
        metrics=ParlayMetrics(
            raw_fragility=final_fragility,
            leg_penalty=8.0 * (num_legs ** 1.5) if num_legs > 0 else 0.0,
            correlation_penalty=correlation_penalty,
            correlation_multiplier=multiplier,
            final_fragility=final_fragility,
        ),
        dna_enforcement=default_enforcement,
    )


# =============================================================================
# Required Test Vectors (CANON)
# =============================================================================


class TestRequiredVectors:
    """Required test vectors from specification."""

    def test_vector_a_stable(self):
        """
        Test A:
        finalFragility=25, legs=1, correlationPenalty=0
        Expected: STABLE
        """
        result = resolve_inductor_from_metrics(
            final_fragility=25,
            num_legs=1,
            correlation_penalty=0,
        )
        assert result.inductor == RiskInductor.STABLE

    def test_vector_b_loaded(self):
        """
        Test B:
        finalFragility=50, legs=3, correlationPenalty=8
        Expected: LOADED
        """
        result = resolve_inductor_from_metrics(
            final_fragility=50,
            num_legs=3,
            correlation_penalty=8,
        )
        assert result.inductor == RiskInductor.LOADED

    def test_vector_c_tense(self):
        """
        Test C:
        finalFragility=65, legs=3, correlationPenalty=12
        Expected: TENSE
        """
        result = resolve_inductor_from_metrics(
            final_fragility=65,
            num_legs=3,
            correlation_penalty=12,
        )
        assert result.inductor == RiskInductor.TENSE

    def test_vector_d_tense_not_critical(self):
        """
        Test D:
        finalFragility=82, legs=2, correlationPenalty=0
        Expected: TENSE (NOT CRITICAL)

        CRITICAL requires fragility > 75 AND at least one escalation factor.
        Here fragility is 82 but no escalation factors present.
        """
        result = resolve_inductor_from_metrics(
            final_fragility=82,
            num_legs=2,
            correlation_penalty=0,
        )
        assert result.inductor == RiskInductor.TENSE
        assert result.inductor != RiskInductor.CRITICAL

    def test_vector_e_critical(self):
        """
        Test E:
        finalFragility=82, legs=4, correlationPenalty=22
        Expected: CRITICAL

        Has fragility > 75 with both escalation factors:
        - legs >= 4 ✓
        - correlationPenalty >= 20 ✓
        """
        result = resolve_inductor_from_metrics(
            final_fragility=82,
            num_legs=4,
            correlation_penalty=22,
        )
        assert result.inductor == RiskInductor.CRITICAL


# =============================================================================
# Threshold Boundary Tests
# =============================================================================


class TestThresholdBoundaries:
    """Tests for exact threshold boundaries."""

    def test_stable_at_30(self):
        """Fragility of exactly 30 is STABLE."""
        result = resolve_inductor_from_metrics(30, 1, 0)
        assert result.inductor == RiskInductor.STABLE

    def test_loaded_at_31(self):
        """Fragility of 31 is LOADED."""
        result = resolve_inductor_from_metrics(31, 1, 0)
        assert result.inductor == RiskInductor.LOADED

    def test_loaded_at_55(self):
        """Fragility of exactly 55 is LOADED."""
        result = resolve_inductor_from_metrics(55, 1, 0)
        assert result.inductor == RiskInductor.LOADED

    def test_tense_at_56(self):
        """Fragility of 56 is TENSE."""
        result = resolve_inductor_from_metrics(56, 1, 0)
        assert result.inductor == RiskInductor.TENSE

    def test_tense_at_75(self):
        """Fragility of exactly 75 is TENSE."""
        result = resolve_inductor_from_metrics(75, 1, 0)
        assert result.inductor == RiskInductor.TENSE

    def test_tense_at_76_without_escalation(self):
        """Fragility of 76 without escalation factors is TENSE."""
        result = resolve_inductor_from_metrics(76, 2, 10)
        assert result.inductor == RiskInductor.TENSE

    def test_critical_at_76_with_legs_escalation(self):
        """Fragility of 76 with 4+ legs is CRITICAL."""
        result = resolve_inductor_from_metrics(76, 4, 0)
        assert result.inductor == RiskInductor.CRITICAL

    def test_critical_at_76_with_correlation_escalation(self):
        """Fragility of 76 with correlationPenalty >= 20 is CRITICAL."""
        result = resolve_inductor_from_metrics(76, 2, 20)
        assert result.inductor == RiskInductor.CRITICAL


# =============================================================================
# CRITICAL Escalation Factor Tests
# =============================================================================


class TestCriticalEscalation:
    """Tests for CRITICAL escalation factors."""

    def test_critical_requires_fragility_above_75(self):
        """CRITICAL never triggers below fragility 76."""
        # Even with all escalation factors, fragility <= 75 means not CRITICAL
        result = resolve_inductor_from_metrics(
            final_fragility=75,
            num_legs=6,
            correlation_penalty=30,
            dna_violations=("violation1", "violation2"),
        )
        assert result.inductor == RiskInductor.TENSE

    def test_critical_with_legs_only(self):
        """CRITICAL triggers with legs >= 4 and fragility > 75."""
        result = resolve_inductor_from_metrics(
            final_fragility=80,
            num_legs=4,
            correlation_penalty=0,
        )
        assert result.inductor == RiskInductor.CRITICAL

    def test_critical_with_correlation_only(self):
        """CRITICAL triggers with correlationPenalty >= 20 and fragility > 75."""
        result = resolve_inductor_from_metrics(
            final_fragility=80,
            num_legs=2,
            correlation_penalty=20,
        )
        assert result.inductor == RiskInductor.CRITICAL

    def test_critical_with_violations_only(self):
        """CRITICAL triggers with DNA violations and fragility > 75."""
        result = resolve_inductor_from_metrics(
            final_fragility=80,
            num_legs=2,
            correlation_penalty=0,
            dna_violations=("some_violation",),
        )
        assert result.inductor == RiskInductor.CRITICAL

    def test_critical_correlation_boundary_19(self):
        """Correlation penalty of 19 does not trigger CRITICAL."""
        result = resolve_inductor_from_metrics(
            final_fragility=80,
            num_legs=2,
            correlation_penalty=19,
        )
        assert result.inductor == RiskInductor.TENSE

    def test_critical_correlation_boundary_20(self):
        """Correlation penalty of exactly 20 triggers CRITICAL."""
        result = resolve_inductor_from_metrics(
            final_fragility=80,
            num_legs=2,
            correlation_penalty=20,
        )
        assert result.inductor == RiskInductor.CRITICAL

    def test_critical_legs_boundary_3(self):
        """3 legs does not trigger CRITICAL."""
        result = resolve_inductor_from_metrics(
            final_fragility=80,
            num_legs=3,
            correlation_penalty=0,
        )
        assert result.inductor == RiskInductor.TENSE

    def test_critical_legs_boundary_4(self):
        """4 legs triggers CRITICAL."""
        result = resolve_inductor_from_metrics(
            final_fragility=80,
            num_legs=4,
            correlation_penalty=0,
        )
        assert result.inductor == RiskInductor.CRITICAL


# =============================================================================
# CRITICAL Rarity Tests (<15% of realistic cases)
# =============================================================================


class TestCriticalRarity:
    """Tests to ensure CRITICAL triggers in < 15% of realistic cases."""

    def test_critical_rarity_random_distribution(self):
        """
        CRITICAL should trigger in less than 15% of realistic random cases.

        Realistic ranges:
        - finalFragility: 10-100 (uniform)
        - legs: 1-6 (weighted toward 2-4)
        - correlationPenalty: 0-30 (weighted toward 0-15)
        """
        random.seed(42)  # Deterministic
        total_cases = 1000
        critical_count = 0

        for _ in range(total_cases):
            # Realistic fragility distribution
            final_fragility = random.uniform(10, 100)

            # Realistic leg distribution (most parlays are 2-4 legs)
            legs = random.choices(
                [1, 2, 3, 4, 5, 6],
                weights=[10, 30, 30, 20, 7, 3],
            )[0]

            # Realistic correlation penalty (usually low)
            correlation_penalty = random.choices(
                [0, 5, 10, 15, 20, 25, 30],
                weights=[40, 25, 15, 10, 5, 3, 2],
            )[0]

            result = resolve_inductor_from_metrics(
                final_fragility=final_fragility,
                num_legs=legs,
                correlation_penalty=correlation_penalty,
            )

            if result.inductor == RiskInductor.CRITICAL:
                critical_count += 1

        critical_percentage = (critical_count / total_cases) * 100

        # CRITICAL should be < 15%
        assert critical_percentage < 15, (
            f"CRITICAL triggered {critical_percentage:.1f}% of the time, "
            f"should be < 15%"
        )

    def test_critical_rarity_conservative_distribution(self):
        """
        CRITICAL should be even rarer with conservative betting patterns.

        Conservative bettors:
        - Lower fragility (10-60)
        - Fewer legs (1-3)
        - Lower correlation (0-10)
        """
        random.seed(123)
        total_cases = 1000
        critical_count = 0

        for _ in range(total_cases):
            final_fragility = random.uniform(10, 60)
            legs = random.choices([1, 2, 3], weights=[30, 50, 20])[0]
            correlation_penalty = random.choices(
                [0, 5, 10],
                weights=[60, 30, 10],
            )[0]

            result = resolve_inductor_from_metrics(
                final_fragility=final_fragility,
                num_legs=legs,
                correlation_penalty=correlation_penalty,
            )

            if result.inductor == RiskInductor.CRITICAL:
                critical_count += 1

        # Conservative patterns should never trigger CRITICAL
        # (fragility max 60, legs max 3, penalty max 10)
        assert critical_count == 0, (
            f"CRITICAL triggered {critical_count} times for conservative patterns"
        )


# =============================================================================
# Explanation Tests
# =============================================================================


class TestExplanations:
    """Tests for explanation generation."""

    def test_explanation_is_one_sentence(self):
        """Explanation should be one sentence (no periods except at end)."""
        for fragility in [20, 40, 60, 80]:
            for legs in [1, 3, 5]:
                for penalty in [0, 15, 25]:
                    # Skip invalid CRITICAL cases
                    if fragility > 75 and (legs < 4 and penalty < 20):
                        continue

                    result = resolve_inductor_from_metrics(fragility, legs, penalty)

                    # Should end with period
                    assert result.explanation.endswith(".")

                    # Should have exactly one period (at the end)
                    period_count = result.explanation.count(".")
                    assert period_count == 1, (
                        f"Expected 1 period, got {period_count}: {result.explanation}"
                    )

    def test_explanation_no_prediction_language(self):
        """Explanation should not contain prediction language."""
        prediction_words = [
            "will",
            "gonna",
            "should",
            "likely",
            "probably",
            "expect",
            "predict",
            "forecast",
            "chance",
            "odds",
        ]

        for fragility, legs, penalty in [
            (20, 1, 0),
            (40, 3, 8),
            (60, 3, 12),
            (80, 4, 22),
        ]:
            result = resolve_inductor_from_metrics(fragility, legs, penalty)

            for word in prediction_words:
                assert word not in result.explanation.lower(), (
                    f"Prediction word '{word}' found in: {result.explanation}"
                )

    def test_explanation_no_shaming_language(self):
        """Explanation should not contain shaming language."""
        shaming_words = [
            "stupid",
            "dumb",
            "bad",
            "terrible",
            "awful",
            "mistake",
            "wrong",
            "foolish",
            "risky",  # Allowed: "risk" but not judgmental framing
        ]

        for fragility, legs, penalty in [
            (20, 1, 0),
            (40, 3, 8),
            (60, 3, 12),
            (80, 4, 22),
        ]:
            result = resolve_inductor_from_metrics(fragility, legs, penalty)

            for word in shaming_words:
                assert word not in result.explanation.lower(), (
                    f"Shaming word '{word}' found in: {result.explanation}"
                )

    def test_stable_explanation(self):
        """STABLE explanation describes simple structure."""
        result = resolve_inductor_from_metrics(25, 1, 0)
        assert "simple" in result.explanation.lower() or "straightforward" in result.explanation.lower()

    def test_loaded_explanation(self):
        """LOADED explanation mentions assumptions and correlations."""
        result = resolve_inductor_from_metrics(50, 3, 8)
        assert "assumptions" in result.explanation.lower() or "correlation" in result.explanation.lower()

    def test_tense_explanation(self):
        """TENSE explanation mentions failure paths or structure."""
        result = resolve_inductor_from_metrics(65, 3, 12)
        assert "failure" in result.explanation.lower() or "structure" in result.explanation.lower() or "fragility" in result.explanation.lower()

    def test_critical_explanation(self):
        """CRITICAL explanation mentions fragility and contributing factors."""
        result = resolve_inductor_from_metrics(82, 4, 22)
        assert "fragility" in result.explanation.lower()


# =============================================================================
# ParlayState Integration Tests
# =============================================================================


class TestParlayStateIntegration:
    """Tests using full ParlayState objects."""

    def test_resolve_with_parlay_state(self, zero_modifiers: ContextModifiers):
        """resolve_inductor works with ParlayState."""
        parlay = make_parlay_state(
            num_legs=3,
            final_fragility=50,
            correlation_penalty=8,
        )

        result = resolve_inductor(parlay)

        assert result.inductor == RiskInductor.LOADED

    def test_resolve_with_dna_violations(self, zero_modifiers: ContextModifiers):
        """DNA violations trigger CRITICAL when fragility > 75."""
        parlay = make_parlay_state(
            num_legs=2,
            final_fragility=80,
            correlation_penalty=0,
        )

        # Without violations: TENSE
        result_no_violations = resolve_inductor(parlay)
        assert result_no_violations.inductor == RiskInductor.TENSE

        # With violations: CRITICAL
        result_with_violations = resolve_inductor(
            parlay,
            dna_violations=("fragility_over_tolerance",),
        )
        assert result_with_violations.inductor == RiskInductor.CRITICAL


# =============================================================================
# Determinism Tests
# =============================================================================


class TestDeterminism:
    """Tests to ensure outputs are deterministic."""

    def test_same_inputs_same_outputs(self):
        """Same inputs always produce same outputs."""
        for _ in range(10):
            result1 = resolve_inductor_from_metrics(
                final_fragility=65,
                num_legs=3,
                correlation_penalty=12,
            )
            result2 = resolve_inductor_from_metrics(
                final_fragility=65,
                num_legs=3,
                correlation_penalty=12,
            )

            assert result1.inductor == result2.inductor
            assert result1.explanation == result2.explanation

    def test_deterministic_across_all_thresholds(self):
        """Determinism holds across all threshold boundaries."""
        test_cases = [
            (25, 1, 0),   # STABLE
            (30, 1, 0),   # STABLE boundary
            (31, 1, 0),   # LOADED boundary
            (50, 3, 8),   # LOADED
            (55, 1, 0),   # LOADED boundary
            (56, 1, 0),   # TENSE boundary
            (65, 3, 12),  # TENSE
            (75, 1, 0),   # TENSE boundary
            (76, 4, 0),   # CRITICAL boundary
            (82, 4, 22),  # CRITICAL
        ]

        for fragility, legs, penalty in test_cases:
            results = [
                resolve_inductor_from_metrics(fragility, legs, penalty)
                for _ in range(5)
            ]

            # All results should be identical
            first = results[0]
            for result in results[1:]:
                assert result.inductor == first.inductor
                assert result.explanation == first.explanation


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_zero_fragility(self):
        """Zero fragility is STABLE."""
        result = resolve_inductor_from_metrics(0, 1, 0)
        assert result.inductor == RiskInductor.STABLE

    def test_max_fragility(self):
        """Max fragility (100) with escalation is CRITICAL."""
        result = resolve_inductor_from_metrics(100, 4, 20)
        assert result.inductor == RiskInductor.CRITICAL

    def test_max_fragility_no_escalation(self):
        """Max fragility without escalation is TENSE."""
        result = resolve_inductor_from_metrics(100, 2, 0)
        assert result.inductor == RiskInductor.TENSE

    def test_empty_violations_tuple(self):
        """Empty violations tuple does not trigger CRITICAL."""
        result = resolve_inductor_from_metrics(
            final_fragility=80,
            num_legs=2,
            correlation_penalty=0,
            dna_violations=(),
        )
        assert result.inductor == RiskInductor.TENSE

    def test_none_violations(self):
        """None violations does not trigger CRITICAL."""
        result = resolve_inductor_from_metrics(
            final_fragility=80,
            num_legs=2,
            correlation_penalty=0,
            dna_violations=None,
        )
        assert result.inductor == RiskInductor.TENSE

    def test_single_leg_high_fragility(self):
        """Single leg with high fragility is TENSE without escalation."""
        result = resolve_inductor_from_metrics(
            final_fragility=90,
            num_legs=1,
            correlation_penalty=0,
        )
        assert result.inductor == RiskInductor.TENSE
