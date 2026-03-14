"""
Backend OCR review parsing helpers.

These helpers mirror the existing frontend OCR heuristics closely enough to
freeze a review contract on the backend without changing the scoring pipeline.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional


_MARKET_KEYWORDS = re.compile(r"(ml|moneyline|spread|over|under|pts|points|rebounds|assists)", re.IGNORECASE)
_NON_ALPHA_ENTITY = re.compile(r"^[a-zA-Z\s]+$")
_UNUSUAL_CHARS = re.compile(r"[^a-zA-Z0-9\s.+-]")
_SPORT_NOISE = re.compile(r"\b(nba|nfl|mlb|ncaa|college|basketball|football|baseball)\b", re.IGNORECASE)
_GENERIC_NOISE = re.compile(r"\b(game|match|vs|@|at)\b", re.IGNORECASE)


def _clean_entity_name(name: str) -> str:
    cleaned = _SPORT_NOISE.sub("", name)
    cleaned = _GENERIC_NOISE.sub("", cleaned)
    cleaned = re.sub(r"[,()]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _infer_sport(line: str) -> Optional[str]:
    if re.search(r"\b(nba|basketball)\b", line, re.IGNORECASE):
        return "NBA"
    if re.search(r"\b(nfl|football)\b", line, re.IGNORECASE):
        return "NFL"
    if re.search(r"\b(mlb|baseball)\b", line, re.IGNORECASE):
        return "MLB"
    if re.search(r"\b(ncaa|college)\b", line, re.IGNORECASE):
        return "NCAA"
    return None


def _generate_leg_id(entity: str, market: str, value: Optional[str], sport: Optional[str]) -> str:
    canonical = "|".join(
        [
            (entity or "").lower().strip(),
            (market or "").lower().strip(),
            (value or "").lower().strip(),
            (sport or "").lower().strip(),
        ]
    )
    return f"leg_{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:16]}"


def get_ocr_leg_clarity(leg: Dict[str, Any]) -> str:
    """Match the existing frontend clarity scoring well enough for contract freeze."""
    score = 0

    if leg.get("market") and leg["market"] != "unknown":
        score += 2
    if leg.get("entity") and len(leg["entity"]) >= 3 and _NON_ALPHA_ENTITY.match(leg["entity"]):
        score += 1
    if leg.get("value") and re.search(r"\d", leg["value"]):
        score += 1
    if _MARKET_KEYWORDS.search(leg.get("raw", "")):
        score += 1
    if len(leg.get("raw", "")) < 5:
        score -= 1
    if _UNUSUAL_CHARS.search(leg.get("raw", "")):
        score -= 1

    if score >= 4:
        return "clear"
    if score >= 2:
        return "review"
    return "ambiguous"


def parse_ocr_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse one OCR output line into a structured review leg."""
    raw = line.strip()
    if not raw:
        return None

    entity = ""
    market = "unknown"
    value = None
    sport = _infer_sport(raw)

    if re.search(r"\b(ml|moneyline|to win)\b", raw, re.IGNORECASE):
        market = "moneyline"
        entity = _clean_entity_name(re.sub(r"\b(ml|moneyline|to win)\b", "", raw, flags=re.IGNORECASE))
    elif re.search(r"[+-]\d+\.?\d*", raw, re.IGNORECASE) and not re.search(
        r"\b(over|under|o/u|pts|points|rebounds|assists|3pt)\b", raw, re.IGNORECASE
    ):
        market = "spread"
        spread_match = re.search(r"([+-]\d+\.?\d*)", raw)
        if spread_match:
            value = spread_match.group(1)
            entity = _clean_entity_name(re.sub(r"[+-]\d+\.?\d*", "", raw))
            entity = _clean_entity_name(re.sub(r"\bspread\b", "", entity, flags=re.IGNORECASE))
    elif re.search(r"\b(over|under|o/u)\b", raw, re.IGNORECASE) or re.search(r"[ou]\d+\.?\d*", raw, re.IGNORECASE):
        market = "total"
        over_match = re.search(r"\b(over|o)\s*(\d+\.?\d*)", raw, re.IGNORECASE)
        under_match = re.search(r"\b(under|u)\s*(\d+\.?\d*)", raw, re.IGNORECASE)
        if over_match:
            value = f"over {over_match.group(2)}"
            entity = _clean_entity_name(re.sub(r"\b(over|o)\s*\d+\.?\d*", "", raw, flags=re.IGNORECASE))
        elif under_match:
            value = f"under {under_match.group(2)}"
            entity = _clean_entity_name(re.sub(r"\b(under|u)\s*\d+\.?\d*", "", raw, flags=re.IGNORECASE))
    elif re.search(r"\b(pts|points|rebounds|assists|3pt|threes|steals|blocks)\b", raw, re.IGNORECASE):
        market = "player_prop"
        prop_match = re.search(
            r"(over|under)?\s*(\d+\.?\d*)\s*(pts|points|rebounds|assists|3pt|threes|steals|blocks)",
            raw,
            re.IGNORECASE,
        )
        if prop_match:
            direction = (prop_match.group(1) or "over").lower()
            value = f"{direction} {prop_match.group(2)} {prop_match.group(3).lower()}"
        entity = _clean_entity_name(
            re.sub(
                r"(over|under)?\s*\d+\.?\d*\s*(pts|points|rebounds|assists|3pt|threes|steals|blocks)",
                "",
                raw,
                flags=re.IGNORECASE,
            )
        )
    else:
        entity = _clean_entity_name(raw)

    if not entity or len(entity) < 2:
        entity = raw.split()[0] if raw.split() else raw

    leg = {
        "legId": _generate_leg_id(entity, market, value, sport),
        "entity": entity,
        "market": market,
        "value": value,
        "raw": raw,
        "source": "ocr",
        "sport": sport,
    }
    leg["clarity"] = get_ocr_leg_clarity(leg)
    return leg


def parse_ocr_text(raw_text: str) -> List[Dict[str, Any]]:
    """Parse OCR text into detected leg objects."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    legs: List[Dict[str, Any]] = []
    for line in lines:
        leg = parse_ocr_line(line)
        if leg:
            legs.append(leg)
    return legs


def build_ocr_review_response(raw_text: str, file_name: Optional[str], request_id: str) -> Dict[str, Any]:
    """Build the frozen OCR review payload."""
    detected_legs = parse_ocr_text(raw_text)

    clarity_weights = {
        "clear": 1.0,
        "review": 0.6,
        "ambiguous": 0.2,
    }
    if detected_legs:
        confidence = sum(clarity_weights[leg["clarity"]] for leg in detected_legs) / len(detected_legs)
    else:
        confidence = 0.0

    requires_review = not detected_legs or any(leg["clarity"] != "clear" for leg in detected_legs)

    return {
        "requestId": request_id,
        "source": "image",
        "fileName": file_name,
        "rawText": raw_text,
        "detectedLegs": detected_legs,
        "confidence": round(confidence, 3),
        "requiresReview": requires_review,
    }
