"""
Tier configuration and feature gating for S18-C.
"""

TIER_FEATURES = {
    "GOOD": {
        "max_legs": 4,
        "max_protocols": 1,
        "suggestions": False,
        "live_data": False,
        "weather": False,
        "history": True,
        "analytics": False,
        "tier_name": "GOOD",
        "tier_label": "Free",
        "color": "gray"
    },
    "BETTER": {
        "max_legs": 6,
        "max_protocols": 3,
        "suggestions": True,
        "live_data": True,
        "weather": False,
        "history": True,
        "analytics": False,
        "tier_name": "BETTER",
        "tier_label": "$29/mo",
        "color": "blue"
    },
    "BEST": {
        "max_legs": 10,
        "max_protocols": 5,
        "suggestions": True,
        "live_data": True,
        "weather": True,
        "history": True,
        "analytics": True,
        "tier_name": "BEST",
        "tier_label": "$99/mo",
        "color": "gold"
    }
}


def get_tier_features(tier: str) -> dict:
    """Get feature set for a tier."""
    return TIER_FEATURES.get(tier, TIER_FEATURES["GOOD"])


def check_tier_limit(tier: str, feature: str, current_value: int) -> tuple[bool, str]:
    """
    Check if user has exceeded tier limit.
    
    Returns:
        (allowed: bool, error_message: str)
    """
    features = get_tier_features(tier)
    
    if feature == "legs":
        max_legs = features["max_legs"]
        if current_value > max_legs:
            return False, f"GOOD tier limited to {max_legs} legs. Upgrade to BETTER for more."
    
    elif feature == "protocols":
        max_protocols = features["max_protocols"]
        if current_value > max_protocols:
            return False, f"GOOD tier limited to {max_protocols} protocol. Upgrade to BETTER for multi-game parlays."
    
    return True, ""


def is_feature_enabled(tier: str, feature: str) -> bool:
    """Check if a feature is enabled for a tier."""
    features = get_tier_features(tier)
    return features.get(feature, False)
