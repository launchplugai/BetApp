# app/rate_limiter.py
"""
In-memory rate limiter for abuse prevention.

Uses token bucket algorithm:
- Each IP gets a bucket with max_tokens capacity
- Tokens refill at refill_rate per second
- Each request consumes 1 token
- When bucket is empty, request is rejected with 429

Designed for single Railway instance (no shared state).

CI/Test Mode:
- Set DNA_RATE_LIMIT_MODE=ci to bypass rate limiting in tests
- Set DNA_RATE_LIMIT_MODE=off to disable entirely (non-production only)
- Production safety: bypass NEVER activates when ENV=production
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Callable, Dict, Optional, Tuple

_logger = logging.getLogger(__name__)

# =============================================================================
# Rate Limit Mode Configuration
# =============================================================================

# Valid modes
RATE_LIMIT_MODE_PROD = "prod"  # Default: normal rate limiting
RATE_LIMIT_MODE_CI = "ci"      # CI/test: bypass rate limiting
RATE_LIMIT_MODE_OFF = "off"    # Off: bypass entirely (non-prod only)

_bypass_warning_logged = False


def _get_rate_limit_mode() -> str:
    """Get rate limit mode from environment."""
    return os.environ.get("DNA_RATE_LIMIT_MODE", RATE_LIMIT_MODE_PROD).lower()


def _get_bypass_until() -> Optional[datetime]:
    """Get optional bypass time-bomb timestamp."""
    until_str = os.environ.get("DNA_RATE_LIMIT_BYPASS_UNTIL")
    if not until_str:
        return None
    try:
        return datetime.fromisoformat(until_str.replace("Z", "+00:00"))
    except ValueError:
        _logger.warning(f"Invalid DNA_RATE_LIMIT_BYPASS_UNTIL format: {until_str}")
        return None


def _is_production() -> bool:
    """Check if running in production environment."""
    env = os.environ.get("ENV", "").lower()
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT", "").lower()
    return env == "production" or railway_env == "production"


def _is_bypass_allowed() -> bool:
    """
    Determine if rate limit bypass is allowed.

    Safety invariants:
    - NEVER bypass in production, regardless of env vars
    - Check time-bomb if set
    - Log warning once when bypass is active
    """
    global _bypass_warning_logged

    mode = _get_rate_limit_mode()

    # Default mode: no bypass
    if mode == RATE_LIMIT_MODE_PROD:
        return False

    # Production safety: NEVER bypass
    if _is_production():
        if mode != RATE_LIMIT_MODE_PROD:
            _logger.error(
                f"SECURITY: Rate limit bypass attempted in production with mode={mode}. "
                "Bypass DENIED. Set DNA_RATE_LIMIT_MODE=prod or remove the variable."
            )
        return False

    # Check time-bomb
    bypass_until = _get_bypass_until()
    if bypass_until:
        now = datetime.now(timezone.utc)
        if now > bypass_until:
            _logger.warning(
                f"Rate limit bypass expired at {bypass_until.isoformat()}. "
                "Reverting to normal rate limiting."
            )
            return False

    # Bypass is allowed - log warning once
    if not _bypass_warning_logged:
        until_msg = f" until {bypass_until.isoformat()}" if bypass_until else ""
        _logger.warning(
            f"RATE_LIMIT_BYPASS_ACTIVE: mode={mode}{until_msg}. "
            "This should only be used in CI/test environments."
        )
        _bypass_warning_logged = True

    return True


@dataclass
class TokenBucket:
    """Token bucket for a single client."""
    tokens: float
    last_refill: float
    max_tokens: float
    refill_rate: float  # tokens per second

    def consume(self, now: float) -> Tuple[bool, float]:
        """
        Try to consume a token.

        Returns:
            (allowed, retry_after_seconds)
            - allowed: True if request is allowed
            - retry_after_seconds: Seconds until next token available (0 if allowed)
        """
        # Refill tokens based on time elapsed
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, 0.0
        else:
            # Calculate time until next token
            tokens_needed = 1.0 - self.tokens
            retry_after = tokens_needed / self.refill_rate
            return False, retry_after


@dataclass
class RateLimiter:
    """
    In-memory rate limiter using token bucket algorithm.

    Attributes:
        requests_per_minute: Maximum sustained request rate
        burst_size: Maximum burst allowance (bucket capacity)
        clock: Callable returning current time (for testing)
    """
    requests_per_minute: int = 10
    burst_size: int = 3
    clock: Callable[[], float] = field(default=time.time)
    _buckets: Dict[str, TokenBucket] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)
    _cleanup_interval: float = 60.0  # Cleanup stale buckets every 60s
    _last_cleanup: float = field(default=0.0)

    def __post_init__(self):
        # Calculate refill rate: tokens per second
        self._refill_rate = self.requests_per_minute / 60.0
        self._last_cleanup = self.clock()

    def check(self, client_ip: str) -> Tuple[bool, float]:
        """
        Check if request from client_ip is allowed.

        Returns:
            (allowed, retry_after_seconds)
        """
        now = self.clock()

        with self._lock:
            # Periodic cleanup of stale buckets
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup_stale_buckets(now)
                self._last_cleanup = now

            # Get or create bucket for this IP
            if client_ip not in self._buckets:
                self._buckets[client_ip] = TokenBucket(
                    tokens=self.burst_size,  # Start with full burst allowance
                    last_refill=now,
                    max_tokens=self.burst_size,
                    refill_rate=self._refill_rate,
                )

            return self._buckets[client_ip].consume(now)

    def _cleanup_stale_buckets(self, now: float) -> None:
        """Remove buckets that haven't been used recently."""
        stale_threshold = 300.0  # 5 minutes
        stale_ips = [
            ip for ip, bucket in self._buckets.items()
            if now - bucket.last_refill > stale_threshold
        ]
        for ip in stale_ips:
            del self._buckets[ip]

    def reset(self) -> None:
        """Reset all buckets (for testing)."""
        with self._lock:
            self._buckets.clear()


def get_client_ip(request) -> str:
    """
    Extract client IP from request, respecting X-Forwarded-For.

    Safety: Only trust the first IP in X-Forwarded-For chain,
    as subsequent IPs could be spoofed.
    """
    # Check X-Forwarded-For header (set by proxies/load balancers)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP (original client)
        # Format: "client, proxy1, proxy2, ..."
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip

    # Fall back to direct client IP
    if request.client and request.client.host:
        return request.client.host

    # Ultimate fallback
    return "unknown"


# Global rate limiter instance
# Can be replaced in tests
_rate_limiter: Optional[RateLimiter] = None


class BypassRateLimiter:
    """
    A rate limiter that always allows requests.

    Used in CI/test mode to prevent flaky tests due to rate limiting.
    """

    def check(self, client_ip: str) -> Tuple[bool, float]:
        """Always allow the request."""
        return True, 0.0

    def reset(self) -> None:
        """No-op for bypass limiter."""
        pass


def get_rate_limiter() -> RateLimiter:
    """
    Get or create the global rate limiter.

    Returns a bypass limiter in CI/test mode (when safe).
    """
    global _rate_limiter

    # Check if bypass is allowed (handles all safety checks)
    if _is_bypass_allowed():
        return BypassRateLimiter()

    # Normal rate limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            requests_per_minute=10,
            burst_size=3,
        )
    return _rate_limiter


def set_rate_limiter(limiter: Optional[RateLimiter]) -> None:
    """Set the global rate limiter (for testing)."""
    global _rate_limiter
    _rate_limiter = limiter


def reset_bypass_warning() -> None:
    """Reset the bypass warning flag (for testing)."""
    global _bypass_warning_logged
    _bypass_warning_logged = False
