"""
S-INT-3: Controlled Activation Layer

Beta-weighted integration of incentive intelligence into projections.
Caps, weights, and backtest receipts for controlled rollout.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from app.intelligence import IncentiveIntelligence
from app.sherlock.audit import IncentiveAudit, Claim, ClaimStatus


class ActivationWeight(str, Enum):
    """Beta rollout weights for incentive integration."""
    OFF = "off"           # 0% - no impact
    MINIMAL = "minimal"   # 10% - observation mode
    LOW = "low"           # 25% - conservative
    MEDIUM = "medium"     # 50% - balanced
    HIGH = "high"         # 75% - aggressive
    FULL = "full"         # 100% - complete integration


@dataclass(frozen=True)
class ProjectionAdjustment:
    """
    Single projection adjustment from incentive signal.
    Immutable. Magnitude capped at weight limit.
    """
    signal_source: str          # Which claim triggered this
    original_value: float
    adjusted_value: float
    adjustment_pct: float       # Percentage change (capped)
    confidence: float           # Claim confidence that triggered
    weight_applied: float       # Actual weight used
    rationale: str
    
    def __post_init__(self):
        """Validate adjustment bounds."""
        object.__setattr__(self, 'adjustment_pct', 
            round(max(-0.5, min(0.5, self.adjustment_pct)), 4))
        object.__setattr__(self, 'confidence',
            round(max(0.0, min(1.0, self.confidence)), 4))


@dataclass(frozen=True)
class ActivationResult:
    """
    Complete activation result with all adjustments.
    Includes backtest receipt for tracking.
    """
    intelligence: IncentiveIntelligence
    audit: IncentiveAudit
    weight_tier: ActivationWeight
    max_adjustment_pct: float
    adjustments: List[ProjectionAdjustment] = field(default_factory=list)
    activation_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    receipt_id: str = field(default_factory=lambda: f"ACT-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize activation result."""
        return {
            "receipt_id": self.receipt_id,
            "timestamp": self.activation_timestamp,
            "weight_tier": self.weight_tier.value,
            "max_adjustment_pct": self.max_adjustment_pct,
            "adjustment_count": len(self.adjustments),
            "adjustments": [
                {
                    "signal_source": adj.signal_source,
                    "original": adj.original_value,
                    "adjusted": adj.adjusted_value,
                    "adjustment_pct": adj.adjustment_pct,
                    "confidence": adj.confidence,
                    "weight": adj.weight_applied,
                    "rationale": adj.rationale
                }
                for adj in self.adjustments
            ],
            "audit_summary": {
                "claim_count": len(self.audit.claims),
                "actionable_claims": sum(1 for c in self.audit.claims if c.recommended_action)
            }
        }
    
    def has_adjustments(self) -> bool:
        """True if any adjustments were applied."""
        return len(self.adjustments) > 0
    
    def total_impact(self) -> float:
        """Sum of absolute adjustment percentages."""
        return sum(abs(adj.adjustment_pct) for adj in self.adjustments)


# Weight tier configuration
WEIGHT_CONFIG: Dict[ActivationWeight, Dict[str, Any]] = {
    ActivationWeight.OFF: {
        "max_adjustment_pct": 0.0,
        "min_confidence_threshold": 1.0,  # Never triggers
        "description": "No incentive integration"
    },
    ActivationWeight.MINIMAL: {
        "max_adjustment_pct": 0.02,  # 2% max
        "min_confidence_threshold": 0.8,
        "description": "Observation mode - minimal impact"
    },
    ActivationWeight.LOW: {
        "max_adjustment_pct": 0.05,  # 5% max
        "min_confidence_threshold": 0.7,
        "description": "Conservative adjustments"
    },
    ActivationWeight.MEDIUM: {
        "max_adjustment_pct": 0.10,  # 10% max
        "min_confidence_threshold": 0.6,
        "description": "Balanced integration"
    },
    ActivationWeight.HIGH: {
        "max_adjustment_pct": 0.20,  # 20% max
        "min_confidence_threshold": 0.5,
        "description": "Aggressive integration"
    },
    ActivationWeight.FULL: {
        "max_adjustment_pct": 0.50,  # 50% max (safety cap)
        "min_confidence_threshold": 0.4,
        "description": "Full integration with safety limits"
    }
}


def get_weight_config(weight: ActivationWeight) -> Dict[str, Any]:
    """Get configuration for weight tier."""
    return WEIGHT_CONFIG.get(weight, WEIGHT_CONFIG[ActivationWeight.OFF])
