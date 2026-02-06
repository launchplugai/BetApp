"""
S7-A: Next Action Guidance Tests

Verifies that next action guidance is provided based on signal state.
"""
import pytest
from app.pipeline import run_evaluation, NormalizedInput, Tier


class TestNextActionGuidance:
    """Test S7-A: Next Action Guidance feature."""

    def test_next_action_included_in_response(self):
        """Verify next_action field is present in evaluation response."""
        normalized = NormalizedInput(
            input_text="Lakers -5.5",
            tier=Tier.GOOD,
        )
        result = run_evaluation(normalized)
        
        # Next action should be present
        assert hasattr(result, 'next_action'), "next_action field missing from PipelineResponse"
        assert result.next_action is not None, "next_action should not be None"
        assert 'suggestion' in result.next_action, "next_action should contain 'suggestion' key"

    def test_blue_signal_next_action(self):
        """Blue signal should suggest structure is clean."""
        normalized = NormalizedInput(
            input_text="Lakers -5.5",  # Simple single leg should be blue
            tier=Tier.GOOD,
        )
        result = run_evaluation(normalized)
        
        assert result.signal_info['signal'] == 'blue'
        assert result.next_action is not None
        assert 'clean' in result.next_action['suggestion'].lower() or 'balanced' in result.next_action['suggestion'].lower()

    def test_red_signal_with_fix_suggests_builder(self):
        """Red signal with fix available should suggest using builder."""
        normalized = NormalizedInput(
            input_text="Lakers ML + Lakers -5.5 + Lakers O220.5 + Warriors ML + Nets ML + Heat ML",
            tier=Tier.GOOD,
        )
        result = run_evaluation(normalized)
        
        # Should have a red or yellow signal
        assert result.signal_info['signal'] in ('red', 'yellow')
        
        # Should have next action
        assert result.next_action is not None
        suggestion = result.next_action['suggestion'].lower()
        
        # Should suggest either reviewing or using builder
        assert any(word in suggestion for word in ['review', 'builder', 'address', 'check', 'consider'])

    def test_next_action_is_single_suggestion(self):
        """Verify exactly one suggestion is provided."""
        normalized = NormalizedInput(
            input_text="Lakers -5.5 + Warriors +3",
            tier=Tier.GOOD,
        )
        result = run_evaluation(normalized)
        
        assert result.next_action is not None
        assert 'suggestion' in result.next_action
        # Should be a single string, not a list
        assert isinstance(result.next_action['suggestion'], str)
        # Should be reasonable length (not empty, not a novel)
        assert 10 < len(result.next_action['suggestion']) < 200
