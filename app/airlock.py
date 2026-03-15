# app/airlock.py
"""
Airlock - Single source of truth for evaluation input validation and normalization.

All evaluation endpoints MUST pass through Airlock before calling the evaluation pipeline.
This ensures:
- Consistent validation rules across all entry points
- No duplicate validation logic in routes
- Single place to update validation rules

Airlock does NOT:
- Log raw input (only input_length for safety)
- Call evaluation engines directly
- Handle HTTP concerns (that's the route's job)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Optional


# =============================================================================
# Constants
# =============================================================================

# Maximum input length (characters)
MAX_INPUT_LENGTH = 10000

# Minimum input length (must have content)
MIN_INPUT_LENGTH = 1


# =============================================================================
# Canonical Tier Enum
# =============================================================================


class Tier(str, Enum):
    """
    Canonical tier values used internally.

    External APIs may accept various forms (good/GOOD/free), but internally
    we always use this canonical form.
    """
    GOOD = "good"
    BETTER = "better"
    BEST = "best"


# Tier aliases for backwards compatibility
TIER_ALIASES = {
    "free": Tier.GOOD,  # Legacy "free" plan maps to GOOD
}


# =============================================================================
# Validation Errors
# =============================================================================


class AirlockError(Exception):
    """Base exception for Airlock validation errors."""

    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class EmptyInputError(AirlockError):
    """Raised when input is empty or whitespace-only."""

    def __init__(self):
        super().__init__(
            message="Input cannot be empty or whitespace-only",
            code="EMPTY_INPUT",
        )


class InputTooLongError(AirlockError):
    """Raised when input exceeds maximum length."""

    def __init__(self, length: int, max_length: int):
        super().__init__(
            message=f"Input length {length} exceeds maximum of {max_length} characters",
            code="INPUT_TOO_LONG",
        )
        self.length = length
        self.max_length = max_length


class InvalidTierError(AirlockError):
    """Raised when tier is not a valid value."""

    def __init__(self, tier: str):
        valid = ", ".join([t.value.upper() for t in Tier])
        super().__init__(
            message=f"Invalid tier '{tier}'. Must be one of: {valid}",
            code="INVALID_TIER",
        )
        self.tier = tier


# =============================================================================
# Normalized Input
# =============================================================================


@dataclass(frozen=True)
class CanonicalLegData:
    """
    Ticket 27: Canonical leg representation (frozen dataclass).

    This is the source of truth when legs come from the builder.
    """
    entity: str  # Team or player name
    market: str  # Market type: moneyline, spread, total, player_prop
    value: Optional[str]  # Line value (e.g., '-5.5', 'over 220')
    raw: str  # Original text as entered


@dataclass(frozen=True)
class NormalizedInput:
    """
    Validated and normalized input from Airlock.

    All fields are guaranteed to be valid when this object exists.
    Routes should use these values instead of raw request values.
    """
    input_text: str  # Trimmed, validated input text
    tier: Tier  # Canonical tier enum
    session_id: Optional[str] = None  # Optional session identifier
    # Ticket 27: Canonical legs from builder (None means use text parsing)
    canonical_legs: Optional[tuple] = None  # Tuple of CanonicalLegData

    @property
    def input_length(self) -> int:
        """Length of input text (safe to log)."""
        return len(self.input_text)

    @property
    def has_canonical_legs(self) -> bool:
        """True if canonical legs are present (builder mode)."""
        return self.canonical_legs is not None and len(self.canonical_legs) > 0


# =============================================================================
# Core Validation Functions
# =============================================================================


def _validate_input_text(text: Optional[str]) -> str:
    """
    Validate and normalize input text.

    - Strips whitespace
    - Rejects empty/whitespace-only
    - Enforces max length

    Returns:
        Trimmed, validated text

    Raises:
        EmptyInputError: If text is empty or whitespace-only
        InputTooLongError: If text exceeds max length
    """
    if text is None:
        raise EmptyInputError()

    trimmed = text.strip()

    if not trimmed:
        raise EmptyInputError()

    if len(trimmed) > MAX_INPUT_LENGTH:
        raise InputTooLongError(len(trimmed), MAX_INPUT_LENGTH)

    return trimmed


def _normalize_tier(tier: Optional[str]) -> Tier:
    """
    Normalize tier string to canonical Tier enum.

    - Case-insensitive
    - Handles aliases (e.g., "free" -> GOOD)
    - Defaults to GOOD if None

    Returns:
        Canonical Tier enum value

    Raises:
        InvalidTierError: If tier is not a valid value
    """
    if tier is None:
        return Tier.GOOD

    tier_lower = tier.lower().strip()

    # Check aliases first
    if tier_lower in TIER_ALIASES:
        return TIER_ALIASES[tier_lower]

    # Check canonical values
    try:
        return Tier(tier_lower)
    except ValueError:
        raise InvalidTierError(tier)


# =============================================================================
# Main Entry Point
# =============================================================================


def airlock_ingest(
    input_text: Optional[str],
    tier: Optional[str] = None,
    session_id: Optional[str] = None,
    canonical_legs: Optional[list] = None,
) -> NormalizedInput:
    """
    Validate and normalize evaluation input.

    This is the ONLY entry point for input validation. All evaluation endpoints
    MUST call this function before proceeding with evaluation.

    Args:
        input_text: Raw input text (bet description)
        tier: Plan tier (good/better/best, case-insensitive, optional)
        session_id: Optional session identifier
        canonical_legs: Ticket 27 - structured legs from builder (optional)

    Returns:
        NormalizedInput with validated, normalized values

    Raises:
        EmptyInputError: If input is empty or whitespace-only
        InputTooLongError: If input exceeds max length
        InvalidTierError: If tier is not valid

    Example:
        try:
            normalized = airlock_ingest(
                input_text=request.input,
                tier=request.tier,
            )
            # Use normalized.input_text, normalized.tier
        except AirlockError as e:
            return error_response(e.code, e.message)
    """
    # Validate and normalize input text
    validated_text = _validate_input_text(input_text)

    # Normalize tier
    normalized_tier = _normalize_tier(tier)

    # Ticket 27: Convert canonical legs to frozen dataclass tuple
    frozen_legs = None
    if canonical_legs:
        frozen_legs = tuple(
            CanonicalLegData(
                entity=leg.get("entity", ""),
                market=leg.get("market", "unknown"),
                value=leg.get("value"),
                raw=leg.get("raw", ""),
            )
            for leg in canonical_legs
        )

    # Build and return normalized input
    return NormalizedInput(
        input_text=validated_text,
        tier=normalized_tier,
        session_id=session_id,
        canonical_legs=frozen_legs,
    )


def _snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase for frontend-safe output shaping."""
    if snake_str.startswith("_"):
        return snake_str
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def _convert_keys_to_camel(obj: Any):
    """Recursively convert dict keys from snake_case to camelCase."""
    if isinstance(obj, dict):
        return {_snake_to_camel(k): _convert_keys_to_camel(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_keys_to_camel(item) for item in obj]
    return obj


def _extract_evaluation_id(result_dict: dict[str, Any]) -> Optional[str]:
    """Resolve the canonical frontend evaluation identifier from an evaluation result."""
    evaluation_obj = result_dict.get("evaluation", {})
    if isinstance(evaluation_obj, dict) and evaluation_obj.get("parlay_id") is not None:
        return str(evaluation_obj["parlay_id"])
    if isinstance(result_dict.get("evaluation_id"), str) and result_dict["evaluation_id"].strip():
        return result_dict["evaluation_id"].strip()
    return None


def _get_nested_value(payload: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    """Return the first non-empty nested value found across candidate paths."""
    for path in paths:
        current: Any = payload
        found = True
        for key in path:
            if not isinstance(current, dict) or key not in current:
                found = False
                break
            current = current[key]
        if found and current is not None:
            if not isinstance(current, str) or current.strip():
                return current
    return None


def build_builder_handoff_payload(
    result_dict: dict[str, Any],
    normalized: NormalizedInput,
    evaluation_id: Optional[str],
) -> dict[str, Any]:
    """
    Shape the minimum viable Builder handoff contract through Airlock.

    This makes the handoff explicit instead of relying on frontend JS to infer
    its own context from scattered response fields.
    """
    primary_failure = result_dict.get("primary_failure")
    signal_info = result_dict.get("signal_info")
    delta_preview = result_dict.get("delta_preview")
    tier_value = result_dict.get("tier", normalized.tier.value)
    final_verdict = result_dict.get("final_verdict")
    protocol_context_note = None
    if isinstance(final_verdict, dict):
        note = final_verdict.get("protocol_context_note")
        if isinstance(note, str) and note.strip():
            protocol_context_note = note.strip()
    fastest_fix = None
    if isinstance(primary_failure, dict):
        fastest_fix = primary_failure.get("fastestFix") or primary_failure.get("fastest_fix")

    return {
        "evaluation_id": evaluation_id,
        "input_text": normalized.input_text,
        "tier": tier_value,
        "primary_failure": primary_failure,
        "fastest_fix": fastest_fix,
        "delta_preview": delta_preview,
        "signal_info": signal_info,
        "protocol_context_note": protocol_context_note,
    }


def build_builder_handoff_from_history_raw(
    raw_result: Optional[dict[str, Any]],
    item_dict: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Build a frontend-safe Builder handoff from stored history replay data."""
    if not isinstance(raw_result, dict):
        return None

    existing_handoff = raw_result.get("builderHandoff")
    if isinstance(existing_handoff, dict):
        return existing_handoff

    evaluation_id = _get_nested_value(
        raw_result,
        ("evaluationId",),
        ("evaluation_id",),
        ("evaluation", "parlayId"),
        ("evaluation", "parlay_id"),
    )
    input_text = (
        item_dict.get("inputText")
        or _get_nested_value(raw_result, ("input", "betText"), ("input", "bet_text"))
        or ""
    )
    tier = (
        _get_nested_value(raw_result, ("input", "tier"), ("tier",))
        or "good"
    )
    primary_failure = raw_result.get("primaryFailure") or raw_result.get("primary_failure")
    fastest_fix = None
    if isinstance(primary_failure, dict):
        fastest_fix = primary_failure.get("fastestFix") or primary_failure.get("fastest_fix")

    return {
        "evaluationId": str(evaluation_id) if evaluation_id is not None else None,
        "inputText": input_text,
        "tier": str(tier),
        "primaryFailure": primary_failure,
        "fastestFix": fastest_fix,
        "deltaPreview": raw_result.get("deltaPreview") or raw_result.get("delta_preview"),
        "signalInfo": raw_result.get("signalInfo") or raw_result.get("signal_info"),
        "protocolContextNote": _get_nested_value(
            raw_result,
            ("builderHandoff", "protocolContextNote"),
            ("finalVerdict", "protocolContextNote"),
            ("final_verdict", "protocol_context_note"),
        ),
    }


def airlock_shape_evaluate_response(
    result: Any,
    normalized: NormalizedInput,
    elapsed_ms: Optional[float] = None,
) -> dict[str, Any]:
    """
    Shape the frontend evaluation response through Airlock.

    Airlock owns the frontend-safe boundary:
    - stable top-level evaluation identifier
    - explicit builder handoff payload
    - compatibility input object
    - camelCase output for web clients
    """
    result_dict = asdict(result) if is_dataclass(result) else dict(result)
    if elapsed_ms is not None:
        result_dict["_meta"] = {"elapsed_ms": round(elapsed_ms, 2)}

    result_dict["input"] = {
        "bet_text": normalized.input_text,
        "tier": result_dict.get("tier", normalized.tier.value),
    }

    evaluation_id = _extract_evaluation_id(result_dict)
    if evaluation_id:
        result_dict["evaluation_id"] = evaluation_id

    result_dict["builder_handoff"] = build_builder_handoff_payload(
        result_dict=result_dict,
        normalized=normalized,
        evaluation_id=evaluation_id,
    )

    return _convert_keys_to_camel(result_dict)


def airlock_shape_history_list_response(
    items: list[dict[str, Any]],
    request_id: str,
) -> dict[str, Any]:
    """Shape history list output through the Airlock membrane."""
    return {
        "requestId": request_id,
        "items": items,
        "count": len(items),
    }


def airlock_shape_history_item_response(
    item_dict: dict[str, Any],
    request_id: str,
) -> dict[str, Any]:
    """Shape history replay detail into a frontend-safe contract."""
    raw_result = item_dict.get("raw")
    replay = {
        "evaluationId": _get_nested_value(
            item_dict,
            ("evaluationId",),
            ("raw", "evaluationId"),
            ("raw", "evaluation", "parlayId"),
            ("raw", "evaluation", "parlay_id"),
        ),
        "inputText": item_dict.get("inputText")
        or _get_nested_value(raw_result or {}, ("input", "betText"), ("input", "bet_text"))
        or "",
        "tier": _get_nested_value(raw_result or {}, ("input", "tier"), ("tier",)) or "good",
        "builderHandoff": build_builder_handoff_from_history_raw(raw_result, item_dict),
    }
    shaped_item = dict(item_dict)
    shaped_item["replay"] = replay
    return {
        "requestId": request_id,
        "item": shaped_item,
    }


# =============================================================================
# Utility Functions
# =============================================================================


def get_max_input_length() -> int:
    """Get the maximum allowed input length."""
    return MAX_INPUT_LENGTH


def get_valid_tiers() -> list[str]:
    """Get list of valid tier values (for documentation/error messages)."""
    return [t.value for t in Tier]
