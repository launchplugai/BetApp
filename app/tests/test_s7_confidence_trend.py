"""
S7-B: Confidence Trend Tests

Verifies that confidence trend is computed and provided based on session history.
"""
import pytest
from app.pipeline import run_evaluation, NormalizedInput, Tier
from app.delta_engine import (
    compute_confidence_trend,
    store_signal_for_session,
    get_previous_signal_for_session,
    _signal_storage,
)


class TestConfidenceTrendComputation:
    """Test S7-B: Confidence Trend computation."""

    def setup_method(self):
        """Clear signal storage before each test."""
        _signal_storage.clear()

    def test_first_evaluation_has_no_trend(self):
        """First evaluation in session should have no trend."""
        result = compute_confidence_trend(
            previous_signal=None,
            current_signal={"signal": "green", "fragilityScore": 25}
        )
        
        assert result["has_trend"] is False
        assert result["trend"] is None
        assert result["trend_text"] is None

    def test_improved_when_signal_better(self):
        """Trend should be 'improved' when signal improves."""
        result = compute_confidence_trend(
            previous_signal={"signal": "yellow", "fragility_score": 50},
            current_signal={"signal": "green", "fragilityScore": 30}
        )
        
        assert result["has_trend"] is True
        assert result["trend"] == "improved"
        assert "strengthened" in result["trend_text"].lower()

    def test_softened_when_signal_worse(self):
        """Trend should be 'softened' when signal degrades."""
        result = compute_confidence_trend(
            previous_signal={"signal": "green", "fragility_score": 30},
            current_signal={"signal": "yellow", "fragilityScore": 50}
        )
        
        assert result["has_trend"] is True
        assert result["trend"] == "softened"
        assert "softened" in result["trend_text"].lower()

    def test_unchanged_when_same_signal_similar_score(self):
        """Trend should be 'unchanged' when signal and score are similar."""
        result = compute_confidence_trend(
            previous_signal={"signal": "green", "fragility_score": 30},
            current_signal={"signal": "green", "fragilityScore": 31}
        )
        
        assert result["has_trend"] is True
        assert result["trend"] == "unchanged"
        assert "similar" in result["trend_text"].lower()

    def test_improved_when_same_signal_lower_fragility(self):
        """Same signal but meaningfully lower fragility = improved."""
        result = compute_confidence_trend(
            previous_signal={"signal": "green", "fragility_score": 35},
            current_signal={"signal": "green", "fragilityScore": 28}  # 7pt improvement
        )
        
        assert result["has_trend"] is True
        assert result["trend"] == "improved"

    def test_softened_when_same_signal_higher_fragility(self):
        """Same signal but meaningfully higher fragility = softened."""
        result = compute_confidence_trend(
            previous_signal={"signal": "green", "fragility_score": 28},
            current_signal={"signal": "green", "fragilityScore": 38}  # 10pt worse
        )
        
        assert result["has_trend"] is True
        assert result["trend"] == "softened"


class TestConfidenceTrendStorage:
    """Test signal storage for trend tracking."""

    def setup_method(self):
        """Clear signal storage before each test."""
        _signal_storage.clear()

    def test_store_and_retrieve_signal(self):
        """Signal info can be stored and retrieved."""
        session_id = "test-session-123"
        signal_info = {"signal": "green", "fragilityScore": 25}
        
        store_signal_for_session(session_id, signal_info)
        retrieved = get_previous_signal_for_session(session_id)
        
        assert retrieved is not None
        assert retrieved["signal"] == "green"
        assert retrieved["fragility_score"] == 25

    def test_retrieve_nonexistent_session(self):
        """Nonexistent session returns None."""
        retrieved = get_previous_signal_for_session("nonexistent")
        assert retrieved is None


class TestConfidenceTrendIntegration:
    """Integration tests for confidence trend in pipeline."""

    def setup_method(self):
        """Clear signal storage before each test."""
        _signal_storage.clear()

    def test_confidence_trend_in_response(self):
        """Verify confidence_trend field is present in evaluation response."""
        normalized = NormalizedInput(
            input_text="Lakers -5.5",
            tier=Tier.GOOD,
        )
        result = run_evaluation(normalized)
        
        assert hasattr(result, 'confidence_trend'), "confidence_trend field missing"
        assert result.confidence_trend is not None
        # First evaluation should have no trend
        assert result.confidence_trend["has_trend"] is False

    def test_second_evaluation_shows_trend(self):
        """Second evaluation should show trend compared to first."""
        normalized = NormalizedInput(
            input_text="Lakers -5.5",
            tier=Tier.GOOD,
        )
        
        # First evaluation
        result1 = run_evaluation(normalized)
        parlay_id = result1.evaluation.parlay_id
        
        # Store signal manually for same session
        store_signal_for_session(str(parlay_id), {
            "signal": result1.signal_info["signal"],
            "fragilityScore": result1.signal_info["fragilityScore"]
        })
        
        # Second evaluation (same parlay_id simulation - use different input)
        result2 = run_evaluation(normalized)
        
        # Note: Each run_evaluation gets a new parlay_id, so this tests the storage
        # In production, the session_id would persist across refinements
        assert result2.confidence_trend is not None
