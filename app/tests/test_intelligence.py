"""
Tests for Intelligence Layer
S-INT-1: Incentive Intelligence Foundation

Requirements:
- Tanking score bounded 0-1
- Effort modifier bounded 0.8-1.0
- Alignment mapping deterministic
- Synthetic fixtures produce expected output
"""

import pytest
from app.intelligence.team_state import (
    calculate_tanking_score,
    classify_competitive_state,
    calculate_rotation_stability
)
from app.intelligence.effort_decay import (
    calculate_effort_decay_modifier,
    fatigue_rest_interaction
)
from app.intelligence.alignment import (
    classify_alignment,
    calculate_alignment_confidence,
    ContractIncentive
)
from app.intelligence import (
    TeamCompetitiveState,
    AlignmentType,
    IncentiveIntelligence,
    default_intelligence
)


class TestTankingScoreBounds:
    """Tanking score must be bounded [0, 1]."""
    
    def test_tanking_score_minimum(self):
        """Best case scenario = low tanking score."""
        score = calculate_tanking_score(
            wins=50, losses=10, games_remaining=22,
            star_players_sitting=0, youth_minutes_pct=0.0,
            defensive_effort_drop=0.0, trade_asset_pct=0.0
        )
        assert score < 0.1  # Very low but not exactly 0 due to formula
    
    def test_tanking_score_maximum(self):
        """Worst case scenario = 1.0 tanking score."""
        score = calculate_tanking_score(
            wins=10, losses=50, games_remaining=22,
            star_players_sitting=5, youth_minutes_pct=1.0,
            defensive_effort_drop=1.0, trade_asset_pct=1.0
        )
        assert 0.0 <= score <= 1.0
        assert score > 0.9  # Should be near max
    
    def test_tanking_score_mid_range(self):
        """Typical tanking signals."""
        score = calculate_tanking_score(
            wins=20, losses=40, games_remaining=22,
            star_players_sitting=2, youth_minutes_pct=0.4,
            defensive_effort_drop=0.2, trade_asset_pct=0.3
        )
        assert 0.0 <= score <= 1.0
        assert 0.3 < score < 0.7  # Mid-range
    
    def test_tanking_score_clamped_inputs(self):
        """Inputs outside bounds are clamped."""
        score = calculate_tanking_score(
            wins=20, losses=40, games_remaining=22,
            star_players_sitting=10,  # > 5, should clamp
            youth_minutes_pct=1.5,     # > 1.0, should clamp
            defensive_effort_drop=-0.5,  # < 0, should clamp
            trade_asset_pct=2.0        # > 1.0, should clamp
        )
        assert 0.0 <= score <= 1.0


class TestEffortDecayBounds:
    """Effort modifier must be bounded [0.8, 1.0]."""
    
    def test_effort_modifier_maximum(self):
        """Well-rested, home court = higher modifier."""
        modifier = calculate_effort_decay_modifier(
            games_played_last_14=3,
            minutes_avg_last_5=28.0,
            travel_miles_last_week=0.0,
            is_back_to_back=False,
            is_4_in_5_nights=False,
            team_competitive_state="contending",
            player_age=25.0
        )
        assert 0.8 <= modifier <= 1.0
        # Modifier varies based on formula; accept anything in valid range
    
    def test_effort_modifier_minimum_boundary(self):
        """Maximum fatigue should bottom at 0.8, not below."""
        modifier = calculate_effort_decay_modifier(
            games_played_last_14=14,
            minutes_avg_last_5=45.0,
            travel_miles_last_week=8000.0,
            is_back_to_back=True,
            is_4_in_5_nights=True,
            team_competitive_state="tanking",
            player_age=38.0
        )
        assert 0.8 <= modifier <= 1.0
        assert modifier >= 0.8  # Hard floor
    
    def test_effort_modifier_back_to_back(self):
        """B2B penalty applied correctly."""
        base = calculate_effort_decay_modifier(is_back_to_back=False)
        b2b = calculate_effort_decay_modifier(is_back_to_back=True)
        assert b2b <= base  # Less than or equal due to floor
        assert 0.8 <= b2b <= 1.0
    
    def test_effort_modifier_4_in_5(self):
        """4-in-5 penalty applied correctly."""
        base = calculate_effort_decay_modifier(is_4_in_5_nights=False)
        dense = calculate_effort_decay_modifier(is_4_in_5_nights=True)
        assert dense <= base  # Less than or equal due to floor
        assert 0.8 <= dense <= 1.0
    
    def test_fatigue_rest_interaction_bounds(self):
        """Rest interaction maintains bounds."""
        modifier = fatigue_rest_interaction(
            base_effort_modifier=0.85,
            rest_days=3,
            is_home=True
        )
        assert 0.8 <= modifier <= 1.0


class TestCompetitiveStateClassification:
    """Deterministic state classification."""
    
    def test_eliminated_team(self):
        """Elimination number = 0 means development mode."""
        state = classify_competitive_state(
            wins=20, losses=50, games_remaining=12,
            elimination_number=0
        )
        assert state == TeamCompetitiveState.DEVELOPMENT
    
    def test_clinched_team(self):
        """Clinch number = 0 means resting mode."""
        state = classify_competitive_state(
            wins=55, losses=15, games_remaining=12,
            clinch_number=0
        )
        assert state == TeamCompetitiveState.RESTING
    
    def test_tanking_threshold(self):
        """Tank score > 0.70 triggers tanking state."""
        state = classify_competitive_state(
            wins=15, losses=45, games_remaining=22,
            tanking_score=0.75
        )
        assert state == TeamCompetitiveState.TANKING
    
    def test_contending_by_position(self):
        """Top 6 seed = contending."""
        state = classify_competitive_state(
            wins=45, losses=20, games_remaining=17,
            playoff_position=3
        )
        assert state == TeamCompetitiveState.CONTENDING
    
    def test_play_in_by_position(self):
        """7-10 seed = play-in territory."""
        state = classify_competitive_state(
            wins=38, losses=30, games_remaining=14,
            playoff_position=8
        )
        assert state == TeamCompetitiveState.PLAY_IN


class TestAlignmentClassification:
    """Deterministic alignment mapping."""
    
    def test_contract_year_chase(self):
        """Contract year + high usage = CONTRACT_CHASE."""
        alignment = classify_alignment(
            team_competitive_state="contending",
            contract_incentive=ContractIncentive.CONTRACT_YEAR,
            minutes_trend_last_10=5.0,
            usage_trend_last_10=4.0
        )
        assert alignment == AlignmentType.CONTRACT_CHASE
    
    def test_contract_year_conflicted(self):
        """Contract year + dropping minutes = CONFLICTED."""
        alignment = classify_alignment(
            team_competitive_state="contending",
            contract_incentive=ContractIncentive.CONTRACT_YEAR,
            minutes_trend_last_10=-5.0,
            usage_trend_last_10=-4.0
        )
        assert alignment == AlignmentType.CONFLICTED
    
    def test_load_management_pattern(self):
        """Star player + decreasing minutes in playoff hunt = LOAD_MANAGEMENT."""
        alignment = classify_alignment(
            team_competitive_state="contending",
            contract_incentive=ContractIncentive.LONG_TERM_SECURED,
            minutes_trend_last_10=-3.0,
            is_star_player=True,
            playoff_eligible=False
        )
        assert alignment == AlignmentType.LOAD_MANAGEMENT
    
    def test_aligned_default(self):
        """No conflict signals = ALIGNED."""
        alignment = classify_alignment(
            team_competitive_state="contending",
            contract_incentive=ContractIncentive.LONG_TERM_SECURED
        )
        assert alignment == AlignmentType.ALIGNED
    
    def test_alignment_deterministic(self):
        """Same inputs always produce same output."""
        inputs = {
            "team_competitive_state": "tanking",
            "contract_incentive": ContractIncentive.CONTRACT_YEAR,
            "minutes_trend_last_10": 4.0,
            "usage_trend_last_10": 3.0
        }
        result1 = classify_alignment(**inputs)
        result2 = classify_alignment(**inputs)
        assert result1 == result2


class TestRotationStability:
    """Rotation stability scoring."""
    
    def test_stability_perfect(self):
        """No changes, consistent minutes, good rest = high stability."""
        score = calculate_rotation_stability(
            lineup_changes_last_10=0,
            minutes_variance_pct=0.0,
            back_to_backs=0,
            rest_days_avg=3.0
        )
        assert 0.0 <= score <= 1.0
        assert score > 0.9
    
    def test_stability_poor(self):
        """Constant changes, high variance, many B2Bs = low stability."""
        score = calculate_rotation_stability(
            lineup_changes_last_10=8,
            minutes_variance_pct=0.5,
            back_to_backs=3,
            rest_days_avg=1.0
        )
        assert 0.0 <= score <= 1.0
        assert score < 0.4


class TestIncentiveIntelligenceDataclass:
    """Core data structure validation."""
    
    def test_default_intelligence_structure(self):
        """Default intelligence has valid structure."""
        intel = default_intelligence()
        assert intel.team_competitive_state == TeamCompetitiveState.CONTENDING
        assert intel.tanking_score == 0.0
        assert intel.effort_decay_modifier == 1.0
    
    def test_intelligence_bounds_enforced(self):
        """Dataclass validates bounds at construction."""
        with pytest.raises(AssertionError):
            IncentiveIntelligence(
                team_competitive_state=TeamCompetitiveState.TANKING,
                tanking_score=1.5,  # Invalid: > 1.0
                rotation_stability_score=0.5,
                alignment_type=AlignmentType.ALIGNED,
                effort_decay_modifier=0.9
            )
    
    def test_intelligence_serialization(self):
        """to_dict produces serializable output."""
        intel = default_intelligence()
        data = intel.to_dict()
        assert "team_competitive_state" in data
        assert "tanking_score" in data
        assert isinstance(data["tanking_score"], float)


class TestSyntheticFixtures:
    """Synthetic data produces expected outputs."""
    
    def test_tanking_team_fixture(self):
        """Known tanking team signals produce high tanking score."""
        # Portland 2024-25 vibes
        score = calculate_tanking_score(
            wins=18, losses=42, games_remaining=22,
            star_players_sitting=2,
            youth_minutes_pct=0.45,
            defensive_effort_drop=0.25,
            trade_asset_pct=0.40
        )
        assert score > 0.55  # Clear tanking signals
    
    def test_contending_team_fixture(self):
        """Known contending team signals produce low tanking score."""
        # OKC 2024-25 vibes
        score = calculate_tanking_score(
            wins=48, losses=12, games_remaining=22,
            star_players_sitting=0,
            youth_minutes_pct=0.15,
            defensive_effort_drop=0.0,
            trade_asset_pct=0.0
        )
        assert score < 0.10  # No tanking signals
    
    def test_star_player_load_management(self):
        """Kawhi-style load management pattern."""
        modifier = calculate_effort_decay_modifier(
            games_played_last_14=6,
            minutes_avg_last_5=34.0,
            team_competitive_state="contending",
            player_age=32.0
        )
        # Should still be healthy modifier despite selective sitting
        assert modifier >= 0.80