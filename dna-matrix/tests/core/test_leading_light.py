# tests/core/test_leading_light.py
"""
Unit tests for Leading Light core types.

These tests verify:
- Schemas match documentation exactly
- Invalid inputs are rejected
- System invariants are enforced
- Edge cases are handled correctly
"""
import pytest
from uuid import UUID, uuid4

from core.models.leading_light import (
    # Enums
    BetType,
    ContextSignalType,
    ContextTarget,
    SuggestedBlockLabel,
    # Supporting types
    ContextModifier,
    ContextModifiers,
    ContextImpact,
    Correlation,
    ParlayMetrics,
    DNAEnforcement,
    # Core types
    BetBlock,
    ContextSignal,
    ParlayState,
    SuggestedBlock,
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
    """Context modifiers with some applied changes."""
    return ContextModifiers(
        weather=ContextModifier(applied=True, delta=2.5, reason="Rain expected"),
        injury=ContextModifier(applied=True, delta=5.0, reason="Questionable status"),
        trade=ContextModifier(applied=False, delta=0.0),
        role=ContextModifier(applied=True, delta=3.0, reason="Role uncertainty from injury"),
    )


@pytest.fixture
def sample_bet_block(sample_modifiers: ContextModifiers) -> BetBlock:
    """A valid sample bet block."""
    return BetBlock.create(
        sport="NBA",
        game_id="nba-2024-001",
        bet_type=BetType.PLAYER_PROP,
        selection="LeBron James Over 25.5 Points",
        base_fragility=30.0,
        context_modifiers=sample_modifiers,
        correlation_tags=["lakers", "points"],
        player_id="lebron-james",
    )


# =============================================================================
# Test ContextModifier
# =============================================================================


class TestContextModifier:
    def test_valid_creation(self):
        cm = ContextModifier(applied=True, delta=5.0, reason="Test reason")
        assert cm.applied is True
        assert cm.delta == 5.0
        assert cm.reason == "Test reason"

    def test_no_reason(self):
        cm = ContextModifier(applied=False, delta=0.0)
        assert cm.reason is None

    def test_rejects_negative_delta(self):
        """INVARIANT: context never reduces fragility."""
        with pytest.raises(ValueError, match="delta must be >= 0"):
            ContextModifier(applied=True, delta=-1.0)

    def test_rejects_invalid_applied(self):
        with pytest.raises(TypeError, match="applied must be a boolean"):
            ContextModifier(applied="yes", delta=0.0)  # type: ignore

    def test_roundtrip(self):
        original = ContextModifier(applied=True, delta=3.5, reason="Weather impact")
        d = original.to_dict()
        restored = ContextModifier.from_dict(d)
        assert restored.applied == original.applied
        assert restored.delta == original.delta
        assert restored.reason == original.reason


# =============================================================================
# Test ContextModifiers
# =============================================================================


class TestContextModifiers:
    def test_valid_creation(self, zero_modifiers: ContextModifiers):
        assert zero_modifiers.weather.applied is False
        assert zero_modifiers.injury.applied is False
        assert zero_modifiers.trade.applied is False
        assert zero_modifiers.role.applied is False

    def test_total_delta_zero(self, zero_modifiers: ContextModifiers):
        assert zero_modifiers.total_delta() == 0.0

    def test_total_delta_with_applied(self, sample_modifiers: ContextModifiers):
        # weather: 2.5, injury: 5.0, trade: 0.0 (not applied), role: 3.0
        assert sample_modifiers.total_delta() == 10.5

    def test_has_all_four_categories(self, sample_modifiers: ContextModifiers):
        """Verify all four modifier categories exist."""
        assert hasattr(sample_modifiers, "weather")
        assert hasattr(sample_modifiers, "injury")
        assert hasattr(sample_modifiers, "trade")
        assert hasattr(sample_modifiers, "role")

    def test_roundtrip(self, sample_modifiers: ContextModifiers):
        d = sample_modifiers.to_dict()
        restored = ContextModifiers.from_dict(d)
        assert restored.total_delta() == sample_modifiers.total_delta()


# =============================================================================
# Test ContextImpact
# =============================================================================


class TestContextImpact:
    def test_valid_creation(self):
        impact = ContextImpact(fragility_delta=5.0, confidence_delta=-0.1)
        assert impact.fragility_delta == 5.0
        assert impact.confidence_delta == -0.1

    def test_rejects_negative_fragility_delta(self):
        """INVARIANT: context never reduces fragility."""
        with pytest.raises(ValueError, match="fragility_delta must be >= 0"):
            ContextImpact(fragility_delta=-1.0, confidence_delta=0.0)

    def test_confidence_delta_can_be_negative(self):
        """Confidence delta can reduce confidence (signal is uncertain)."""
        impact = ContextImpact(fragility_delta=0.0, confidence_delta=-0.5)
        assert impact.confidence_delta == -0.5

    def test_roundtrip(self):
        original = ContextImpact(fragility_delta=3.0, confidence_delta=0.2)
        d = original.to_dict()
        restored = ContextImpact.from_dict(d)
        assert restored.fragility_delta == original.fragility_delta
        assert restored.confidence_delta == original.confidence_delta


# =============================================================================
# Test BetBlock
# =============================================================================


class TestBetBlock:
    def test_valid_creation(self, sample_bet_block: BetBlock):
        assert sample_bet_block.sport == "NBA"
        assert sample_bet_block.bet_type == BetType.PLAYER_PROP
        assert sample_bet_block.base_fragility == 30.0
        # effective = base + sum of applied deltas = 30 + 10.5 = 40.5
        assert sample_bet_block.effective_fragility == 40.5

    def test_effective_fragility_computed(self, zero_modifiers: ContextModifiers):
        """Verify effective fragility equals base when no modifiers applied."""
        block = BetBlock.create(
            sport="NFL",
            game_id="nfl-001",
            bet_type=BetType.SPREAD,
            selection="Chiefs -3.5",
            base_fragility=25.0,
            context_modifiers=zero_modifiers,
            correlation_tags=["chiefs"],
        )
        assert block.effective_fragility == 25.0

    def test_effective_fragility_increases_with_context(self, sample_modifiers: ContextModifiers):
        """INVARIANT: effectiveFragility >= baseFragility."""
        block = BetBlock.create(
            sport="NBA",
            game_id="nba-001",
            bet_type=BetType.TOTAL,
            selection="Over 220.5",
            base_fragility=20.0,
            context_modifiers=sample_modifiers,
            correlation_tags=[],
        )
        assert block.effective_fragility > block.base_fragility
        assert block.effective_fragility == 30.5  # 20 + 10.5

    def test_rejects_effective_less_than_base(self, zero_modifiers: ContextModifiers):
        """INVARIANT VIOLATION: effective_fragility < base_fragility."""
        with pytest.raises(ValueError, match="INVARIANT VIOLATION"):
            BetBlock(
                block_id=uuid4(),
                sport="NBA",
                game_id="nba-001",
                bet_type=BetType.ML,
                selection="Lakers ML",
                base_fragility=50.0,
                context_modifiers=zero_modifiers,
                correlation_tags=(),
                effective_fragility=40.0,  # Less than base - VIOLATION
            )

    def test_all_bet_types(self, zero_modifiers: ContextModifiers):
        """Verify all bet types from spec are valid."""
        for bet_type in BetType:
            block = BetBlock.create(
                sport="TEST",
                game_id="test-001",
                bet_type=bet_type,
                selection="Test Selection",
                base_fragility=10.0,
                context_modifiers=zero_modifiers,
                correlation_tags=[],
            )
            assert block.bet_type == bet_type

    def test_rejects_empty_sport(self, zero_modifiers: ContextModifiers):
        with pytest.raises(ValueError, match="sport must be a non-empty string"):
            BetBlock.create(
                sport="",
                game_id="game-001",
                bet_type=BetType.ML,
                selection="Test",
                base_fragility=10.0,
                context_modifiers=zero_modifiers,
                correlation_tags=[],
            )

    def test_rejects_empty_game_id(self, zero_modifiers: ContextModifiers):
        with pytest.raises(ValueError, match="game_id must be a non-empty string"):
            BetBlock.create(
                sport="NBA",
                game_id="",
                bet_type=BetType.ML,
                selection="Test",
                base_fragility=10.0,
                context_modifiers=zero_modifiers,
                correlation_tags=[],
            )

    def test_optional_player_id(self, sample_bet_block: BetBlock):
        assert sample_bet_block.player_id == "lebron-james"

    def test_optional_team_id(self, zero_modifiers: ContextModifiers):
        block = BetBlock.create(
            sport="NFL",
            game_id="nfl-001",
            bet_type=BetType.TEAM_TOTAL,
            selection="Chiefs Over 27.5",
            base_fragility=20.0,
            context_modifiers=zero_modifiers,
            correlation_tags=["chiefs"],
            team_id="kansas-city-chiefs",
        )
        assert block.team_id == "kansas-city-chiefs"

    def test_roundtrip(self, sample_bet_block: BetBlock):
        d = sample_bet_block.to_dict()
        restored = BetBlock.from_dict(d)
        assert restored.block_id == sample_bet_block.block_id
        assert restored.sport == sample_bet_block.sport
        assert restored.bet_type == sample_bet_block.bet_type
        assert restored.base_fragility == sample_bet_block.base_fragility
        assert restored.effective_fragility == sample_bet_block.effective_fragility


# =============================================================================
# Test ContextSignal
# =============================================================================


class TestContextSignal:
    def test_valid_creation(self):
        signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.INJURY,
            target=ContextTarget.PLAYER,
            status="Questionable",
            confidence=0.85,
            impact=ContextImpact(fragility_delta=5.0, confidence_delta=0.0),
            explanation="Player listed as questionable with ankle injury",
        )
        assert signal.type == ContextSignalType.INJURY
        assert signal.target == ContextTarget.PLAYER
        assert signal.confidence == 0.85

    def test_all_signal_types(self):
        """Verify only weather, injury, trade are valid (NOT role)."""
        valid_types = {ContextSignalType.WEATHER, ContextSignalType.INJURY, ContextSignalType.TRADE}
        assert set(ContextSignalType) == valid_types

    def test_all_targets(self):
        """Verify player, team, game targets exist."""
        for target in [ContextTarget.PLAYER, ContextTarget.TEAM, ContextTarget.GAME]:
            signal = ContextSignal(
                context_id=uuid4(),
                type=ContextSignalType.WEATHER,
                target=target,
                status="Active",
                confidence=0.9,
                impact=ContextImpact(fragility_delta=1.0, confidence_delta=0.0),
                explanation="Test",
            )
            assert signal.target == target

    def test_confidence_bounds(self):
        """Confidence must be 0.0-1.0."""
        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            ContextSignal(
                context_id=uuid4(),
                type=ContextSignalType.WEATHER,
                target=ContextTarget.GAME,
                status="Active",
                confidence=1.5,  # Invalid
                impact=ContextImpact(fragility_delta=0.0, confidence_delta=0.0),
                explanation="Test",
            )

    def test_confidence_lower_bound(self):
        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            ContextSignal(
                context_id=uuid4(),
                type=ContextSignalType.WEATHER,
                target=ContextTarget.GAME,
                status="Active",
                confidence=-0.1,  # Invalid
                impact=ContextImpact(fragility_delta=0.0, confidence_delta=0.0),
                explanation="Test",
            )

    def test_edge_confidence_values(self):
        """Test boundary values 0.0 and 1.0 are valid."""
        for conf in [0.0, 1.0]:
            signal = ContextSignal(
                context_id=uuid4(),
                type=ContextSignalType.INJURY,
                target=ContextTarget.PLAYER,
                status="Active",
                confidence=conf,
                impact=ContextImpact(fragility_delta=0.0, confidence_delta=0.0),
                explanation="Boundary test",
            )
            assert signal.confidence == conf

    def test_roundtrip(self):
        original = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.TRADE,
            target=ContextTarget.TEAM,
            status="Recent trade",
            confidence=0.7,
            impact=ContextImpact(fragility_delta=8.0, confidence_delta=-0.1),
            explanation="Player traded 3 days ago",
        )
        d = original.to_dict()
        restored = ContextSignal.from_dict(d)
        assert restored.context_id == original.context_id
        assert restored.type == original.type
        assert restored.confidence == original.confidence


# =============================================================================
# Test ParlayMetrics
# =============================================================================


class TestParlayMetrics:
    def test_valid_creation(self):
        metrics = ParlayMetrics(
            raw_fragility=35.0,
            leg_penalty=5.0,
            correlation_penalty=3.0,
            correlation_multiplier=1.15,
            final_fragility=50.0,
        )
        assert metrics.raw_fragility == 35.0
        assert metrics.correlation_multiplier == 1.15

    def test_valid_correlation_multipliers(self):
        """Only [1.0, 1.15, 1.3, 1.5] are valid."""
        for mult in [1.0, 1.15, 1.3, 1.5]:
            metrics = ParlayMetrics(
                raw_fragility=20.0,
                leg_penalty=0.0,
                correlation_penalty=0.0,
                correlation_multiplier=mult,
                final_fragility=20.0,
            )
            assert metrics.correlation_multiplier == mult

    def test_rejects_invalid_correlation_multiplier(self):
        """Multipliers outside the set are rejected."""
        with pytest.raises(ValueError, match="correlation_multiplier must be one of"):
            ParlayMetrics(
                raw_fragility=20.0,
                leg_penalty=0.0,
                correlation_penalty=0.0,
                correlation_multiplier=1.25,  # Not in valid set
                final_fragility=20.0,
            )

    def test_final_fragility_clamped_lower(self):
        with pytest.raises(ValueError, match="final_fragility must be clamped between 0 and 100"):
            ParlayMetrics(
                raw_fragility=0.0,
                leg_penalty=0.0,
                correlation_penalty=0.0,
                correlation_multiplier=1.0,
                final_fragility=-1.0,  # Invalid
            )

    def test_final_fragility_clamped_upper(self):
        with pytest.raises(ValueError, match="final_fragility must be clamped between 0 and 100"):
            ParlayMetrics(
                raw_fragility=50.0,
                leg_penalty=30.0,
                correlation_penalty=30.0,
                correlation_multiplier=1.5,
                final_fragility=101.0,  # Invalid
            )

    def test_edge_final_fragility_values(self):
        """Test boundary values 0 and 100 are valid."""
        for val in [0.0, 100.0]:
            metrics = ParlayMetrics(
                raw_fragility=val,
                leg_penalty=0.0,
                correlation_penalty=0.0,
                correlation_multiplier=1.0,
                final_fragility=val,
            )
            assert metrics.final_fragility == val


# =============================================================================
# Test DNAEnforcement
# =============================================================================


class TestDNAEnforcement:
    def test_valid_creation(self):
        enforcement = DNAEnforcement(
            max_legs=4,
            fragility_tolerance=75.0,
            stake_cap=100.0,
            violations=("too many legs", "high fragility"),
        )
        assert enforcement.max_legs == 4
        assert len(enforcement.violations) == 2

    def test_empty_violations(self):
        enforcement = DNAEnforcement(
            max_legs=3,
            fragility_tolerance=50.0,
            stake_cap=50.0,
            violations=(),
        )
        assert enforcement.violations == ()

    def test_rejects_zero_max_legs(self):
        with pytest.raises(ValueError, match="max_legs must be >= 1"):
            DNAEnforcement(
                max_legs=0,
                fragility_tolerance=50.0,
                stake_cap=50.0,
                violations=(),
            )

    def test_rejects_negative_stake_cap(self):
        with pytest.raises(ValueError, match="stake_cap must be >= 0"):
            DNAEnforcement(
                max_legs=3,
                fragility_tolerance=50.0,
                stake_cap=-10.0,
                violations=(),
            )

    def test_roundtrip(self):
        original = DNAEnforcement(
            max_legs=5,
            fragility_tolerance=80.0,
            stake_cap=200.0,
            violations=("violation1",),
        )
        d = original.to_dict()
        restored = DNAEnforcement.from_dict(d)
        assert restored.max_legs == original.max_legs
        assert restored.violations == original.violations


# =============================================================================
# Test Correlation
# =============================================================================


class TestCorrelation:
    def test_valid_creation(self):
        id_a = uuid4()
        id_b = uuid4()
        corr = Correlation(
            block_a=id_a,
            block_b=id_b,
            type="same_game",
            penalty=5.0,
        )
        assert corr.block_a == id_a
        assert corr.penalty == 5.0

    def test_rejects_empty_type(self):
        with pytest.raises(ValueError, match="type must be a non-empty string"):
            Correlation(
                block_a=uuid4(),
                block_b=uuid4(),
                type="",
                penalty=3.0,
            )

    def test_rejects_negative_penalty(self):
        with pytest.raises(ValueError, match="penalty must be >= 0"):
            Correlation(
                block_a=uuid4(),
                block_b=uuid4(),
                type="same_player",
                penalty=-1.0,
            )


# =============================================================================
# Test ParlayState
# =============================================================================


class TestParlayState:
    def test_valid_creation(self, sample_bet_block: BetBlock):
        parlay = ParlayState(
            parlay_id=uuid4(),
            blocks=(sample_bet_block,),
            metrics=ParlayMetrics(
                raw_fragility=40.5,
                leg_penalty=0.0,
                correlation_penalty=0.0,
                correlation_multiplier=1.0,
                final_fragility=40.5,
            ),
            correlations=(),
            dna_enforcement=DNAEnforcement(
                max_legs=4,
                fragility_tolerance=75.0,
                stake_cap=100.0,
                violations=(),
            ),
        )
        assert len(parlay.blocks) == 1
        assert parlay.blocks[0].sport == "NBA"

    def test_multiple_blocks(self, zero_modifiers: ContextModifiers):
        block1 = BetBlock.create(
            sport="NBA",
            game_id="nba-001",
            bet_type=BetType.SPREAD,
            selection="Lakers -3.5",
            base_fragility=25.0,
            context_modifiers=zero_modifiers,
            correlation_tags=["lakers"],
        )
        block2 = BetBlock.create(
            sport="NBA",
            game_id="nba-001",
            bet_type=BetType.TOTAL,
            selection="Over 220.5",
            base_fragility=20.0,
            context_modifiers=zero_modifiers,
            correlation_tags=["lakers"],
        )
        parlay = ParlayState(
            parlay_id=uuid4(),
            blocks=(block1, block2),
            metrics=ParlayMetrics(
                raw_fragility=45.0,
                leg_penalty=5.0,
                correlation_penalty=3.0,
                correlation_multiplier=1.15,
                final_fragility=61.0,
            ),
            correlations=(
                Correlation(
                    block_a=block1.block_id,
                    block_b=block2.block_id,
                    type="same_game",
                    penalty=3.0,
                ),
            ),
            dna_enforcement=DNAEnforcement(
                max_legs=4,
                fragility_tolerance=75.0,
                stake_cap=100.0,
                violations=(),
            ),
        )
        assert len(parlay.blocks) == 2
        assert len(parlay.correlations) == 1

    def test_roundtrip(self, sample_bet_block: BetBlock):
        original = ParlayState(
            parlay_id=uuid4(),
            blocks=(sample_bet_block,),
            metrics=ParlayMetrics(
                raw_fragility=40.5,
                leg_penalty=0.0,
                correlation_penalty=0.0,
                correlation_multiplier=1.0,
                final_fragility=40.5,
            ),
            correlations=(),
            dna_enforcement=DNAEnforcement(
                max_legs=4,
                fragility_tolerance=75.0,
                stake_cap=100.0,
                violations=(),
            ),
        )
        d = original.to_dict()
        restored = ParlayState.from_dict(d)
        assert restored.parlay_id == original.parlay_id
        assert len(restored.blocks) == len(original.blocks)


# =============================================================================
# Test SuggestedBlock
# =============================================================================


class TestSuggestedBlock:
    def test_valid_creation(self):
        suggestion = SuggestedBlock(
            candidate_block_id=uuid4(),
            delta_fragility=5.0,
            added_correlation=2.0,
            dna_compatible=True,
            label=SuggestedBlockLabel.LOWEST_ADDED_RISK,
            reason="Minimal impact on parlay fragility",
        )
        assert suggestion.delta_fragility == 5.0
        assert suggestion.dna_compatible is True

    def test_all_labels(self):
        """Verify all three label types exist."""
        expected = {
            SuggestedBlockLabel.LOWEST_ADDED_RISK,
            SuggestedBlockLabel.BALANCED,
            SuggestedBlockLabel.AGGRESSIVE_WITHIN_LIMITS,
        }
        assert set(SuggestedBlockLabel) == expected

    def test_rejects_zero_delta_fragility(self):
        """RULE: deltaFragility must be > 0."""
        with pytest.raises(ValueError, match="delta_fragility must be > 0"):
            SuggestedBlock(
                candidate_block_id=uuid4(),
                delta_fragility=0.0,  # Invalid
                added_correlation=0.0,
                dna_compatible=True,
                label=SuggestedBlockLabel.BALANCED,
                reason="Test",
            )

    def test_rejects_negative_delta_fragility(self):
        """RULE: deltaFragility must be > 0."""
        with pytest.raises(ValueError, match="delta_fragility must be > 0"):
            SuggestedBlock(
                candidate_block_id=uuid4(),
                delta_fragility=-1.0,  # Invalid
                added_correlation=0.0,
                dna_compatible=True,
                label=SuggestedBlockLabel.BALANCED,
                reason="Test",
            )

    def test_dna_incompatible(self):
        """Verify dna_compatible=False is valid."""
        suggestion = SuggestedBlock(
            candidate_block_id=uuid4(),
            delta_fragility=15.0,
            added_correlation=8.0,
            dna_compatible=False,
            label=SuggestedBlockLabel.AGGRESSIVE_WITHIN_LIMITS,
            reason="Exceeds fragility tolerance",
        )
        assert suggestion.dna_compatible is False

    def test_roundtrip(self):
        original = SuggestedBlock(
            candidate_block_id=uuid4(),
            delta_fragility=7.5,
            added_correlation=3.0,
            dna_compatible=True,
            label=SuggestedBlockLabel.BALANCED,
            reason="Moderate risk addition",
        )
        d = original.to_dict()
        restored = SuggestedBlock.from_dict(d)
        assert restored.candidate_block_id == original.candidate_block_id
        assert restored.delta_fragility == original.delta_fragility
        assert restored.label == original.label


# =============================================================================
# Test Invariant Enforcement
# =============================================================================


class TestInvariants:
    """Tests specifically for system invariants."""

    def test_invariant_fragility_never_decreases(self, zero_modifiers: ContextModifiers):
        """
        INVARIANT: Fragility never decreases due to context.
        All context deltas must be >= 0.
        """
        # This should fail because we're trying to create a modifier with negative delta
        with pytest.raises(ValueError, match="delta must be >= 0"):
            ContextModifier(applied=True, delta=-5.0, reason="Invalid reduction")

    def test_invariant_effective_gte_base(self, zero_modifiers: ContextModifiers):
        """
        INVARIANT: effectiveFragility >= baseFragility.
        """
        with pytest.raises(ValueError, match="INVARIANT VIOLATION"):
            BetBlock(
                block_id=uuid4(),
                sport="NBA",
                game_id="nba-001",
                bet_type=BetType.ML,
                selection="Test",
                base_fragility=50.0,
                context_modifiers=zero_modifiers,
                correlation_tags=(),
                effective_fragility=30.0,  # Violates invariant
            )

    def test_invariant_final_fragility_bounds(self):
        """
        INVARIANT: finalFragility clamped [0, 100].
        """
        with pytest.raises(ValueError, match="final_fragility must be clamped"):
            ParlayMetrics(
                raw_fragility=200.0,
                leg_penalty=0.0,
                correlation_penalty=0.0,
                correlation_multiplier=1.0,
                final_fragility=200.0,  # Exceeds 100
            )

    def test_invariant_correlation_multiplier_discrete(self):
        """
        INVARIANT: correlationMultiplier must be one of [1.0, 1.15, 1.3, 1.5].
        No interpolation allowed.
        """
        with pytest.raises(ValueError, match="correlation_multiplier must be one of"):
            ParlayMetrics(
                raw_fragility=30.0,
                leg_penalty=0.0,
                correlation_penalty=0.0,
                correlation_multiplier=1.2,  # Not in valid set
                final_fragility=30.0,
            )

    def test_invariant_suggested_block_adds_risk(self):
        """
        INVARIANT: deltaFragility must be > 0.
        Adding a block always adds risk.
        """
        with pytest.raises(ValueError, match="delta_fragility must be > 0"):
            SuggestedBlock(
                candidate_block_id=uuid4(),
                delta_fragility=0.0,
                added_correlation=0.0,
                dna_compatible=True,
                label=SuggestedBlockLabel.LOWEST_ADDED_RISK,
                reason="Zero risk is impossible",
            )

    def test_context_signal_fragility_never_negative(self):
        """
        INVARIANT: fragilityDelta in ContextImpact must be >= 0.
        """
        with pytest.raises(ValueError, match="fragility_delta must be >= 0"):
            ContextImpact(fragility_delta=-3.0, confidence_delta=0.0)
