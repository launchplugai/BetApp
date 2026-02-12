"""
Tests for Activation Layer - S-INT-3

Controlled integration of incentive intelligence into projections.
Tests confidence bounds, weight limits, caps, and backtest receipts.
"""

import pytest
from app.activation import (
    ActivationWeight,
    ActivationResult,
    ProjectionAdjustment,
    get_weight_config
)
from app.activation.engine import (
    activate_intelligence,
    get_current_weight,
    parse_weight,
    apply_claim_adjustment,
    _get_affected_stats
)
from app.sherlock.audit import empty_audit, IncentiveAudit, Claim, ClaimStatus
from app.intelligence import IncentiveIntelligence, default_intelligence


class TestWeightConfiguration:
    """Weight tiers have correct configuration."""
    
    def test_weight_config_structure(self):
        """Each weight tier has required config fields."""
        for weight in ActivationWeight:
            config = get_weight_config(weight)
            assert "max_adjustment_pct" in config
            assert "min_confidence_threshold" in config
            assert "description" in config
            assert config["max_adjustment_pct"] >= 0.0
    
    def test_weight_tier_progression(self):
        """Higher tiers have higher adjustment limits."""
        tiers = [
            ActivationWeight.OFF,
            ActivationWeight.MINIMAL,
            ActivationWeight.LOW,
            ActivationWeight.MEDIUM,
            ActivationWeight.HIGH,
            ActivationWeight.FULL
        ]
        prev_max = -1.0
        for tier in tiers:
            max_adj = get_weight_config(tier)["max_adjustment_pct"]
            assert max_adj >= prev_max
            prev_max = max_adj
    
    def test_off_weight_zero_impact(self):
        """OFF tier has zero adjustment capability."""
        config = get_weight_config(ActivationWeight.OFF)
        assert config["max_adjustment_pct"] == 0.0
    
    def test_parse_weight_valid(self):
        """Parse valid weight strings."""
        assert parse_weight("off") == ActivationWeight.OFF
        assert parse_weight("minimal") == ActivationWeight.MINIMAL
        assert parse_weight("low") == ActivationWeight.LOW
        assert parse_weight("medium") == ActivationWeight.MEDIUM
        assert parse_weight("high") == ActivationWeight.HIGH
        assert parse_weight("full") == ActivationWeight.FULL
    
    def test_parse_weight_invalid_defaults_off(self):
        """Invalid weight strings default to OFF."""
        assert parse_weight("unknown") == ActivationWeight.OFF
        assert parse_weight("") == ActivationWeight.OFF


class TestProjectionAdjustment:
    """Projection adjustments are bounded and tracked."""
    
    def test_adjustment_bounds_enforced(self):
        """Adjustment percentage capped at [-50%, +50%]."""
        adj = ProjectionAdjustment(
            signal_source="test",
            original_value=100.0,
            adjusted_value=200.0,  # Would be +100%
            adjustment_pct=1.0,  # Exceeds limit
            confidence=0.8,
            weight_applied=0.5,
            rationale="test"
        )
        assert adj.adjustment_pct <= 0.5
    
    def test_adjustment_negative_bounds(self):
        """Negative adjustments also bounded."""
        adj = ProjectionAdjustment(
            signal_source="test",
            original_value=100.0,
            adjusted_value=0.0,
            adjustment_pct=-0.8,  # Exceeds -50% limit
            confidence=0.8,
            weight_applied=0.5,
            rationale="test"
        )
        assert adj.adjustment_pct >= -0.5


class TestActivationResult:
    """Activation results track all adjustments."""
    
    def test_empty_result_has_no_adjustments(self):
        """Result with no claims has empty adjustments."""
        intel = default_intelligence()
        audit = empty_audit()
        result = ActivationResult(
            intelligence=intel,
            audit=audit,
            weight_tier=ActivationWeight.OFF,
            max_adjustment_pct=0.0,
            adjustments=[]
        )
        assert not result.has_adjustments()
        assert result.total_impact() == 0.0
    
    def test_result_serialization(self):
        """Result serializes to dict with all fields."""
        intel = default_intelligence()
        audit = empty_audit()
        result = ActivationResult(
            intelligence=intel,
            audit=audit,
            weight_tier=ActivationWeight.MEDIUM,
            max_adjustment_pct=0.10,
            adjustments=[]
        )
        data = result.to_dict()
        assert "receipt_id" in data
        assert "timestamp" in data
        assert "weight_tier" in data
        assert "adjustment_count" in data
        assert "audit_summary" in data


class TestClaimToStatsMapping:
    """Claims map to correct stat categories."""
    
    def test_tanking_affects_core_stats(self):
        """Tanking claim affects pts, reb, ast, etc."""
        stats = _get_affected_stats("team_tanking")
        assert "pts" in stats
        assert "win_prob" in stats
    
    def test_suppression_affects_minutes(self):
        """Minutes suppression affects minutes and counting stats."""
        stats = _get_affected_stats("minutes_suppression_risk")
        assert "minutes" in stats
        assert "pts" in stats
        assert "ast" in stats
    
    def test_pace_affects_pace_stats(self):
        """Pace down affects pace-dependent stats."""
        stats = _get_affected_stats("effort_decay_pace_down")
        assert "pace" in stats
        assert "possessions" in stats


class TestApplyClaimAdjustment:
    """Individual claim adjustments respect weights."""
    
    def test_claim_below_threshold_returns_none(self):
        """Claim with confidence below threshold returns no adjustment."""
        claim = Claim(
            id="team_tanking",
            claim="Team is tanking",
            confidence=0.3,  # Below typical threshold
            falsifier="test",
            recommended_action="reduce projections"
        )
        config = get_weight_config(ActivationWeight.LOW)
        result = apply_claim_adjustment(claim, 100.0, config)
        assert result is None
    
    def test_claim_without_action_returns_none(self):
        """Claim with no recommended action returns no adjustment."""
        claim = Claim(
            id="team_tanking",
            claim="Team is tanking",
            confidence=0.9,
            falsifier="test",
            recommended_action=""  # No action
        )
        config = get_weight_config(ActivationWeight.MEDIUM)
        result = apply_claim_adjustment(claim, 100.0, config)
        assert result is None
    
    def test_tanking_claim_reduces_projection(self):
        """Tanking claim reduces projection (negative adjustment)."""
        claim = Claim(
            id="team_tanking",
            claim="Team is tanking",
            confidence=0.9,
            falsifier="test",
            recommended_action="reduce projections"
        )
        config = get_weight_config(ActivationWeight.MEDIUM)
        result = apply_claim_adjustment(claim, 100.0, config)
        assert result is not None
        assert result.adjustment_pct < 0
    
    def test_adjustment_respects_weight_cap(self):
        """Adjustment never exceeds weight tier max."""
        claim = Claim(
            id="team_tanking",
            claim="Team is tanking",
            confidence=1.0,  # Maximum confidence
            falsifier="test",
            recommended_action="reduce projections"
        )
        config = get_weight_config(ActivationWeight.MINIMAL)
        result = apply_claim_adjustment(claim, 100.0, config)
        assert result is not None
        abs_adj = abs(result.adjustment_pct)
        assert abs_adj <= config["max_adjustment_pct"]


class TestActivateIntelligence:
    """Full activation flow with claims."""
    
    def test_off_weight_returns_empty(self):
        """OFF weight tier returns no adjustments."""
        intel = default_intelligence()
        audit = empty_audit()
        projections = {"pts": 100.0, "reb": 50.0}
        result = activate_intelligence(
            intel, audit, projections, weight=ActivationWeight.OFF
        )
        assert not result.has_adjustments()
    
    def test_with_claims_produces_adjustments(self):
        """Audit with claims produces adjustments at non-zero weight."""
        intel = IncentiveIntelligence(
            team_competitive_state="tanking",
            tanking_score=0.8,
            rotation_stability_score=0.3,
            alignment_type="aligned",
            effort_decay_modifier=0.95
        )
        # Create audit with tanking claim
        from app.sherlock.claims import evaluate_team_tanking
        claim = evaluate_team_tanking(intel)
        audit = IncentiveAudit(claims=[claim])
        projections = {"pts": 100.0, "win_prob": 0.5}
        result = activate_intelligence(
            intel, audit, projections, weight=ActivationWeight.MEDIUM
        )
        # Should have adjustments for pts and win_prob
        assert result.has_adjustments()
        for adj in result.adjustments:
            assert adj.signal_source == "team_tanking"


class TestDeterminism:
    """Activation is deterministic given same inputs."""
    
    def test_same_inputs_same_outputs(self):
        """Same inputs produce identical adjustments."""
        intel = default_intelligence()
        audit = empty_audit()
        projections = {"pts": 100.0}
        result1 = activate_intelligence(
            intel, audit, projections, weight=ActivationWeight.LOW
        )
        result2 = activate_intelligence(
            intel, audit, projections, weight=ActivationWeight.LOW
        )
        assert result1.weight_tier == result2.weight_tier
        assert result1.max_adjustment_pct == result2.max_adjustment_pct
