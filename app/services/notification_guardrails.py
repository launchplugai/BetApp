"""
Notification Guardrails for S20.
Prevents notification spam through cooldown tracking, daily caps,
high entropy suppression, and kill switch functionality.
"""

import logging
from typing import Dict, Any, Optional, Set
from datetime import UTC, datetime, timedelta, time
from collections import defaultdict
import threading

from app.models import get_session
from app.models.notification_event import NotificationEvent
from app.models.notification_receipt import get_telemetry_counters
from app.services.notification_types import GuardrailResult
from app.config import is_beta_user, load_config

logger = logging.getLogger(__name__)

# Module-level kill switch for emergency use
_kill_switch_active = False


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Normalize naive or aware datetimes to timezone-aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class NotificationGuardrails:
    """
    Notification Guardrails prevents spam and enforces notification policies.
    
    Features:
    - Per-user, per-game cooldown tracking
    - Daily notification cap enforcement
    - High entropy (duplicate) suppression
    - Kill switch for emergencies
    """
    
    def __init__(self):
        self._cooldowns: Dict[str, datetime] = {}  # user_id:game_id -> last_notification_time
        self._daily_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        # user_id -> {date_str -> count}

        self._entropy_cache: Dict[str, datetime] = {}  # content_hash -> first_seen_time
        self._lock = threading.RLock()

        # Default limits
        self.default_daily_cap = 10
        self.default_cooldown_minutes = 60
        self.entropy_window_minutes = 30

        # Telemetry counters reference
        self._telemetry = get_telemetry_counters()
    
    def can_notify(self, user_id: str, game_id: str,
                   opportunity_type: str = "opportunity_alert",
                   content_hash: Optional[str] = None,
                   rules: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        """
        Check if notification can be sent based on guardrails.

        Args:
            user_id: The user to notify
            game_id: The game/event identifier
            opportunity_type: Type of opportunity
            content_hash: Hash of notification content for entropy check
            rules: User's notification rules (optional, fetched from DB if not provided)

        Returns:
            GuardrailResult with allow status and details
        """
        # Check kill switch first
        kill_switch = self._check_kill_switch()
        if kill_switch:
            self._telemetry.increment_suppressed("Kill switch active")
            return GuardrailResult(
                allowed=False,
                reason="Kill switch active - notifications paused",
                remaining_today=0,
                beta_gate_pass=False
            )

        # Check beta user gate (S20-P2)
        config = load_config(fail_fast=False)
        beta_gate_pass = is_beta_user(user_id, config.notifications_beta_user_ids)
        if not beta_gate_pass:
            logger.debug(f"Beta gate blocked notification for user {user_id}")
            self._telemetry.increment_suppressed("beta_gate")
            return GuardrailResult(
                allowed=False,
                reason="beta_gate",
                remaining_today=0,
                beta_gate_pass=False
            )

        # Check quiet hours
        if self._in_quiet_hours(user_id):
            self._telemetry.increment_suppressed("quiet_hours")
            return GuardrailResult(
                allowed=False,
                reason="In quiet hours period",
                remaining_today=self._get_remaining_daily(user_id, rules),
                beta_gate_pass=True
            )

        # Check daily cap
        daily_check = self._check_daily_cap(user_id, rules)
        if not daily_check.allowed:
            self._telemetry.increment_suppressed("daily_cap")
            return daily_check

        # Check cooldown
        cooldown_key = f"{user_id}:{game_id}"
        cooldown_check = self._check_cooldown(cooldown_key, rules)
        if not cooldown_check.allowed:
            self._telemetry.increment_suppressed("cooldown")
            return cooldown_check

        # Check entropy (duplicate suppression)
        if content_hash:
            entropy_check = self._check_entropy(content_hash)
            if not entropy_check.allowed:
                self._telemetry.increment_suppressed("cooldown")
                return GuardrailResult(
                    allowed=False,
                    reason=entropy_check.reason,
                    remaining_today=daily_check.remaining_today,
                    beta_gate_pass=True
                )

        return GuardrailResult(
            allowed=True,
            reason="All guardrails passed",
            remaining_today=daily_check.remaining_today - 1,
            beta_gate_pass=True
        )
    
    def _check_kill_switch(self) -> bool:
        """Check if kill switch is active."""
        global _kill_switch_active
        return _kill_switch_active
    
    def _check_cooldown(self, cooldown_key: str,
                        rules: Optional[Dict[str, Any]]) -> GuardrailResult:
        """Check per-user, per-game cooldown."""
        cooldown_minutes = self.default_cooldown_minutes

        if rules and "cooldown_minutes" in rules:
            cooldown_minutes = rules["cooldown_minutes"]

        with self._lock:
            last_sent = self._cooldowns.get(cooldown_key)

            if last_sent:
                elapsed = utc_now() - ensure_utc(last_sent)
                if elapsed < timedelta(minutes=cooldown_minutes):
                    remaining = cooldown_minutes - int(elapsed.total_seconds() / 60)
                    return GuardrailResult(
                        allowed=False,
                        reason=f"Cooldown active: {remaining} minutes remaining",
                        remaining_today=self._get_remaining_daily(cooldown_key.split(":")[0], rules),
                        beta_gate_pass=True
                    )

        return GuardrailResult(allowed=True, reason="", remaining_today=0, beta_gate_pass=True)
    
    def _check_daily_cap(self, user_id: str,
                         rules: Optional[Dict[str, Any]]) -> GuardrailResult:
        """Check daily notification cap."""
        daily_cap = self.default_daily_cap

        if rules and "max_notifications_per_day" in rules:
            daily_cap = rules["max_notifications_per_day"]

        today = utc_now().strftime("%Y-%m-%d")

        with self._lock:
            current_count = self._daily_counts[user_id][today]

            if current_count >= daily_cap:
                return GuardrailResult(
                    allowed=False,
                    reason=f"Daily cap reached: {daily_cap} notifications",
                    remaining_today=0,
                    beta_gate_pass=True
                )

            return GuardrailResult(
                allowed=True,
                reason="",
                remaining_today=daily_cap - current_count,
                beta_gate_pass=True
            )
    
    def _check_entropy(self, content_hash: str) -> GuardrailResult:
        """
        Check for high entropy (duplicate) content.
        Prevents sending the same or very similar notifications repeatedly.
        """
        with self._lock:
            first_seen = self._entropy_cache.get(content_hash)

            if first_seen:
                elapsed = utc_now() - ensure_utc(first_seen)
                if elapsed < timedelta(minutes=self.entropy_window_minutes):
                    remaining = self.entropy_window_minutes - int(elapsed.total_seconds() / 60)
                    return GuardrailResult(
                        allowed=False,
                        reason=f"Similar notification sent recently ({remaining} min cooldown)",
                        remaining_today=0,
                        beta_gate_pass=True
                    )
            else:
                # First time seeing this content
                self._entropy_cache[content_hash] = utc_now()

        return GuardrailResult(allowed=True, reason="", remaining_today=0, beta_gate_pass=True)
    
    def _in_quiet_hours(self, user_id: str) -> bool:
        """Check if current time is in user's quiet hours."""
        # Get user's quiet hours from preferences
        try:
            from app.models.user_preferences import UserPreferences
            session = get_session()
            prefs = session.query(UserPreferences).filter_by(user_id=user_id).first()
            
            if not prefs:
                return False
            
            rules = prefs.get_notification_rules()
            quiet_hours = rules.get("quiet_hours", {})
            
            if not quiet_hours.get("enabled", False):
                return False
            
            start_str = quiet_hours.get("start")
            end_str = quiet_hours.get("end")
            
            if not start_str or not end_str:
                return False
            
            # Parse times
            start = time.fromisoformat(start_str)
            end = time.fromisoformat(end_str)
            
            now = utc_now().time()
            
            # Handle overnight quiet hours (e.g., 22:00 - 08:00)
            if start > end:
                # Overnight span
                return now >= start or now <= end
            else:
                # Same day span
                return start <= now <= end
                
        except Exception as e:
            logger.error(f"Error checking quiet hours: {e}")
            return False
        finally:
            session.close()
    
    def _get_remaining_daily(self, user_id: str, 
                              rules: Optional[Dict[str, Any]]) -> int:
        """Get remaining notifications for today."""
        daily_cap = self.default_daily_cap
        
        if rules and "max_notifications_per_day" in rules:
            daily_cap = rules["max_notifications_per_day"]
        
        today = utc_now().strftime("%Y-%m-%d")
        
        with self._lock:
            current_count = self._daily_counts[user_id][today]
            return max(0, daily_cap - current_count)
    
    def record_notification(self, user_id: str, game_id: str,
                           notification_id: str):
        """
        Record that a notification was sent.
        Updates cooldowns and daily counts.
        """
        cooldown_key = f"{user_id}:{game_id}"
        today = utc_now().strftime("%Y-%m-%d")
        
        with self._lock:
            self._cooldowns[cooldown_key] = utc_now()
            self._daily_counts[user_id][today] += 1
        
        logger.debug(
            f"Recorded notification: user={user_id}, game={game_id}, "
            f"notification={notification_id}"
        )
    
    def get_cooldown_status(self, user_id: str, 
                            game_id: str) -> Dict[str, Any]:
        """Get cooldown status for a user/game."""
        cooldown_key = f"{user_id}:{game_id}"
        
        with self._lock:
            last_sent = self._cooldowns.get(cooldown_key)
            
            if not last_sent:
                return {
                    "in_cooldown": False,
                    "last_sent": None,
                    "remaining_minutes": 0
                }
            
            elapsed = utc_now() - ensure_utc(last_sent)
            remaining = max(0, self.default_cooldown_minutes - int(elapsed.total_seconds() / 60))
            
            return {
                "in_cooldown": remaining > 0,
                "last_sent": last_sent.isoformat(),
                "remaining_minutes": remaining
            }
    
    def get_daily_stats(self, user_id: str) -> Dict[str, Any]:
        """Get daily notification statistics for a user."""
        today = utc_now().strftime("%Y-%m-%d")
        
        with self._lock:
            sent_today = self._daily_counts[user_id][today]
        
        return {
            "date": today,
            "sent_today": sent_today,
            "remaining_today": max(0, self.default_daily_cap - sent_today),
            "daily_cap": self.default_daily_cap
        }
    
    def reset_daily_counts(self):
        """Reset daily counts (call at midnight)."""
        with self._lock:
            self._daily_counts.clear()
        logger.info("Reset daily notification counts")
    
    def cleanup_entropy_cache(self, max_age_minutes: int = 60):
        """Clean up old entropy cache entries."""
        cutoff = utc_now() - timedelta(minutes=max_age_minutes)
        
        with self._lock:
            old_keys = [
                k for k, v in self._entropy_cache.items()
                if ensure_utc(v) < cutoff
            ]
            for k in old_keys:
                del self._entropy_cache[k]
        
        if old_keys:
            logger.debug(f"Cleaned up {len(old_keys)} entropy cache entries")
    
    def activate_kill_switch(self):
        """Activate the notification kill switch (emergency use)."""
        global _kill_switch_active
        _kill_switch_active = True
        logger.warning("NOTIFICATION KILL SWITCH ACTIVATED")
    
    def deactivate_kill_switch(self):
        """Deactivate the notification kill switch."""
        global _kill_switch_active
        _kill_switch_active = False
        logger.info("Notification kill switch deactivated")


# Singleton instance
_guardrails_instance: Optional[NotificationGuardrails] = None


def get_notification_guardrails() -> NotificationGuardrails:
    """Get or create the singleton NotificationGuardrails instance."""
    global _guardrails_instance
    if _guardrails_instance is None:
        _guardrails_instance = NotificationGuardrails()
    return _guardrails_instance
