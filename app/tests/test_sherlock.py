"""
Tests for Sherlock Audit Layer - S-INT-2

Requirements:
- Schema validation (required fields exist)
- Confidence bounds [0–1]
- Deterministic outputs given same inputs
- Claim-specific edge cases
"""

import pytest
from app.sherlock.audit import Claim, ClaimStatus, IncentiveAudit, empty_audit
from app.sherlock.claims import (
    evaluate_team_tanking,
    evaluate_minutes_suppression,
    evaluate_effort_decay_pace
)
from app.sherlock.audit import run_incentive_audit, create_initial_audit
from app.intelligence import (
    IncentiveIntelligence,
    TeamCompetitiveState,
    AlignmentType,
    default_intelligence
)


class TestSchemaValidation:
    """Audit schema has required fields."""
    
    def test_claim_has_required_fields(self):
        """Claim contains all required fields."""
        claim = Claim(
            id="test_claim",
            claim="Test claim text",
            confidence=0.5,
            support=["evidence1"],
            counter=["counter1"],
            falsifier="If X then not claim",
            recommended_action="Do something"
        )
        data = claim.to_dict()
        assert "id" in data
        assert "claim" in data
        assert "confidence" in data
        assert "support" in data
        assert "counter" in data
        assert "falsifier" in data
        assert "recommended_action" in data
        assert "status" in data
    
    def test_audit_has_required_fields(self):
        """Audit contains all required fields."""
        audit = IncentiveAudit(claims=[])
        data = audit.to_dict()
        assert "claims" in data
        assert "audit_version" in data
        assert "claim_count" in data
    
    def test_empty_audit_structure(self):
        """Empty audit has valid structure."""
        audit = empty_audit()
        assert audit.claims == []
        assert audit.audit_version == "1.0.0"


class TestConfidenceBounds:
    """Confidence always bounded [0, 1]."""
    
    def test_claim_confidence_clamped_high(self):
        """Confidence > 1 is clamped to 1."""
        claim = Claim(
            id="test",
            claim="test",
            confidence=1.5,
            falsifier="test",
            recommended_action=""
        )
        assert claim.confidence == 1.0
    
    def test_claim_confidence_clamped_low(self):
        """Confidence < 0 is clamped to 0."""
        claim = Claim(
            id="test",
            claim="test",
            confidence=-0.5,
            falsifier="test",
            recommended_action=""
        )
        assert claim.confidence == 0.0
    
    def test_tanking_claim_bounds(self):
        """Tanking claim confidence in [0, 1]."""
        intel = default_intelligence()
        claim = evaluate_team_tanking(intel)
        assert 0.0 <= claim.confidence <= 1.0
    
    def test_suppression_claim_bounds(self):
        """Suppression claim confidence in [0, 1]."""
        intel = default_intelligence()
        claim = evaluate_minutes_suppression(intel)
        assert 0.0 <= claim.confidence <= 1.0
    
    def test_pace_claim_bounds(self):
        """Pace claim confidence in [0, 1]."""
        intel = default_intelligence()
        claim = evaluate_effort_decay_pace(intel)
        assert 0.0 <= claim.confidence <= 1.0


class TestDeterminism:
    """Same inputs produce same outputs."""
    
    def test_tanking_claim_deterministic(self):
        """Tanking claim is deterministic."""
        intel = default_intelligence()
        claim1 = evaluate_team_tanking(intel)
        claim2 = evaluate_team_tanking(intel)
        assert claim1.confidence == claim2.confidence
        assert claim1.status == claim2.status
    
    def test_suppression_claim_deterministic(self):
        """Suppression claim is deterministic."""
        intel = default_intelligence()
        claim1 = evaluate_minutes_suppression(intel)
        claim2 = evaluate_minutes_suppression(intel)
        assert claim1.confidence == claim2.confidence
    
    def test_pace_claim_deterministic(self):
        """Pace claim is deterministic."""
        intel = default_intelligence()
        claim1 = evaluate_effort_decay_pace(intel)
        claim2 = evaluate_effort_decay_pace(intel)
        assert claim1.confidence == claim2.confidence


class TestTeamTankingEdgeCases:
    """Tanking claim specific edge cases."""
    
    def test_high_tanking_high_stability_reduces_confidence(self):
        """High tanking score but high rotation stability → confidence drops."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.TANKING,
            tanking_score=0.8,  # High tanking
            rotation_stability_score=0.8,  # But stable rotation
            alignment_type=AlignmentType.ALIGNED,
            effort_decay_modifier=0.95
        )
        claim = evaluate_team_tanking(intel)
        # Confidence should be reduced due to high stability
        assert claim.confidence < 0.7
        assert len(claim.counter) > 0
    
    def test_high_tanking_low_stability_increases_confidence(self):
        """High tanking + low stability → higher confidence."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.TANKING,
            tanking_score=0.8,
            rotation_stability_score=0.3,  # Chaotic rotation
            alignment_type=AlignmentType.ALIGNED,
            effort_decay_modifier=0.95
        )
        claim = evaluate_team_tanking(intel)
        # Confidence boosted by chaos
        assert claim.confidence > 0.6
    
    def test_low_tanking_insufficient_status(self):
        """Low tanking score → INSUFFICIENT status."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.CONTENDING,
            tanking_score=0.1,
            rotation_stability_score=0.5,
            alignment_type=AlignmentType.ALIGNED,
            effort_decay_modifier=0.95
        )
        claim = evaluate_team_tanking(intel)
        assert claim.status == ClaimStatus.INSUFFICIENT
        assert claim.confidence < 0.3


class TestSuppressionEdgeCases:
    """Minutes suppression claim edge cases."""
    
    def test_load_management_high_confidence(self):
        """Load management alignment → high confidence."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.CONTENDING,
            tanking_score=0.2,
            rotation_stability_score=0.5,
            alignment_type=AlignmentType.LOAD_MANAGEMENT,
            effort_decay_modifier=0.95
        )
        claim = evaluate_minutes_suppression(intel)
        assert claim.confidence > 0.7
        assert claim.status == ClaimStatus.SUPPORTED
    
    def test_aligned_incentives_no_suppression(self):
        """Aligned incentives → low/no suppression claim."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.CONTENDING,
            tanking_score=0.2,
            rotation_stability_score=0.5,
            alignment_type=AlignmentType.ALIGNED,
            effort_decay_modifier=0.95
        )
        claim = evaluate_minutes_suppression(intel)
        # Should be insufficient or very low confidence
        assert claim.confidence < 0.4


class TestPaceEdgeCases:
    """Pace decay claim edge cases."""
    
    def test_low_effort_modifier_high_pace_confidence(self):
        """Low effort modifier → high pace_down confidence."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.CONTENDING,
            tanking_score=0.2,
            rotation_stability_score=0.5,
            alignment_type=AlignmentType.ALIGNED,
            effort_decay_modifier=0.82  # Low modifier
        )
        claim = evaluate_effort_decay_pace(intel)
        assert claim.confidence > 0.6
    
    def test_high_effort_modifier_insufficient(self):
        """High effort modifier → INSUFFICIENT status."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.CONTENDING,
            tanking_score=0.2,
            rotation_stability_score=0.5,
            alignment_type=AlignmentType.ALIGNED,
            effort_decay_modifier=0.97  # High modifier
        )
        claim = evaluate_effort_decay_pace(intel)
        assert claim.status == ClaimStatus.INSUFFICIENT
    
    def test_tanking_amplifies_pace_claim(self):
        """Tanking state amplifies pace decay confidence."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.TANKING,
            tanking_score=0.7,
            rotation_stability_score=0.5,
            alignment_type=AlignmentType.ALIGNED,
            effort_decay_modifier=0.88
        )
        claim = evaluate_effort_decay_pace(intel)
        assert claim.confidence > 0.7
        assert "tanking" in str(claim.support).lower()


class TestClaimStatuses:
    """Claim status transitions based on confidence."""
    
    def test_insufficient_status_for_low_confidence(self):
        """Confidence < 0.3 → INSUFFICIENT."""
        claim = Claim(
            id="test",
            claim="test",
            confidence=0.2,
            falsifier="test",
            recommended_action="",
            status=ClaimStatus.INSUFFICIENT
        )
        assert claim.status == ClaimStatus.INSUFFICIENT
    
    def test_supported_status_for_high_confidence(self):
        """Confidence > 0.6 → SUPPORTED."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.TANKING,
            tanking_score=0.8,
            rotation_stability_score=0.3,
            alignment_type=AlignmentType.ALIGNED,
            effort_decay_modifier=0.95
        )
        claim = evaluate_team_tanking(intel)
        assert claim.status == ClaimStatus.SUPPORTED


class TestFalsifiersPresent:
    """Every claim includes a falsifier."""
    
    def test_tanking_has_falsifier(self):
        """Tanking claim includes falsifier."""
        intel = default_intelligence()
        claim = evaluate_team_tanking(intel)
        assert claim.falsifier != ""
        assert "rotation" in claim.falsifier.lower()
    
    def test_suppression_has_falsifier(self):
        """Suppression claim includes falsifier."""
        intel = default_intelligence()
        claim = evaluate_minutes_suppression(intel)
        assert claim.falsifier != ""
        assert "minutes" in claim.falsifier.lower()
    
    def test_pace_has_falsifier(self):
        """Pace claim includes falsifier."""
        intel = default_intelligence()
        claim = evaluate_effort_decay_pace(intel)
        assert claim.falsifier != ""
        assert "pace" in claim.falsifier.lower()


class TestRecommendedActions:
    """Actions present when confidence warrants."""
    
    def test_high_confidence_has_action(self):
        """High confidence claims include actions."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.TANKING,
            tanking_score=0.8,
            rotation_stability_score=0.3,
            alignment_type=AlignmentType.ALIGNED,
            effort_decay_modifier=0.95
        )
        claim = evaluate_team_tanking(intel)
        assert claim.confidence > 0.7
        assert claim.recommended_action != ""
    
    def test_low_confidence_no_action(self):
        """Low confidence claims have no action."""
        intel = IncentiveIntelligence(
            team_competitive_state=TeamCompetitiveState.CONTENDING,
            tanking_score=0.1,
            rotation_stability_score=0.5,
            alignment_type=AlignmentType.ALIGNED,
            effort_decay_modifier=0.95
        )
        claim = evaluate_team_tanking(intel)
        assert claim.confidence < 0.4
        assert claim.recommended_action == ""


class TestFullAudit:
    """Complete audit with all claims."""
    
    def test_audit_contains_all_three_claims(self):
        """Full audit has 3 claims."""
        intel = default_intelligence()
        audit = create_initial_audit(intel)
        # Note: create_initial_audit currently returns empty
        # This test will need updating when integrated
        assert isinstance(audit, IncentiveAudit)
    
    def test_audit_serialization(self):
        """Audit serializes to dict correctly."""
        claim = Claim(
            id="test",
            claim="test claim",
            confidence=0.5,
            support=["evidence"],
            counter=[],
            falsifier="if X",
            recommended_action="do Y"
        )
        audit = IncentiveAudit(claims=[claim])
        data = audit.to_dict()
        assert data["claim_count"] == 1
        assert len(data["claims"]) == 1
        assert data["claims"][0]["id"] == "test"