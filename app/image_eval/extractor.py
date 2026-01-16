# app/image_eval/extractor.py
"""
Image-to-text extraction using OpenAI Vision API.

Extracts bet information from sportsbook screenshots and bet slips.
"""

import base64
import json
import logging
from dataclasses import dataclass
from typing import Optional

from .config import get_image_eval_model, get_openai_api_key, is_openai_configured

logger = logging.getLogger(__name__)


@dataclass
class ImageParseResult:
    """Result of parsing an image for bet information."""

    bet_text: str
    confidence: float  # 0.0 to 1.0
    notes: list[str]
    missing: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "bet_text": self.bet_text,
            "confidence": self.confidence,
            "notes": self.notes,
            "missing": self.missing,
        }


class ImageExtractionError(Exception):
    """Error during image extraction."""

    pass


# Prompt for OpenAI Vision to extract bet information
EXTRACTION_PROMPT = """You are analyzing a sportsbook bet slip or screenshot. Extract the bet information and output ONLY valid JSON.

Your task:
1. Identify all legs/selections in the bet
2. Extract team names, player names, bet types (spread, moneyline, total, player prop), lines, and odds
3. Format as a concise single-line bet description suitable for evaluation

Output format (JSON only, no markdown):
{
  "bet_text": "Lakers -5.5 (-110) + Celtics ML (-150) + LeBron O27.5 pts (-115)",
  "confidence": 0.85,
  "notes": ["2-leg parlay", "NBA basketball"],
  "missing": ["exact odds not visible"]
}

Rules for bet_text:
- Use standard betting notation: team/player + bet type + line + odds in parentheses
- Separate multiple legs with " + "
- For spreads: "Team -5.5 (-110)" or "Team +3.5 (-110)"
- For totals: "O 220.5 (-110)" or "U 220.5 (-110)"
- For moneylines: "Team ML (-150)" or "Team ML (+130)"
- For player props: "Player O27.5 pts (-115)" or "Player U10.5 reb (-110)"

Confidence scoring:
- 0.9-1.0: All information clearly visible and extracted
- 0.7-0.9: Most information visible, some inferred
- 0.5-0.7: Partial information, significant inference needed
- Below 0.5: Cannot reliably extract bet information

If you cannot extract any bet information, return:
{
  "bet_text": "",
  "confidence": 0.0,
  "notes": ["Could not identify bet information"],
  "missing": ["all bet details"]
}

Analyze the image and return ONLY the JSON object, no other text."""


async def extract_bet_text_from_image(image_bytes: bytes) -> ImageParseResult:
    """
    Extract bet text from an image using OpenAI Vision API.

    Args:
        image_bytes: Raw image bytes (PNG, JPG, or WebP)

    Returns:
        ImageParseResult with extracted bet information

    Raises:
        ImageExtractionError: If extraction fails
    """
    if not is_openai_configured():
        raise ImageExtractionError("OpenAI API key not configured")

    try:
        import openai
    except ImportError:
        raise ImageExtractionError("openai package not installed")

    # Base64 encode the image
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Detect image type from magic bytes
    content_type = _detect_image_type(image_bytes)

    # Build the API request
    client = openai.AsyncOpenAI(api_key=get_openai_api_key())
    model = get_image_eval_model()

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{content_type};base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=500,
            temperature=0.1,  # Low temperature for consistent extraction
        )

        # Parse the response
        content = response.choices[0].message.content
        if not content:
            raise ImageExtractionError("Empty response from OpenAI")

        # Clean up the response (remove markdown code blocks if present)
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # Parse JSON
        try:
            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {content}")
            raise ImageExtractionError(f"Invalid JSON response: {e}")

        # Validate required fields
        bet_text = result.get("bet_text", "")
        confidence = float(result.get("confidence", 0.0))
        notes = result.get("notes", [])
        missing = result.get("missing", [])

        # Ensure lists
        if not isinstance(notes, list):
            notes = [str(notes)] if notes else []
        if not isinstance(missing, list):
            missing = [str(missing)] if missing else []

        return ImageParseResult(
            bet_text=bet_text,
            confidence=min(1.0, max(0.0, confidence)),  # Clamp to [0, 1]
            notes=notes,
            missing=missing,
        )

    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        raise ImageExtractionError(f"OpenAI API error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during image extraction: {e}")
        raise ImageExtractionError(f"Extraction failed: {e}")


def _detect_image_type(image_bytes: bytes) -> str:
    """Detect image MIME type from magic bytes."""
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    elif image_bytes[:2] == b"\xff\xd8":
        return "image/jpeg"
    elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    else:
        # Default to JPEG
        return "image/jpeg"


# Synchronous wrapper for non-async contexts
def extract_bet_text_from_image_sync(image_bytes: bytes) -> ImageParseResult:
    """Synchronous wrapper for extract_bet_text_from_image."""
    import asyncio

    return asyncio.run(extract_bet_text_from_image(image_bytes))
