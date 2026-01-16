# app/tests/test_correlation.py
"""
Tests for correlation ID middleware and structured logging.

These tests verify:
1. Client-provided X-Request-Id is echoed in response
2. Missing X-Request-Id generates a new one
3. /app/evaluate JSON includes request_id
4. Logging doesn't include raw input text
"""
import os
import logging
import pytest
from unittest.mock import MagicMock, patch

from app.correlation import (
    validate_request_id,
    generate_request_id,
    get_request_id,
    CorrelationIdMiddleware,
)


class TestValidateRequestId:
    """Tests for request ID validation."""

    def test_valid_uuid(self):
        """Valid UUID is accepted."""
        request_id = "550e8400-e29b-41d4-a716-446655440000"
        assert validate_request_id(request_id) == request_id

    def test_valid_alphanumeric(self):
        """Valid alphanumeric ID is accepted."""
        request_id = "abc123-DEF_456"
        assert validate_request_id(request_id) == request_id

    def test_empty_string_rejected(self):
        """Empty string is rejected."""
        assert validate_request_id("") is None

    def test_none_rejected(self):
        """None is rejected."""
        assert validate_request_id(None) is None

    def test_too_long_rejected(self):
        """IDs longer than 64 chars are rejected."""
        long_id = "a" * 65
        assert validate_request_id(long_id) is None

    def test_max_length_accepted(self):
        """IDs at exactly 64 chars are accepted."""
        max_id = "a" * 64
        assert validate_request_id(max_id) == max_id

    def test_special_chars_rejected(self):
        """Special characters are rejected."""
        assert validate_request_id("abc@123") is None
        assert validate_request_id("abc 123") is None
        assert validate_request_id("abc/123") is None
        assert validate_request_id("abc;123") is None

    def test_safe_chars_accepted(self):
        """Hyphens and underscores are accepted."""
        assert validate_request_id("abc-123") == "abc-123"
        assert validate_request_id("abc_123") == "abc_123"
        assert validate_request_id("ABC-123_xyz") == "ABC-123_xyz"


class TestGenerateRequestId:
    """Tests for request ID generation."""

    def test_generates_uuid_format(self):
        """Generated ID is UUID4 format."""
        request_id = generate_request_id()
        # UUID4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        parts = request_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12

    def test_unique_each_call(self):
        """Each call generates a unique ID."""
        ids = [generate_request_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestGetRequestId:
    """Tests for getting request ID from request state."""

    def test_returns_request_id_from_state(self):
        """Returns request_id if set in state."""
        request = MagicMock()
        request.state.request_id = "test-id-123"
        assert get_request_id(request) == "test-id-123"

    def test_returns_none_if_not_set(self):
        """Returns None if request_id not in state."""
        request = MagicMock(spec=[])
        request.state = MagicMock(spec=[])
        assert get_request_id(request) is None


class TestCorrelationIdIntegration:
    """Integration tests for correlation ID with FastAPI."""

    @pytest.fixture
    def client(self):
        """Create test client with Leading Light enabled."""
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        # Reset rate limiter for clean state
        from app.rate_limiter import set_rate_limiter, RateLimiter
        set_rate_limiter(RateLimiter(requests_per_minute=100, burst_size=100))
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_client_request_id_echoed(self, client):
        """Client-provided X-Request-Id is echoed in response."""
        client_request_id = "my-custom-request-id-123"
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
            headers={"X-Request-Id": client_request_id},
        )
        assert response.headers.get("X-Request-Id") == client_request_id

    def test_missing_request_id_generated(self, client):
        """Missing X-Request-Id generates a new one."""
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )
        request_id = response.headers.get("X-Request-Id")
        assert request_id is not None
        # Should be UUID4 format
        parts = request_id.split("-")
        assert len(parts) == 5

    def test_json_includes_request_id(self, client):
        """/app/evaluate JSON response includes request_id."""
        client_request_id = "json-test-id-456"
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
            headers={"X-Request-Id": client_request_id},
        )
        data = response.json()
        assert "request_id" in data
        assert data["request_id"] == client_request_id

    def test_error_response_includes_request_id(self, client):
        """Error responses also include request_id."""
        # Disable Leading Light to trigger 503
        os.environ["LEADING_LIGHT_ENABLED"] = "false"
        from app.main import app
        from fastapi.testclient import TestClient
        client_disabled = TestClient(app)

        client_request_id = "error-test-id-789"
        response = client_disabled.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
            headers={"X-Request-Id": client_request_id},
        )
        assert response.status_code == 503
        data = response.json()
        assert "request_id" in data
        assert data["request_id"] == client_request_id

    def test_invalid_request_id_replaced(self, client):
        """Invalid X-Request-Id is replaced with generated one."""
        invalid_request_id = "invalid@id!with#special"
        response = client.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
            headers={"X-Request-Id": invalid_request_id},
        )
        returned_id = response.headers.get("X-Request-Id")
        # Should NOT be the invalid one
        assert returned_id != invalid_request_id
        # Should be a valid UUID4
        parts = returned_id.split("-")
        assert len(parts) == 5

    def test_health_gets_request_id(self, client):
        """Health endpoint also gets X-Request-Id header."""
        response = client.get("/health")
        request_id = response.headers.get("X-Request-Id")
        assert request_id is not None


class TestStructuredLogging:
    """Tests for structured logging safety."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        os.environ["LEADING_LIGHT_ENABLED"] = "true"
        from app.rate_limiter import set_rate_limiter, RateLimiter
        set_rate_limiter(RateLimiter(requests_per_minute=100, burst_size=100))
        from app.main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_logging_does_not_include_raw_input(self, client):
        """Verify logging doesn't include raw user input."""
        secret_input = "SUPER_SECRET_BET_TEXT_12345"

        # Capture log output
        with patch("app.routers.web._logger") as mock_logger:
            response = client.post(
                "/app/evaluate",
                json={"input": secret_input, "tier": "good"},
            )
            assert response.status_code == 200

            # Check all log calls
            for call in mock_logger.info.call_args_list:
                log_message = str(call)
                assert secret_input not in log_message, \
                    f"Raw input found in log: {log_message}"

    def test_logging_includes_input_length(self, client):
        """Verify logging includes input_length (not raw text)."""
        test_input = "Lakers -5.5 parlay"

        with patch("app.routers.web._logger") as mock_logger:
            response = client.post(
                "/app/evaluate",
                json={"input": test_input, "tier": "good"},
            )
            assert response.status_code == 200

            # Verify logger was called
            assert mock_logger.info.called
            # Get the log dict (second argument to info())
            call_args = mock_logger.info.call_args
            log_dict = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
            assert log_dict["input_length"] == len(test_input)

    def test_logging_includes_request_id(self, client):
        """Verify logging includes request_id."""
        test_request_id = "log-test-request-id"

        with patch("app.routers.web._logger") as mock_logger:
            response = client.post(
                "/app/evaluate",
                json={"input": "Lakers -5.5", "tier": "good"},
                headers={"X-Request-Id": test_request_id},
            )
            assert response.status_code == 200

            # Verify logger was called with request_id
            call_args = mock_logger.info.call_args
            log_dict = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
            assert log_dict["request_id"] == test_request_id

    def test_logging_includes_tier(self, client):
        """Verify logging includes tier."""
        with patch("app.routers.web._logger") as mock_logger:
            response = client.post(
                "/app/evaluate",
                json={"input": "Lakers -5.5", "tier": "better"},
            )
            assert response.status_code == 200

            call_args = mock_logger.info.call_args
            log_dict = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
            assert log_dict["tier"] == "better"

    def test_rate_limited_request_logged(self, client):
        """Verify rate-limited requests are logged with rate_limited=True."""
        # Use strict limiter
        from app.rate_limiter import set_rate_limiter, RateLimiter
        set_rate_limiter(RateLimiter(requests_per_minute=60, burst_size=1))
        from app.main import app
        from fastapi.testclient import TestClient
        client_strict = TestClient(app)

        # First request succeeds
        client_strict.post(
            "/app/evaluate",
            json={"input": "Lakers -5.5", "tier": "good"},
        )

        # Second request should be rate limited
        with patch("app.routers.web._logger") as mock_logger:
            response = client_strict.post(
                "/app/evaluate",
                json={"input": "Lakers -5.5", "tier": "good"},
            )
            assert response.status_code == 429

            call_args = mock_logger.info.call_args
            log_dict = call_args[0][1] if len(call_args[0]) > 1 else call_args[1]
            assert log_dict["rate_limited"] is True
            assert log_dict["status_code"] == 429
