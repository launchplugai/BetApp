"""
Dedicated OCR review router for the separated frontend.

This endpoint intentionally stops at extraction + parsed-leg review so the
frontend can own the trust gate experience.
"""
from __future__ import annotations

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from app.routers.leading_light import (
    MAX_IMAGE_SIZE_BYTES,
    _check_rate_limit,
    _parse_bet_slip_image,
    is_leading_light_enabled,
)
from app.schemas.frontend_contracts import OcrReviewResponseSchema
from app.services.ocr_review import build_ocr_review_response


router = APIRouter(prefix="/api/ocr", tags=["ocr"])


@router.post(
    "/review",
    response_model=OcrReviewResponseSchema,
    summary="Extract a bet slip and return parsed legs for review",
    responses={
        400: {"description": "Invalid upload"},
        413: {"description": "File too large"},
        429: {"description": "Rate limited"},
        503: {"description": "OCR unavailable"},
    },
)
async def review_bet_slip(
    request: Request,
    image: UploadFile = File(...),
    plan: str = Form("good"),
    session_id: Optional[str] = Form(None),
):
    """
    Extract slip text and return parsed review legs without evaluating.

    `plan` and `session_id` are accepted for additive compatibility with the
    existing OCR form flow, but they do not change the review payload.
    """
    del plan
    del session_id

    if not is_leading_light_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "OCR disabled",
                "detail": "OCR review is currently disabled",
                "code": "SERVICE_DISABLED",
            },
        )

    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid file type",
                "detail": "Only images are supported",
                "code": "INVALID_FILE_TYPE",
            },
        )

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "File too large",
                "detail": f"Maximum file size is {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB",
                "code": "FILE_TOO_LARGE",
            },
        )

    request_id = str(uuid4())[:8]
    raw_text = await _parse_bet_slip_image(image_bytes)
    return build_ocr_review_response(
        raw_text=raw_text,
        file_name=image.filename,
        request_id=request_id,
    )
