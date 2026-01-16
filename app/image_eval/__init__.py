# app/image_eval/__init__.py
"""
Image evaluation module for extracting bet text from images.

Uses OpenAI Vision API to parse bet slip screenshots and extract
structured bet information for evaluation.
"""

from .config import is_image_eval_enabled, get_image_eval_model
from .extractor import extract_bet_text_from_image, ImageParseResult

__all__ = [
    "is_image_eval_enabled",
    "get_image_eval_model",
    "extract_bet_text_from_image",
    "ImageParseResult",
]
