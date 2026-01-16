# tests/core/test_builder_contract.py
"""
Tests for Parlay Builder UI Contract.

Tests the BuilderView model and derive functions.
"""
import pytest
from uuid import uuid4

from core.builder_contract import (
    BuilderView,
    BlockBreakdown,
    ContextDeltas,
    MeterValues,
    InductorDisplay,
    DNADisplay,
    CorrelationDisplay,
    derive_builder_view,
    build_view_from_blocks,
    _generate_block_notes,
    _generate_block_label,
    _create_block_breakdown,
)
from core.evaluation import (
    EvaluationResponse,
    InductorInfo,
    MetricsInfo,
    DNAInfo,
    Recommendation,
    RecommendationAction,
    evaluate_parlay,
)
from core.models.leading_light import (
    BetBlock,
    BetType,
    Correlation,
    ContextModifier,
    ContextModifiers,
    SuggestedBlock,
    SuggestedBlockLabel,
)
from core.risk_inductor import RiskInductor
from core.context_adapters import adapt_and_apply_signals


# =============================================================================
# Fixtures
# =============================================================================


def _default_modifiers():
    """Create default context modifiers."""
    default_mod = ContextModifier(applied=False, delta=0.0, reason=None)
    return ContextModifiers(
        weather=default_mod,
        injury=default_mod,
        trade=default_mod,
        role=default_mod,
    )


def _make_block(
    selection: str = "Test Selection",
    bet_type: BetType = BetType.SPREAD,
    base_fragility: float = 15.0,
    player_id: str = None,
    team_id: str = None,
    context_modifiers: ContextModifiers = None,
    correlation_tags: tuple = (),
) -> BetBlock:
    """Create a test block."""
    if context_modifiers is None:
        context_modifiers = _default_modifiers()

    effective = base_fragility + context_modifiers.total_delta()

    return BetBlock(
        block_id=uuid4(),
        sport="NFL",
        game_id="game-123",
        bet_type=bet_type,
        selection=selection,
        base_fragility=base_fragility,
        context_modifiers=context_modifiers,
        correlation_tags=correlation_tags,
        effective_fragility=effective,
        player_id=player_id,
        team_id=team_id,
    )


@pytest.fixture
def simple_block():
    """Simple spread block."""
    return _make_block(
        selection="Team A -3.5",
        bet_type=BetType.SPREAD,
        base_fragility=12.0,
    )


@pytest.fixture
def player_prop_block():
    """Player prop block."""
    return _make_block(
        selection="Player X Over 100 yards",
        bet_type=BetType.PLAYER_PROP,
        base_fragility=18.0,
        player_id="player-1",
    )


@pytest.fixture
def context_block():
    """Block with context modifiers applied."""
    weather_mod = ContextModifier(applied=True, delta=4.0, reason="High wind")
    injury_mod = ContextModifier(applied=True, delta=6.0, reason="Key player doubtful")
    trade_mod = ContextModifier(applied=False, delta=0.0, reason=None)
    role_mod = ContextModifier(applied=True, delta=3.0, reason="Role instability")
    default_mod = ContextModifier(applied=False, delta=0.0, reason=None)

    modifiers = ContextModifiers(
        weather=weather_mod,
        injury=injury_mod,
        trade=trade_mod,
        role=role_mod,
    )

    return _make_block(
        selection="QB Over 250 passing yards",
        bet_type=BetType.PLAYER_PROP,
        base_fragility=15.0,
        player_id="player-1",
        context_modifiers=modifiers,
        correlation_tags=("passing",),
    )


# =============================================================================
# Required Test Vectors
# =============================================================================


class TestRequiredVectors:
    """Required test vectors from specification."""

    def test_vector_a_minimal_builder_view(self, simple_block):
        """
        Test A: Minimal BuilderView.

        1 block, no context, no candidates.
        Expected:
        - meter values present
        - one block breakdown present
        - inductor present
        """
        view = build_view_from_blocks([simple_block])

        # Meter values present
        assert view.meter is not None
        assert view.meter.final_fragility > 0
        assert view.meter.raw_fragility > 0
        assert view.meter.leg_penalty >= 0
        assert view.meter.correlation_penalty >= 0
        assert view.meter.correlation_multiplier == 1.0

        # One block breakdown present
        assert len(view.blocks) == 1
        block = view.blocks[0]
        assert block.block_id == simple_block.block_id
        assert block.label == simple_block.selection
        assert block.bet_type == "spread"
        assert block.base_fragility == 12.0
        assert block.effective_fragility == 12.0

        # Inductor present
        assert view.inductor is not None
        assert view.inductor.level in ("stable", "loaded", "tense", "critical")
        assert len(view.inductor.explanation) > 0

    def test_vector_b_context_breakdown(self, context_block):
        """
        Test B: Context breakdown.

        Apply weather + injury signals.
        Expected:
        - context_deltas reflect deltas
        - context_delta_total correct
        - notes include factual context lines
        """
        view = build_view_from_blocks([context_block])

        # One block with context
        assert len(view.blocks) == 1
        block = view.blocks[0]

        # Context deltas reflect deltas
        assert block.context_deltas.weather == 4.0
        assert block.context_deltas.injury == 6.0
        assert block.context_deltas.trade == 0.0
        assert block.context_deltas.role == 3.0

        # Context delta total correct
        assert block.context_delta_total == 13.0  # 4 + 6 + 0 + 3

        # Effective fragility = base + context
        assert block.effective_fragility == 15.0 + 13.0  # 28.0

        # Notes include factual context lines
        notes = block.notes
        assert any("Weather +4.0" in note for note in notes)
        assert any("Injury +6.0" in note for note in notes)
        assert any("Role instability +3.0" in note for note in notes)

    def test_vector_c_correlation_notes(self):
        """
        Test C: Correlation notes.

        Two player props same player -> same_player_multi_props.
        Expected:
        - correlations list present
        - both blocks include note referencing correlation type/penalty
        """
        # Create two player props for same player
        player_id = "player-1"
        block1 = _make_block(
            selection="Player X Over 100 yards",
            bet_type=BetType.PLAYER_PROP,
            base_fragility=15.0,
            player_id=player_id,
        )
        block2 = _make_block(
            selection="Player X Over 5 receptions",
            bet_type=BetType.PLAYER_PROP,
            base_fragility=15.0,
            player_id=player_id,
        )

        view = build_view_from_blocks([block1, block2])

        # Correlations list present
        assert len(view.correlations) > 0

        # Find same_player_multi_props correlation
        same_player_corr = [
            c for c in view.correlations
            if c.type == "same_player_multi_props"
        ]
        assert len(same_player_corr) > 0

        # Both blocks should have correlation notes
        block1_breakdown = next(b for b in view.blocks if b.block_id == block1.block_id)
        block2_breakdown = next(b for b in view.blocks if b.block_id == block2.block_id)

        assert any("correlation" in note.lower() for note in block1_breakdown.notes)
        assert any("correlation" in note.lower() for note in block2_breakdown.notes)

    def test_vector_d_suggestions_passthrough(self, simple_block):
        """
        Test D: Suggestions passthrough.

        Include candidates.
        Expected:
        - suggestions included and sorted
        """
        candidate1 = _make_block(
            selection="Candidate A",
            bet_type=BetType.SPREAD,
            base_fragility=8.0,
        )
        candidate2 = _make_block(
            selection="Candidate B",
            bet_type=BetType.SPREAD,
            base_fragility=12.0,
        )
        candidate3 = _make_block(
            selection="Candidate C",
            bet_type=BetType.TOTAL,
            base_fragility=6.0,
        )

        view = build_view_from_blocks(
            [simple_block],
            candidates=[candidate1, candidate2, candidate3],
        )

        # Suggestions included
        assert view.suggestions is not None
        assert len(view.suggestions) > 0

        # Verify suggestions are SuggestedBlock instances
        for suggestion in view.suggestions:
            assert hasattr(suggestion, "candidate_block_id")
            assert hasattr(suggestion, "delta_fragility")
            assert hasattr(suggestion, "label")


# =============================================================================
# BuilderView Structure Tests
# =============================================================================


class TestBuilderViewStructure:
    """Tests for BuilderView structure."""

    def test_parlay_id_present(self, simple_block):
        """BuilderView has parlay_id."""
        view = build_view_from_blocks([simple_block])
        assert view.parlay_id is not None
        assert isinstance(view.parlay_id, type(uuid4()))

    def test_all_required_fields_present(self, simple_block):
        """All required fields are present."""
        view = build_view_from_blocks([simple_block])

        assert hasattr(view, "parlay_id")
        assert hasattr(view, "inductor")
        assert hasattr(view, "meter")
        assert hasattr(view, "dna")
        assert hasattr(view, "blocks")
        assert hasattr(view, "correlations")
        assert hasattr(view, "alerts")
        assert hasattr(view, "suggestions")

    def test_view_is_frozen(self, simple_block):
        """BuilderView is immutable."""
        view = build_view_from_blocks([simple_block])

        with pytest.raises(Exception):  # FrozenInstanceError
            view.parlay_id = uuid4()


# =============================================================================
# Meter Values Tests
# =============================================================================


class TestMeterValues:
    """Tests for MeterValues."""

    def test_meter_has_all_fields(self, simple_block):
        """Meter has all required fields."""
        view = build_view_from_blocks([simple_block])

        assert hasattr(view.meter, "final_fragility")
        assert hasattr(view.meter, "raw_fragility")
        assert hasattr(view.meter, "leg_penalty")
        assert hasattr(view.meter, "correlation_penalty")
        assert hasattr(view.meter, "correlation_multiplier")

    def test_meter_values_are_numbers(self, simple_block):
        """All meter values are numeric."""
        view = build_view_from_blocks([simple_block])

        assert isinstance(view.meter.final_fragility, (int, float))
        assert isinstance(view.meter.raw_fragility, (int, float))
        assert isinstance(view.meter.leg_penalty, (int, float))
        assert isinstance(view.meter.correlation_penalty, (int, float))
        assert isinstance(view.meter.correlation_multiplier, (int, float))


# =============================================================================
# Block Breakdown Tests
# =============================================================================


class TestBlockBreakdown:
    """Tests for block breakdown."""

    def test_block_breakdown_has_all_fields(self, simple_block):
        """Block breakdown has all required fields."""
        view = build_view_from_blocks([simple_block])
        block = view.blocks[0]

        assert hasattr(block, "block_id")
        assert hasattr(block, "label")
        assert hasattr(block, "bet_type")
        assert hasattr(block, "base_fragility")
        assert hasattr(block, "context_deltas")
        assert hasattr(block, "context_delta_total")
        assert hasattr(block, "effective_fragility")
        assert hasattr(block, "notes")

    def test_context_deltas_structure(self, context_block):
        """Context deltas has weather/injury/trade/role."""
        view = build_view_from_blocks([context_block])
        deltas = view.blocks[0].context_deltas

        assert hasattr(deltas, "weather")
        assert hasattr(deltas, "injury")
        assert hasattr(deltas, "trade")
        assert hasattr(deltas, "role")

    def test_label_truncation(self):
        """Long labels are truncated."""
        long_selection = "A" * 100  # Very long selection
        block = _make_block(selection=long_selection)

        label = _generate_block_label(block)

        assert len(label) <= 50
        assert label.endswith("...")


# =============================================================================
# Note Generation Tests
# =============================================================================


class TestNoteGeneration:
    """Tests for note generation."""

    def test_no_notes_for_default_context(self, simple_block):
        """No notes when no context applied."""
        notes = _generate_block_notes(simple_block, [])
        assert len(notes) == 0

    def test_weather_note_format(self, context_block):
        """Weather note has correct format."""
        notes = _generate_block_notes(context_block, [])
        weather_notes = [n for n in notes if "Weather" in n]
        assert len(weather_notes) == 1
        assert "+4.0" in weather_notes[0]

    def test_correlation_note_generated(self):
        """Correlation notes are generated."""
        block = _make_block(bet_type=BetType.PLAYER_PROP, player_id="player-1")
        correlation = Correlation(
            block_a=block.block_id,
            block_b=uuid4(),
            type="same_player_multi_props",
            penalty=8.0,
        )

        notes = _generate_block_notes(block, [correlation])

        assert any("correlation" in note.lower() for note in notes)
        assert any("+8.0" in note for note in notes)


# =============================================================================
# DNA Display Tests
# =============================================================================


class TestDNADisplay:
    """Tests for DNA display."""

    def test_dna_without_profile(self, simple_block):
        """DNA display works without profile."""
        view = build_view_from_blocks([simple_block])

        assert view.dna is not None
        assert view.dna.violations == ()
        assert view.dna.base_stake_cap is None
        assert view.dna.recommended_stake is None

    def test_dna_with_profile_and_violations(self, simple_block):
        """DNA shows violations from profile."""
        from core.dna_enforcement import DNAProfile, RiskProfile, BehaviorProfile

        # Conservative profile that triggers violations
        profile = DNAProfile(
            risk=RiskProfile(
                tolerance=10,  # Very low - will trigger violation
                max_parlay_legs=1,  # Only 1 leg allowed
                max_stake_pct=0.01,
                avoid_live_bets=False,
                avoid_props=False,
            ),
            behavior=BehaviorProfile(discipline=0.9),
        )

        # Create blocks that will violate
        block1 = _make_block(base_fragility=15.0)
        block2 = _make_block(base_fragility=15.0)  # 2 legs violates max_legs=1

        view = build_view_from_blocks(
            [block1, block2],
            dna_profile=profile,
            bankroll=1000.0,
        )

        # Should have violations
        assert len(view.dna.violations) > 0


# =============================================================================
# Alerts Tests
# =============================================================================


class TestAlertsIntegration:
    """Tests for alerts integration."""

    def test_no_alerts_without_prev_response(self, simple_block):
        """No alerts when no previous response."""
        view = build_view_from_blocks([simple_block])
        assert view.alerts is None

    def test_alerts_with_context_applied(self, simple_block):
        """Alerts generated when context applied."""
        context_applied = {
            "weather_delta": 5.0,
            "injury_delta": 0.0,
            "trade_delta": 0.0,
            "role_delta": 0.0,
        }

        view = build_view_from_blocks(
            [simple_block],
            context_applied=context_applied,
        )

        # Should have context impact alert
        assert view.alerts is not None
        assert len(view.alerts) > 0


# =============================================================================
# Determinism Tests
# =============================================================================


class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_same_inputs_same_outputs(self, simple_block):
        """Same inputs produce same BuilderView."""
        view1 = build_view_from_blocks([simple_block])
        view2 = build_view_from_blocks([simple_block])

        # Meter values should match
        assert view1.meter.final_fragility == view2.meter.final_fragility
        assert view1.meter.raw_fragility == view2.meter.raw_fragility

        # Block breakdowns should match
        assert len(view1.blocks) == len(view2.blocks)
        for b1, b2 in zip(view1.blocks, view2.blocks):
            assert b1.base_fragility == b2.base_fragility
            assert b1.effective_fragility == b2.effective_fragility

        # Inductor should match
        assert view1.inductor.level == view2.inductor.level


# =============================================================================
# Context Adapters Integration Tests
# =============================================================================


class TestContextAdaptersIntegration:
    """Tests for context adapters integration."""

    def test_weather_context_reflected(self):
        """Weather context from adapters reflected in view."""
        block = _make_block(
            selection="QB Over 250 passing yards",
            bet_type=BetType.PLAYER_PROP,
            base_fragility=12.0,
            player_id="player-1",
            correlation_tags=("passing",),
        )

        # Apply weather context
        raw_signals = [
            {
                "type": "weather",
                "game_id": "game-123",
                "wind_mph": 20,
                "precip": True,
            }
        ]

        blocks_with_context = adapt_and_apply_signals([block], raw_signals)

        view = build_view_from_blocks(list(blocks_with_context))

        # Weather delta should be reflected
        assert view.blocks[0].context_deltas.weather > 0

    def test_injury_context_reflected(self):
        """Injury context from adapters reflected in view."""
        block = _make_block(
            selection="RB Over 80 rushing yards",
            bet_type=BetType.PLAYER_PROP,
            base_fragility=12.0,
            player_id="player-1",
        )

        # Apply injury context
        raw_signals = [
            {
                "type": "injury",
                "player_id": "player-1",
                "status": "OUT",
                "injury": "Knee",
            }
        ]

        blocks_with_context = adapt_and_apply_signals([block], raw_signals)

        view = build_view_from_blocks(list(blocks_with_context))

        # Injury delta should be reflected
        assert view.blocks[0].context_deltas.injury > 0
        # Role delta from injury OUT should also be reflected
        assert view.blocks[0].context_deltas.role > 0


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_blocks(self):
        """Empty blocks list produces valid view."""
        view = build_view_from_blocks([])

        assert view.parlay_id is not None
        assert view.blocks == ()
        assert view.meter.final_fragility == 0.0

    def test_single_block(self, simple_block):
        """Single block produces valid view."""
        view = build_view_from_blocks([simple_block])

        assert len(view.blocks) == 1
        assert view.correlations == ()  # No correlations with single block

    def test_many_blocks(self):
        """Many blocks are all included."""
        blocks = [_make_block(selection=f"Block {i}") for i in range(10)]

        view = build_view_from_blocks(blocks)

        assert len(view.blocks) == 10

    def test_no_candidates_no_suggestions(self, simple_block):
        """No candidates means no suggestions."""
        view = build_view_from_blocks([simple_block])

        assert view.suggestions is None

    def test_empty_candidates_no_suggestions(self, simple_block):
        """Empty candidates list means no suggestions."""
        view = build_view_from_blocks([simple_block], candidates=[])

        assert view.suggestions is None
