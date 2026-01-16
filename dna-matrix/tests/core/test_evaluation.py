# tests/core/test_evaluation.py
"""
Tests for Evaluation Output Contract.

Tests the canonical PRD response for parlay evaluation.
"""
from uuid import UUID, uuid4

import pytest

from core.dna_enforcement import (
    BehaviorProfile,
    DNAProfile,
    RiskProfile,
)
from core.evaluation import (
    DNAInfo,
    EvaluationRequest,
    EvaluationResponse,
    InductorInfo,
    MetricsInfo,
    Recommendation,
    RecommendationAction,
    compute_recommendation,
    evaluate_from_request,
    evaluate_parlay,
)
from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextModifier,
    ContextModifiers,
)
from core.risk_inductor import RiskInductor


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
def default_profile() -> DNAProfile:
    """Default DNA profile for testing."""
    return DNAProfile(
        risk=RiskProfile(
            tolerance=50,
            max_parlay_legs=4,
            max_stake_pct=0.10,
            avoid_live_bets=False,
            avoid_props=False,
        ),
        behavior=BehaviorProfile(discipline=0.5),
    )


@pytest.fixture
def conservative_profile() -> DNAProfile:
    """Conservative DNA profile for testing."""
    return DNAProfile(
        risk=RiskProfile(
            tolerance=30,
            max_parlay_legs=2,
            max_stake_pct=0.05,
            avoid_live_bets=True,
            avoid_props=True,
        ),
        behavior=BehaviorProfile(discipline=0.8),
    )


def make_block(
    base_fragility: float,
    modifiers: ContextModifiers,
    bet_type: BetType = BetType.SPREAD,
    game_id: str | None = None,
    player_id: str | None = None,
    correlation_tags: tuple[str, ...] = (),
) -> BetBlock:
    """Helper to create a BetBlock."""
    return BetBlock(
        block_id=uuid4(),
        sport="NFL",
        game_id=game_id or f"game-{uuid4().hex[:8]}",
        bet_type=bet_type,
        selection="Test Selection",
        base_fragility=base_fragility,
        context_modifiers=modifiers,
        correlation_tags=correlation_tags,
        effective_fragility=base_fragility + modifiers.total_delta(),
        player_id=player_id,
        team_id=None,
    )


# =============================================================================
# Required Test Vectors
# =============================================================================


class TestRequiredVectors:
    """Required test vectors from specification."""

    def test_vector_a_minimal_evaluation(self, zero_modifiers: ContextModifiers):
        """
        Test A: Minimal evaluation - blocks only.

        Expected:
        - Response includes metrics, inductor, recommendations, correlations list
        - dna section present with empty violations (no dna_profile provided)
        - suggestions absent or empty (no candidates provided)
        """
        blocks = [
            make_block(10.0, zero_modifiers, game_id="game-1"),
            make_block(15.0, zero_modifiers, game_id="game-2"),
        ]

        response = evaluate_parlay(blocks)

        # Response structure
        assert isinstance(response, EvaluationResponse)
        assert isinstance(response.parlay_id, UUID)

        # Inductor present
        assert isinstance(response.inductor, InductorInfo)
        assert isinstance(response.inductor.level, RiskInductor)
        assert isinstance(response.inductor.explanation, str)
        assert len(response.inductor.explanation) > 0

        # Metrics present
        assert isinstance(response.metrics, MetricsInfo)
        assert response.metrics.final_fragility >= 0
        assert response.metrics.raw_fragility >= 0
        assert response.metrics.leg_penalty >= 0
        assert response.metrics.correlation_penalty >= 0
        assert response.metrics.correlation_multiplier >= 1.0

        # Correlations list present (possibly empty)
        assert isinstance(response.correlations, tuple)

        # DNA section present with empty violations (no profile)
        assert isinstance(response.dna, DNAInfo)
        assert response.dna.violations == ()
        assert response.dna.base_stake_cap is None  # No bankroll
        assert response.dna.recommended_stake is None  # No bankroll

        # Recommendation present
        assert isinstance(response.recommendation, Recommendation)
        assert isinstance(response.recommendation.action, RecommendationAction)
        assert isinstance(response.recommendation.reason, str)

        # Suggestions absent or empty (no candidates)
        assert response.suggestions is None or len(response.suggestions) == 0

    def test_vector_b_with_dna_and_bankroll(
        self, zero_modifiers: ContextModifiers, conservative_profile: DNAProfile
    ):
        """
        Test B: With DNA + bankroll.

        Expected:
        - baseStakeCap and recommendedStake populated
        - violations populated when triggered
        - recommendation downgraded if violations exist
        """
        # Create blocks that trigger violations:
        # - 4 legs exceeds max_parlay_legs=2
        # - player_prop violates avoid_props=True
        blocks = [
            make_block(10.0, zero_modifiers, bet_type=BetType.SPREAD),
            make_block(10.0, zero_modifiers, bet_type=BetType.PLAYER_PROP),
            make_block(10.0, zero_modifiers, bet_type=BetType.SPREAD),
            make_block(10.0, zero_modifiers, bet_type=BetType.SPREAD),
        ]

        response = evaluate_parlay(
            blocks,
            dna_profile=conservative_profile,
            bankroll=1000.0,
        )

        # Stake calculations populated
        assert response.dna.base_stake_cap is not None
        assert response.dna.base_stake_cap == 50.0  # 1000 * 0.05
        assert response.dna.recommended_stake is not None

        # Violations populated
        assert len(response.dna.violations) > 0
        assert "max_legs_exceeded" in response.dna.violations
        assert "props_not_allowed" in response.dna.violations

        # Recommendation downgraded due to violations
        # With LOADED/STABLE inductor + violations => at least REDUCE
        assert response.recommendation.action in [
            RecommendationAction.REDUCE,
            RecommendationAction.AVOID,
        ]

    def test_vector_c_with_candidates(self, zero_modifiers: ContextModifiers):
        """
        Test C: With candidates.

        Expected:
        - suggestions list populated and sorted
        """
        blocks = [make_block(15.0, zero_modifiers, game_id="game-1")]

        candidates = [
            make_block(5.0, zero_modifiers, game_id="game-2"),
            make_block(10.0, zero_modifiers, game_id="game-3"),
            make_block(3.0, zero_modifiers, game_id="game-4"),
        ]

        response = evaluate_parlay(
            blocks,
            candidates=candidates,
            max_suggestions=5,
        )

        # Suggestions populated
        assert response.suggestions is not None
        assert len(response.suggestions) == 3

        # Suggestions sorted by delta_fragility (ascending)
        deltas = [s.delta_fragility for s in response.suggestions]
        assert deltas == sorted(deltas)


# =============================================================================
# Response Structure Tests
# =============================================================================


class TestResponseStructure:
    """Tests for response structure and field types."""

    def test_all_required_fields_present(self, zero_modifiers: ContextModifiers):
        """All required fields are present in response."""
        blocks = [make_block(10.0, zero_modifiers)]
        response = evaluate_parlay(blocks)

        # Top-level fields
        assert hasattr(response, "parlay_id")
        assert hasattr(response, "inductor")
        assert hasattr(response, "metrics")
        assert hasattr(response, "correlations")
        assert hasattr(response, "dna")
        assert hasattr(response, "recommendation")
        assert hasattr(response, "suggestions")

        # Inductor fields
        assert hasattr(response.inductor, "level")
        assert hasattr(response.inductor, "explanation")

        # Metrics fields
        assert hasattr(response.metrics, "raw_fragility")
        assert hasattr(response.metrics, "final_fragility")
        assert hasattr(response.metrics, "leg_penalty")
        assert hasattr(response.metrics, "correlation_penalty")
        assert hasattr(response.metrics, "correlation_multiplier")

        # DNA fields
        assert hasattr(response.dna, "violations")
        assert hasattr(response.dna, "base_stake_cap")
        assert hasattr(response.dna, "recommended_stake")
        assert hasattr(response.dna, "max_legs")
        assert hasattr(response.dna, "fragility_tolerance")

        # Recommendation fields
        assert hasattr(response.recommendation, "action")
        assert hasattr(response.recommendation, "reason")

    def test_response_is_frozen(self, zero_modifiers: ContextModifiers):
        """Response dataclass is immutable."""
        blocks = [make_block(10.0, zero_modifiers)]
        response = evaluate_parlay(blocks)

        with pytest.raises(AttributeError):
            response.parlay_id = uuid4()


# =============================================================================
# Recommendation Logic Tests
# =============================================================================


class TestRecommendationLogic:
    """Tests for recommendation computation."""

    def test_stable_no_violations_accept(self):
        """STABLE without violations => ACCEPT."""
        rec = compute_recommendation(RiskInductor.STABLE, violations=())
        assert rec.action == RecommendationAction.ACCEPT

    def test_loaded_no_violations_accept(self):
        """LOADED without violations => ACCEPT."""
        rec = compute_recommendation(RiskInductor.LOADED, violations=())
        assert rec.action == RecommendationAction.ACCEPT

    def test_tense_no_violations_reduce(self):
        """TENSE without violations => REDUCE."""
        rec = compute_recommendation(RiskInductor.TENSE, violations=())
        assert rec.action == RecommendationAction.REDUCE

    def test_critical_no_violations_avoid(self):
        """CRITICAL without violations => AVOID."""
        rec = compute_recommendation(RiskInductor.CRITICAL, violations=())
        assert rec.action == RecommendationAction.AVOID

    def test_stable_with_violations_reduce(self):
        """STABLE with violations => REDUCE (downgraded)."""
        rec = compute_recommendation(
            RiskInductor.STABLE,
            violations=("some_violation",),
        )
        assert rec.action == RecommendationAction.REDUCE

    def test_loaded_with_violations_reduce(self):
        """LOADED with violations => REDUCE (downgraded)."""
        rec = compute_recommendation(
            RiskInductor.LOADED,
            violations=("some_violation",),
        )
        assert rec.action == RecommendationAction.REDUCE

    def test_tense_with_violations_avoid(self):
        """TENSE with violations => AVOID (downgraded)."""
        rec = compute_recommendation(
            RiskInductor.TENSE,
            violations=("some_violation",),
        )
        assert rec.action == RecommendationAction.AVOID

    def test_critical_with_violations_avoid(self):
        """CRITICAL with violations => AVOID (stays AVOID)."""
        rec = compute_recommendation(
            RiskInductor.CRITICAL,
            violations=("some_violation",),
        )
        assert rec.action == RecommendationAction.AVOID

    def test_recommendation_has_reason(self):
        """All recommendations have a reason."""
        for inductor in RiskInductor:
            for violations in [(), ("violation",)]:
                rec = compute_recommendation(inductor, violations)
                assert isinstance(rec.reason, str)
                assert len(rec.reason) > 0
                assert rec.reason.endswith(".")


# =============================================================================
# DNA Downgrade Tests
# =============================================================================


class TestDNADowngrade:
    """Tests to ensure DNA can only downgrade, never upgrade."""

    def test_dna_cannot_upgrade_from_avoid(
        self, zero_modifiers: ContextModifiers, default_profile: DNAProfile
    ):
        """DNA cannot upgrade from AVOID even without violations."""
        # Create blocks that trigger CRITICAL
        # High fragility (>75) + 4 legs = CRITICAL
        blocks = [
            make_block(25.0, zero_modifiers) for _ in range(4)
        ]

        response = evaluate_parlay(
            blocks,
            dna_profile=default_profile,
            bankroll=1000.0,
        )

        # Should be AVOID (from CRITICAL or downgraded)
        # DNA with no violations shouldn't upgrade to ACCEPT
        if response.inductor.level == RiskInductor.CRITICAL:
            assert response.recommendation.action == RecommendationAction.AVOID

    def test_violations_always_downgrade_or_maintain(
        self, zero_modifiers: ContextModifiers
    ):
        """Violations should downgrade action, never upgrade."""
        # Test all inductor levels
        for inductor in RiskInductor:
            no_violation_rec = compute_recommendation(inductor, violations=())
            with_violation_rec = compute_recommendation(
                inductor, violations=("test",)
            )

            # Action order: ACCEPT < REDUCE < AVOID
            action_order = {
                RecommendationAction.ACCEPT: 0,
                RecommendationAction.REDUCE: 1,
                RecommendationAction.AVOID: 2,
            }

            # With violations should be same or worse (higher order number)
            assert action_order[with_violation_rec.action] >= action_order[no_violation_rec.action]


# =============================================================================
# Determinism Tests
# =============================================================================


class TestDeterminism:
    """Tests to ensure outputs are deterministic."""

    def test_same_inputs_same_outputs(self, zero_modifiers: ContextModifiers):
        """Same inputs always produce same outputs."""
        blocks = [
            make_block(15.0, zero_modifiers, game_id="game-1"),
            make_block(10.0, zero_modifiers, game_id="game-2"),
        ]

        # Create blocks with fixed IDs for comparison
        block1 = BetBlock(
            block_id=UUID("12345678-1234-5678-1234-567812345678"),
            sport="NFL",
            game_id="game-1",
            bet_type=BetType.SPREAD,
            selection="Test",
            base_fragility=15.0,
            context_modifiers=zero_modifiers,
            correlation_tags=(),
            effective_fragility=15.0,
            player_id=None,
            team_id=None,
        )
        block2 = BetBlock(
            block_id=UUID("87654321-4321-8765-4321-876543218765"),
            sport="NFL",
            game_id="game-2",
            bet_type=BetType.SPREAD,
            selection="Test",
            base_fragility=10.0,
            context_modifiers=zero_modifiers,
            correlation_tags=(),
            effective_fragility=10.0,
            player_id=None,
            team_id=None,
        )

        fixed_blocks = [block1, block2]

        results = [evaluate_parlay(fixed_blocks) for _ in range(5)]

        # All results should have same values (except parlay_id)
        first = results[0]
        for result in results[1:]:
            assert result.inductor.level == first.inductor.level
            assert result.inductor.explanation == first.inductor.explanation
            assert result.metrics == first.metrics
            assert result.correlations == first.correlations
            assert result.dna == first.dna
            assert result.recommendation == first.recommendation


# =============================================================================
# EvaluationRequest Tests
# =============================================================================


class TestEvaluationRequest:
    """Tests for EvaluationRequest usage."""

    def test_evaluate_from_request(
        self, zero_modifiers: ContextModifiers, default_profile: DNAProfile
    ):
        """evaluate_from_request produces same result as evaluate_parlay."""
        blocks = [make_block(15.0, zero_modifiers)]

        request = EvaluationRequest(
            blocks=blocks,
            dna_profile=default_profile,
            bankroll=1000.0,
            candidates=None,
            max_suggestions=5,
        )

        response1 = evaluate_from_request(request)
        response2 = evaluate_parlay(
            blocks=blocks,
            dna_profile=default_profile,
            bankroll=1000.0,
            candidates=None,
            max_suggestions=5,
        )

        # Should have same values
        assert response1.inductor == response2.inductor
        assert response1.metrics == response2.metrics
        assert response1.dna == response2.dna
        assert response1.recommendation == response2.recommendation


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for full evaluation flow."""

    def test_empty_blocks(self, zero_modifiers: ContextModifiers):
        """Empty blocks list produces valid response."""
        response = evaluate_parlay([])

        assert isinstance(response, EvaluationResponse)
        assert response.inductor.level == RiskInductor.STABLE
        assert response.metrics.final_fragility == 0
        assert len(response.correlations) == 0

    def test_correlation_detection(self, zero_modifiers: ContextModifiers):
        """Correlations are detected and included in response."""
        # Same player multi-props should trigger correlation
        blocks = [
            make_block(
                10.0,
                zero_modifiers,
                bet_type=BetType.PLAYER_PROP,
                game_id="game-1",
                player_id="player-1",
            ),
            make_block(
                10.0,
                zero_modifiers,
                bet_type=BetType.PLAYER_PROP,
                game_id="game-1",
                player_id="player-1",
            ),
        ]

        response = evaluate_parlay(blocks)

        assert response.metrics.correlation_penalty > 0
        assert len(response.correlations) > 0

    def test_inductor_affects_recommendation(self, zero_modifiers: ContextModifiers):
        """Higher inductor levels produce more cautious recommendations."""
        # Low fragility -> STABLE -> ACCEPT
        low_blocks = [make_block(5.0, zero_modifiers)]
        low_response = evaluate_parlay(low_blocks)

        if low_response.inductor.level == RiskInductor.STABLE:
            assert low_response.recommendation.action == RecommendationAction.ACCEPT

    def test_suggestions_with_dna_profile(
        self, zero_modifiers: ContextModifiers, conservative_profile: DNAProfile
    ):
        """Suggestions respect DNA profile constraints."""
        blocks = [make_block(10.0, zero_modifiers, bet_type=BetType.SPREAD)]

        # Candidate that violates avoid_props
        prop_candidate = make_block(
            5.0,
            zero_modifiers,
            bet_type=BetType.PLAYER_PROP,
            game_id="game-2",
        )

        # Candidate that's OK
        spread_candidate = make_block(
            5.0,
            zero_modifiers,
            bet_type=BetType.SPREAD,
            game_id="game-3",
        )

        response = evaluate_parlay(
            blocks,
            dna_profile=conservative_profile,
            candidates=[prop_candidate, spread_candidate],
        )

        assert response.suggestions is not None
        assert len(response.suggestions) == 2

        # Find prop suggestion - should be dna_incompatible
        prop_suggestion = next(
            s for s in response.suggestions
            if s.candidate_block_id == prop_candidate.block_id
        )
        assert prop_suggestion.dna_compatible is False

        # Spread suggestion - should be compatible (assuming within leg limit)
        spread_suggestion = next(
            s for s in response.suggestions
            if s.candidate_block_id == spread_candidate.block_id
        )
        assert spread_suggestion.dna_compatible is True


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_profile_without_bankroll(
        self, zero_modifiers: ContextModifiers, default_profile: DNAProfile
    ):
        """DNA profile without bankroll extracts limits but no stake."""
        blocks = [make_block(10.0, zero_modifiers)]

        response = evaluate_parlay(
            blocks,
            dna_profile=default_profile,
            bankroll=None,
        )

        # Max legs and tolerance should be extracted
        assert response.dna.max_legs == default_profile.risk.max_parlay_legs
        assert response.dna.fragility_tolerance == default_profile.risk.tolerance

        # Stake calculations should be None
        assert response.dna.base_stake_cap is None
        assert response.dna.recommended_stake is None

    def test_zero_bankroll(
        self, zero_modifiers: ContextModifiers, default_profile: DNAProfile
    ):
        """Zero bankroll produces zero stake."""
        blocks = [make_block(10.0, zero_modifiers)]

        response = evaluate_parlay(
            blocks,
            dna_profile=default_profile,
            bankroll=0.0,
        )

        assert response.dna.base_stake_cap == 0.0
        assert response.dna.recommended_stake == 0.0

    def test_empty_candidates_list(self, zero_modifiers: ContextModifiers):
        """Empty candidates list produces empty suggestions."""
        blocks = [make_block(10.0, zero_modifiers)]

        response = evaluate_parlay(
            blocks,
            candidates=[],
        )

        # Empty list should produce None or empty tuple
        assert response.suggestions is None or len(response.suggestions) == 0

    def test_single_block(self, zero_modifiers: ContextModifiers):
        """Single block evaluation works."""
        blocks = [make_block(10.0, zero_modifiers)]

        response = evaluate_parlay(blocks)

        assert isinstance(response, EvaluationResponse)
        assert response.metrics.leg_penalty > 0  # 8 * 1^1.5 = 8
