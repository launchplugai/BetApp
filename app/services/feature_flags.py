"""
Feature Flags Service - S-PROT-4G

Capability gating for Good/Better/Best tiers.
No pricing exposed — just wiring the capability gates.

Layer: Service Layer
Used by: All routers for capability checks

Core Design Rule:
- Feature flags gate capabilities, not code paths
- Flags are tier-based, not individual features
- Pricing not exposed (future addition)
"""

from enum import Enum
from typing import Set, Dict, Any, Optional
from dataclasses import dataclass


class Tier(str, Enum):
    """Subscription tiers."""
    GOOD = "GOOD"
    BETTER = "BETTER"
    BEST = "BEST"


# =============================================================================
# Feature Definitions by Tier
# =============================================================================

GOOD_FEATURES: Set[str] = {
    # Core functionality
    "bet_builder",
    "protocol_creation",
    "basic_snapshots",
    "history_tracking",
    
    # Basic data
    "odds_data",
    "game_schedules",
    
    # Risk
    "basic_risk_profile",
    
    # Dashboard
    "dashboard_basic",
}

BETTER_FEATURES: Set[str] = {
    # Inherits all GOOD features
    *GOOD_FEATURES,
    
    # Enhanced snapshots
    "advanced_snapshots",
    "narrative_intelligence",
    "confidence_v3",
    
    # Edge detection
    "edge_feed",
    "injury_alerts",
    "line_movement_alerts",
    
    # Risk
    "advanced_risk_controls",
    "kelly_criterion",
    "correlation_detection",
    
    # Dashboard
    "dashboard_advanced",
    "real_time_updates",
}

BEST_FEATURES: Set[str] = {
    # Inherits all BETTER features
    *BETTER_FEATURES,
    
    # Full intelligence
    "fragility_scoring",
    "sentiment_analysis",
    "advanced_correlation",
    
    # Pro features
    "api_access",
    "custom_alerts",
    "export_data",
    "priority_support",
    
    # Dashboard
    "dashboard_pro",
    "custom_layouts",
    "advanced_analytics",
}


# Feature metadata (description, category)
FEATURE_METADATA: Dict[str, Dict[str, Any]] = {
    "bet_builder": {"category": "core", "description": "Build and evaluate bets"},
    "protocol_creation": {"category": "core", "description": "Create tracking protocols"},
    "basic_snapshots": {"category": "data", "description": "Basic game snapshots"},
    "history_tracking": {"category": "core", "description": "Track bet history"},
    "odds_data": {"category": "data", "description": "Access odds data"},
    "game_schedules": {"category": "data", "description": "View game schedules"},
    "basic_risk_profile": {"category": "risk", "description": "Basic risk settings"},
    "dashboard_basic": {"category": "ui", "description": "Basic dashboard"},
    
    "advanced_snapshots": {"category": "data", "description": "Advanced snapshot intelligence"},
    "narrative_intelligence": {"category": "intelligence", "description": "Narrative analysis"},
    "confidence_v3": {"category": "intelligence", "description": "Structured confidence scoring"},
    "edge_feed": {"category": "intelligence", "description": "Edge detection signals"},
    "injury_alerts": {"category": "alerts", "description": "Injury impact alerts"},
    "line_movement_alerts": {"category": "alerts", "description": "Line movement alerts"},
    "advanced_risk_controls": {"category": "risk", "description": "Advanced risk settings"},
    "kelly_criterion": {"category": "risk", "description": "Kelly criterion sizing"},
    "correlation_detection": {"category": "risk", "description": "Leg correlation detection"},
    "dashboard_advanced": {"category": "ui", "description": "Advanced dashboard"},
    "real_time_updates": {"category": "ui", "description": "Real-time data updates"},
    
    "fragility_scoring": {"category": "intelligence", "description": "Bet fragility analysis"},
    "sentiment_analysis": {"category": "intelligence", "description": "Market sentiment tracking"},
    "advanced_correlation": {"category": "risk", "description": "Advanced correlation models"},
    "api_access": {"category": "pro", "description": "API access"},
    "custom_alerts": {"category": "pro", "description": "Custom alert rules"},
    "export_data": {"category": "pro", "description": "Data export"},
    "priority_support": {"category": "pro", "description": "Priority support"},
    "dashboard_pro": {"category": "ui", "description": "Pro dashboard"},
    "custom_layouts": {"category": "ui", "description": "Custom dashboard layouts"},
    "advanced_analytics": {"category": "pro", "description": "Advanced analytics"},
}


class FeatureFlagsService:
    """
    Feature flags service for tier-based capability gating.
    
    Usage:
        service = get_feature_flags_service()
        if service.has_feature(user.tier, "edge_feed"):
            show_edge_feed()
    """
    
    def __init__(self):
        self._tier_features: Dict[Tier, Set[str]] = {
            Tier.GOOD: GOOD_FEATURES,
            Tier.BETTER: BETTER_FEATURES,
            Tier.BEST: BEST_FEATURES,
        }
    
    def has_feature(self, tier: str, feature: str) -> bool:
        """
        Check if a tier has access to a feature.
        
        Args:
            tier: GOOD|BETTER|BEST
            feature: Feature name
            
        Returns:
            True if tier has feature
        """
        try:
            tier_enum = Tier(tier.upper())
        except ValueError:
            # Unknown tier defaults to GOOD
            tier_enum = Tier.GOOD
        
        return feature in self._tier_features.get(tier_enum, GOOD_FEATURES)
    
    def get_features_for_tier(self, tier: str) -> Set[str]:
        """
        Get all features available to a tier.
        
        Args:
            tier: GOOD|BETTER|BEST
            
        Returns:
            Set of feature names
        """
        try:
            tier_enum = Tier(tier.upper())
        except ValueError:
            tier_enum = Tier.GOOD
        
        return self._tier_features.get(tier_enum, GOOD_FEATURES).copy()
    
    def get_feature_metadata(self, feature: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a feature."""
        return FEATURE_METADATA.get(feature)
    
    def get_features_by_category(self, tier: str, category: str) -> Set[str]:
        """
        Get features in a category for a tier.
        
        Args:
            tier: GOOD|BETTER|BEST
            category: core|data|risk|intelligence|alerts|ui|pro
        """
        features = self.get_features_for_tier(tier)
        return {
            f for f in features
            if FEATURE_METADATA.get(f, {}).get("category") == category
        }
    
    def check_requirement(
        self,
        user_tier: str,
        required_tier: str,
        allow_higher: bool = True
    ) -> bool:
        """
        Check if user tier meets requirement.
        
        Args:
            user_tier: User's current tier
            required_tier: Minimum tier required
            allow_higher: If True, higher tiers also pass
            
        Returns:
            True if requirement met
        """
        tier_order = {Tier.GOOD: 1, Tier.BETTER: 2, Tier.BEST: 3}
        
        try:
            user_level = tier_order.get(Tier(user_tier.upper()), 1)
            required_level = tier_order.get(Tier(required_tier.upper()), 1)
        except ValueError:
            return False
        
        if allow_higher:
            return user_level >= required_level
        else:
            return user_level == required_level
    
    def get_upgrade_path(self, current_tier: str) -> Dict[str, Any]:
        """
        Get upgrade information for a tier.
        
        Returns features that would be unlocked by upgrading.
        No pricing information (future addition).
        """
        tier_order = [Tier.GOOD, Tier.BETTER, Tier.BEST]
        
        try:
            current = Tier(current_tier.upper())
        except ValueError:
            current = Tier.GOOD
        
        current_idx = tier_order.index(current)
        
        if current_idx >= len(tier_order) - 1:
            return {
                "current_tier": current_tier,
                "has_upgrade": False,
                "next_tier": None,
                "unlocked_features": []
            }
        
        next_tier = tier_order[current_idx + 1]
        current_features = self._tier_features[current]
        next_features = self._tier_features[next_tier]
        
        unlocked = next_features - current_features
        
        return {
            "current_tier": current_tier,
            "has_upgrade": True,
            "next_tier": next_tier.value,
            "unlocked_features": sorted(unlocked),
            "feature_count": {
                "current": len(current_features),
                "next": len(next_features),
                "new": len(unlocked)
            }
        }


# Singleton instance
_flags_service: Optional[FeatureFlagsService] = None


def get_feature_flags_service() -> FeatureFlagsService:
    """Get or create the feature flags service singleton."""
    global _flags_service
    if _flags_service is None:
        _flags_service = FeatureFlagsService()
    return _flags_service


# =============================================================================
# Convenience Functions
# =============================================================================

def has_feature(tier: str, feature: str) -> bool:
    """Check if tier has feature."""
    return get_feature_flags_service().has_feature(tier, feature)


def require_feature(tier: str, feature: str) -> None:
    """
    Require a feature, raise if not available.
    
    Raises:
        PermissionError: If feature not available
    """
    if not has_feature(tier, feature):
        raise PermissionError(
            f"Feature '{feature}' not available in tier '{tier}'"
        )
