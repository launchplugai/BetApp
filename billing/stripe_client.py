# billing/stripe_client.py
"""
Stripe SDK initialization and configuration.

Environment variables:
- STRIPE_SECRET_KEY: Stripe API secret key (required for production)
- STRIPE_WEBHOOK_SECRET: Webhook signing secret (required for webhooks)
- STRIPE_TEST_MODE: Set to "true" to use test mode (default: true)
"""

from __future__ import annotations

import os
import logging

_logger = logging.getLogger(__name__)

# Stripe SDK import with graceful fallback
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    stripe = None  # type: ignore
    _logger.warning("Stripe SDK not installed. Billing features disabled.")


def get_stripe_key() -> str:
    """Get Stripe secret key from environment."""
    return os.environ.get("STRIPE_SECRET_KEY", "")


def get_webhook_secret() -> str:
    """Get Stripe webhook signing secret from environment."""
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "")


def is_test_mode() -> bool:
    """Check if running in Stripe test mode."""
    return os.environ.get("STRIPE_TEST_MODE", "true").lower() == "true"


def is_billing_enabled() -> bool:
    """Check if billing is enabled (Stripe key configured)."""
    if not STRIPE_AVAILABLE:
        return False
    key = get_stripe_key()
    return bool(key and len(key) > 10)


def init_stripe() -> bool:
    """
    Initialize Stripe SDK with API key.

    Returns:
        True if initialized successfully, False otherwise
    """
    if not STRIPE_AVAILABLE:
        _logger.error("Stripe SDK not available")
        return False

    key = get_stripe_key()
    if not key:
        _logger.warning("STRIPE_SECRET_KEY not set. Billing disabled.")
        return False

    stripe.api_key = key

    # Set API version for consistency
    stripe.api_version = "2023-10-16"

    mode = "test" if is_test_mode() else "live"
    _logger.info(f"Stripe initialized in {mode} mode")

    return True


def get_stripe() -> "stripe":
    """
    Get initialized Stripe module.

    Raises:
        RuntimeError: If Stripe is not available or not initialized
    """
    if not STRIPE_AVAILABLE:
        raise RuntimeError("Stripe SDK not installed")

    if not stripe.api_key:
        if not init_stripe():
            raise RuntimeError("Stripe not initialized. Check STRIPE_SECRET_KEY.")

    return stripe
