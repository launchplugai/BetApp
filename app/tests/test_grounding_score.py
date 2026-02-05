# app/tests/test_grounding_score.py
"""
Tests for Ticket 38B-C2: Grounding Score Engine

Verifies:
1. Grounding percentages always sum to 100
2. Structural-heavy scenarios score higher on structural
3. Heuristics-heavy scenarios score higher on heuristics
4. Generic fallback scenarios score higher on generic
5. Deterministic (same inputs → same outputs)
"""
import pytest
from app.grounding_score import compute_grounding_score, GroundingScore


class TestGroundingScoreInvariant:
    """Test that grounding scores always sum to 100."""
    
    def test_always_sums_to_100_no_data(self):
        """With no data, percentages sum to 100."""
        score = compute_grounding_score()
        assert score.structural + score.heuristics + score.generic == 100
    
    def test_always_sums_to_100_minimal_structure(self):
        """With minimal structure, percentages sum to 100."""
        structure = {
            "leg_count": 2,
            "leg_ids": ["leg_1", "leg_2"],
            "leg_types": ["ml", "spread"],
            "props": 0,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": [],
        }
        score = compute_grounding_score(structure=structure)
        assert score.structural + score.heuristics + score.generic == 100
    
    def test_always_sums_to_100_full_data(self):
        """With full data, percentages sum to 100."""
        structure = {
            "leg_count": 4,
            "leg_ids": ["leg_1", "leg_2", "leg_3", "leg_4"],
            "leg_types": ["player_prop", "player_prop", "spread", "total"],
            "props": 2,
            "totals": 1,
            "correlation_flags": ["same_game"],
            "volatility_sources": ["player_prop", "totals"],
        }
        evaluation = {
            "metrics": {
                "correlation_penalty": 15.5,
                "correlation_multiplier": 1.2,
            },
            "correlations": [
                {"type": "same_game", "penalty": 15.5}
            ],
        }
        score = compute_grounding_score(structure=structure, evaluation=evaluation)
        assert score.structural + score.heuristics + score.generic == 100


class TestGroundingScoreDistribution:
    """Test that grounding scores reflect content source accurately."""
    
    def test_structural_heavy_scenario(self):
        """High correlation + multi-leg parlay → high structural."""
        structure = {
            "leg_count": 5,
            "leg_ids": ["leg_1", "leg_2", "leg_3", "leg_4", "leg_5"],
            "leg_types": ["ml", "ml", "spread", "spread", "total"],
            "props": 0,
            "totals": 1,
            "correlation_flags": ["same_game", "player_dependency"],
            "volatility_sources": ["totals"],
        }
        evaluation = {
            "metrics": {
                "correlation_penalty": 25.0,
                "correlation_multiplier": 1.5,
            },
            "correlations": [
                {"type": "same_game", "penalty": 15.0},
                {"type": "player_dependency", "penalty": 10.0},
            ],
        }
        score = compute_grounding_score(structure=structure, evaluation=evaluation)
        
        # Structural should dominate
        assert score.structural > 50, f"Expected structural > 50%, got {score.structural}%"
        assert score.structural > score.heuristics
        assert score.structural > score.generic
    
    def test_heuristics_heavy_scenario(self):
        """Many props + diverse leg types → high heuristics."""
        structure = {
            "leg_count": 4,
            "leg_ids": ["leg_1", "leg_2", "leg_3", "leg_4"],
            "leg_types": ["player_prop", "player_prop", "player_prop", "total"],
            "props": 3,
            "totals": 1,
            "correlation_flags": [],  # No correlations
            "volatility_sources": ["player_prop"],
        }
        evaluation = {
            "metrics": {
                "correlation_penalty": 0,
                "correlation_multiplier": 1.0,
            },
            "correlations": [],
        }
        primary_failure = {
            "type": "correlation_risk",
            "severity": "medium",
        }
        score = compute_grounding_score(
            structure=structure,
            evaluation=evaluation,
            primary_failure=primary_failure
        )
        
        # Heuristics should be significant (props + leg-type diversity)
        assert score.heuristics > 30, f"Expected heuristics > 30%, got {score.heuristics}%"
    
    def test_generic_fallback_scenario(self):
        """No structure data → high generic."""
        score = compute_grounding_score(
            structure=None,
            evaluation=None,
            primary_failure=None,
            final_verdict=None,
        )
        
        # Generic should dominate when no data available
        assert score.generic > 50, f"Expected generic > 50%, got {score.generic}%"
        assert score.generic > score.structural
        assert score.generic > score.heuristics
    
    def test_minimal_structure_minimal_generic(self):
        """With structure but no correlations, generic should be moderate."""
        structure = {
            "leg_count": 2,
            "leg_ids": ["leg_1", "leg_2"],
            "leg_types": ["ml", "ml"],
            "props": 0,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": [],
        }
        score = compute_grounding_score(structure=structure)
        
        # Some structural (leg count), some generic (no correlations)
        assert score.structural > 0
        assert score.generic > 0
        assert score.structural + score.heuristics + score.generic == 100


class TestGroundingScoreDeterminism:
    """Test that grounding scores are deterministic."""
    
    def test_same_inputs_same_outputs(self):
        """Same inputs produce same outputs."""
        structure = {
            "leg_count": 3,
            "leg_ids": ["leg_1", "leg_2", "leg_3"],
            "leg_types": ["spread", "player_prop", "total"],
            "props": 1,
            "totals": 1,
            "correlation_flags": ["same_game"],
            "volatility_sources": ["player_prop", "totals"],
        }
        evaluation = {
            "metrics": {
                "correlation_penalty": 10.0,
                "correlation_multiplier": 1.1,
            },
            "correlations": [{"type": "same_game", "penalty": 10.0}],
        }
        
        score1 = compute_grounding_score(structure=structure, evaluation=evaluation)
        score2 = compute_grounding_score(structure=structure, evaluation=evaluation)
        
        assert score1.structural == score2.structural
        assert score1.heuristics == score2.heuristics
        assert score1.generic == score2.generic


class TestGroundingScoreContract:
    """Test the GroundingScore dataclass contract."""
    
    def test_valid_grounding_score(self):
        """Valid percentages create GroundingScore."""
        score = GroundingScore(structural=60, heuristics=30, generic=10)
        assert score.structural == 60
        assert score.heuristics == 30
        assert score.generic == 10
    
    def test_invalid_sum_raises_error(self):
        """Percentages not summing to 100 raise ValueError."""
        with pytest.raises(ValueError, match="must sum to 100"):
            GroundingScore(structural=60, heuristics=30, generic=20)
    
    def test_to_dict(self):
        """to_dict() returns correct structure."""
        score = GroundingScore(structural=50, heuristics=30, generic=20)
        result = score.to_dict()
        
        assert result == {
            "structural": 50,
            "heuristics": 30,
            "generic": 20,
        }
    
    def test_to_display_string(self):
        """to_display_string() formats correctly."""
        score = GroundingScore(structural=70, heuristics=20, generic=10)
        result = score.to_display_string()
        
        assert result == "Grounding: 70% structural, 20% heuristics, 10% generic"


class TestGroundingScoreEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_legs(self):
        """Zero legs still produces valid score."""
        structure = {
            "leg_count": 0,
            "leg_ids": [],
            "leg_types": [],
            "props": 0,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": [],
        }
        score = compute_grounding_score(structure=structure)
        
        assert score.structural + score.heuristics + score.generic == 100
    
    def test_large_parlay(self):
        """Large parlay (10+ legs) still produces valid score."""
        structure = {
            "leg_count": 12,
            "leg_ids": [f"leg_{i}" for i in range(12)],
            "leg_types": ["ml"] * 12,
            "props": 0,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": [],
        }
        score = compute_grounding_score(structure=structure)
        
        assert score.structural + score.heuristics + score.generic == 100
        # Large parlays should be heavily structural
        assert score.structural > 40
    
    def test_all_props(self):
        """All player props should be heuristics-heavy."""
        structure = {
            "leg_count": 5,
            "leg_ids": [f"leg_{i}" for i in range(5)],
            "leg_types": ["player_prop"] * 5,
            "props": 5,
            "totals": 0,
            "correlation_flags": [],
            "volatility_sources": ["player_prop"],
        }
        score = compute_grounding_score(structure=structure)
        
        # Props drive heuristics
        assert score.heuristics > 35, f"Expected heuristics > 35% for all props, got {score.heuristics}%"
