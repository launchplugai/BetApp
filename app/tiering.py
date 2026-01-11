# app/tiering.py
"""
Tier Gating System for Leading Light.

Defines plan tiers (GOOD, BETTER, BEST) and gates capabilities deterministically.

Feature Matrix:
- GOOD: metrics, inductor, correlations, dna, NO alerts, NO suggestions, weather only
- BETTER: + alerts, + suggestions (max 5), + injury signals
- BEST: + trade/role signals, suggestions (max 10), demo endpoints

No payment. No auth. No persistence. Pure capability gating.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional, Set, Tuple

if TYPE_CHECKING:
    from core.evaluation import EvaluationResponse
    from core.builder_contract import BuilderView


# =============================================================================
# Plan Enum
# =============================================================================


class Plan(str, Enum):
    """Subscription plan tiers."""
    GOOD = "good"
    BETTER = "better"
    BEST = "best"


# =============================================================================
# Allowed Context Signal Types
# =============================================================================

# Context signal types allowed per plan
GOOD_SIGNALS: Set[str] = {"weather"}
BETTER_SIGNALS: Set[str] = {"weather", "injury"}
BEST_SIGNALS: Set[str] = {"weather", "injury", "trade"}


def get_allowed_signals(plan: Plan) -> Set[str]:
    """Get allowed context signal types for a plan."""
    if plan == Plan.GOOD:
        return GOOD_SIGNALS
    elif plan == Plan.BETTER:
        return BETTER_SIGNALS
    else:  # BEST
        return BEST_SIGNALS


# =============================================================================
# Tier Policy
# =============================================================================


@dataclass(frozen=True)
class TierPolicy:
    """
    Policy defining what features are allowed for a plan.

    Attributes:
        plan: The plan tier
        alerts_allowed: Whether alerts are included in response
        suggestions_allowed: Whether suggestions are included
        max_suggestions: Maximum number of suggestions (if allowed)
        allowed_signal_types: Set of allowed context signal types
        demo_endpoints_allowed: Whether demo endpoints are accessible
        full_context_notes: Whether full context notes are shown in builder
    """
    plan: Plan
    alerts_allowed: bool
    suggestions_allowed: bool
    max_suggestions: int
    allowed_signal_types: Set[str]
    demo_endpoints_allowed: bool
    full_context_notes: bool


# Pre-defined policies for each plan
GOOD_POLICY = TierPolicy(
    plan=Plan.GOOD,
    alerts_allowed=False,
    suggestions_allowed=False,
    max_suggestions=0,
    allowed_signal_types=GOOD_SIGNALS,
    demo_endpoints_allowed=False,
    full_context_notes=False,
)

BETTER_POLICY = TierPolicy(
    plan=Plan.BETTER,
    alerts_allowed=True,
    suggestions_allowed=True,
    max_suggestions=5,
    allowed_signal_types=BETTER_SIGNALS,
    demo_endpoints_allowed=False,
    full_context_notes=True,
)

BEST_POLICY = TierPolicy(
    plan=Plan.BEST,
    alerts_allowed=True,
    suggestions_allowed=True,
    max_suggestions=10,
    allowed_signal_types=BEST_SIGNALS,
    demo_endpoints_allowed=True,
    full_context_notes=True,
)

POLICIES = {
    Plan.GOOD: GOOD_POLICY,
    Plan.BETTER: BETTER_POLICY,
    Plan.BEST: BEST_POLICY,
}


def get_policy(plan: Plan) -> TierPolicy:
    """Get the tier policy for a plan."""
    return POLICIES[plan]


# =============================================================================
# Context Signal Validation
# =============================================================================


class ContextSignalNotAllowedError(Exception):
    """Raised when a context signal type is not allowed for the plan."""

    def __init__(self, signal_type: str, plan: Plan, allowed_types: Set[str]):
        self.signal_type = signal_type
        self.plan = plan
        self.allowed_types = allowed_types
        allowed_str = ", ".join(sorted(allowed_types)) if allowed_types else "none"
        super().__init__(
            f"Context signal type '{signal_type}' is not allowed for plan '{plan.value}'. "
            f"Allowed types: {allowed_str}. Upgrade to a higher plan for access."
        )


def validate_context_signals(
    signals: list[dict],
    plan: Plan,
) -> None:
    """
    Validate that all context signals are allowed for the plan.

    Args:
        signals: List of context signal dicts (must have 'type' key)
        plan: The plan to validate against

    Raises:
        ContextSignalNotAllowedError: If any signal type is not allowed
    """
    policy = get_policy(plan)
    allowed = policy.allowed_signal_types

    for signal in signals:
        signal_type = signal.get("type", "").lower()
        if signal_type not in allowed:
            raise ContextSignalNotAllowedError(signal_type, plan, allowed)


# =============================================================================
# Response Filtering
# =============================================================================


def apply_tier_to_response(
    plan: Plan,
    response: "EvaluationResponse",
) -> "EvaluationResponse":
    """
    Apply tier gating to an EvaluationResponse.

    Filters out:
    - suggestions if not allowed or over limit
    - (alerts are not part of EvaluationResponse, they're in BuilderView)

    Args:
        plan: The plan tier
        response: The original evaluation response

    Returns:
        Filtered EvaluationResponse
    """
    from dataclasses import replace
    from core.evaluation import EvaluationResponse

    policy = get_policy(plan)

    # Handle suggestions
    filtered_suggestions = None
    if policy.suggestions_allowed and response.suggestions is not None:
        # Limit to max_suggestions
        filtered_suggestions = response.suggestions[:policy.max_suggestions]
        if len(filtered_suggestions) == 0:
            filtered_suggestions = None

    # Create filtered response
    return replace(response, suggestions=filtered_suggestions)


# =============================================================================
# Builder View Filtering
# =============================================================================


def apply_tier_to_builder_view(
    plan: Plan,
    view: "BuilderView",
) -> "BuilderView":
    """
    Apply tier gating to a BuilderView.

    Filters out:
    - alerts if not allowed
    - suggestions if not allowed or over limit
    - detailed notes if not allowed (GOOD gets basic notes only)

    Args:
        plan: The plan tier
        view: The original builder view

    Returns:
        Filtered BuilderView
    """
    from dataclasses import replace
    from core.builder_contract import BuilderView, BlockBreakdown

    policy = get_policy(plan)

    # Handle alerts
    filtered_alerts = None
    if policy.alerts_allowed and view.alerts is not None:
        filtered_alerts = view.alerts

    # Handle suggestions
    filtered_suggestions = None
    if policy.suggestions_allowed and view.suggestions is not None:
        filtered_suggestions = view.suggestions[:policy.max_suggestions]
        if len(filtered_suggestions) == 0:
            filtered_suggestions = None

    # Handle block notes (GOOD gets limited notes)
    filtered_blocks = view.blocks
    if not policy.full_context_notes:
        # Strip detailed context notes for GOOD plan
        filtered_blocks = tuple(
            _strip_context_notes(block) for block in view.blocks
        )

    return replace(
        view,
        alerts=filtered_alerts,
        suggestions=filtered_suggestions,
        blocks=filtered_blocks,
    )


def _strip_context_notes(block: "BlockBreakdown") -> "BlockBreakdown":
    """
    Strip detailed context notes from a block breakdown.

    For GOOD plan, we only keep basic notes (no context delta details).
    """
    from dataclasses import replace

    # Filter out context-related notes (Weather, Injury, Trade, Role)
    basic_notes = tuple(
        note for note in block.notes
        if not any(
            note.startswith(prefix)
            for prefix in ("Weather", "Injury", "Trade", "Role")
        )
    )

    return replace(block, notes=basic_notes)


# =============================================================================
# Demo Endpoint Gating
# =============================================================================


def is_demo_allowed(plan: Plan, env_override: bool = False) -> bool:
    """
    Check if demo endpoints are allowed for the plan.

    Args:
        plan: The plan tier
        env_override: Whether an environment variable override is present

    Returns:
        True if demo endpoints are allowed
    """
    if env_override:
        return True
    return get_policy(plan).demo_endpoints_allowed


# =============================================================================
# Utility Functions
# =============================================================================


def parse_plan(plan_str: Optional[str]) -> Plan:
    """
    Parse a plan string to Plan enum.

    Args:
        plan_str: Plan string (case-insensitive) or None

    Returns:
        Plan enum (defaults to GOOD if None or invalid)
    """
    if plan_str is None:
        return Plan.GOOD

    try:
        return Plan(plan_str.lower())
    except ValueError:
        return Plan.GOOD


def get_max_suggestions_for_plan(plan: Plan) -> int:
    """Get the maximum number of suggestions allowed for a plan."""
    return get_policy(plan).max_suggestions
