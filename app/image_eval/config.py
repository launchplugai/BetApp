# app/image_eval/config.py
"""
Configuration for image evaluation feature.

Environment variables:
- IMAGE_EVAL_ENABLED: Enable/disable image evaluation (default: true)
- IMAGE_EVAL_MODEL: OpenAI model to use for vision (default: gpt-4o-mini)
- OPENAI_API_KEY: Required for image evaluation to work
"""

import os


def is_image_eval_enabled() -> bool:
    """Check if image evaluation is enabled."""
    enabled = os.environ.get("IMAGE_EVAL_ENABLED", "true").lower()
    return enabled in ("true", "1", "yes")


def get_image_eval_model() -> str:
    """Get the OpenAI model to use for image evaluation."""
    return os.environ.get("IMAGE_EVAL_MODEL", "gpt-4o-mini")


def get_openai_api_key() -> str | None:
    """Get the OpenAI API key."""
    return os.environ.get("OPENAI_API_KEY")


def is_openai_configured() -> bool:
    """Check if OpenAI API key is configured."""
    key = get_openai_api_key()
    return key is not None and len(key) > 0


# Maximum file size for image uploads (5MB)
MAX_IMAGE_SIZE = 5 * 1024 * 1024

# Allowed image MIME types
ALLOWED_IMAGE_TYPES = [
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
]

# Allowed file extensions
ALLOWED_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"]
