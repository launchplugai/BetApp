# app/tests/test_security.py
"""Tests for security middleware."""
import pytest
from fastapi.testclient import TestClient

from app.main import app, MAX_REQUEST_SIZE_BYTES


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestRequestSizeLimit:
    """Tests for request size limit middleware."""

    def test_small_request_allowed(self, client):
        """Requests under size limit are allowed."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_large_content_length_rejected(self, client):
        """Requests with Content-Length exceeding limit return 413."""
        # Simulate a request claiming to be larger than limit
        oversized = MAX_REQUEST_SIZE_BYTES + 1
        response = client.post(
            "/",
            headers={"Content-Length": str(oversized)},
            content=b"x",  # Actual content doesn't matter; header is checked first
        )
        assert response.status_code == 413
        assert response.json()["detail"] == "Request entity too large"


class TestSecurityHeaders:
    """Tests for security headers middleware."""

    def test_security_headers_present(self, client):
        """Response contains required security headers."""
        response = client.get("/health")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert response.headers.get("Cache-Control") == "no-store"

    def test_security_headers_on_all_endpoints(self, client):
        """Security headers are present on root endpoint too."""
        response = client.get("/")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
