"""
S7-C: Emphasis Rebalancing Tests

Verifies that UI sections are rebalanced based on signal.
"""
import pytest


class TestEmphasisRebalancingCSS:
    """Test S7-C: CSS classes for emphasis rebalancing."""

    def test_emphasis_classes_in_css(self):
        """Verify emphasis CSS classes exist."""
        with open("app/web_assets/static/app.css", "r") as f:
            css = f.read()
        
        # Check for emphasis classes
        assert ".emphasis-red" in css
        assert ".emphasis-yellow" in css
        assert ".emphasis-green" in css
        assert ".emphasis-blue" in css

    def test_flex_ordering_in_css(self):
        """Verify flex order properties are set."""
        with open("app/web_assets/static/app.css", "r") as f:
            css = f.read()
        
        # Check for order properties
        assert "order:" in css
        assert "#pf-card" in css
        assert "#tips-card" in css

    def test_visual_weight_adjustments(self):
        """Verify cards have visual weight adjustments."""
        with open("app/web_assets/static/app.css", "r") as f:
            css = f.read()
        
        # Check for transform/shadow for emphasis
        assert "transform: scale" in css
        assert "box-shadow" in css


class TestEmphasisRebalancingJS:
    """Test S7-C: JavaScript sets emphasis class."""

    def test_emphasis_class_logic_in_js(self):
        """Verify JS adds emphasis class based on signal."""
        with open("app/web_assets/static/app.js", "r") as f:
            js = f.read()
        
        # Check for emphasis class logic
        assert "emphasis-" in js
        assert "signalForEmphasis" in js
        assert "classList.add('emphasis-'" in js


class TestEmphasisRebalancingHTML:
    """Test S7-C: HTML structure supports rebalancing."""

    def test_results_container_has_id(self):
        """Verify results container has ID for CSS targeting."""
        with open("app/web_assets/templates/app.html", "r") as f:
            html = f.read()
        
        assert 'id="eval-results-content"' in html
