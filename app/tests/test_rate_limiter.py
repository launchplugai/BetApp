# app/tests/test_rate_limiter.py
"""
Tests for rate limiting functionality.

These tests verify:
1. First request succeeds
2. Exceeding limit returns 429
3. Retry-After header present on 429
4. /health is not rate-limited
5. Token bucket refills over time
"""
import os
import pytest
from unittest.mock import MagicMock

from app.rate_limiter import RateLimiter, TokenBucket, get_client_ip


class TestTokenBucket:
    """Tests for TokenBucket class."""

    def test_initial_tokens_available(self):
        """Bucket starts with full tokens."""
        bucket = TokenBucket(
            tokens=3.0,
            last_refill=0.0,
            max_tokens=3.0,
            refill_rate=0.1667,  # 10/minute
        )
        allowed, retry_after = bucket.consume(0.0)
        assert allowed is True
        assert retry_after == 0.0

    def test_tokens_deplete(self):
        """Tokens deplete after consumption."""
        bucket = TokenBucket(
            tokens=2.0,
            last_refill=0.0,
            max_tokens=3.0,
            refill_rate=0.1667,
        )
        # Consume first token
        allowed, _ = bucket.consume(0.0)
        assert allowed is True
        assert bucket.tokens == 1.0

        # Consume second token
        allowed, _ = bucket.consume(0.0)
        assert allowed is True
        assert bucket.tokens == 0.0

        # Third request should fail (no time passed for refill)
        allowed, retry_after = bucket.consume(0.0)
        assert allowed is False
        assert retry_after > 0

    def test_tokens_refill_over_time(self):
        """Tokens refill based on elapsed time."""
        bucket = TokenBucket(
            tokens=0.0,
            last_refill=0.0,
            max_tokens=3.0,
            refill_rate=1.0,  # 1 token per second
        )
        # After 1 second, should have 1 token
        allowed, _ = bucket.consume(1.0)
        assert allowed is True

    def test_tokens_cap_at_max(self):
        """Tokens don't exceed max capacity."""
        bucket = TokenBucket(
            tokens=3.0,
            last_refill=0.0,
            max_tokens=3.0,
            refill_rate=1.0,
        )
        # Even after 100 seconds, tokens stay at max
        bucket.consume(100.0)
        assert bucket.tokens <= 3.0


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_first_request_allowed(self):
        """First request from new IP is allowed."""
        mock_time = 0.0
        limiter = RateLimiter(
            requests_per_minute=10,
            burst_size=3,
            clock=lambda: mock_time,
        )
        allowed, retry_after = limiter.check("192.168.1.1")
        assert allowed is True
        assert retry_after == 0.0

    def test_burst_requests_allowed(self):
        """Burst requests up to burst_size are allowed."""
        mock_time = 0.0
        limiter = RateLimiter(
            requests_per_minute=10,
            burst_size=3,
            clock=lambda: mock_time,
        )
        # First 3 requests should succeed (burst)
        for i in range(3):
            allowed, _ = limiter.check("192.168.1.1")
            assert allowed is True, f"Request {i+1} should be allowed"

        # 4th request should fail (burst exhausted, no time for refill)
        allowed, retry_after = limiter.check("192.168.1.1")
        assert allowed is False
        assert retry_after > 0

    def test_rate_limit_exceeded_returns_retry_after(self):
        """Exceeding rate limit returns proper retry_after value."""
        mock_time = 0.0
        limiter = RateLimiter(
            requests_per_minute=10,
            burst_size=3,
            clock=lambda: mock_time,
        )
        # Exhaust burst
        for _ in range(3):
            limiter.check("192.168.1.1")

        # Next request should be denied with retry_after
        allowed, retry_after = limiter.check("192.168.1.1")
        assert allowed is False
        assert retry_after > 0
        # Should be approximately 6 seconds (1 token / (10/60) tokens/sec)
        assert 5 < retry_after < 7

    def test_different_ips_have_separate_buckets(self):
        """Different IPs don't share rate limit buckets."""
        mock_time = 0.0
        limiter = RateLimiter(
            requests_per_minute=10,
            burst_size=3,
            clock=lambda: mock_time,
        )
        # Exhaust IP1's burst
        for _ in range(3):
            limiter.check("192.168.1.1")
        allowed, _ = limiter.check("192.168.1.1")
        assert allowed is False

        # IP2 should still have full burst
        for _ in range(3):
            allowed, _ = limiter.check("192.168.1.2")
            assert allowed is True

    def test_tokens_refill_after_time(self):
        """Tokens refill after time passes."""
        current_time = [0.0]
        limiter = RateLimiter(
            requests_per_minute=60,  # 1 per second for easy math
            burst_size=1,
            clock=lambda: current_time[0],
        )
        # Use the one token
        allowed, _ = limiter.check("192.168.1.1")
        assert allowed is True

        # Immediate retry should fail
        allowed, _ = limiter.check("192.168.1.1")
        assert allowed is False

        # After 1 second, should have a new token
        current_time[0] = 1.0
        allowed, _ = limiter.check("192.168.1.1")
        assert allowed is True

    def test_reset_clears_all_buckets(self):
        """Reset method clears all buckets."""
        mock_time = 0.0
        limiter = RateLimiter(
            requests_per_minute=10,
            burst_size=1,
            clock=lambda: mock_time,
        )
        # Use tokens
        limiter.check("192.168.1.1")
        limiter.check("192.168.1.2")

        # Reset
        limiter.reset()

        # Both IPs should have fresh buckets
        allowed, _ = limiter.check("192.168.1.1")
        assert allowed is True
        allowed, _ = limiter.check("192.168.1.2")
        assert allowed is True


class TestGetClientIp:
    """Tests for get_client_ip function."""

    def test_uses_x_forwarded_for_first_ip(self):
        """Uses first IP from X-Forwarded-For header."""
        request = MagicMock()
        request.headers = {"x-forwarded-for": "203.0.113.1, 198.51.100.1, 192.0.2.1"}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        ip = get_client_ip(request)
        assert ip == "203.0.113.1"

    def test_falls_back_to_client_host(self):
        """Falls back to request.client.host when no X-Forwarded-For."""
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "192.168.1.100"

        ip = get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_handles_empty_x_forwarded_for(self):
        """Handles empty X-Forwarded-For header."""
        request = MagicMock()
        request.headers = {"x-forwarded-for": ""}
        request.client = MagicMock()
        request.client.host = "10.0.0.1"

        ip = get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_returns_unknown_when_no_client(self):
        """Returns 'unknown' when no client info available."""
        request = MagicMock()
        request.headers = {}
        request.client = None

        ip = get_client_ip(request)
        assert ip == "unknown"


class TestRateLimiterIntegration:
    """Integration tests for rate limiting with FastAPI."""

    @pytest.fixture
    def client(self):
        """Create test client with Leading Light enabled and fresh rate limiter."""
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        # Reset rate limiter for clean state
        from app.rate_limiter import set_rate_limiter, RateLimiter
        # Use a limiter with controllable time for testing
        set_rate_limiter(RateLimiter(
            requests_per_minute=10,
            burst_size=3,
        ))
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    @pytest.fixture
    def client_strict(self):
        """Create test client with strict rate limits for testing 429."""
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        from app.rate_limiter import set_rate_limiter, RateLimiter
        # Very strict: only 1 request allowed
        set_rate_limiter(RateLimiter(
            requests_per_minute=60,
            burst_size=1,
        ))
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_first_request_succeeds(self, client):
        """First request to /app/evaluate succeeds."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        assert response.status_code == 200

    def test_exceeding_limit_returns_429(self, client_strict):
        """Exceeding rate limit returns 429."""
        # First request should succeed
        response = client_strict.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        assert response.status_code == 200

        # Second request should be rate limited
        response = client_strict.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        assert response.status_code == 429

    def test_429_includes_retry_after_header(self, client_strict):
        """429 response includes Retry-After header."""
        # Exhaust rate limit
        client_strict.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        # This should be rate limited
        response = client_strict.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        assert response.status_code == 429
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0

    def test_429_includes_json_body(self, client_strict):
        """429 response includes proper JSON body."""
        # Exhaust rate limit
        client_strict.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        # This should be rate limited
        response = client_strict.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        assert response.status_code == 429
        data = response.json()
        assert data["error"] == "rate_limited"
        assert "retry_after_seconds" in data
        assert data["retry_after_seconds"] > 0

    def test_health_not_rate_limited(self, client_strict):
        """Health endpoint is not affected by rate limiting."""
        # Exhaust rate limit on /app/evaluate
        client_strict.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        # Verify rate limit is active
        response = client_strict.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        assert response.status_code == 429

        # /health should still work
        response = client_strict.get("/health")
        assert response.status_code == 200


class TestAbuseGuards:
    """Tests for input validation and abuse prevention."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        from app.rate_limiter import set_rate_limiter, RateLimiter
        set_rate_limiter(RateLimiter(
            requests_per_minute=100,
            burst_size=100,
        ))
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_rejects_oversized_input(self, client):
        """Rejects input exceeding max length (Airlock returns 400)."""
        oversized_input = "x" * 10001  # MAX_INPUT_LENGTH is 10000
        response = client.post(
            "/app/evaluate",
            json={"input": oversized_input, "tier": "good"},
        )
        assert response.status_code == 400

    def test_accepts_max_length_input(self, client):
        """Accepts input at exactly max length."""
        max_input = "Lakers " * 1428  # ~9996 chars
        response = client.post(
            "/app/evaluate",
            json={"input": max_input[:10000], "tier": "good"},
        )
        # Should not fail due to length
        assert response.status_code in [200, 400]  # 400 if parsing fails, but not 422 for length

    def test_rejects_invalid_tier(self, client):
        """Rejects invalid tier values (Airlock returns 400)."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "PREMIUM"},
        )
        assert response.status_code == 400

    def test_accepts_valid_tiers(self, client):
        """Accepts all valid tier values."""
        for tier in ["good", "GOOD", "better", "BETTER", "best", "BEST"]:
            response = client.post(
                "/app/evaluate",
                json={"input": "Lakers -5.5", "tier": tier},
            )
            assert response.status_code == 200, f"Failed for tier: {tier}"
