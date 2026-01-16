# app/rate_limiter.py
"""
In-memory rate limiter for abuse prevention.

Uses token bucket algorithm:
- Each IP gets a bucket with max_tokens capacity
- Tokens refill at refill_rate per second
- Each request consumes 1 token
- When bucket is empty, request is rejected with 429

Designed for single Railway instance (no shared state).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Dict, Optional, Tuple


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


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
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
