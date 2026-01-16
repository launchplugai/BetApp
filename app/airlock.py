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

from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
class NormalizedInput:
    """
    Validated and normalized input from Airlock.

    All fields are guaranteed to be valid when this object exists.
    Routes should use these values instead of raw request values.
    """
    input_text: str  # Trimmed, validated input text
    tier: Tier  # Canonical tier enum
    session_id: Optional[str] = None  # Optional session identifier

    @property
    def input_length(self) -> int:
        """Length of input text (safe to log)."""
        return len(self.input_text)


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
) -> NormalizedInput:
    """
    Validate and normalize evaluation input.

    This is the ONLY entry point for input validation. All evaluation endpoints
    MUST call this function before proceeding with evaluation.

    Args:
        input_text: Raw input text (bet description)
        tier: Plan tier (good/better/best, case-insensitive, optional)
        session_id: Optional session identifier

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

    # Build and return normalized input
    return NormalizedInput(
        input_text=validated_text,
        tier=normalized_tier,
        session_id=session_id,
    )


# =============================================================================
# Utility Functions
# =============================================================================


def get_max_input_length() -> int:
    """Get the maximum allowed input length."""
    return MAX_INPUT_LENGTH


def get_valid_tiers() -> list[str]:
    """Get list of valid tier values (for documentation/error messages)."""
    return [t.value for t in Tier]
