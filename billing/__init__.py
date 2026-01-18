# billing/__init__.py
"""
Billing module for Stripe subscriptions.

Provides:
- Stripe Checkout session creation
- Webhook handling for subscription events
- Tier upgrade/downgrade management
"""

from billing.service import (
    create_checkout_session,
    handle_checkout_completed,
    handle_subscription_deleted,
    handle_payment_failed,
    get_customer_portal_url,
)

__all__ = [
    "create_checkout_session",
    "handle_checkout_completed",
    "handle_subscription_deleted",
    "handle_payment_failed",
    "get_customer_portal_url",
]
