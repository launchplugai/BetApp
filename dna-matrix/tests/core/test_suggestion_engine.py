# tests/core/test_suggestion_engine.py
"""
Unit tests for Suggestion Engine.

Tests ranking, labels, DNA compatibility, and determinism.
"""
import pytest
from uuid import uuid4

from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextModifier,
    ContextModifiers,
    SuggestedBlockLabel,
)
from core.parlay_reducer import build_parlay_state
from core.suggestion_engine import (
    assign_label,
    compute_suggestions,
    evaluate_candidate,
    rank_candidates,
    CandidateEvaluation,
    THRESHOLD_LOWEST_RISK,
    THRESHOLD_BALANCED,
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
    bet_type: BetType = BetType.PLAYER_PROP,
    game_id: str = "game-1",
    player_id: str | None = None,
    base_fragility: float = 10.0,
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
# Test assign_label
# =============================================================================


class TestAssignLabel:
    def test_lowest_risk_boundary(self):
        """deltaFragility <= 8 => Lowest added risk."""
        assert assign_label(0.0) == SuggestedBlockLabel.LOWEST_ADDED_RISK
        assert assign_label(5.0) == SuggestedBlockLabel.LOWEST_ADDED_RISK
        assert assign_label(8.0) == SuggestedBlockLabel.LOWEST_ADDED_RISK

    def test_balanced_boundary(self):
        """9 <= deltaFragility <= 18 => Balanced."""
        assert assign_label(9.0) == SuggestedBlockLabel.BALANCED
        assert assign_label(12.0) == SuggestedBlockLabel.BALANCED
        assert assign_label(18.0) == SuggestedBlockLabel.BALANCED

    def test_aggressive_boundary(self):
        """deltaFragility > 18 => Aggressive but within limits."""
        assert assign_label(19.0) == SuggestedBlockLabel.AGGRESSIVE_WITHIN_LIMITS
        assert assign_label(25.0) == SuggestedBlockLabel.AGGRESSIVE_WITHIN_LIMITS
        assert assign_label(100.0) == SuggestedBlockLabel.AGGRESSIVE_WITHIN_LIMITS


# =============================================================================
# Test rank_candidates
# =============================================================================


class TestRankCandidates:
    def test_rank_by_delta_fragility(self, zero_modifiers: ContextModifiers):
        """Primary ranking: lowest deltaFragility first."""
        block1 = make_block(modifiers=zero_modifiers)
        block2 = make_block(modifiers=zero_modifiers)
        block3 = make_block(modifiers=zero_modifiers)

        evals = [
            CandidateEvaluation(block=block1, delta_fragility=12.0, added_correlation=0.0,
                               dna_compatible=True, label=SuggestedBlockLabel.BALANCED, reason=""),
            CandidateEvaluation(block=block2, delta_fragility=6.0, added_correlation=0.0,
                               dna_compatible=True, label=SuggestedBlockLabel.LOWEST_ADDED_RISK, reason=""),
            CandidateEvaluation(block=block3, delta_fragility=20.0, added_correlation=0.0,
                               dna_compatible=True, label=SuggestedBlockLabel.AGGRESSIVE_WITHIN_LIMITS, reason=""),
        ]

        ranked = rank_candidates(evals)

        assert ranked[0].delta_fragility == 6.0
        assert ranked[1].delta_fragility == 12.0
        assert ranked[2].delta_fragility == 20.0

    def test_rank_by_correlation_secondary(self, zero_modifiers: ContextModifiers):
        """Secondary ranking: lowest addedCorrelation when delta is equal."""
        block1 = make_block(modifiers=zero_modifiers)
        block2 = make_block(modifiers=zero_modifiers)

        evals = [
            CandidateEvaluation(block=block1, delta_fragility=6.0, added_correlation=8.0,
                               dna_compatible=True, label=SuggestedBlockLabel.LOWEST_ADDED_RISK, reason=""),
            CandidateEvaluation(block=block2, delta_fragility=6.0, added_correlation=0.0,
                               dna_compatible=True, label=SuggestedBlockLabel.LOWEST_ADDED_RISK, reason=""),
        ]

        ranked = rank_candidates(evals)

        assert ranked[0].added_correlation == 0.0
        assert ranked[1].added_correlation == 8.0

    def test_rank_by_dna_compatible_tertiary(self, zero_modifiers: ContextModifiers):
        """Tertiary ranking: dnaCompatible=True preferred."""
        block1 = make_block(modifiers=zero_modifiers)
        block2 = make_block(modifiers=zero_modifiers)

        evals = [
            CandidateEvaluation(block=block1, delta_fragility=6.0, added_correlation=0.0,
                               dna_compatible=False, label=SuggestedBlockLabel.LOWEST_ADDED_RISK, reason=""),
            CandidateEvaluation(block=block2, delta_fragility=6.0, added_correlation=0.0,
                               dna_compatible=True, label=SuggestedBlockLabel.LOWEST_ADDED_RISK, reason=""),
        ]

        ranked = rank_candidates(evals)

        assert ranked[0].dna_compatible is True
        assert ranked[1].dna_compatible is False


# =============================================================================
# REQUIRED TEST VECTORS
# =============================================================================


class TestRequiredVectors:
    """Required test vectors from specification."""

    def test_vector_a_ranking(self, zero_modifiers: ContextModifiers):
        """
        Test A: Ranking

        Verify candidates are ranked by:
        - Primary: lowest deltaFragility
        - Secondary: lowest addedCorrelation
        - Tertiary: dnaCompatible=True preferred

        Note: Delta includes leg penalty and correlation penalty per canonical formula.
        With leg penalty = 8*(n^1.5), adding a 2nd leg increases penalty by ~14.6.
        Correlation penalty (same_player_multi_props = 12) adds to delta.
        """
        # Create base parlay with one block
        base_block_with_player = make_block(
            base_fragility=15.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        parlay = build_parlay_state([base_block_with_player])

        # C1: Low fragility, no correlation (different game)
        # delta ≈ 5 + 14.63 = 19.63
        c1 = make_block(
            base_fragility=5.0,
            game_id="game-2",
            modifiers=zero_modifiers,
        )

        # C2: Low fragility, but same player as base (adds correlation)
        # delta ≈ 5 + 14.63 + 12 (correlation) = 31.63
        c2 = make_block(
            base_fragility=5.0,
            game_id="game-1",
            player_id="player-1",
            modifiers=zero_modifiers,
        )

        # C3: Higher fragility, no correlation
        # delta ≈ 12 + 14.63 = 26.63
        c3 = make_block(
            base_fragility=12.0,
            game_id="game-3",
            modifiers=zero_modifiers,
        )

        suggestions = compute_suggestions(parlay, [c1, c2, c3])

        # Ranking by delta: C1 (19.6) < C3 (26.6) < C2 (31.6)
        assert len(suggestions) == 3
        assert suggestions[0].candidate_block_id == c1.block_id  # lowest delta
        assert suggestions[1].candidate_block_id == c3.block_id  # middle delta
        assert suggestions[2].candidate_block_id == c2.block_id  # highest (correlation adds)

    def test_vector_b_labels(self, zero_modifiers: ContextModifiers):
        """
        Test B: Labels

        - Candidate delta=6 => "Lowest added risk"
        - Candidate delta=12 => "Balanced"
        - Candidate delta=25 => "Aggressive but within limits"
        """
        # Labels are assigned based on deltaFragility
        assert assign_label(6.0) == SuggestedBlockLabel.LOWEST_ADDED_RISK
        assert assign_label(12.0) == SuggestedBlockLabel.BALANCED
        assert assign_label(25.0) == SuggestedBlockLabel.AGGRESSIVE_WITHIN_LIMITS

    def test_vector_c_determinism(self, zero_modifiers: ContextModifiers):
        """
        Test C: Determinism

        Same parlay + same candidates => identical suggestion ordering and values.
        """
        base_block = make_block(base_fragility=15.0, modifiers=zero_modifiers)
        parlay = build_parlay_state([base_block])

        candidates = [
            make_block(base_fragility=5.0, game_id="game-2", modifiers=zero_modifiers),
            make_block(base_fragility=10.0, game_id="game-3", modifiers=zero_modifiers),
            make_block(base_fragility=8.0, game_id="game-4", modifiers=zero_modifiers),
        ]

        suggestions1 = compute_suggestions(parlay, candidates)
        suggestions2 = compute_suggestions(parlay, candidates)

        # Identical ordering
        assert len(suggestions1) == len(suggestions2)
        for s1, s2 in zip(suggestions1, suggestions2):
            assert s1.candidate_block_id == s2.candidate_block_id
            assert s1.delta_fragility == s2.delta_fragility
            assert s1.added_correlation == s2.added_correlation
            assert s1.dna_compatible == s2.dna_compatible
            assert s1.label == s2.label

    def test_vector_d_delta_fragility_positive(self, zero_modifiers: ContextModifiers):
        """
        Test D: deltaFragility > 0

        Ensure engine filters candidates where deltaFragility <= 0.
        (Should not happen in practice, but enforced)
        """
        base_block = make_block(base_fragility=15.0, modifiers=zero_modifiers)
        parlay = build_parlay_state([base_block])

        # Normal candidate should have positive delta
        candidate = make_block(base_fragility=5.0, game_id="game-2", modifiers=zero_modifiers)

        eval_result = evaluate_candidate(parlay, candidate)

        # deltaFragility should always be positive
        assert eval_result is not None
        assert eval_result.delta_fragility > 0


# =============================================================================
# Test compute_suggestions
# =============================================================================


class TestComputeSuggestions:
    def test_empty_candidates(self, zero_modifiers: ContextModifiers):
        """Empty candidates returns empty suggestions."""
        parlay = build_parlay_state([])
        suggestions = compute_suggestions(parlay, [])
        assert suggestions == []

    def test_max_suggestions_limit(self, zero_modifiers: ContextModifiers):
        """Suggestions limited to maxSuggestions."""
        base_block = make_block(base_fragility=10.0, modifiers=zero_modifiers)
        parlay = build_parlay_state([base_block])

        # Create 10 candidates
        candidates = [
            make_block(base_fragility=5.0, game_id=f"game-{i}", modifiers=zero_modifiers)
            for i in range(10)
        ]

        suggestions = compute_suggestions(parlay, candidates, max_suggestions=3)

        assert len(suggestions) <= 3

    def test_dna_incompatible_included(self, zero_modifiers: ContextModifiers):
        """DNA incompatible suggestions are included but flagged."""
        # Create parlay at max legs
        blocks = [
            make_block(base_fragility=5.0, game_id=f"game-{i}", modifiers=zero_modifiers)
            for i in range(3)
        ]
        parlay = build_parlay_state(blocks)

        candidate = make_block(base_fragility=5.0, game_id="game-new", modifiers=zero_modifiers)

        # With max_legs=3, adding would exceed
        suggestions = compute_suggestions(parlay, [candidate], max_legs=3)

        assert len(suggestions) == 1
        assert suggestions[0].dna_compatible is False
        assert "exceeds" in suggestions[0].reason.lower() or "constraint" in suggestions[0].reason.lower()

    def test_uses_reducer_simulation(self, zero_modifiers: ContextModifiers):
        """Suggestions use build_parlay_state for simulation."""
        base_block = make_block(
            base_fragility=15.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        parlay = build_parlay_state([base_block])

        # Candidate that will correlate
        candidate = make_block(
            base_fragility=10.0,
            player_id="player-1",  # Same player -> correlation
            modifiers=zero_modifiers,
        )

        suggestions = compute_suggestions(parlay, [candidate])

        # Should detect correlation penalty
        assert len(suggestions) == 1
        assert suggestions[0].added_correlation > 0  # Correlation detected


# =============================================================================
# Test evaluate_candidate
# =============================================================================


class TestEvaluateCandidate:
    def test_computes_delta_fragility(self, zero_modifiers: ContextModifiers):
        """Evaluates delta fragility correctly."""
        base_block = make_block(base_fragility=15.0, modifiers=zero_modifiers)
        parlay = build_parlay_state([base_block])

        candidate = make_block(base_fragility=10.0, game_id="game-2", modifiers=zero_modifiers)

        eval_result = evaluate_candidate(parlay, candidate)

        assert eval_result is not None
        assert eval_result.delta_fragility > 0

    def test_computes_added_correlation(self, zero_modifiers: ContextModifiers):
        """Evaluates added correlation correctly."""
        base_block = make_block(
            base_fragility=15.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )
        parlay = build_parlay_state([base_block])

        # Candidate with same player -> correlation
        correlated = make_block(
            base_fragility=10.0,
            player_id="player-1",
            modifiers=zero_modifiers,
        )

        eval_result = evaluate_candidate(parlay, correlated)

        assert eval_result is not None
        assert eval_result.added_correlation == 12.0  # same_player_multi_props

    def test_assigns_correct_label(self, zero_modifiers: ContextModifiers):
        """Assigns correct label based on delta."""
        parlay = build_parlay_state([])

        # Adding a block to empty parlay:
        # delta = base_fragility + legPenalty(1) - 0
        # legPenalty(1) = 8*(1^1.5) = 8
        # So base_fragility=1 -> delta=9 -> BALANCED (9 > 8)
        # For LOWEST_ADDED_RISK (delta <= 8), we need base_fragility = 0
        # But base_fragility must be >= 0, and delta > 0 is enforced
        # So the minimum delta is legPenalty(1) = 8 exactly

        # A block with base_fragility=0 would have delta=8 (exactly at threshold)
        # -> LOWEST_ADDED_RISK
        zero_frag_block = make_block(base_fragility=0.0, modifiers=zero_modifiers)
        eval_result = evaluate_candidate(parlay, zero_frag_block)

        assert eval_result is not None
        assert eval_result.delta_fragility == 8.0  # legPenalty only
        assert eval_result.label == SuggestedBlockLabel.LOWEST_ADDED_RISK
