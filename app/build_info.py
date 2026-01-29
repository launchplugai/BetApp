# app/build_info.py
"""
Build Info Resolution Module.

Provides deployment visibility by safely resolving build information
from environment variables. Never crashes if values are missing.

Priority order for commit SHA:
1. GIT_SHA
2. RAILWAY_GIT_COMMIT_SHA
3. COMMIT_SHA
Fallback: "unknown"
"""
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class BuildInfo:
    """Build information for deployment visibility."""

    service: str
    environment: str
    commit: str
    build_time_utc: str
    server_time_utc: str


def get_commit_sha() -> str:
    """
    Resolve commit SHA from environment variables.

    Priority order:
    1. GIT_SHA
    2. RAILWAY_GIT_COMMIT_SHA
    3. COMMIT_SHA

    Returns "unknown" if none are set.
    """
    return (
        os.environ.get("GIT_SHA")
        or os.environ.get("RAILWAY_GIT_COMMIT_SHA")
        or os.environ.get("COMMIT_SHA")
        or "unknown"
    )


def get_short_commit_sha() -> str:
    """Get first 7 characters of commit SHA, or 'unknown'."""
    sha = get_commit_sha()
    if sha == "unknown":
        return sha
    return sha[:7]


def get_environment() -> str:
    """
    Resolve environment name.

    Priority order:
    1. RAILWAY_ENVIRONMENT
    2. ENVIRONMENT

    Returns "unknown" if none are set.
    """
    return (
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("ENVIRONMENT")
        or "unknown"
    )


def get_build_time_utc() -> str:
    """
    Get build time from environment.

    Returns "unknown" if BUILD_TIME_UTC is not set.
    """
    return os.environ.get("BUILD_TIME_UTC") or "unknown"


def get_build_info() -> BuildInfo:
    """
    Get complete build information for /build endpoint.

    Returns a BuildInfo dataclass with all deployment details.
    All fields are safe - never crashes on missing values.
    """
    return BuildInfo(
        service="dna-bet-engine",
        environment=get_environment(),
        commit=get_commit_sha(),
        build_time_utc=get_build_time_utc(),
        server_time_utc=datetime.now(timezone.utc).isoformat(),
    )


def is_commit_unknown() -> bool:
    """Check if commit SHA is unknown (for stale defense)."""
    return get_commit_sha() == "unknown"
