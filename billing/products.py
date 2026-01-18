# billing/products.py
"""
Stripe product and price configuration.

Products:
- BEST tier monthly subscription

Price IDs should be set via environment variables for flexibility
between test and production environments.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Plan:
    """Subscription plan configuration."""
    name: str
    tier: str
    price_id: str
    amount_cents: int  # For display purposes
    currency: str = "usd"
    interval: str = "month"


# Default test price ID (create in Stripe Dashboard)
DEFAULT_BEST_PRICE_ID = "price_test_best_monthly"


def get_best_price_id() -> str:
    """Get the BEST tier monthly price ID from environment."""
    return os.environ.get("STRIPE_BEST_PRICE_ID", DEFAULT_BEST_PRICE_ID)


def get_best_plan() -> Plan:
    """Get the BEST tier subscription plan."""
    return Plan(
        name="DNA BEST",
        tier="BEST",
        price_id=get_best_price_id(),
        amount_cents=1999,  # $19.99/month
        currency="usd",
        interval="month",
    )


# Tier mapping
TIER_TO_PLAN = {
    "BEST": get_best_plan,
}

# Default tier when subscription ends
DEFAULT_TIER = "GOOD"


def get_plan_for_tier(tier: str) -> Optional[Plan]:
    """Get plan configuration for a tier."""
    tier = tier.upper()
    factory = TIER_TO_PLAN.get(tier)
    return factory() if factory else None


def tier_from_price_id(price_id: str) -> Optional[str]:
    """
    Determine tier from a Stripe price ID.

    Returns:
        Tier name or None if not a known price
    """
    best_plan = get_best_plan()
    if price_id == best_plan.price_id:
        return "BEST"
    return None
