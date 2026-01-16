# core/context_adapters.py
"""
Context Ingestion Adapters for Weather, Injury, and Trade signals.

Provides standardized adapters to ingest external context and map it into
ContextSignal objects and BetBlock contextModifiers.

Rules:
- All deltas must be >= 0 (context never reduces fragility)
- Role delta is derived from injury + trade signals
- Role delta caps at 10
- Deterministic mapping
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID, uuid4

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
# Constants
# =============================================================================

# Weather thresholds
WIND_THRESHOLD_MPH = 15
WIND_FRAGILITY_DELTA = 4
PRECIP_FRAGILITY_DELTA = 3

# Injury status deltas
INJURY_DELTA_OUT = 10
INJURY_DELTA_DOUBTFUL = 6
INJURY_DELTA_QUESTIONABLE = 3

# Trade delta
TRADE_FRAGILITY_DELTA = 5

# Role derivation
ROLE_DELTA_TRADE = 4
ROLE_DELTA_INJURY_OUT = 3
ROLE_DELTA_INJURY_DOUBTFUL = 3
ROLE_DELTA_CAP = 10

# Bet types affected by weather (passing/kicking)
WEATHER_AFFECTED_BET_TYPES = {BetType.PLAYER_PROP, BetType.SPREAD, BetType.TOTAL, BetType.TEAM_TOTAL}
WEATHER_AFFECTED_TAGS = {"passing", "kicking", "receiving", "qb"}


# =============================================================================
# Adapter Result Type
# =============================================================================


@dataclass(frozen=True)
class AdapterResult:
    """Result from a context adapter."""
    signals: tuple[ContextSignal, ...]

    @property
    def is_empty(self) -> bool:
        return len(self.signals) == 0


# =============================================================================
# Weather Adapter
# =============================================================================


def _is_weather_affected_block(block: BetBlock) -> bool:
    """Check if a block is affected by weather conditions."""
    # Check bet type
    if block.bet_type in WEATHER_AFFECTED_BET_TYPES:
        # Check correlation tags for specific weather-sensitive markers
        tags_lower = {tag.lower() for tag in block.correlation_tags}
        if tags_lower & WEATHER_AFFECTED_TAGS:
            return True
        # Player props are generally weather-affected for passing/kicking
        if block.bet_type == BetType.PLAYER_PROP:
            selection_lower = block.selection.lower()
            if any(kw in selection_lower for kw in ["pass", "yard", "reception", "kick", "fg", "field goal"]):
                return True
    return False


class WeatherAdapter:
    """
    Adapter for weather context signals.

    Converts raw weather data into ContextSignal objects.

    Input format:
    {
        "game_id": "game-123",
        "wind_mph": 20,
        "precip": true,
        "temp_f": 45,
        "conditions": "Rain"
    }
    """

    @staticmethod
    def adapt(payload: Dict[str, Any]) -> AdapterResult:
        """
        Convert weather payload to ContextSignal(s).

        Args:
            payload: Raw weather data dict

        Returns:
            AdapterResult with weather signals
        """
        signals: List[ContextSignal] = []

        game_id = payload.get("game_id", "unknown")
        wind_mph = payload.get("wind_mph", 0)
        precip = payload.get("precip", False)
        conditions = payload.get("conditions", "")

        fragility_delta = 0.0
        reasons: List[str] = []

        # Wind check
        if wind_mph >= WIND_THRESHOLD_MPH:
            fragility_delta += WIND_FRAGILITY_DELTA
            reasons.append(f"High wind ({wind_mph} mph)")

        # Precipitation check
        if precip:
            fragility_delta += PRECIP_FRAGILITY_DELTA
            reasons.append("Precipitation expected")

        # Only emit signal if there's actual impact
        if fragility_delta > 0:
            explanation = "; ".join(reasons) if reasons else "Weather conditions present"

            signal = ContextSignal(
                context_id=uuid4(),
                type=ContextSignalType.WEATHER,
                target=ContextTarget.GAME,
                status=conditions or "adverse",
                confidence=0.9,  # Weather data is generally reliable
                impact=ContextImpact(
                    fragility_delta=fragility_delta,
                    confidence_delta=0.0,
                ),
                explanation=explanation,
            )
            signals.append(signal)

        return AdapterResult(signals=tuple(signals))


# =============================================================================
# Injury Adapter
# =============================================================================


class InjuryAdapter:
    """
    Adapter for injury context signals.

    Converts injury report data into ContextSignal objects.

    Input format:
    {
        "player_id": "player-123",
        "player_name": "John Doe",
        "team_id": "team-456",
        "status": "OUT",  # OUT, DOUBTFUL, QUESTIONABLE
        "injury": "Knee",
        "game_id": "game-789"
    }
    """

    @staticmethod
    def adapt(payload: Dict[str, Any]) -> AdapterResult:
        """
        Convert injury payload to ContextSignal(s).

        Args:
            payload: Raw injury data dict

        Returns:
            AdapterResult with injury signals
        """
        signals: List[ContextSignal] = []

        player_id = payload.get("player_id")
        player_name = payload.get("player_name", "Unknown player")
        status = payload.get("status", "").upper()
        injury = payload.get("injury", "undisclosed")

        # Determine fragility delta based on status
        if status == "OUT":
            fragility_delta = INJURY_DELTA_OUT
        elif status == "DOUBTFUL":
            fragility_delta = INJURY_DELTA_DOUBTFUL
        elif status == "QUESTIONABLE":
            fragility_delta = INJURY_DELTA_QUESTIONABLE
        else:
            # Unknown status, no signal
            return AdapterResult(signals=())

        explanation = f"{player_name} is {status} ({injury})"

        signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.INJURY,
            target=ContextTarget.PLAYER,
            status=status,
            confidence=0.95,  # Injury reports are official
            impact=ContextImpact(
                fragility_delta=fragility_delta,
                confidence_delta=-0.1 if status == "OUT" else -0.05,
            ),
            explanation=explanation,
        )
        signals.append(signal)

        return AdapterResult(signals=tuple(signals))


# =============================================================================
# Trade Adapter
# =============================================================================


class TradeAdapter:
    """
    Adapter for trade context signals.

    Converts trade/transaction data into ContextSignal objects.

    Input format:
    {
        "player_id": "player-123",
        "player_name": "John Doe",
        "from_team_id": "team-old",
        "to_team_id": "team-new",
        "trade_date": "2024-01-15",
        "games_affected": 3  # Number of games in adjustment window
    }
    """

    @staticmethod
    def adapt(payload: Dict[str, Any]) -> AdapterResult:
        """
        Convert trade payload to ContextSignal(s).

        Args:
            payload: Raw trade data dict

        Returns:
            AdapterResult with trade signals
        """
        signals: List[ContextSignal] = []

        player_id = payload.get("player_id")
        player_name = payload.get("player_name", "Unknown player")
        from_team = payload.get("from_team_id", "unknown")
        to_team = payload.get("to_team_id", "unknown")
        games_affected = payload.get("games_affected", 3)

        if not player_id:
            return AdapterResult(signals=())

        explanation = f"{player_name} traded from {from_team} to {to_team}; {games_affected} games in adjustment window"

        signal = ContextSignal(
            context_id=uuid4(),
            type=ContextSignalType.TRADE,
            target=ContextTarget.PLAYER,
            status=f"traded:{games_affected}",  # Encode games affected in status
            confidence=1.0,  # Trades are facts
            impact=ContextImpact(
                fragility_delta=TRADE_FRAGILITY_DELTA,
                confidence_delta=-0.15,  # Reduced confidence due to new situation
            ),
            explanation=explanation,
        )
        signals.append(signal)

        return AdapterResult(signals=tuple(signals))


# =============================================================================
# Signal Matching Logic
# =============================================================================


def _signal_matches_block(signal: ContextSignal, block: BetBlock) -> bool:
    """
    Check if a context signal should be applied to a block.

    Matching rules:
    - WEATHER signals: match by game_id (in correlation_tags or game_id field)
    - INJURY signals: match by player_id
    - TRADE signals: match by player_id or team_id
    """
    if signal.type == ContextSignalType.WEATHER:
        # Weather affects game-level - check if block is weather-affected type
        return _is_weather_affected_block(block)

    elif signal.type == ContextSignalType.INJURY:
        # Injury affects specific player
        if signal.target == ContextTarget.PLAYER and block.player_id:
            # For now, we match if the block has a player_id set
            # In production, we'd match signal metadata with block.player_id
            return block.bet_type == BetType.PLAYER_PROP
        return False

    elif signal.type == ContextSignalType.TRADE:
        # Trade affects specific player/team
        if signal.target == ContextTarget.PLAYER and block.player_id:
            return block.bet_type == BetType.PLAYER_PROP
        if signal.target == ContextTarget.TEAM and block.team_id:
            return True
        return False

    return False


def _signal_matches_block_by_id(
    signal: ContextSignal,
    block: BetBlock,
    signal_metadata: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Check if a signal matches a block by ID (player_id, team_id, game_id).

    Args:
        signal: The context signal
        block: The bet block
        signal_metadata: Optional metadata containing IDs from the original payload
    """
    if signal_metadata is None:
        return _signal_matches_block(signal, block)

    if signal.type == ContextSignalType.WEATHER:
        game_id = signal_metadata.get("game_id")
        if game_id and block.game_id == game_id:
            return _is_weather_affected_block(block)
        return False

    elif signal.type == ContextSignalType.INJURY:
        player_id = signal_metadata.get("player_id")
        if player_id and block.player_id == player_id:
            return True
        return False

    elif signal.type == ContextSignalType.TRADE:
        player_id = signal_metadata.get("player_id")
        team_id = signal_metadata.get("to_team_id") or signal_metadata.get("from_team_id")
        if player_id and block.player_id == player_id:
            return True
        if team_id and block.team_id == team_id:
            return True
        return False

    return False


# =============================================================================
# Role Derivation
# =============================================================================


def _compute_role_delta(signals: Sequence[ContextSignal]) -> float:
    """
    Compute role delta from injury and trade signals.

    Rules:
    - Any trade signal => +4
    - Injury DOUBTFUL/OUT => +3
    - Role delta caps at 10
    """
    role_delta = 0.0

    for signal in signals:
        if signal.type == ContextSignalType.TRADE:
            role_delta += ROLE_DELTA_TRADE
        elif signal.type == ContextSignalType.INJURY:
            status = signal.status.upper()
            if status in ("OUT", "DOUBTFUL"):
                role_delta += ROLE_DELTA_INJURY_OUT

    # Cap at maximum
    return min(role_delta, ROLE_DELTA_CAP)


# =============================================================================
# Apply Context Signals
# =============================================================================


def apply_context_signals(
    blocks: Sequence[BetBlock],
    signals: Sequence[ContextSignal],
    signal_metadata: Optional[Sequence[Dict[str, Any]]] = None,
) -> tuple[BetBlock, ...]:
    """
    Apply context signals to bet blocks, updating their contextModifiers.

    Rules:
    - Only increases fragility (deltas >= 0)
    - Maps weather/injury/trade into matching contextModifiers
    - Derives role modifier from injury + trade signals
    - Returns new blocks (immutable)

    Args:
        blocks: Sequence of BetBlock objects
        signals: Sequence of ContextSignal objects to apply
        signal_metadata: Optional metadata for each signal (for ID matching)

    Returns:
        Tuple of BetBlock objects with updated contextModifiers
    """
    if not signals:
        return tuple(blocks)

    result_blocks: List[BetBlock] = []

    for block in blocks:
        # Find signals that match this block
        matching_signals: List[ContextSignal] = []

        for i, signal in enumerate(signals):
            metadata = signal_metadata[i] if signal_metadata and i < len(signal_metadata) else None
            if _signal_matches_block_by_id(signal, block, metadata):
                matching_signals.append(signal)

        if not matching_signals:
            result_blocks.append(block)
            continue

        # Compute deltas from matching signals
        weather_delta = 0.0
        injury_delta = 0.0
        trade_delta = 0.0
        weather_reasons: List[str] = []
        injury_reasons: List[str] = []
        trade_reasons: List[str] = []

        for signal in matching_signals:
            if signal.type == ContextSignalType.WEATHER:
                weather_delta += signal.impact.fragility_delta
                weather_reasons.append(signal.explanation)
            elif signal.type == ContextSignalType.INJURY:
                injury_delta += signal.impact.fragility_delta
                injury_reasons.append(signal.explanation)
            elif signal.type == ContextSignalType.TRADE:
                trade_delta += signal.impact.fragility_delta
                trade_reasons.append(signal.explanation)

        # Compute role delta from injury + trade signals
        role_delta = _compute_role_delta(matching_signals)

        # Build new context modifiers (merge with existing)
        old_mods = block.context_modifiers

        new_weather = ContextModifier(
            applied=old_mods.weather.applied or weather_delta > 0,
            delta=old_mods.weather.delta + weather_delta,
            reason="; ".join(filter(None, [old_mods.weather.reason] + weather_reasons)) or None,
        )

        new_injury = ContextModifier(
            applied=old_mods.injury.applied or injury_delta > 0,
            delta=old_mods.injury.delta + injury_delta,
            reason="; ".join(filter(None, [old_mods.injury.reason] + injury_reasons)) or None,
        )

        new_trade = ContextModifier(
            applied=old_mods.trade.applied or trade_delta > 0,
            delta=old_mods.trade.delta + trade_delta,
            reason="; ".join(filter(None, [old_mods.trade.reason] + trade_reasons)) or None,
        )

        new_role = ContextModifier(
            applied=old_mods.role.applied or role_delta > 0,
            delta=min(old_mods.role.delta + role_delta, ROLE_DELTA_CAP),
            reason="Role instability from injury/trade" if role_delta > 0 else old_mods.role.reason,
        )

        new_modifiers = ContextModifiers(
            weather=new_weather,
            injury=new_injury,
            trade=new_trade,
            role=new_role,
        )

        # Compute new effective fragility
        new_effective = block.base_fragility + new_modifiers.total_delta()

        # Create new block with updated modifiers
        new_block = BetBlock(
            block_id=block.block_id,
            sport=block.sport,
            game_id=block.game_id,
            bet_type=block.bet_type,
            selection=block.selection,
            base_fragility=block.base_fragility,
            context_modifiers=new_modifiers,
            correlation_tags=block.correlation_tags,
            effective_fragility=new_effective,
            player_id=block.player_id,
            team_id=block.team_id,
        )

        result_blocks.append(new_block)

    return tuple(result_blocks)


# =============================================================================
# Convenience Function for API
# =============================================================================


def adapt_and_apply_signals(
    blocks: Sequence[BetBlock],
    raw_signals: Sequence[Dict[str, Any]],
) -> tuple[BetBlock, ...]:
    """
    Convenience function to adapt raw signal payloads and apply to blocks.

    Each raw signal dict should have a "type" field indicating the signal type:
    - "weather": processed by WeatherAdapter
    - "injury": processed by InjuryAdapter
    - "trade": processed by TradeAdapter

    Args:
        blocks: Sequence of BetBlock objects
        raw_signals: Sequence of raw signal dicts

    Returns:
        Tuple of BetBlock objects with applied context
    """
    if not raw_signals:
        return tuple(blocks)

    all_signals: List[ContextSignal] = []
    all_metadata: List[Dict[str, Any]] = []

    for raw in raw_signals:
        signal_type = raw.get("type", "").lower()

        if signal_type == "weather":
            result = WeatherAdapter.adapt(raw)
        elif signal_type == "injury":
            result = InjuryAdapter.adapt(raw)
        elif signal_type == "trade":
            result = TradeAdapter.adapt(raw)
        else:
            continue

        for signal in result.signals:
            all_signals.append(signal)
            all_metadata.append(raw)

    return apply_context_signals(blocks, all_signals, all_metadata)
