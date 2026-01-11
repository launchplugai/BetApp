# app/voice/router.py
"""
Voice Narration API Router.

Provides endpoints for:
- GET /leading-light/demo/{case_name}/narration - Demo case narration audio
- POST /voice/tts - Generic text-to-speech

Feature gated by VOICE_ENABLED environment variable.
Plan gated to BEST tier (unless VOICE_OVERRIDE=true).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.tiering import Plan, parse_plan
from app.voice.narration import get_narration, list_available_narrations
from app.voice.tts_client import (
    generate_narration,
    generate_speech,
    is_voice_enabled,
    is_voice_override_enabled,
    get_tts_voice,
    get_tts_model,
    TTSDisabledError,
    TTSConfigurationError,
    TTSAPIError,
)


# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(tags=["Voice"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class TTSRequest(BaseModel):
    """Request schema for generic TTS endpoint."""
    text: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Text to convert to speech (max 4096 characters)",
    )
    voice: Optional[str] = Field(
        default=None,
        description="Voice to use (default: env OPENAI_TTS_VOICE or 'alloy')",
    )
    model: Optional[str] = Field(
        default=None,
        description="Model to use (default: env OPENAI_TTS_MODEL or 'gpt-4o-mini-tts')",
    )
    plan: Optional[str] = Field(
        default="good",
        description="Subscription plan tier: good, better, or best",
    )


# =============================================================================
# Plan Gating
# =============================================================================


def _check_voice_access(plan: Optional[str]) -> None:
    """
    Check if voice access is allowed for the given plan.

    Voice requires BEST plan or VOICE_OVERRIDE=true.

    Raises:
        HTTPException: 403 if not allowed
    """
    parsed_plan = parse_plan(plan)
    override = is_voice_override_enabled()

    if override:
        return

    if parsed_plan != Plan.BEST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Voice access denied",
                "detail": f"Voice narration requires plan='best' or VOICE_OVERRIDE=true. Current plan: '{parsed_plan.value}'",
                "code": "VOICE_ACCESS_DENIED",
            },
        )


def _handle_tts_error(e: Exception) -> None:
    """
    Convert TTS exceptions to appropriate HTTP exceptions.

    Args:
        e: The exception to handle

    Raises:
        HTTPException: Appropriate HTTP error
    """
    if isinstance(e, TTSDisabledError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Voice service disabled",
                "detail": str(e),
                "code": "SERVICE_DISABLED",
            },
        )
    elif isinstance(e, TTSConfigurationError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Voice service misconfigured",
                "detail": str(e),
                "code": "SERVICE_MISCONFIGURED",
            },
        )
    elif isinstance(e, TTSAPIError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "TTS API error",
                "detail": str(e),
                "code": "TTS_API_ERROR",
            },
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal error",
                "detail": str(e),
                "code": "INTERNAL_ERROR",
            },
        )


# =============================================================================
# Demo Narration Endpoint
# =============================================================================


@router.get(
    "/leading-light/demo/{case_name}/narration",
    responses={
        200: {
            "description": "Audio narration (MP3)",
            "content": {"audio/mpeg": {}},
        },
        403: {"description": "Voice access denied"},
        404: {"description": "Demo case not found"},
        503: {"description": "Service disabled"},
    },
    summary="Get demo case narration",
    description="Get audio narration for a demo case. Requires BEST plan or VOICE_OVERRIDE.",
)
async def get_demo_narration(
    case_name: str,
    plan: Optional[str] = None,
    voice: Optional[str] = None,
) -> Response:
    """
    Get audio narration for a demo case.

    Returns MP3 audio with the narration script for the specified demo case.
    """
    # Check plan gating
    _check_voice_access(plan)

    # Get narration text
    narration_text = get_narration(case_name)
    if narration_text is None:
        available = list_available_narrations()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Narration not found",
                "detail": f"No narration available for case '{case_name}'. Available: {', '.join(available)}",
                "code": "NOT_FOUND",
            },
        )

    try:
        # Generate audio (with caching)
        audio_bytes = await generate_narration(
            case_name=case_name,
            text=narration_text,
            voice=voice,
            use_cache=True,
        )

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="{case_name}_narration.mp3"',
                "Cache-Control": "public, max-age=86400",
            },
        )

    except (TTSDisabledError, TTSConfigurationError, TTSAPIError) as e:
        _handle_tts_error(e)
    except Exception as e:
        _handle_tts_error(e)


# =============================================================================
# Generic TTS Endpoint
# =============================================================================


@router.post(
    "/voice/tts",
    responses={
        200: {
            "description": "Generated audio (MP3)",
            "content": {"audio/mpeg": {}},
        },
        400: {"description": "Invalid request"},
        403: {"description": "Voice access denied"},
        503: {"description": "Service disabled"},
    },
    summary="Text-to-speech",
    description="Convert text to speech audio. Requires BEST plan or VOICE_OVERRIDE.",
)
async def text_to_speech(request: TTSRequest) -> Response:
    """
    Convert arbitrary text to speech audio.

    Returns MP3 audio generated from the input text.
    """
    # Check plan gating
    _check_voice_access(request.plan)

    try:
        # Generate audio (no caching for generic TTS)
        audio_bytes = await generate_speech(
            text=request.text,
            voice=request.voice,
            model=request.model,
        )

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": 'inline; filename="tts_output.mp3"',
            },
        )

    except (TTSDisabledError, TTSConfigurationError, TTSAPIError) as e:
        _handle_tts_error(e)
    except Exception as e:
        _handle_tts_error(e)


# =============================================================================
# Status Endpoint
# =============================================================================


@router.get(
    "/voice/status",
    summary="Check voice service status",
    description="Check if the voice/TTS service is enabled and configured.",
)
async def voice_status():
    """Check voice service status."""
    from app.voice.tts_client import get_openai_api_key

    enabled = is_voice_enabled()
    has_api_key = get_openai_api_key() is not None

    return {
        "enabled": enabled,
        "configured": has_api_key if enabled else None,
        "model": get_tts_model() if enabled else None,
        "voice": get_tts_voice() if enabled else None,
        "service": "voice-tts",
    }

# =============================================================================
# Narration Text Endpoint
# =============================================================================


@router.get(
    "/leading-light/demo/{case_name}/narration-text",
    responses={
        200: {
            "description": "Narration text with plain-English explanation and glossary",
            "content": {"application/json": {}},
        },
        404: {"description": "Demo case not found"},
    },
    summary="Get demo case narration text",
    description="Get the narration script, plain-English explanation, and glossary for a demo case.",
)
async def get_demo_narration_text(case_name: str):
    """
    Get narration text and educational content for a demo case.

    Returns the exact text used for audio narration plus beginner-friendly
    explanations and glossary terms.
    """
    from app.voice.narration import get_demo_case_data

    data = get_demo_case_data(case_name)
    if data is None:
        available = list_available_narrations()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Demo case not found",
                "detail": f"No narration available for case '{case_name}'. Available: {', '.join(available)}",
                "code": "NOT_FOUND",
            },
        )

    return {
        "case_name": case_name.lower(),
        "title": f"{case_name.capitalize()} Demo",
        "narration": data["narration"],
        "plain_english": data["plain_english"],
        "glossary": data["glossary"],
    }
