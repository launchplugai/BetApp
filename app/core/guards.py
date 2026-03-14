"""
Core Guard System for BetApp

Request-level enforcement with tracing and logging.
Used for tier-based access control, rate limiting, and feature gating.
"""

import time
import logging
from typing import Callable
from fastapi import Request, HTTPException

log = logging.getLogger("guards")


class GuardResult:
    """Result of a guard check."""
    def __init__(self, ok: bool, reason: str | None = None):
        self.ok = ok
        self.reason = reason


def with_guard(name: str, check: Callable[[Request], GuardResult]):
    """
    Decorator for request-level guard enforcement.
    Turns silent failure into loud, traceable failure.
    """
    def decorator(func: Callable):
        async def guard_wrapper(request: Request, *args, **kwargs):
            start = time.time()
            result = check(request)
            elapsed = round((time.time() - start) * 1000, 2)
            
            if not result.ok:
                log.warning(
                    "GUARD_BLOCKED",
                    extra={
                        "guard": name,
                        "reason": result.reason,
                        "path": request.url.path,
                        "method": request.method,
                        "ms": elapsed,
                    },
                )
                raise HTTPException(
                    status_code=401,
                    detail=result.reason or "Request blocked by guard",
                )
            
            log.info(
                "GUARD_PASSED",
                extra={
                    "guard": name,
                    "path": request.url.path,
                    "method": request.method,
                    "ms": elapsed,
                },
            )
            
            return await func(request, *args, **kwargs)
        
        return guard_wrapper
    return decorator


# =============================================================================
# Built-in Guard Checks
# =============================================================================

def require_auth(request: Request) -> GuardResult:
    """Guard: Require valid authentication."""
    from app.services.auth import get_current_user_from_token
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return GuardResult(False, "Missing or invalid authorization header")
    
    token = auth_header.replace("Bearer ", "")
    user = get_current_user_from_token(token)
    
    if not user:
        return GuardResult(False, "Invalid or expired token")
    
    # Attach user to request for downstream use
    request.state.user = user
    return GuardResult(True)


def require_tier(min_tier: str):
    """Guard: Require minimum tier (GOOD < BETTER < BEST)."""
    tier_order = {"GOOD": 0, "BETTER": 1, "BEST": 2}
    
    def check(request: Request) -> GuardResult:
        # First check auth
        auth_result = require_auth(request)
        if not auth_result.ok:
            return auth_result
        
        user = request.state.user
        user_tier_level = tier_order.get(user.tier, 0)
        min_tier_level = tier_order.get(min_tier, 0)
        
        if user_tier_level < min_tier_level:
            return GuardResult(
                False, 
                f"This feature requires {min_tier} tier. Your tier: {user.tier}"
            )
        
        return GuardResult(True)
    
    return check


def rate_limit_guard(max_requests: int, window_seconds: int):
    """Guard: Rate limiting per user/IP."""
    # Simple in-memory rate limiting (can upgrade to Redis)
    _requests = {}
    
    def check(request: Request) -> GuardResult:
        # Get identifier (user ID if auth'd, else IP)
        client_id = request.client.host
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            from app.services.auth import decode_token
            token = auth_header.replace("Bearer ", "")
            payload = decode_token(token)
            if payload and payload.get("sub"):
                client_id = payload["sub"]
        
        now = time.time()
        window_start = now - window_seconds
        
        # Get client's request history
        client_requests = _requests.get(client_id, [])
        
        # Filter to current window
        client_requests = [t for t in client_requests if t > window_start]
        
        # Check limit
        if len(client_requests) >= max_requests:
            return GuardResult(
                False,
                f"Rate limit exceeded: {max_requests} requests per {window_seconds}s"
            )
        
        # Record this request
        client_requests.append(now)
        _requests[client_id] = client_requests
        
        return GuardResult(True)
    
    return check


def validate_request_size(max_bytes: int):
    """Guard: Validate request body size."""
    def check(request: Request) -> GuardResult:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_bytes:
            return GuardResult(
                False,
                f"Request too large: {content_length} bytes (max: {max_bytes})"
            )
        return GuardResult(True)
    
    return check
