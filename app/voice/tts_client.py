# app/voice/tts_client.py
"""
OpenAI Text-to-Speech Client.

Uses OpenAI Audio API to generate speech from text.
Includes in-memory caching to avoid repeat API calls.
"""
from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import httpx


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_TTS_VOICE = "alloy"
OPENAI_TTS_ENDPOINT = "https://api.openai.com/v1/audio/speech"

# Cache TTL in seconds (15 minutes)
CACHE_TTL_SECONDS = 900


# =============================================================================
# Exceptions
# =============================================================================


class TTSError(Exception):
    """Base exception for TTS errors."""
    pass


class TTSDisabledError(TTSError):
    """Raised when TTS service is disabled."""
    pass


class TTSConfigurationError(TTSError):
    """Raised when TTS is misconfigured (e.g., missing API key)."""
    pass


class TTSAPIError(TTSError):
    """Raised when OpenAI API returns an error."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


# =============================================================================
# Cache Entry
# =============================================================================


@dataclass
class CacheEntry:
    """Cached audio response."""
    audio_bytes: bytes
    created_at: float


# In-memory cache: (case_name, voice, model, text_hash) -> CacheEntry
_audio_cache: Dict[Tuple[str, str, str, str], CacheEntry] = {}


def _get_text_hash(text: str) -> str:
    """Generate a short hash of the text for cache key."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _get_cache_key(case_name: str, voice: str, model: str, text: str) -> Tuple[str, str, str, str]:
    """Generate cache key tuple."""
    return (case_name, voice, model, _get_text_hash(text))


def get_cached_audio(case_name: str, voice: str, model: str, text: str) -> Optional[bytes]:
    """
    Get cached audio if available and not expired.

    Args:
        case_name: Demo case name
        voice: TTS voice
        model: TTS model
        text: Narration text

    Returns:
        Cached audio bytes, or None if not cached/expired
    """
    key = _get_cache_key(case_name, voice, model, text)
    entry = _audio_cache.get(key)

    if entry is None:
        return None

    # Check if expired
    if time.time() - entry.created_at > CACHE_TTL_SECONDS:
        # Remove expired entry
        del _audio_cache[key]
        return None

    return entry.audio_bytes


def set_cached_audio(
    case_name: str,
    voice: str,
    model: str,
    text: str,
    audio_bytes: bytes,
) -> None:
    """
    Store audio in cache.

    Args:
        case_name: Demo case name
        voice: TTS voice
        model: TTS model
        text: Narration text
        audio_bytes: Generated audio bytes
    """
    key = _get_cache_key(case_name, voice, model, text)
    _audio_cache[key] = CacheEntry(
        audio_bytes=audio_bytes,
        created_at=time.time(),
    )


def clear_cache() -> None:
    """Clear all cached audio (for testing)."""
    _audio_cache.clear()


# =============================================================================
# Configuration Helpers
# =============================================================================


def is_voice_enabled() -> bool:
    """Check if voice/TTS service is enabled."""
    return os.environ.get("VOICE_ENABLED", "false").lower() == "true"


def is_voice_override_enabled() -> bool:
    """Check if voice override is enabled (bypasses plan check)."""
    return os.environ.get("VOICE_OVERRIDE", "false").lower() == "true"


def get_openai_api_key() -> Optional[str]:
    """Get OpenAI API key from environment."""
    return os.environ.get("OPENAI_API_KEY")


def get_tts_model() -> str:
    """Get TTS model from environment or default."""
    return os.environ.get("OPENAI_TTS_MODEL", DEFAULT_TTS_MODEL)


def get_tts_voice() -> str:
    """Get TTS voice from environment or default."""
    return os.environ.get("OPENAI_TTS_VOICE", DEFAULT_TTS_VOICE)


# =============================================================================
# TTS Generation
# =============================================================================


async def generate_speech(
    text: str,
    voice: Optional[str] = None,
    model: Optional[str] = None,
) -> bytes:
    """
    Generate speech audio from text using OpenAI TTS API.

    Args:
        text: Text to convert to speech
        voice: Voice to use (default from env or 'alloy')
        model: Model to use (default from env or 'gpt-4o-mini-tts')

    Returns:
        Audio bytes (MP3 format)

    Raises:
        TTSDisabledError: If VOICE_ENABLED is not true
        TTSConfigurationError: If OPENAI_API_KEY is not set
        TTSAPIError: If OpenAI API returns an error
    """
    # Check if enabled
    if not is_voice_enabled():
        raise TTSDisabledError("Voice service is disabled. Set VOICE_ENABLED=true to enable.")

    # Get API key
    api_key = get_openai_api_key()
    if not api_key:
        raise TTSConfigurationError("OPENAI_API_KEY environment variable is not set.")

    # Use defaults if not specified
    voice = voice or get_tts_voice()
    model = model or get_tts_model()

    # Build request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "voice": voice,
        "input": text,
        "response_format": "mp3",
    }

    # Make request
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            OPENAI_TTS_ENDPOINT,
            headers=headers,
            json=payload,
        )

    # Handle errors
    if response.status_code != 200:
        error_detail = response.text
        try:
            error_json = response.json()
            error_detail = error_json.get("error", {}).get("message", response.text)
        except Exception:
            pass
        raise TTSAPIError(
            f"OpenAI TTS API error: {error_detail}",
            status_code=response.status_code,
        )

    return response.content


async def generate_narration(
    case_name: str,
    text: str,
    voice: Optional[str] = None,
    model: Optional[str] = None,
    use_cache: bool = True,
) -> bytes:
    """
    Generate narration audio for a demo case with caching.

    Args:
        case_name: Demo case name (for cache key)
        text: Narration text
        voice: Voice to use
        model: Model to use
        use_cache: Whether to use/update cache

    Returns:
        Audio bytes (MP3 format)
    """
    voice = voice or get_tts_voice()
    model = model or get_tts_model()

    # Check cache first
    if use_cache:
        cached = get_cached_audio(case_name, voice, model, text)
        if cached is not None:
            return cached

    # Generate fresh audio
    audio_bytes = await generate_speech(text, voice=voice, model=model)

    # Store in cache
    if use_cache:
        set_cached_audio(case_name, voice, model, text, audio_bytes)

    return audio_bytes
