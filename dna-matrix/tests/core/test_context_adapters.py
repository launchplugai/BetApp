# tests/core/test_context_adapters.py
"""
Tests for Context Ingestion Adapters.

Tests weather, injury, and trade adapters, plus the apply_context_signals mapper.
"""
import pytest
from uuid import uuid4

from core.context_adapters import (
    WeatherAdapter,
    InjuryAdapter,
    TradeAdapter,
    apply_context_signals,
    adapt_and_apply_signals,
    _compute_role_delta,
    _is_weather_affected_block,
    WIND_THRESHOLD_MPH,
    WIND_FRAGILITY_DELTA,
    PRECIP_FRAGILITY_DELTA,
    INJURY_DELTA_OUT,
    INJURY_DELTA_DOUBTFUL,
    INJURY_DELTA_QUESTIONABLE,
    TRADE_FRAGILITY_DELTA,
    ROLE_DELTA_TRADE,
    ROLE_DELTA_INJURY_OUT,
    ROLE_DELTA_CAP,
)
from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextImpact,
    ContextModifier,
    ContextModifiers,
    ContextSignal,
    ContextSignalType,
    ContextTarget,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def default_modifiers():
    """Default context modifiers (all unapplied)."""
    default_mod = ContextModifier(applied=False, delta=0.0, reason=None)
    return ContextModifiers(
        weather=default_mod,
        injury=default_mod,
        trade=default_mod,
        role=default_mod,
    )


@pytest.fixture
def player_prop_block(default_modifiers):
    """Player prop block for testing."""
    return BetBlock(
        block_id=uuid4(),
        sport="NFL",
        game_id="game-123",
        bet_type=BetType.PLAYER_PROP,
        selection="Player X Over 100 passing yards",
        base_fragility=15.0,
        context_modifiers=default_modifiers,
        correlation_tags=("passing",),
        effective_fragility=15.0,
        player_id="player-1",
        team_id="team-1",
    )


@pytest.fixture
def spread_block(default_modifiers):
    """Spread block for testing."""
    return BetBlock(
        block_id=uuid4(),
        sport="NFL",
        game_id="game-123",
        bet_type=BetType.SPREAD,
        selection="Team A -3.5",
        base_fragility=10.0,
        context_modifiers=default_modifiers,
        correlation_tags=(),
        effective_fragility=10.0,
        player_id=None,
        team_id="team-1",
    )


@pytest.fixture
def kicking_block(default_modifiers):
    """Kicking-related block for weather tests."""
    return BetBlock(
        block_id=uuid4(),
        sport="NFL",
        game_id="game-123",
        bet_type=BetType.PLAYER_PROP,
        selection="Kicker Y Over 7.5 points",
        base_fragility=12.0,
        context_modifiers=default_modifiers,
        correlation_tags=("kicking",),
        effective_fragility=12.0,
        player_id="player-2",
        team_id="team-1",
    )


# =============================================================================
# Weather Adapter Tests
# =============================================================================


class TestWeatherAdapter:
    """Tests for WeatherAdapter."""

    def test_high_wind_increases_fragility(self):
        """High wind (>= 15 mph) increases fragility by 4."""
        payload = {
            "game_id": "game-123",
            "wind_mph": 20,
            "precip": False,
            "conditions": "Windy",
        }
        result = WeatherAdapter.adapt(payload)

        assert len(result.signals) == 1
        signal = result.signals[0]
        assert signal.type == ContextSignalType.WEATHER
        assert signal.impact.fragility_delta == WIND_FRAGILITY_DELTA
        assert "wind" in signal.explanation.lower()

    def test_wind_at_threshold(self):
        """Wind exactly at threshold triggers delta."""
        payload = {
            "game_id": "game-123",
            "wind_mph": WIND_THRESHOLD_MPH,
            "precip": False,
        }
        result = WeatherAdapter.adapt(payload)

        assert len(result.signals) == 1
        assert result.signals[0].impact.fragility_delta == WIND_FRAGILITY_DELTA

    def test_wind_below_threshold(self):
        """Wind below threshold produces no signal."""
        payload = {
            "game_id": "game-123",
            "wind_mph": 10,
            "precip": False,
        }
        result = WeatherAdapter.adapt(payload)

        assert len(result.signals) == 0
        assert result.is_empty

    def test_precipitation_increases_fragility(self):
        """Precipitation increases fragility by 3."""
        payload = {
            "game_id": "game-123",
            "wind_mph": 5,
            "precip": True,
            "conditions": "Rain",
        }
        result = WeatherAdapter.adapt(payload)

        assert len(result.signals) == 1
        signal = result.signals[0]
        assert signal.impact.fragility_delta == PRECIP_FRAGILITY_DELTA
        assert "precipitation" in signal.explanation.lower()

    def test_wind_and_precip_stack(self):
        """Wind and precipitation deltas stack."""
        payload = {
            "game_id": "game-123",
            "wind_mph": 20,
            "precip": True,
            "conditions": "Rain and Wind",
        }
        result = WeatherAdapter.adapt(payload)

        assert len(result.signals) == 1
        signal = result.signals[0]
        expected_delta = WIND_FRAGILITY_DELTA + PRECIP_FRAGILITY_DELTA
        assert signal.impact.fragility_delta == expected_delta

    def test_no_weather_impact(self):
        """Clear weather produces no signal."""
        payload = {
            "game_id": "game-123",
            "wind_mph": 5,
            "precip": False,
            "conditions": "Clear",
        }
        result = WeatherAdapter.adapt(payload)

        assert len(result.signals) == 0

    def test_weather_signal_targets_game(self):
        """Weather signal targets the game level."""
        payload = {
            "game_id": "game-123",
            "wind_mph": 20,
            "precip": False,
        }
        result = WeatherAdapter.adapt(payload)

        assert result.signals[0].target == ContextTarget.GAME


# =============================================================================
# Injury Adapter Tests
# =============================================================================


class TestInjuryAdapter:
    """Tests for InjuryAdapter."""

    def test_injury_out_increases_fragility_10(self):
        """OUT status increases fragility by 10."""
        payload = {
            "player_id": "player-1",
            "player_name": "John Doe",
            "status": "OUT",
            "injury": "Knee",
            "game_id": "game-123",
        }
        result = InjuryAdapter.adapt(payload)

        assert len(result.signals) == 1
        signal = result.signals[0]
        assert signal.type == ContextSignalType.INJURY
        assert signal.impact.fragility_delta == INJURY_DELTA_OUT
        assert signal.status == "OUT"
        assert "John Doe" in signal.explanation

    def test_injury_doubtful_increases_fragility_6(self):
        """DOUBTFUL status increases fragility by 6."""
        payload = {
            "player_id": "player-1",
            "player_name": "Jane Smith",
            "status": "DOUBTFUL",
            "injury": "Hamstring",
        }
        result = InjuryAdapter.adapt(payload)

        assert len(result.signals) == 1
        assert result.signals[0].impact.fragility_delta == INJURY_DELTA_DOUBTFUL

    def test_injury_questionable_increases_fragility_3(self):
        """QUESTIONABLE status increases fragility by 3."""
        payload = {
            "player_id": "player-1",
            "player_name": "Bob Jones",
            "status": "QUESTIONABLE",
            "injury": "Ankle",
        }
        result = InjuryAdapter.adapt(payload)

        assert len(result.signals) == 1
        assert result.signals[0].impact.fragility_delta == INJURY_DELTA_QUESTIONABLE

    def test_injury_unknown_status_no_signal(self):
        """Unknown injury status produces no signal."""
        payload = {
            "player_id": "player-1",
            "player_name": "Test Player",
            "status": "PROBABLE",
            "injury": "Minor",
        }
        result = InjuryAdapter.adapt(payload)

        assert len(result.signals) == 0

    def test_injury_status_case_insensitive(self):
        """Injury status matching is case insensitive."""
        for status in ["out", "Out", "OUT"]:
            payload = {
                "player_id": "player-1",
                "status": status,
                "injury": "Knee",
            }
            result = InjuryAdapter.adapt(payload)
            assert len(result.signals) == 1
            assert result.signals[0].impact.fragility_delta == INJURY_DELTA_OUT

    def test_injury_signal_targets_player(self):
        """Injury signal targets the player level."""
        payload = {
            "player_id": "player-1",
            "status": "OUT",
            "injury": "Knee",
        }
        result = InjuryAdapter.adapt(payload)

        assert result.signals[0].target == ContextTarget.PLAYER


# =============================================================================
# Trade Adapter Tests
# =============================================================================


class TestTradeAdapter:
    """Tests for TradeAdapter."""

    def test_trade_increases_fragility_5(self):
        """Trade increases fragility by 5."""
        payload = {
            "player_id": "player-1",
            "player_name": "Star Player",
            "from_team_id": "team-old",
            "to_team_id": "team-new",
            "games_affected": 3,
        }
        result = TradeAdapter.adapt(payload)

        assert len(result.signals) == 1
        signal = result.signals[0]
        assert signal.type == ContextSignalType.TRADE
        assert signal.impact.fragility_delta == TRADE_FRAGILITY_DELTA
        assert "traded" in signal.explanation.lower()

    def test_trade_encodes_games_in_status(self):
        """Trade status encodes games affected."""
        payload = {
            "player_id": "player-1",
            "player_name": "Player",
            "from_team_id": "team-old",
            "to_team_id": "team-new",
            "games_affected": 5,
        }
        result = TradeAdapter.adapt(payload)

        assert "5" in result.signals[0].status

    def test_trade_missing_player_id_no_signal(self):
        """Trade without player_id produces no signal."""
        payload = {
            "player_name": "Test",
            "from_team_id": "team-old",
            "to_team_id": "team-new",
        }
        result = TradeAdapter.adapt(payload)

        assert len(result.signals) == 0

    def test_trade_signal_targets_player(self):
        """Trade signal targets the player level."""
        payload = {
            "player_id": "player-1",
            "from_team_id": "team-old",
            "to_team_id": "team-new",
        }
        result = TradeAdapter.adapt(payload)

        assert result.signals[0].target == ContextTarget.PLAYER

    def test_trade_default_games_affected(self):
        """Trade defaults to 3 games affected."""
        payload = {
            "player_id": "player-1",
            "from_team_id": "team-old",
            "to_team_id": "team-new",
        }
        result = TradeAdapter.adapt(payload)

        assert "3" in result.signals[0].status


# =============================================================================
# Role Derivation Tests
# =============================================================================


class TestRoleDerivation:
    """Tests for role delta computation."""

    def test_trade_adds_role_delta_4(self):
        """Trade signal adds 4 to role delta."""
        trade_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.TRADE,
            target=ContextTarget.PLAYER,
            status="traded:3",
            confidence=1.0,
            impact=ContextImpact(fragility_delta=5.0, confidence_delta=0.0),
            explanation="Player traded",
        )

        delta = _compute_role_delta([trade_signal])
        assert delta == ROLE_DELTA_TRADE

    def test_injury_out_adds_role_delta_3(self):
        """Injury OUT adds 3 to role delta."""
        injury_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.INJURY,
            target=ContextTarget.PLAYER,
            status="OUT",
            confidence=0.95,
            impact=ContextImpact(fragility_delta=10.0, confidence_delta=0.0),
            explanation="Player OUT",
        )

        delta = _compute_role_delta([injury_signal])
        assert delta == ROLE_DELTA_INJURY_OUT

    def test_injury_doubtful_adds_role_delta_3(self):
        """Injury DOUBTFUL adds 3 to role delta."""
        injury_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.INJURY,
            target=ContextTarget.PLAYER,
            status="DOUBTFUL",
            confidence=0.95,
            impact=ContextImpact(fragility_delta=6.0, confidence_delta=0.0),
            explanation="Player DOUBTFUL",
        )

        delta = _compute_role_delta([injury_signal])
        assert delta == ROLE_DELTA_INJURY_OUT

    def test_injury_questionable_no_role_delta(self):
        """Injury QUESTIONABLE does not add role delta."""
        injury_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.INJURY,
            target=ContextTarget.PLAYER,
            status="QUESTIONABLE",
            confidence=0.95,
            impact=ContextImpact(fragility_delta=3.0, confidence_delta=0.0),
            explanation="Player QUESTIONABLE",
        )

        delta = _compute_role_delta([injury_signal])
        assert delta == 0.0

    def test_role_delta_stacks(self):
        """Role delta stacks from multiple signals."""
        trade_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.TRADE,
            target=ContextTarget.PLAYER,
            status="traded:3",
            confidence=1.0,
            impact=ContextImpact(fragility_delta=5.0, confidence_delta=0.0),
            explanation="Traded",
        )
        injury_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.INJURY,
            target=ContextTarget.PLAYER,
            status="OUT",
            confidence=0.95,
            impact=ContextImpact(fragility_delta=10.0, confidence_delta=0.0),
            explanation="OUT",
        )

        delta = _compute_role_delta([trade_signal, injury_signal])
        assert delta == ROLE_DELTA_TRADE + ROLE_DELTA_INJURY_OUT

    def test_role_delta_capped_at_10(self):
        """Role delta is capped at 10."""
        signals = [
            ContextSignal(
                context_id=uuid4(),
                type=ContextSignalType.TRADE,
                target=ContextTarget.PLAYER,
                status="traded:3",
                confidence=1.0,
                impact=ContextImpact(fragility_delta=5.0, confidence_delta=0.0),
                explanation="Trade",
            )
            for _ in range(5)  # 5 x 4 = 20, but capped at 10
        ]

        delta = _compute_role_delta(signals)
        assert delta == ROLE_DELTA_CAP

    def test_weather_no_role_delta(self):
        """Weather signals do not affect role delta."""
        weather_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.WEATHER,
            target=ContextTarget.GAME,
            status="adverse",
            confidence=0.9,
            impact=ContextImpact(fragility_delta=7.0, confidence_delta=0.0),
            explanation="Bad weather",
        )

        delta = _compute_role_delta([weather_signal])
        assert delta == 0.0


# =============================================================================
# Apply Context Signals Tests
# =============================================================================


class TestApplyContextSignals:
    """Tests for apply_context_signals mapper."""

    def test_weather_increases_weather_delta(self, player_prop_block):
        """Weather signal increases weather delta on matching blocks."""
        weather_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.WEATHER,
            target=ContextTarget.GAME,
            status="adverse",
            confidence=0.9,
            impact=ContextImpact(fragility_delta=7.0, confidence_delta=0.0),
            explanation="High wind and rain",
        )

        result = apply_context_signals([player_prop_block], [weather_signal])

        assert len(result) == 1
        new_block = result[0]
        assert new_block.context_modifiers.weather.applied is True
        assert new_block.context_modifiers.weather.delta == 7.0
        assert new_block.effective_fragility == player_prop_block.base_fragility + 7.0

    def test_injury_increases_injury_delta(self, player_prop_block):
        """Injury signal increases injury delta on matching blocks."""
        injury_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.INJURY,
            target=ContextTarget.PLAYER,
            status="OUT",
            confidence=0.95,
            impact=ContextImpact(fragility_delta=10.0, confidence_delta=-0.1),
            explanation="Star player OUT",
        )

        result = apply_context_signals([player_prop_block], [injury_signal])

        assert len(result) == 1
        new_block = result[0]
        assert new_block.context_modifiers.injury.applied is True
        assert new_block.context_modifiers.injury.delta == 10.0

    def test_injury_adds_role_delta(self, player_prop_block):
        """Injury OUT/DOUBTFUL adds role delta."""
        injury_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.INJURY,
            target=ContextTarget.PLAYER,
            status="OUT",
            confidence=0.95,
            impact=ContextImpact(fragility_delta=10.0, confidence_delta=-0.1),
            explanation="Star player OUT",
        )

        result = apply_context_signals([player_prop_block], [injury_signal])

        new_block = result[0]
        assert new_block.context_modifiers.role.applied is True
        assert new_block.context_modifiers.role.delta == ROLE_DELTA_INJURY_OUT

    def test_trade_increases_trade_delta(self, player_prop_block):
        """Trade signal increases trade delta on matching blocks."""
        trade_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.TRADE,
            target=ContextTarget.PLAYER,
            status="traded:3",
            confidence=1.0,
            impact=ContextImpact(fragility_delta=5.0, confidence_delta=-0.15),
            explanation="Player traded",
        )

        result = apply_context_signals([player_prop_block], [trade_signal])

        assert len(result) == 1
        new_block = result[0]
        assert new_block.context_modifiers.trade.applied is True
        assert new_block.context_modifiers.trade.delta == 5.0

    def test_trade_adds_role_delta(self, player_prop_block):
        """Trade signal adds role delta."""
        trade_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.TRADE,
            target=ContextTarget.PLAYER,
            status="traded:3",
            confidence=1.0,
            impact=ContextImpact(fragility_delta=5.0, confidence_delta=-0.15),
            explanation="Player traded",
        )

        result = apply_context_signals([player_prop_block], [trade_signal])

        new_block = result[0]
        assert new_block.context_modifiers.role.applied is True
        assert new_block.context_modifiers.role.delta == ROLE_DELTA_TRADE

    def test_no_negative_deltas(self, player_prop_block):
        """All deltas are >= 0."""
        # Even if we try to create a signal with negative delta, the model rejects it
        # So we just verify that applied signals result in non-negative deltas
        weather_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.WEATHER,
            target=ContextTarget.GAME,
            status="adverse",
            confidence=0.9,
            impact=ContextImpact(fragility_delta=5.0, confidence_delta=0.0),
            explanation="Weather",
        )

        result = apply_context_signals([player_prop_block], [weather_signal])

        new_block = result[0]
        assert new_block.context_modifiers.weather.delta >= 0
        assert new_block.context_modifiers.injury.delta >= 0
        assert new_block.context_modifiers.trade.delta >= 0
        assert new_block.context_modifiers.role.delta >= 0

    def test_empty_signals_returns_original_blocks(self, player_prop_block):
        """Empty signals list returns original blocks."""
        result = apply_context_signals([player_prop_block], [])

        assert len(result) == 1
        assert result[0] is player_prop_block

    def test_non_matching_signal_leaves_block_unchanged(self, spread_block):
        """Signals that don't match a block leave it unchanged."""
        # Spread block has no player_id, injury signal targets player
        injury_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.INJURY,
            target=ContextTarget.PLAYER,
            status="OUT",
            confidence=0.95,
            impact=ContextImpact(fragility_delta=10.0, confidence_delta=-0.1),
            explanation="Player OUT",
        )

        result = apply_context_signals([spread_block], [injury_signal])

        assert len(result) == 1
        assert result[0] is spread_block

    def test_multiple_signals_stack(self, player_prop_block):
        """Multiple matching signals stack their deltas."""
        weather_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.WEATHER,
            target=ContextTarget.GAME,
            status="adverse",
            confidence=0.9,
            impact=ContextImpact(fragility_delta=4.0, confidence_delta=0.0),
            explanation="Wind",
        )
        injury_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.INJURY,
            target=ContextTarget.PLAYER,
            status="OUT",
            confidence=0.95,
            impact=ContextImpact(fragility_delta=10.0, confidence_delta=-0.1),
            explanation="OUT",
        )

        result = apply_context_signals(
            [player_prop_block],
            [weather_signal, injury_signal],
        )

        new_block = result[0]
        # Weather + injury + role
        total_delta = 4.0 + 10.0 + ROLE_DELTA_INJURY_OUT
        assert new_block.effective_fragility == player_prop_block.base_fragility + total_delta

    def test_deterministic_output(self, player_prop_block):
        """Same inputs produce same outputs."""
        weather_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.WEATHER,
            target=ContextTarget.GAME,
            status="adverse",
            confidence=0.9,
            impact=ContextImpact(fragility_delta=5.0, confidence_delta=0.0),
            explanation="Weather",
        )

        result1 = apply_context_signals([player_prop_block], [weather_signal])
        result2 = apply_context_signals([player_prop_block], [weather_signal])

        assert result1[0].effective_fragility == result2[0].effective_fragility
        assert result1[0].context_modifiers.weather.delta == result2[0].context_modifiers.weather.delta


# =============================================================================
# Adapt and Apply Tests
# =============================================================================


class TestAdaptAndApplySignals:
    """Tests for adapt_and_apply_signals convenience function."""

    def test_weather_payload_applied(self, player_prop_block):
        """Weather payload is adapted and applied."""
        raw_signals = [
            {
                "type": "weather",
                "game_id": "game-123",
                "wind_mph": 20,
                "precip": False,
            }
        ]

        result = adapt_and_apply_signals([player_prop_block], raw_signals)

        assert len(result) == 1
        new_block = result[0]
        assert new_block.context_modifiers.weather.applied is True
        assert new_block.context_modifiers.weather.delta == WIND_FRAGILITY_DELTA

    def test_injury_payload_applied(self, player_prop_block):
        """Injury payload is adapted and applied."""
        raw_signals = [
            {
                "type": "injury",
                "player_id": "player-1",
                "player_name": "Star",
                "status": "OUT",
                "injury": "Knee",
            }
        ]

        result = adapt_and_apply_signals([player_prop_block], raw_signals)

        new_block = result[0]
        assert new_block.context_modifiers.injury.applied is True
        assert new_block.context_modifiers.injury.delta == INJURY_DELTA_OUT

    def test_trade_payload_applied(self, player_prop_block):
        """Trade payload is adapted and applied."""
        raw_signals = [
            {
                "type": "trade",
                "player_id": "player-1",
                "player_name": "Star",
                "from_team_id": "old",
                "to_team_id": "new",
                "games_affected": 3,
            }
        ]

        result = adapt_and_apply_signals([player_prop_block], raw_signals)

        new_block = result[0]
        assert new_block.context_modifiers.trade.applied is True
        assert new_block.context_modifiers.trade.delta == TRADE_FRAGILITY_DELTA
        assert new_block.context_modifiers.role.delta == ROLE_DELTA_TRADE

    def test_unknown_type_ignored(self, player_prop_block):
        """Unknown signal types are ignored."""
        raw_signals = [
            {
                "type": "unknown",
                "data": "test",
            }
        ]

        result = adapt_and_apply_signals([player_prop_block], raw_signals)

        assert len(result) == 1
        assert result[0] is player_prop_block

    def test_multiple_payloads(self, player_prop_block):
        """Multiple payloads of different types are all applied."""
        raw_signals = [
            {
                "type": "weather",
                "game_id": "game-123",
                "wind_mph": 15,
                "precip": True,
            },
            {
                "type": "injury",
                "player_id": "player-1",
                "status": "DOUBTFUL",
                "injury": "Ankle",
            },
        ]

        result = adapt_and_apply_signals([player_prop_block], raw_signals)

        new_block = result[0]
        assert new_block.context_modifiers.weather.applied is True
        assert new_block.context_modifiers.injury.applied is True
        # Weather: 4 (wind) + 3 (precip) = 7
        # Injury: 6 (doubtful)
        # Role: 3 (from doubtful)
        total = 7 + 6 + 3
        assert new_block.effective_fragility == player_prop_block.base_fragility + total


# =============================================================================
# Weather Affected Block Tests
# =============================================================================


class TestWeatherAffectedBlock:
    """Tests for _is_weather_affected_block helper."""

    def test_player_prop_with_passing_tag(self, default_modifiers):
        """Player prop with passing tag is weather affected."""
        block = BetBlock(
            block_id=uuid4(),
            sport="NFL",
            game_id="game-123",
            bet_type=BetType.PLAYER_PROP,
            selection="Test",
            base_fragility=10.0,
            context_modifiers=default_modifiers,
            correlation_tags=("passing",),
            effective_fragility=10.0,
            player_id="player-1",
        )
        assert _is_weather_affected_block(block) is True

    def test_player_prop_with_kicking_tag(self, default_modifiers):
        """Player prop with kicking tag is weather affected."""
        block = BetBlock(
            block_id=uuid4(),
            sport="NFL",
            game_id="game-123",
            bet_type=BetType.PLAYER_PROP,
            selection="Test",
            base_fragility=10.0,
            context_modifiers=default_modifiers,
            correlation_tags=("kicking",),
            effective_fragility=10.0,
            player_id="player-1",
        )
        assert _is_weather_affected_block(block) is True

    def test_player_prop_passing_yards_selection(self, default_modifiers):
        """Player prop with passing yards in selection is weather affected."""
        block = BetBlock(
            block_id=uuid4(),
            sport="NFL",
            game_id="game-123",
            bet_type=BetType.PLAYER_PROP,
            selection="QB Over 250 passing yards",
            base_fragility=10.0,
            context_modifiers=default_modifiers,
            correlation_tags=(),
            effective_fragility=10.0,
            player_id="player-1",
        )
        assert _is_weather_affected_block(block) is True

    def test_player_prop_field_goal_selection(self, default_modifiers):
        """Player prop with field goal in selection is weather affected."""
        block = BetBlock(
            block_id=uuid4(),
            sport="NFL",
            game_id="game-123",
            bet_type=BetType.PLAYER_PROP,
            selection="Kicker Over 1.5 field goals",
            base_fragility=10.0,
            context_modifiers=default_modifiers,
            correlation_tags=(),
            effective_fragility=10.0,
            player_id="player-1",
        )
        assert _is_weather_affected_block(block) is True

    def test_moneyline_not_weather_affected(self, default_modifiers):
        """Moneyline bets are not weather affected."""
        block = BetBlock(
            block_id=uuid4(),
            sport="NFL",
            game_id="game-123",
            bet_type=BetType.ML,
            selection="Team A ML",
            base_fragility=10.0,
            context_modifiers=default_modifiers,
            correlation_tags=(),
            effective_fragility=10.0,
        )
        assert _is_weather_affected_block(block) is False


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_blocks_and_signals(self):
        """Empty blocks and signals returns empty tuple."""
        result = apply_context_signals([], [])
        assert result == ()

    def test_empty_blocks_with_signals(self):
        """Empty blocks with signals returns empty tuple."""
        signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.WEATHER,
            target=ContextTarget.GAME,
            status="adverse",
            confidence=0.9,
            impact=ContextImpact(fragility_delta=5.0, confidence_delta=0.0),
            explanation="Weather",
        )
        result = apply_context_signals([], [signal])
        assert result == ()

    def test_blocks_with_existing_modifiers(self):
        """Blocks with existing modifiers get deltas added."""
        existing_mod = ContextModifier(applied=True, delta=2.0, reason="Pre-existing")
        default_mod = ContextModifier(applied=False, delta=0.0, reason=None)
        modifiers = ContextModifiers(
            weather=existing_mod,
            injury=default_mod,
            trade=default_mod,
            role=default_mod,
        )
        block = BetBlock(
            block_id=uuid4(),
            sport="NFL",
            game_id="game-123",
            bet_type=BetType.PLAYER_PROP,
            selection="QB passing yards",
            base_fragility=10.0,
            context_modifiers=modifiers,
            correlation_tags=("passing",),
            effective_fragility=12.0,  # 10 + 2
            player_id="player-1",
        )

        weather_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.WEATHER,
            target=ContextTarget.GAME,
            status="adverse",
            confidence=0.9,
            impact=ContextImpact(fragility_delta=5.0, confidence_delta=0.0),
            explanation="More weather",
        )

        result = apply_context_signals([block], [weather_signal])

        new_block = result[0]
        # Existing 2.0 + new 5.0 = 7.0
        assert new_block.context_modifiers.weather.delta == 7.0
        assert new_block.effective_fragility == 10.0 + 7.0

    def test_block_id_preserved(self, player_prop_block):
        """Block ID is preserved after applying signals."""
        original_id = player_prop_block.block_id

        weather_signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.WEATHER,
            target=ContextTarget.GAME,
            status="adverse",
            confidence=0.9,
            impact=ContextImpact(fragility_delta=5.0, confidence_delta=0.0),
            explanation="Weather",
        )

        result = apply_context_signals([player_prop_block], [weather_signal])

        assert result[0].block_id == original_id
