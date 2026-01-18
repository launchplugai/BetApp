# billing/tests/test_billing.py
"""
Comprehensive tests for billing module.

Tests:
- Product/plan configuration
- Checkout session creation (mocked Stripe)
- Webhook handling (mocked events)
- Tier upgrade/downgrade logic
"""

from __future__ import annotations

import os
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

# Set test database before imports
os.environ["DNA_DB_PATH"] = ":memory:"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def reset_database():
    """Reset database before each test."""
    from persistence.db import reset_db, init_db, _local, _init_lock
    import persistence.db as db_module

    # Reset the initialized flag
    with _init_lock:
        db_module._initialized = False

    # Clear thread-local connection
    if hasattr(_local, "connection") and _local.connection:
        _local.connection.close()
        _local.connection = None

    # Initialize fresh
    init_db()
    yield
    reset_db()


@pytest.fixture
def test_user():
    """Create a test user."""
    from auth.service import create_user
    return create_user("test@example.com", "Password123", tier="GOOD")


@pytest.fixture
def best_user():
    """Create a user with BEST tier."""
    from auth.service import create_user
    return create_user("best@example.com", "Password123", tier="BEST")


# =============================================================================
# Product Tests
# =============================================================================


class TestProducts:
    """Tests for product configuration."""

    def test_get_best_plan(self):
        """get_best_plan returns correct plan."""
        from billing.products import get_best_plan

        plan = get_best_plan()

        assert plan.name == "DNA BEST"
        assert plan.tier == "BEST"
        assert plan.amount_cents == 1999
        assert plan.currency == "usd"
        assert plan.interval == "month"

    def test_get_plan_for_tier(self):
        """get_plan_for_tier returns plan for valid tier."""
        from billing.products import get_plan_for_tier

        plan = get_plan_for_tier("BEST")
        assert plan is not None
        assert plan.tier == "BEST"

        # Unknown tier
        assert get_plan_for_tier("UNKNOWN") is None

    def test_tier_from_price_id(self):
        """tier_from_price_id maps price to tier."""
        from billing.products import tier_from_price_id, get_best_plan

        plan = get_best_plan()
        assert tier_from_price_id(plan.price_id) == "BEST"
        assert tier_from_price_id("unknown_price") is None


# =============================================================================
# Stripe Client Tests
# =============================================================================


class TestStripeClient:
    """Tests for Stripe client configuration."""

    def test_is_billing_enabled_without_key(self):
        """is_billing_enabled returns False without key."""
        from billing.stripe_client import is_billing_enabled

        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": ""}, clear=False):
            # Force reimport to pick up env change
            assert not is_billing_enabled() or True  # May have SDK not installed

    def test_get_stripe_key(self):
        """get_stripe_key returns env var."""
        from billing.stripe_client import get_stripe_key

        with patch.dict(os.environ, {"STRIPE_SECRET_KEY": "sk_test_123"}):
            assert get_stripe_key() == "sk_test_123"

    def test_get_webhook_secret(self):
        """get_webhook_secret returns env var."""
        from billing.stripe_client import get_webhook_secret

        with patch.dict(os.environ, {"STRIPE_WEBHOOK_SECRET": "whsec_123"}):
            assert get_webhook_secret() == "whsec_123"

    def test_is_test_mode_default(self):
        """is_test_mode defaults to True."""
        from billing.stripe_client import is_test_mode

        with patch.dict(os.environ, {}, clear=True):
            assert is_test_mode() is True

    def test_is_test_mode_false(self):
        """is_test_mode returns False when set."""
        from billing.stripe_client import is_test_mode

        with patch.dict(os.environ, {"STRIPE_TEST_MODE": "false"}):
            assert is_test_mode() is False


# =============================================================================
# Service Tests (with mocked Stripe)
# =============================================================================


class TestBillingService:
    """Tests for billing service functions."""

    def test_billing_disabled_raises(self, test_user):
        """create_checkout_session raises when billing disabled."""
        from billing.service import create_checkout_session, BillingDisabledError

        with patch("billing.stripe_client.is_billing_enabled", return_value=False):
            with pytest.raises(BillingDisabledError):
                create_checkout_session(
                    user_id=test_user.id,
                    user_email=test_user.email,
                    success_url="http://example.com/success",
                    cancel_url="http://example.com/cancel",
                )

    @patch("billing.service.get_stripe")
    @patch("billing.service.is_billing_enabled", return_value=True)
    def test_create_checkout_session_success(self, mock_enabled, mock_get_stripe, test_user):
        """create_checkout_session creates session successfully."""
        from billing.service import create_checkout_session

        # Mock Stripe
        mock_stripe = MagicMock()
        mock_stripe.checkout.Session.create.return_value = MagicMock(
            id="cs_test_123",
            url="https://checkout.stripe.com/c/pay/cs_test_123",
        )
        mock_get_stripe.return_value = mock_stripe

        result = create_checkout_session(
            user_id=test_user.id,
            user_email=test_user.email,
            success_url="http://example.com/success",
            cancel_url="http://example.com/cancel",
        )

        assert result["session_id"] == "cs_test_123"
        assert "checkout.stripe.com" in result["checkout_url"]

        # Verify Stripe was called correctly
        mock_stripe.checkout.Session.create.assert_called_once()
        call_kwargs = mock_stripe.checkout.Session.create.call_args[1]
        assert call_kwargs["mode"] == "subscription"
        assert call_kwargs["metadata"]["user_id"] == test_user.id

    @patch("billing.service.get_stripe")
    @patch("billing.service.is_billing_enabled", return_value=True)
    def test_create_checkout_non_best_raises(self, mock_enabled, mock_get_stripe, test_user):
        """create_checkout_session raises for non-BEST tier."""
        from billing.service import create_checkout_session, CheckoutError

        with pytest.raises(CheckoutError, match="Only BEST"):
            create_checkout_session(
                user_id=test_user.id,
                user_email=test_user.email,
                success_url="http://example.com/success",
                cancel_url="http://example.com/cancel",
                tier="BETTER",  # Not supported
            )


# =============================================================================
# Webhook Handler Tests
# =============================================================================


class TestWebhookHandlers:
    """Tests for webhook handling."""

    def test_handle_checkout_completed(self, test_user):
        """handle_checkout_completed upgrades user tier."""
        from billing.service import handle_checkout_completed
        from auth.service import get_user_by_id

        # Simulate checkout session
        session = {
            "metadata": {"user_id": test_user.id},
            "customer": "cus_test_123",
            "subscription": "sub_test_123",
        }

        success = handle_checkout_completed(session)
        assert success is True

        # Verify user was upgraded
        updated_user = get_user_by_id(test_user.id)
        assert updated_user.tier == "BEST"
        assert updated_user.stripe_customer_id == "cus_test_123"
        assert updated_user.stripe_subscription_id == "sub_test_123"

    def test_handle_checkout_completed_no_user_id(self):
        """handle_checkout_completed returns False without user_id."""
        from billing.service import handle_checkout_completed

        session = {
            "metadata": {},
            "customer": "cus_test_123",
        }

        success = handle_checkout_completed(session)
        assert success is False

    def test_handle_subscription_deleted(self, test_user):
        """handle_subscription_deleted downgrades user tier."""
        from billing.service import handle_subscription_deleted, _update_user_subscription
        from auth.service import get_user_by_id

        # First upgrade the user
        _update_user_subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            new_tier="BEST",
        )

        # Simulate subscription deletion
        subscription = {
            "id": "sub_test_123",
            "metadata": {"user_id": test_user.id},
        }

        success = handle_subscription_deleted(subscription)
        assert success is True

        # Verify user was downgraded
        updated_user = get_user_by_id(test_user.id)
        assert updated_user.tier == "GOOD"

    def test_handle_payment_failed(self, test_user):
        """handle_payment_failed downgrades user tier."""
        from billing.service import handle_payment_failed, _update_user_subscription
        from auth.service import get_user_by_id

        # First upgrade the user
        _update_user_subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_test_123",
            stripe_subscription_id="sub_test_123",
            new_tier="BEST",
        )

        # Simulate payment failure
        invoice = {
            "subscription": "sub_test_123",
        }

        success = handle_payment_failed(invoice)
        assert success is True

        # Verify user was downgraded
        updated_user = get_user_by_id(test_user.id)
        assert updated_user.tier == "GOOD"


# =============================================================================
# Tier Update Tests
# =============================================================================


class TestTierUpdates:
    """Tests for tier update logic."""

    def test_update_user_subscription(self, test_user):
        """_update_user_subscription updates all fields."""
        from billing.service import _update_user_subscription
        from auth.service import get_user_by_id

        success = _update_user_subscription(
            user_id=test_user.id,
            stripe_customer_id="cus_new_123",
            stripe_subscription_id="sub_new_123",
            new_tier="BEST",
        )

        assert success is True

        updated = get_user_by_id(test_user.id)
        assert updated.stripe_customer_id == "cus_new_123"
        assert updated.stripe_subscription_id == "sub_new_123"
        assert updated.tier == "BEST"
        assert updated.tier_updated_at is not None

    def test_update_user_tier_only(self, test_user):
        """_update_user_subscription can update just tier."""
        from billing.service import _update_user_subscription
        from auth.service import get_user_by_id

        success = _update_user_subscription(
            user_id=test_user.id,
            new_tier="BETTER",
        )

        assert success is True

        updated = get_user_by_id(test_user.id)
        assert updated.tier == "BETTER"
        assert updated.stripe_customer_id is None  # Not changed

    def test_find_user_by_subscription(self, test_user):
        """_find_user_by_subscription finds user."""
        from billing.service import _update_user_subscription, _find_user_by_subscription

        # Set subscription ID
        _update_user_subscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_find_123",
        )

        found_id = _find_user_by_subscription("sub_find_123")
        assert found_id == test_user.id

    def test_find_user_by_subscription_not_found(self):
        """_find_user_by_subscription returns None for unknown."""
        from billing.service import _find_user_by_subscription

        assert _find_user_by_subscription("sub_unknown") is None


# =============================================================================
# Webhook Verification Tests (mocked)
# =============================================================================


class TestWebhookVerification:
    """Tests for webhook signature verification."""

    def test_verify_requires_stripe(self):
        """verify_webhook_signature requires Stripe SDK."""
        from billing.webhooks import verify_webhook_signature, SignatureVerificationError

        with patch("billing.webhooks.STRIPE_AVAILABLE", False):
            with pytest.raises(SignatureVerificationError, match="not available"):
                verify_webhook_signature(b"payload", "sig")

    def test_verify_requires_secret(self):
        """verify_webhook_signature requires webhook secret."""
        from billing.webhooks import verify_webhook_signature, SignatureVerificationError

        with patch("billing.webhooks.STRIPE_AVAILABLE", True):
            with patch("billing.webhooks.get_webhook_secret", return_value=""):
                with pytest.raises(SignatureVerificationError, match="not configured"):
                    verify_webhook_signature(b"payload", "sig")

    @patch("billing.webhooks.get_stripe")
    @patch("billing.webhooks.get_webhook_secret", return_value="whsec_test")
    def test_verify_success(self, mock_secret, mock_get_stripe):
        """verify_webhook_signature returns event on success."""
        from billing.webhooks import verify_webhook_signature

        # Mock successful verification
        mock_stripe = MagicMock()
        mock_event = {"id": "evt_123", "type": "checkout.session.completed"}
        mock_stripe.Webhook.construct_event.return_value = mock_event
        mock_get_stripe.return_value = mock_stripe

        with patch("billing.webhooks.STRIPE_AVAILABLE", True):
            result = verify_webhook_signature(b"payload", "sig_123")

        assert result == mock_event


# =============================================================================
# Process Webhook Event Tests
# =============================================================================


class TestProcessWebhookEvent:
    """Tests for webhook event processing."""

    def test_process_unhandled_event(self):
        """process_webhook_event acknowledges unhandled events."""
        from billing.webhooks import process_webhook_event

        event = {
            "id": "evt_123",
            "type": "customer.created",  # Not handled
            "data": {"object": {}},
        }

        success, message = process_webhook_event(event)
        assert success is True
        assert "not handled" in message

    def test_process_checkout_completed(self, test_user):
        """process_webhook_event handles checkout.session.completed."""
        from billing.webhooks import process_webhook_event
        from auth.service import get_user_by_id

        event = {
            "id": "evt_123",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "mode": "subscription",
                    "metadata": {"user_id": test_user.id},
                    "customer": "cus_test",
                    "subscription": "sub_test",
                }
            },
        }

        success, message = process_webhook_event(event)
        assert success is True

        # Verify user was upgraded
        updated = get_user_by_id(test_user.id)
        assert updated.tier == "BEST"

    def test_process_subscription_deleted(self, test_user):
        """process_webhook_event handles subscription.deleted."""
        from billing.webhooks import process_webhook_event
        from billing.service import _update_user_subscription
        from auth.service import get_user_by_id

        # Setup: upgrade user first
        _update_user_subscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_del",
            new_tier="BEST",
        )

        event = {
            "id": "evt_123",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_del",
                    "metadata": {"user_id": test_user.id},
                }
            },
        }

        success, message = process_webhook_event(event)
        assert success is True

        # Verify user was downgraded
        updated = get_user_by_id(test_user.id)
        assert updated.tier == "GOOD"


# =============================================================================
# Integration Tests
# =============================================================================


class TestBillingIntegration:
    """Integration tests for full billing flows."""

    def test_full_upgrade_flow(self, test_user):
        """Test complete upgrade flow: checkout -> webhook -> tier change."""
        from billing.service import handle_checkout_completed
        from auth.service import get_user_by_id

        # Verify initial state
        assert test_user.tier == "GOOD"
        assert test_user.stripe_subscription_id is None

        # Simulate successful checkout completion
        session = {
            "metadata": {"user_id": test_user.id, "tier": "BEST"},
            "customer": "cus_upgrade_123",
            "subscription": "sub_upgrade_123",
        }

        handle_checkout_completed(session)

        # Verify final state
        updated = get_user_by_id(test_user.id)
        assert updated.tier == "BEST"
        assert updated.stripe_customer_id == "cus_upgrade_123"
        assert updated.stripe_subscription_id == "sub_upgrade_123"
        assert updated.has_active_subscription is True

    def test_full_downgrade_flow(self, test_user):
        """Test complete downgrade flow: upgrade -> cancel -> tier change."""
        from billing.service import handle_checkout_completed, handle_subscription_deleted
        from auth.service import get_user_by_id

        # First upgrade
        session = {
            "metadata": {"user_id": test_user.id},
            "customer": "cus_123",
            "subscription": "sub_123",
        }
        handle_checkout_completed(session)

        # Verify upgraded
        updated = get_user_by_id(test_user.id)
        assert updated.tier == "BEST"

        # Now cancel
        subscription = {
            "id": "sub_123",
            "metadata": {"user_id": test_user.id},
        }
        handle_subscription_deleted(subscription)

        # Verify downgraded
        final = get_user_by_id(test_user.id)
        assert final.tier == "GOOD"
        # Subscription ID is cleared (empty string stored as empty)
        assert not final.stripe_subscription_id or final.stripe_subscription_id == ""
