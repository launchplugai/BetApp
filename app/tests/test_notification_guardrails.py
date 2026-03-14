"""
Tests for Notification Guardrails (S20).
Tests the NotificationGuardrails class that prevents notification spam
through cooldown tracking, daily caps, and kill switch functionality.
"""

import pytest
from datetime import UTC, datetime, timedelta, time
from unittest.mock import Mock, patch, MagicMock

from app.services.notification_guardrails import (
    NotificationGuardrails, get_notification_guardrails
)
from app.services.notification_types import GuardrailResult


@pytest.fixture
def guardrails():
    """Create a fresh NotificationGuardrails instance."""
    return NotificationGuardrails()


@pytest.fixture
def sample_user_id():
    return "user_test123"


@pytest.fixture
def sample_game_id():
    return "game_456"


class TestKillSwitch:
    """Tests for kill switch functionality."""
    
    def test_kill_switch_active(self, guardrails):
        """Kill switch active blocks all notifications."""
        import app.services.notification_guardrails as ng
        
        # Activate kill switch
        ng._kill_switch_active = True
        
        try:
            result = guardrails.can_notify("user_123", "game_456")
            
            assert result.allowed is False
            assert "kill switch" in result.reason.lower()
        finally:
            # Reset kill switch
            ng._kill_switch_active = False
    
    def test_kill_switch_inactive(self, guardrails):
        """Kill switch inactive allows notifications."""
        import app.services.notification_guardrails as ng
        
        # Ensure kill switch is off
        ng._kill_switch_active = False
        
        # Need to bypass quiet hours for this test
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify("user_123", "game_456")
        
        assert result.allowed is True
    
    def test_kill_switch_defaults_open(self, guardrails):
        """Kill switch defaults to allowing (fail open)."""
        import app.services.notification_guardrails as ng
        
        # Ensure kill switch is off (default state)
        ng._kill_switch_active = False
        
        # Should allow notifications
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify("user_123", "game_456")
        
        assert result.allowed is True


class TestDailyCap:
    """Tests for daily notification cap enforcement."""
    
    def test_within_daily_cap(self, guardrails, sample_user_id, sample_game_id):
        """Notification within daily cap is allowed."""
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify(sample_user_id, sample_game_id)
        
        assert result.allowed is True
        assert result.remaining_today == 9  # 10 - 1
    
    def test_daily_cap_reached(self, guardrails, sample_user_id, sample_game_id):
        """Notification at daily cap is blocked."""
        # Fill up to cap
        for i in range(10):
            guardrails.record_notification(sample_user_id, f"game_{i}", f"notif_{i}")
        
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify(sample_user_id, sample_game_id)
        
        assert result.allowed is False
        assert "daily cap" in result.reason.lower()
        assert result.remaining_today == 0
    
    def test_daily_cap_with_custom_limit(self, guardrails, sample_user_id, sample_game_id):
        """Custom daily cap is respected."""
        rules = {"max_notifications_per_day": 2}
        
        # First notification
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result1 = guardrails.can_notify(sample_user_id, "game_1", rules=rules)
        guardrails.record_notification(sample_user_id, "game_1", "notif_1")
        
        # Second notification
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result2 = guardrails.can_notify(sample_user_id, "game_2", rules=rules)
        guardrails.record_notification(sample_user_id, "game_2", "notif_2")
        
        # Third should be blocked
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result3 = guardrails.can_notify(sample_user_id, "game_3", rules=rules)
        
        assert result1.allowed is True
        assert result2.allowed is True
        assert result3.allowed is False
    
    def test_get_daily_stats(self, guardrails, sample_user_id):
        """Daily stats report correctly."""
        guardrails.record_notification(sample_user_id, "game_1", "notif_1")
        guardrails.record_notification(sample_user_id, "game_2", "notif_2")
        
        stats = guardrails.get_daily_stats(sample_user_id)
        
        assert stats["sent_today"] == 2
        assert stats["remaining_today"] == 8
        assert stats["daily_cap"] == 10
    
    def test_reset_daily_counts(self, guardrails, sample_user_id):
        """Reset daily counts clears all counts."""
        guardrails.record_notification(sample_user_id, "game_1", "notif_1")
        
        guardrails.reset_daily_counts()
        
        stats = guardrails.get_daily_stats(sample_user_id)
        assert stats["sent_today"] == 0


class TestCooldown:
    """Tests for per-user, per-game cooldown."""
    
    def test_no_cooldown_first_notification(self, guardrails, sample_user_id, sample_game_id):
        """First notification for game has no cooldown."""
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify(sample_user_id, sample_game_id)
        
        assert result.allowed is True
    
    def test_cooldown_active(self, guardrails, sample_user_id, sample_game_id):
        """Notification during cooldown is blocked."""
        # Record first notification
        guardrails.record_notification(sample_user_id, sample_game_id, "notif_1")
        
        # Try second immediately
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify(sample_user_id, sample_game_id)
        
        assert result.allowed is False
        assert "cooldown" in result.reason.lower()
    
    def test_cooldown_expired(self, guardrails, sample_user_id, sample_game_id):
        """Notification after cooldown expires is allowed."""
        # Record first notification in the past
        cooldown_key = f"{sample_user_id}:{sample_game_id}"
        guardrails._cooldowns[cooldown_key] = datetime.now(UTC) - timedelta(minutes=61)
        
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify(sample_user_id, sample_game_id)
        
        assert result.allowed is True
    
    def test_cooldown_custom_duration(self, guardrails, sample_user_id, sample_game_id):
        """Custom cooldown duration is respected."""
        rules = {"cooldown_minutes": 30}
        
        # Record first notification 31 minutes ago
        cooldown_key = f"{sample_user_id}:{sample_game_id}"
        guardrails._cooldowns[cooldown_key] = datetime.now(UTC) - timedelta(minutes=31)
        
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify(sample_user_id, sample_game_id, rules=rules)
        
        assert result.allowed is True  # 31 > 30
    
    def test_get_cooldown_status_inactive(self, guardrails, sample_user_id, sample_game_id):
        """Cooldown status shows inactive when no cooldown."""
        status = guardrails.get_cooldown_status(sample_user_id, sample_game_id)
        
        assert status["in_cooldown"] is False
        assert status["last_sent"] is None
        assert status["remaining_minutes"] == 0
    
    def test_get_cooldown_status_active(self, guardrails, sample_user_id, sample_game_id):
        """Cooldown status shows active when in cooldown."""
        guardrails.record_notification(sample_user_id, sample_game_id, "notif_1")
        
        status = guardrails.get_cooldown_status(sample_user_id, sample_game_id)
        
        assert status["in_cooldown"] is True
        assert status["last_sent"] is not None
        assert status["remaining_minutes"] > 0
    
    def test_different_games_no_cooldown_conflict(self, guardrails, sample_user_id):
        """Cooldown for one game doesn't affect another."""
        guardrails.record_notification(sample_user_id, "game_1", "notif_1")
        
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify(sample_user_id, "game_2")
        
        assert result.allowed is True


class TestEntropy:
    """Tests for entropy (duplicate) suppression."""
    
    def test_no_entropy_first_content(self, guardrails, sample_user_id, sample_game_id):
        """First unique content has no entropy restriction."""
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify(
                sample_user_id, sample_game_id, 
                content_hash="hash_abc123"
            )
        
        assert result.allowed is True
    
    def test_entropy_duplicate_blocked(self, guardrails, sample_user_id, sample_game_id):
        """Duplicate content within window is blocked."""
        content_hash = "hash_duplicate"
        
        # First notification with this content
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            guardrails.can_notify(sample_user_id, "game_1", content_hash=content_hash)
        
        # Second notification with same content, different game
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify(sample_user_id, "game_2", content_hash=content_hash)
        
        assert result.allowed is False
        assert "similar notification" in result.reason.lower()
    
    def test_entropy_expired(self, guardrails, sample_user_id, sample_game_id):
        """Content after entropy window is allowed."""
        content_hash = "hash_old"
        
        # Add to cache in the past
        guardrails._entropy_cache[content_hash] = datetime.now(UTC) - timedelta(minutes=31)
        
        with patch.object(guardrails, '_in_quiet_hours', return_value=False):
            result = guardrails.can_notify(
                sample_user_id, sample_game_id,
                content_hash=content_hash
            )
        
        assert result.allowed is True
    
    def test_cleanup_entropy_cache(self, guardrails):
        """Old entropy cache entries are cleaned up."""
        # Add old entries
        guardrails._entropy_cache["old_1"] = datetime.now(UTC) - timedelta(minutes=90)
        guardrails._entropy_cache["old_2"] = datetime.now(UTC) - timedelta(minutes=120)
        guardrails._entropy_cache["new_1"] = datetime.now(UTC) - timedelta(minutes=10)
        
        guardrails.cleanup_entropy_cache(max_age_minutes=60)
        
        assert "old_1" not in guardrails._entropy_cache
        assert "old_2" not in guardrails._entropy_cache
        assert "new_1" in guardrails._entropy_cache


class TestQuietHours:
    """Tests for quiet hours functionality."""
    
    @patch('app.services.notification_guardrails.get_session')
    @patch('app.models.user_preferences.UserPreferences')
    def test_in_quiet_hours_blocks(self, mock_prefs_cls, mock_get_session, 
                                    guardrails, sample_user_id):
        """Notifications during quiet hours are blocked."""
        # Setup mock
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        mock_prefs = MagicMock()
        mock_prefs.get_notification_rules.return_value = {
            "quiet_hours": {
                "enabled": True,
                "start": "22:00",
                "end": "08:00"
            }
        }
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_prefs
        
        # Mock current time during quiet hours (23:00)
        with patch('app.services.notification_guardrails.utc_now', return_value=datetime(2024, 1, 1, 23, 0, 0, tzinfo=UTC)):
            
            result = guardrails._in_quiet_hours(sample_user_id)
        
        assert result is True
    
    @patch('app.services.notification_guardrails.get_session')
    @patch('app.models.user_preferences.UserPreferences')
    def test_outside_quiet_hours_allows(self, mock_prefs_cls, mock_get_session,
                                        guardrails, sample_user_id):
        """Notifications outside quiet hours are allowed."""
        # Setup mock
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        mock_prefs = MagicMock()
        mock_prefs.get_notification_rules.return_value = {
            "quiet_hours": {
                "enabled": True,
                "start": "22:00",
                "end": "08:00"
            }
        }
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_prefs
        
        # Mock current time outside quiet hours (14:00)
        with patch('app.services.notification_guardrails.utc_now', return_value=datetime(2024, 1, 1, 14, 0, 0, tzinfo=UTC)):
            
            result = guardrails._in_quiet_hours(sample_user_id)
        
        assert result is False
    
    @patch('app.services.notification_guardrails.get_session')
    def test_quiet_hours_disabled(self, mock_get_session, guardrails, sample_user_id):
        """Quiet hours disabled allows notifications."""
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session
        
        mock_prefs = MagicMock()
        mock_prefs.get_notification_rules.return_value = {
            "quiet_hours": {
                "enabled": False,
                "start": "22:00",
                "end": "08:00"
            }
        }
        mock_session.query.return_value.filter_by.return_value.first.return_value = mock_prefs
        
        # Even at 23:00
        with patch('app.services.notification_guardrails.utc_now', return_value=datetime(2024, 1, 1, 23, 0, 0, tzinfo=UTC)):
            
            result = guardrails._in_quiet_hours(sample_user_id)
        
        assert result is False


class TestRecordNotification:
    """Tests for recording sent notifications."""
    
    def test_record_updates_cooldown(self, guardrails, sample_user_id, sample_game_id):
        """Recording updates cooldown timestamp."""
        cooldown_key = f"{sample_user_id}:{sample_game_id}"
        
        # Initially no cooldown
        assert cooldown_key not in guardrails._cooldowns
        
        guardrails.record_notification(sample_user_id, sample_game_id, "notif_1")
        
        # Now has cooldown
        assert cooldown_key in guardrails._cooldowns
        assert isinstance(guardrails._cooldowns[cooldown_key], datetime)
    
    def test_record_increments_daily_count(self, guardrails, sample_user_id):
        """Recording increments daily count."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        
        initial_count = guardrails._daily_counts[sample_user_id][today]
        
        guardrails.record_notification(sample_user_id, "game_1", "notif_1")
        
        assert guardrails._daily_counts[sample_user_id][today] == initial_count + 1


class TestGetRemainingDaily:
    """Tests for getting remaining daily notifications."""
    
    def test_get_remaining_default_cap(self, guardrails, sample_user_id):
        """Get remaining with default cap."""
        remaining = guardrails._get_remaining_daily(sample_user_id, None)
        assert remaining == 10  # Default daily cap
    
    def test_get_remaining_custom_cap(self, guardrails, sample_user_id):
        """Get remaining with custom cap."""
        rules = {"max_notifications_per_day": 5}
        remaining = guardrails._get_remaining_daily(sample_user_id, rules)
        assert remaining == 5
    
    def test_get_remaining_after_sending(self, guardrails, sample_user_id):
        """Get remaining after sending some."""
        guardrails.record_notification(sample_user_id, "game_1", "notif_1")
        guardrails.record_notification(sample_user_id, "game_2", "notif_2")
        
        remaining = guardrails._get_remaining_daily(sample_user_id, None)
        assert remaining == 8


class TestKillSwitchMethods:
    """Tests for kill switch activation/deactivation."""
    
    def test_activate_kill_switch(self, guardrails):
        """Activate kill switch sets global flag."""
        import app.services.notification_guardrails as ng
        
        # Ensure it's off first
        ng._kill_switch_active = False
        
        guardrails.activate_kill_switch()
        
        assert ng._kill_switch_active is True
        
        # Reset
        ng._kill_switch_active = False
    
    def test_deactivate_kill_switch(self, guardrails):
        """Deactivate kill switch clears global flag."""
        import app.services.notification_guardrails as ng
        
        # Ensure it's on first
        ng._kill_switch_active = True
        
        guardrails.deactivate_kill_switch()
        
        assert ng._kill_switch_active is False


class TestGuardrailResult:
    """Tests for GuardrailResult dataclass."""

    def test_result_allowed(self):
        """Allowed result has correct properties."""
        result = GuardrailResult(
            allowed=True,
            reason="All checks passed",
            remaining_today=5
        )

        assert result.allowed is True
        assert result.remaining_today == 5
        assert result.beta_gate_pass is True  # Default value

    def test_result_blocked(self):
        """Blocked result has correct properties."""
        result = GuardrailResult(
            allowed=False,
            reason="Daily cap reached",
            remaining_today=0
        )

        assert result.allowed is False
        assert "cap" in result.reason


class TestBetaGate:
    """Tests for beta user gating (S20-P2)."""

    def test_beta_user_passes_gate(self, guardrails):
        """Beta user in allowlist passes gate."""
        from app.config import is_beta_user

        # Set up beta allowlist with test user (as list)
        beta_user_ids = ["user_test123", "user_beta456"]

        # Verify user is in allowlist
        assert is_beta_user("user_test123", beta_user_ids) is True

        # Mock config to return beta allowlist
        with patch('app.services.notification_guardrails.load_config') as mock_load_config:
            mock_config = Mock()
            mock_config.notifications_beta_user_ids = beta_user_ids
            mock_load_config.return_value = mock_config

            # Also need to mock quiet hours
            with patch.object(guardrails, '_in_quiet_hours', return_value=False):
                result = guardrails.can_notify("user_test123", "game_456")

        assert result.allowed is True
        assert result.beta_gate_pass is True

    def test_non_beta_user_blocked(self, guardrails):
        """Non-beta user blocked with correct reason."""
        from app.config import is_beta_user

        # Set up beta allowlist without test user (as list)
        beta_user_ids = ["user_beta456", "user_beta789"]

        # Verify user is NOT in allowlist
        assert is_beta_user("user_test123", beta_user_ids) is False

        # Mock config to return beta allowlist
        with patch('app.services.notification_guardrails.load_config') as mock_load_config:
            mock_config = Mock()
            mock_config.notifications_beta_user_ids = beta_user_ids
            mock_load_config.return_value = mock_config

            result = guardrails.can_notify("user_test123", "game_456")

        assert result.allowed is False
        assert result.reason == "beta_gate"
        assert result.beta_gate_pass is False

    def test_empty_allowlist_allows_all(self, guardrails):
        """Empty allowlist allows all users (gating disabled)."""
        from app.config import is_beta_user

        # Empty allowlist (as list)
        beta_user_ids = []

        # All users should pass when allowlist is empty
        assert is_beta_user("any_user", beta_user_ids) is True

        # Mock config with empty allowlist
        with patch('app.services.notification_guardrails.load_config') as mock_load_config:
            mock_config = Mock()
            mock_config.notifications_beta_user_ids = beta_user_ids
            mock_load_config.return_value = mock_config

            with patch.object(guardrails, '_in_quiet_hours', return_value=False):
                result = guardrails.can_notify("any_user", "game_456")

        assert result.allowed is True
        assert result.beta_gate_pass is True

    def test_none_allowlist_allows_all(self, guardrails):
        """None allowlist allows all users (gating disabled)."""
        from app.config import is_beta_user

        # All users should pass when allowlist is None
        assert is_beta_user("any_user", None) is True

        # Mock config with None allowlist
        with patch('app.services.notification_guardrails.load_config') as mock_load_config:
            mock_config = Mock()
            mock_config.notifications_beta_user_ids = None
            mock_load_config.return_value = mock_config

            with patch.object(guardrails, '_in_quiet_hours', return_value=False):
                result = guardrails.can_notify("any_user", "game_456")

        assert result.allowed is True
        assert result.beta_gate_pass is True

    def test_is_beta_user_helper(self):
        """Test is_beta_user helper function directly."""
        from app.config import is_beta_user

        # User in list
        assert is_beta_user("user1", ["user1", "user2", "user3"]) is True
        assert is_beta_user("user2", ["user1", "user2", "user3"]) is True

        # User not in list
        assert is_beta_user("user4", ["user1", "user2", "user3"]) is False
        assert is_beta_user("user1", ["user2", "user3"]) is False

        # Empty list allows all
        assert is_beta_user("any_user", []) is True

        # None allows all
        assert is_beta_user("any_user", None) is True

        # Case sensitivity
        assert is_beta_user("User1", ["user1", "user2"]) is False


class TestSingleton:
    """Tests for singleton behavior."""
    
    def test_get_notification_guardrails_singleton(self):
        """get_notification_guardrails returns same instance."""
        g1 = get_notification_guardrails()
        g2 = get_notification_guardrails()
        
        assert g1 is g2
    
    def test_get_notification_guardrails_creates_instance(self):
        """get_notification_guardrails creates instance if none exists."""
        # Reset singleton for test
        import app.services.notification_guardrails as ng
        ng._guardrails_instance = None
        
        g = get_notification_guardrails()
        
        assert g is not None
        assert isinstance(g, NotificationGuardrails)
