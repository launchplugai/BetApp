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

    # Deploy identification (for unambiguous production verification)
    git_sha: str = "unknown"
    build_time_utc: str = ""  # ISO8601 format, set at startup

    # Security settings
    max_request_size_bytes: int = DEFAULT_MAX_REQUEST_SIZE_BYTES

    # Feature flags (OPTIONAL - default disabled)
    leading_light_enabled: bool = False
    voice_enabled: bool = False

    # Sherlock + DNA integration flags (Ticket 17 - default disabled)
    sherlock_enabled: bool = False
    dna_recording_enabled: bool = False

    # Notification system flags (S20 - default disabled for safe rollout)
    notifications_enabled: bool = False
    notifications_kill_switch: bool = False

    # Notification rate limiting configuration
    notifications_max_daily_per_user: int = 5  # Beta-safe default (was 10)
    notifications_cooldown_minutes: int = 120  # Beta-safe default (was 60)
    notifications_daily_cap: int = 5  # Hard cap for beta period

    # Beta cohort configuration
    notifications_beta_user_ids: list = field(default_factory=list)  # Empty = all users (use with caution)

    # Sherlock incentives configuration (S20-P3)
    feature_sherlock_incentives: bool = True
    incentive_activation_weight: str = "minimal"  # minimal/low/medium/high/off

    # Incentive kill switch - immediate stop validation
    INCENTIVE_KILL_SWITCH_VALIDATION: bool = True  # If True, validates kill switch on startup

    # API keys (OPTIONAL - features disabled without them)
    openai_api_key_present: bool = False
    the_odds_api_key: Optional[str] = None
    
    # Provider configuration (R0.3: Deterministic provider selection)
    odds_provider: str = "mock"  # "mock" or "oddsapi"
    
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

    # Git SHA for deploy identification (Railway provides RAILWAY_GIT_COMMIT_SHA)
    git_sha = (
        os.environ.get("RAILWAY_GIT_COMMIT_SHA")
        or os.environ.get("GIT_SHA")
        or "unknown"
    )

    # Build time for deploy verification (fallback to current time at startup)
    from datetime import datetime, timezone
    build_time_utc = os.environ.get("BUILD_TIME_UTC")
    if not build_time_utc:
        build_time_utc = datetime.now(timezone.utc).isoformat()

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

    # Sherlock + DNA integration flags (Ticket 17 - disabled by default)
    sherlock_enabled = _parse_bool_env("SHERLOCK_ENABLED", False)
    dna_recording_enabled = _parse_bool_env("DNA_RECORDING_ENABLED", False)

    # Notification system flags (S20 - disabled by default for safe rollout)
    notifications_enabled = _parse_bool_env("NOTIFICATIONS_ENABLED", False)
    notifications_kill_switch = _parse_bool_env("NOTIFICATIONS_KILL_SWITCH", False)

    # Notification rate limiting configuration
    notifications_max_daily, nd_warning = _parse_int_env(
        "NOTIFICATIONS_MAX_DAILY_PER_USER", 10, min_value=1
    )
    if nd_warning:
        warnings.append(nd_warning)

    notifications_cooldown, nc_warning = _parse_int_env(
        "NOTIFICATIONS_COOLDOWN_MINUTES", 60, min_value=0
    )
    if nc_warning:
        warnings.append(nc_warning)

    # API key presence (OPTIONAL - check presence, don't store value)
    openai_key = os.environ.get("OPENAI_API_KEY")
    openai_api_key_present = bool(openai_key and len(openai_key) > 0)
    
    # The Odds API key (for live data)
    the_odds_api_key = os.environ.get("THE_ODDS_API_KEY")
    
    # R0.3: Deterministic provider selection
    odds_provider = os.environ.get("ODDS_PROVIDER", "mock").lower()
    if odds_provider not in ("mock", "oddsapi"):
        warnings.append(
            f"ODDS_PROVIDER='{odds_provider}' is not valid; using 'mock'. "
            "Valid values: 'mock' or 'oddsapi'"
        )
        odds_provider = "mock"
    
    # R0.3: Validate oddsapi has API key
    if odds_provider == "oddsapi" and not the_odds_api_key:
        raise ConfigurationError(
            "ODDS_PROVIDER=oddsapi requires THE_ODDS_API_KEY to be set"
        )

    # S20-P3: Incentives configuration
    feature_sherlock_incentives = _parse_bool_env("FEATURE_SHERLOCK_INCENTIVES", True)
    incentive_activation_weight = os.environ.get("INCENTIVE_ACTIVATION_WEIGHT", "minimal").lower()

    # Validate incentive weight values
    valid_weights = ("minimal", "low", "medium", "high", "off")
    if incentive_activation_weight not in valid_weights:
        warnings.append(
            f"INCENTIVE_ACTIVATION_WEIGHT='{incentive_activation_weight}' is not valid; using 'minimal'. "
            f"Valid values: {valid_weights}"
        )
        incentive_activation_weight = "minimal"

    # S20-P3: Kill switch validation - if incentives off, stop immediately
    if incentive_activation_weight == "off":
        logger.warning("[KILL SWITCH] INCENTIVE_ACTIVATION_WEIGHT=off - incentives disabled")
        feature_sherlock_incentives = False

    # S20-P3: Notification kill switch validation - if toggled, disable notification delivery
    if notifications_kill_switch:
        logger.warning("[KILL SWITCH] NOTIFICATIONS_KILL_SWITCH=true - notification delivery disabled")
        notifications_enabled = False

    # S20-P5: Beta-safe notification defaults
    notifications_daily_cap, ndc_warning = _parse_int_env(
        "NOTIFICATIONS_DAILY_CAP", 5, min_value=1
    )
    if ndc_warning:
        warnings.append(ndc_warning)

    # Parse beta user IDs (comma-separated list, empty = all users)
    beta_user_ids_raw = os.environ.get("NOTIFICATIONS_BETA_USER_IDS", "")
    notifications_beta_user_ids = [
        uid.strip() for uid in beta_user_ids_raw.split(",") if uid.strip()
    ] if beta_user_ids_raw else []

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
        git_sha=git_sha,
        build_time_utc=build_time_utc,
        max_request_size_bytes=max_request_size,
        leading_light_enabled=leading_light_enabled,
        voice_enabled=voice_enabled,
        sherlock_enabled=sherlock_enabled,
        dna_recording_enabled=dna_recording_enabled,
        openai_api_key_present=openai_api_key_present,
        the_odds_api_key=the_odds_api_key,
        odds_provider=odds_provider,
        notifications_enabled=notifications_enabled,
        notifications_kill_switch=notifications_kill_switch,
        notifications_max_daily_per_user=notifications_max_daily,
        notifications_cooldown_minutes=notifications_cooldown,
        notifications_daily_cap=notifications_daily_cap,
        notifications_beta_user_ids=notifications_beta_user_ids,
        feature_sherlock_incentives=feature_sherlock_incentives,
        incentive_activation_weight=incentive_activation_weight,
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
        f"git_sha={config.git_sha} "
        f"build_time_utc={config.build_time_utc} "
        f"max_request_size_bytes={config.max_request_size_bytes} "
        f"leading_light_enabled={config.leading_light_enabled} "
        f"voice_enabled={config.voice_enabled} "
        f"sherlock_enabled={config.sherlock_enabled} "
        f"dna_recording_enabled={config.dna_recording_enabled} "
        f"notifications_enabled={config.notifications_enabled} "
        f"notifications_kill_switch={config.notifications_kill_switch} "
        f"notifications_max_daily={config.notifications_max_daily_per_user} "
        f"notifications_cooldown={config.notifications_cooldown_minutes} "
        f"notifications_daily_cap={config.notifications_daily_cap} "
        f"feature_sherlock_incentives={config.feature_sherlock_incentives} "
        f"incentive_activation_weight={config.incentive_activation_weight} "
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


def get_config_health(config: AppConfig) -> dict:
    """
    Generate a health check report for configuration.

    Returns a dict with config status for monitoring and debugging.
    Safe to expose via health endpoint - no sensitive values.
    """
    return {
        "status": "healthy" if not config.warnings else "degraded",
        "environment": config.environment,
        "git_sha": config.git_sha,
        "features": {
            "leading_light": {
                "enabled": config.leading_light_enabled,
                "api_key_present": config.openai_api_key_present,
                "ready": config.leading_light_enabled and config.openai_api_key_present
            },
            "voice": {
                "enabled": config.voice_enabled,
                "api_key_present": config.openai_api_key_present,
                "ready": config.voice_enabled and config.openai_api_key_present
            },
            "sherlock": {
                "enabled": config.sherlock_enabled,
                "ready": config.sherlock_enabled
            },
            "dna_recording": {
                "enabled": config.dna_recording_enabled,
                "ready": config.dna_recording_enabled
            }
        },
        "odds_provider": {
            "provider": config.odds_provider,
            "api_key_present": bool(config.the_odds_api_key),
            "ready": config.odds_provider == "mock" or bool(config.the_odds_api_key)
        },
        "notifications": {
            "enabled": config.notifications_enabled,
            "kill_switch_active": config.notifications_kill_switch,
            "max_daily_per_user": config.notifications_max_daily_per_user,
            "cooldown_minutes": config.notifications_cooldown_minutes,
            "daily_cap": config.notifications_daily_cap,
            "beta_cohort_size": len(config.notifications_beta_user_ids),
            "beta_mode": len(config.notifications_beta_user_ids) > 0,
            "ready": config.notifications_enabled and not config.notifications_kill_switch,
            "status": "paused" if config.notifications_kill_switch else ("active" if config.notifications_enabled else "disabled")
        },
        "sherlock_incentives": {
            "enabled": config.feature_sherlock_incentives,
            "activation_weight": config.incentive_activation_weight,
            "ready": config.feature_sherlock_incentives and config.incentive_activation_weight != "off",
            "status": "off" if config.incentive_activation_weight == "off" else (
                "active" if config.feature_sherlock_incentives else "disabled"
            )
        },
        "warnings": config.warnings,
        "warning_count": len(config.warnings)
    }


def is_beta_user(user_id: str, beta_user_ids: list = None) -> bool:
    """
    Check if a user is in the beta allowlist.

    Args:
        user_id: The user ID to check
        beta_user_ids: List of beta user IDs (from config.notifications_beta_user_ids)
                         Can also be a comma-separated string for convenience.

    Returns:
        True if user is in the allowlist (or allowlist is empty), False otherwise
    """
    # Handle string input (from tests or env var)
    if isinstance(beta_user_ids, str):
        beta_user_ids = [
            uid.strip() for uid in beta_user_ids.split(",") if uid.strip()
        ] if beta_user_ids else []

    if beta_user_ids is None:
        beta_user_ids = []

    # Empty allowlist means everyone is allowed (disabled gating)
    if not beta_user_ids:
        return True

    return user_id in beta_user_ids
