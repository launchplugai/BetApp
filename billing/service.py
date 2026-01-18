# billing/service.py
"""
Billing service for Stripe subscription management.

Handles:
- Checkout session creation
- Subscription event processing
- Tier upgrades and downgrades
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from billing.stripe_client import get_stripe, is_billing_enabled
from billing.products import get_best_plan, tier_from_price_id, DEFAULT_TIER

_logger = logging.getLogger(__name__)


class BillingError(Exception):
    """Base billing error."""
    pass


class BillingDisabledError(BillingError):
    """Billing is not enabled."""
    pass


class CheckoutError(BillingError):
    """Checkout session creation failed."""
    pass


def create_checkout_session(
    user_id: str,
    user_email: str,
    success_url: str,
    cancel_url: str,
    tier: str = "BEST",
) -> dict:
    """
    Create a Stripe Checkout session for subscription.

    Args:
        user_id: Internal user ID (stored in metadata)
        user_email: User's email for Stripe customer
        success_url: URL to redirect on success
        cancel_url: URL to redirect on cancel
        tier: Tier to subscribe to (default: BEST)

    Returns:
        Dict with session_id and checkout_url

    Raises:
        BillingDisabledError: If billing is not enabled
        CheckoutError: If session creation fails
    """
    if not is_billing_enabled():
        raise BillingDisabledError("Billing is not enabled. Check STRIPE_SECRET_KEY.")

    stripe = get_stripe()
    plan = get_best_plan()

    if tier.upper() != "BEST":
        raise CheckoutError(f"Only BEST tier subscriptions are available")

    try:
        # Check if user already has a Stripe customer
        from auth.service import get_user_by_id
        user = get_user_by_id(user_id)

        customer_id = None
        if user and hasattr(user, 'stripe_customer_id') and user.stripe_customer_id:
            customer_id = user.stripe_customer_id

        session_params = {
            "mode": "subscription",
            "payment_method_types": ["card"],
            "line_items": [
                {
                    "price": plan.price_id,
                    "quantity": 1,
                }
            ],
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "user_id": user_id,
                "tier": tier.upper(),
            },
            "subscription_data": {
                "metadata": {
                    "user_id": user_id,
                }
            },
        }

        # Use existing customer or create new
        if customer_id:
            session_params["customer"] = customer_id
        else:
            session_params["customer_email"] = user_email

        session = stripe.checkout.Session.create(**session_params)

        _logger.info(
            f"Created checkout session for user {user_id}",
            extra={"session_id": session.id, "tier": tier},
        )

        return {
            "session_id": session.id,
            "checkout_url": session.url,
        }

    except Exception as e:
        _logger.error(f"Checkout session creation failed: {e}")
        raise CheckoutError(f"Failed to create checkout session: {e}")


def handle_checkout_completed(session: dict) -> bool:
    """
    Handle checkout.session.completed webhook event.

    Updates user tier to BEST and stores Stripe IDs.

    Args:
        session: Stripe checkout session object

    Returns:
        True if handled successfully
    """
    user_id = session.get("metadata", {}).get("user_id")
    if not user_id:
        _logger.warning("Checkout completed without user_id in metadata")
        return False

    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    _logger.info(
        f"Processing checkout completed for user {user_id}",
        extra={
            "customer_id": customer_id,
            "subscription_id": subscription_id,
        },
    )

    try:
        # Update user with Stripe IDs and tier
        _update_user_subscription(
            user_id=user_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=subscription_id,
            new_tier="BEST",
        )
        return True

    except Exception as e:
        _logger.error(f"Failed to update user after checkout: {e}")
        return False


def handle_subscription_deleted(subscription: dict) -> bool:
    """
    Handle customer.subscription.deleted webhook event.

    Downgrades user tier to default (GOOD).

    Args:
        subscription: Stripe subscription object

    Returns:
        True if handled successfully
    """
    user_id = subscription.get("metadata", {}).get("user_id")

    if not user_id:
        # Try to find user by subscription ID
        subscription_id = subscription.get("id")
        user_id = _find_user_by_subscription(subscription_id)

    if not user_id:
        _logger.warning("Subscription deleted but no user found")
        return False

    _logger.info(f"Processing subscription deletion for user {user_id}")

    try:
        _update_user_subscription(
            user_id=user_id,
            stripe_subscription_id="",  # Clear subscription (empty string -> NULL)
            new_tier=DEFAULT_TIER,
        )
        return True

    except Exception as e:
        _logger.error(f"Failed to downgrade user after subscription deletion: {e}")
        return False


def handle_payment_failed(invoice: dict) -> bool:
    """
    Handle invoice.payment_failed webhook event.

    For v1, we immediately downgrade on payment failure.
    No grace period theatrics.

    Args:
        invoice: Stripe invoice object

    Returns:
        True if handled successfully
    """
    subscription_id = invoice.get("subscription")
    if not subscription_id:
        return False

    user_id = _find_user_by_subscription(subscription_id)
    if not user_id:
        _logger.warning(f"Payment failed but no user found for subscription {subscription_id}")
        return False

    _logger.info(f"Processing payment failure for user {user_id}")

    try:
        _update_user_subscription(
            user_id=user_id,
            new_tier=DEFAULT_TIER,
        )
        return True

    except Exception as e:
        _logger.error(f"Failed to downgrade user after payment failure: {e}")
        return False


def get_customer_portal_url(user_id: str, return_url: str) -> Optional[str]:
    """
    Create a Stripe Customer Portal session URL.

    Args:
        user_id: User ID
        return_url: URL to return to after portal

    Returns:
        Portal URL or None if user has no Stripe customer
    """
    if not is_billing_enabled():
        return None

    from auth.service import get_user_by_id
    user = get_user_by_id(user_id)

    if not user:
        return None

    customer_id = getattr(user, 'stripe_customer_id', None)
    if not customer_id:
        return None

    try:
        stripe = get_stripe()
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    except Exception as e:
        _logger.error(f"Failed to create portal session: {e}")
        return None


def _update_user_subscription(
    user_id: str,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
    new_tier: Optional[str] = None,
) -> bool:
    """
    Update user's subscription data in database.

    Args:
        user_id: User ID
        stripe_customer_id: Stripe customer ID (optional)
        stripe_subscription_id: Stripe subscription ID (optional)
        new_tier: New tier to set (optional)

    Returns:
        True if updated successfully
    """
    from persistence.db import get_db, init_db

    init_db()

    updates = []
    params = []

    if stripe_customer_id is not None:
        updates.append("stripe_customer_id = ?")
        params.append(stripe_customer_id)

    if stripe_subscription_id is not None:
        updates.append("stripe_subscription_id = ?")
        params.append(stripe_subscription_id if stripe_subscription_id else None)

    if new_tier is not None:
        updates.append("tier = ?")
        params.append(new_tier.upper())
        updates.append("tier_updated_at = ?")
        params.append(datetime.utcnow().isoformat())

    updates.append("updated_at = ?")
    params.append(datetime.utcnow().isoformat())

    params.append(user_id)

    with get_db() as conn:
        cursor = conn.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        return cursor.rowcount > 0


def _find_user_by_subscription(subscription_id: str) -> Optional[str]:
    """Find user ID by Stripe subscription ID."""
    from persistence.db import get_db, init_db

    init_db()

    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE stripe_subscription_id = ?",
            (subscription_id,),
        ).fetchone()

    return row["id"] if row else None
