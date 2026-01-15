# app/config.py
"""
Centralized configuration management with startup validation.

Defines REQUIRED vs OPTIONAL environment variables and provides
safe configuration loading with validation and logging.
"""
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

SERVICE_NAME = "dna-matrix"
SERVICE_VERSION = "0.1.0"

# Default values
DEFAULT_MAX_REQUEST_SIZE_BYTES = 1_048_576  # 1MB
MIN_REQUEST_SIZE_BYTES = 1024  # 1KB minimum

# Sensitive substrings that should never appear in logs
SENSITIVE_SUBSTRINGS = ("key", "token", "secret", "password", "credential", "auth")


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""

    pass


# =============================================================================
# Configuration Dataclass
# =============================================================================


@dataclass
class AppConfig:
    """Application configuration loaded from environment."""

    # Service info
    service_name: str = SERVICE_NAME
    service_version: str = SERVICE_VERSION
    environment: str = "development"

    # Security settings
    max_request_size_bytes: int = DEFAULT_MAX_REQUEST_SIZE_BYTES

    # Feature flags (OPTIONAL - default disabled)
    leading_light_enabled: bool = False
    voice_enabled: bool = False

    # API keys (OPTIONAL - features disabled without them)
    openai_api_key_present: bool = False

    # Warnings collected during config load
    warnings: list = field(default_factory=list)


# =============================================================================
# Configuration Loading
# =============================================================================


def _parse_int_env(
    name: str, default: int, min_value: Optional[int] = None
) -> tuple[int, Optional[str]]:
    """
    Parse an integer environment variable with validation.

    Returns (value, warning_message).
    On invalid input, returns default with a warning.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default, None

    try:
        value = int(raw)
    except ValueError:
        warning = f"{name}='{raw}' is not a valid integer; using default {default}"
        return default, warning

    if min_value is not None and value < min_value:
        warning = f"{name}={value} is below minimum {min_value}; using default {default}"
        return default, warning

    return value, None


def _parse_bool_env(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    raw = os.environ.get(name, "").lower()
    if raw in ("true", "1", "yes", "on"):
        return True
    if raw in ("false", "0", "no", "off", ""):
        return default
    return default


def load_config(fail_fast: bool = True) -> AppConfig:
    """
    Load and validate application configuration from environment.

    Args:
        fail_fast: If True, raise ConfigurationError on critical issues.
                   If False, collect warnings and continue.

    Returns:
        AppConfig instance with validated configuration.

    Raises:
        ConfigurationError: If required configuration is missing/invalid
                           and fail_fast is True.
    """
    warnings = []

    # Environment
    environment = os.environ.get("RAILWAY_ENVIRONMENT", "development")

    # Security settings with validation
    max_request_size, size_warning = _parse_int_env(
        "MAX_REQUEST_SIZE_BYTES",
        DEFAULT_MAX_REQUEST_SIZE_BYTES,
        min_value=MIN_REQUEST_SIZE_BYTES,
    )
    if size_warning:
        warnings.append(size_warning)

    # Feature flags (OPTIONAL - disabled by default)
    leading_light_enabled = _parse_bool_env("LEADING_LIGHT_ENABLED", False)
    voice_enabled = _parse_bool_env("VOICE_ENABLED", False)

    # API key presence (OPTIONAL - check presence, don't store value)
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_api_key_present = bool(openai_key and len(openai_key) > 0)

    # Warn if features enabled but API key missing
    if (leading_light_enabled or voice_enabled) and not openai_api_key_present:
        warnings.append(
            "LEADING_LIGHT_ENABLED or VOICE_ENABLED is true but OPENAI_API_KEY is not set; "
            "features will return errors at runtime"
        )

    # Log warnings
    for warning in warnings:
        logger.warning(f"[CONFIG] {warning}")

    return AppConfig(
        environment=environment,
        max_request_size_bytes=max_request_size,
        leading_light_enabled=leading_light_enabled,
        voice_enabled=voice_enabled,
        openai_api_key_present=openai_api_key_present,
        warnings=warnings,
    )


def log_config_snapshot(config: AppConfig) -> str:
    """
    Generate and log a safe configuration snapshot.

    Returns the snapshot string for testing purposes.
    Never logs actual secret values - only boolean presence flags.
    """
    snapshot = (
        f"[STARTUP] service={config.service_name} "
        f"version={config.service_version} "
        f"environment={config.environment} "
        f"max_request_size_bytes={config.max_request_size_bytes} "
        f"leading_light_enabled={config.leading_light_enabled} "
        f"voice_enabled={config.voice_enabled} "
        f"openai_api_key_present={config.openai_api_key_present}"
    )
    logger.info(snapshot)
    return snapshot


def validate_config_snapshot_safety(snapshot: str) -> bool:
    """
    Validate that a config snapshot doesn't contain sensitive values.

    Returns True if safe, False if potentially unsafe.
    """
    snapshot_lower = snapshot.lower()

    # Check for patterns like "key=sk-..." or "token=abc123"
    # We allow "key_present=" but not "key=" followed by a non-boolean value
    for sensitive in SENSITIVE_SUBSTRINGS:
        # Pattern: sensitive word followed by = and a value that's not a boolean
        import re

        pattern = rf"{sensitive}=(?!true|false|True|False|\d+_present)"
        if re.search(pattern, snapshot_lower):
            return False

    return True
