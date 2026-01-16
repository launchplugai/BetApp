# billing/webhooks.py
"""
Stripe webhook handling with signature verification.

Security:
- All webhooks verified using Stripe signing secret
- Never trust unverified payloads
- Log all webhook events for audit trail
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from billing.stripe_client import get_stripe, get_webhook_secret, STRIPE_AVAILABLE
from billing.service import (
    handle_checkout_completed,
    handle_subscription_deleted,
    handle_payment_failed,
)

_logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Webhook processing error."""
    pass


class SignatureVerificationError(WebhookError):
    """Webhook signature verification failed."""
    pass


def verify_webhook_signature(payload: bytes, signature: str) -> dict:
    """
    Verify Stripe webhook signature and parse event.

    Args:
        payload: Raw request body bytes
        signature: Stripe-Signature header value

    Returns:
        Parsed Stripe event object

    Raises:
        SignatureVerificationError: If signature is invalid
    """
    if not STRIPE_AVAILABLE:
        raise SignatureVerificationError("Stripe SDK not available")

    webhook_secret = get_webhook_secret()
    if not webhook_secret:
        raise SignatureVerificationError("Webhook secret not configured")

    stripe = get_stripe()

    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            webhook_secret,
        )
        return event

    except stripe.error.SignatureVerificationError as e:
        _logger.warning(f"Webhook signature verification failed: {e}")
        raise SignatureVerificationError("Invalid webhook signature")

    except Exception as e:
        _logger.error(f"Webhook parsing error: {e}")
        raise WebhookError(f"Failed to parse webhook: {e}")


def process_webhook_event(event: dict) -> Tuple[bool, str]:
    """
    Process a verified Stripe webhook event.

    Args:
        event: Verified Stripe event object

    Returns:
        Tuple of (success, message)
    """
    event_type = event.get("type", "unknown")
    event_id = event.get("id", "unknown")

    _logger.info(f"Processing webhook event: {event_type}", extra={"event_id": event_id})

    # Route to appropriate handler
    handlers = {
        "checkout.session.completed": _handle_checkout_session,
        "customer.subscription.deleted": _handle_subscription_deleted,
        "invoice.payment_failed": _handle_invoice_payment_failed,
    }

    handler = handlers.get(event_type)

    if handler is None:
        # Unhandled event type - acknowledge but don't process
        _logger.debug(f"Unhandled webhook event type: {event_type}")
        return True, f"Event type {event_type} not handled"

    try:
        success = handler(event)
        if success:
            return True, f"Successfully processed {event_type}"
        else:
            return False, f"Handler returned failure for {event_type}"

    except Exception as e:
        _logger.error(f"Webhook handler error for {event_type}: {e}")
        return False, f"Handler error: {e}"


def _handle_checkout_session(event: dict) -> bool:
    """Handle checkout.session.completed event."""
    session = event.get("data", {}).get("object", {})

    # Only process subscription checkouts
    if session.get("mode") != "subscription":
        _logger.debug("Ignoring non-subscription checkout")
        return True

    return handle_checkout_completed(session)


def _handle_subscription_deleted(event: dict) -> bool:
    """Handle customer.subscription.deleted event."""
    subscription = event.get("data", {}).get("object", {})
    return handle_subscription_deleted(subscription)


def _handle_invoice_payment_failed(event: dict) -> bool:
    """Handle invoice.payment_failed event."""
    invoice = event.get("data", {}).get("object", {})

    # Only process subscription invoices
    if not invoice.get("subscription"):
        _logger.debug("Ignoring non-subscription invoice")
        return True

    return handle_payment_failed(invoice)
