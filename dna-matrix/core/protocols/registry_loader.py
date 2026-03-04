# core/protocols/registry_loader.py
"""
Registry Loader — reads declarative protocol config from registry.json.

This is the single source of truth for:
- which protocols exist
- which tier they require
- their risk weights and thresholds
- their explanation templates (per user style)

The JSON registry makes protocols tunable without code edits
and provides premium gating per protocol.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_REGISTRY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "protocols", "registry.json",
)

# Cached registry data
_registry_data: Optional[Dict[str, Any]] = None


class ProtocolTier:
    """Protocol tier constants."""
    FREE = "FREE"
    PRO = "PRO"
    ELITE = "ELITE"

    # Tier hierarchy (higher number = more access)
    _LEVELS = {FREE: 0, PRO: 1, ELITE: 2}

    @classmethod
    def has_access(cls, user_tier: str, required_tier: str) -> bool:
        """Check if user tier has access to a protocol requiring required_tier."""
        user_level = cls._LEVELS.get(user_tier.upper(), 0)
        required_level = cls._LEVELS.get(required_tier.upper(), 0)
        return user_level >= required_level

    @classmethod
    def from_app_tier(cls, app_tier: str) -> str:
        """Map app-level tier names to protocol tier."""
        mapping = {
            "good": cls.FREE,
            "better": cls.PRO,
            "best": cls.ELITE,
            "free": cls.FREE,
            "pro": cls.PRO,
            "elite": cls.ELITE,
        }
        return mapping.get(app_tier.lower(), cls.FREE)


def _load_registry() -> Dict[str, Any]:
    """Load and cache the registry JSON."""
    global _registry_data
    if _registry_data is not None:
        return _registry_data

    try:
        path = os.path.normpath(_REGISTRY_PATH)
        with open(path, "r") as f:
            _registry_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _registry_data = {"version": "0.0", "protocols": []}

    return _registry_data


def get_registry_version() -> str:
    """Get the registry version."""
    return _load_registry().get("version", "unknown")


def get_all_protocol_configs() -> List[Dict[str, Any]]:
    """Get all protocol configurations."""
    return _load_registry().get("protocols", [])


def get_protocol_config(protocol_id: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific protocol."""
    for proto in get_all_protocol_configs():
        if proto.get("protocolId") == protocol_id:
            return proto
    return None


def get_enabled_protocols(user_tier: str = "FREE") -> List[Dict[str, Any]]:
    """
    Get protocols enabled for a given user tier.

    Args:
        user_tier: Protocol tier (FREE, PRO, ELITE)

    Returns:
        List of protocol configs the user has access to
    """
    results = []
    for proto in get_all_protocol_configs():
        if not proto.get("enabled", False):
            continue
        required = proto.get("tier", "FREE")
        if ProtocolTier.has_access(user_tier, required):
            results.append(proto)
    return results


def get_protocol_names_for_tier(user_tier: str = "FREE") -> List[str]:
    """Get just the protocol IDs enabled for a tier."""
    return [p["protocolId"] for p in get_enabled_protocols(user_tier)]


def get_protocol_weights(user_tier: str = "FREE") -> Dict[str, float]:
    """
    Get risk weight overrides from registry for enabled protocols.

    Returns dict of protocol_id -> riskWeight.
    """
    weights = {}
    for proto in get_enabled_protocols(user_tier):
        w = proto.get("weights", {}).get("riskWeight")
        if w is not None:
            weights[proto["protocolId"]] = w
    return weights


def get_explain_template(
    protocol_id: str,
    user_style: str = "novice",
) -> Dict[str, str]:
    """
    Get explanation template for a protocol, adapted to user style.

    Args:
        protocol_id: Protocol identifier
        user_style: One of "risk_averse", "aggressive", "novice", "expert"

    Returns:
        Dict with "title" and "summary" keys
    """
    config = get_protocol_config(protocol_id)
    if not config:
        return {"title": protocol_id, "summary": ""}

    templates = config.get("explainTemplates", {})
    title = templates.get("title", config.get("name", protocol_id))

    # Get user-style summary, falling back to analyst summary
    user_summaries = templates.get("userSummary", {})
    summary = user_summaries.get(
        user_style,
        user_summaries.get("novice", templates.get("analystSummary", "")),
    )

    return {"title": title, "summary": summary}


def get_protocol_catalog() -> Dict[str, List[Dict[str, str]]]:
    """
    Get the full protocol catalog organized by category.

    Returns:
        Dict of category -> list of {id, name, tier, enabled}
    """
    catalog: Dict[str, List[Dict[str, str]]] = {}
    for proto in get_all_protocol_configs():
        cat = proto.get("category", "unknown")
        if cat not in catalog:
            catalog[cat] = []
        catalog[cat].append({
            "id": proto["protocolId"],
            "name": proto["name"],
            "tier": proto.get("tier", "FREE"),
            "enabled": str(proto.get("enabled", False)),
        })
    return catalog


def reload_registry() -> None:
    """Force reload of the registry from disk."""
    global _registry_data
    _registry_data = None
    _load_registry()
