# app/correlation.py
"""
Correlation ID middleware for request tracing.

Provides:
- X-Request-Id header handling (accepts client-provided or generates UUID4)
- Request state storage for downstream access
- Response header injection for traceability
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


# Validation for client-provided request IDs
MAX_REQUEST_ID_LENGTH = 64
# Allow alphanumeric, hyphens, underscores only (safe for logging)
SAFE_REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_request_id(request_id: Optional[str]) -> Optional[str]:
    """
    Validate a client-provided request ID.

    Returns:
        The request_id if valid, None otherwise.
    """
    if not request_id:
        return None
    if len(request_id) > MAX_REQUEST_ID_LENGTH:
        return None
    if not SAFE_REQUEST_ID_PATTERN.match(request_id):
        return None
    return request_id


def generate_request_id() -> str:
    """Generate a new UUID4 request ID."""
    return str(uuid.uuid4())


def get_request_id(request: Request) -> Optional[str]:
    """Get request ID from request state (if set by middleware)."""
    return getattr(request.state, "request_id", None)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that handles X-Request-Id for request correlation.

    - Reads X-Request-Id from incoming request (validates format)
    - Generates UUID4 if not provided or invalid
    - Stores in request.state.request_id
    - Adds X-Request-Id to all responses
    """

    async def dispatch(self, request: Request, call_next):
        # Get client-provided request ID or generate new one
        client_request_id = request.headers.get("x-request-id")
        request_id = validate_request_id(client_request_id) or generate_request_id()

        # Store in request state for downstream access
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-Id"] = request_id

        return response
