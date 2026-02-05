# app/grounding_score.py
"""
Grounding Score Engine (Ticket 38B-C2)

Calculates a percentage breakdown of how evaluation outputs are derived:
- structural: % from snapshot features directly driving outputs
- heuristics: % from leg-type templates and rules
- generic: % from fallback/boilerplate language

Invariant: structural + heuristics + generic = 100

Design:
- Pure function, no side effects
- Deterministic (same inputs → same outputs)
- No ML, no external calls
- Does NOT affect scoring or verdicts
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GroundingScore:
    """
    Grounding breakdown percentages.
    
    Attributes:
        structural: % of output grounded in structural features (correlations, leg count, etc.)
        heuristics: % of output grounded in leg-type heuristics (spread/prop/total templates)
        generic: % of output using generic/fallback language
    """
    structural: int
    heuristics: int
    generic: int
    
    def __post_init__(self):
        """Validate that percentages sum to 100."""
        total = self.structural + self.heuristics + self.generic
        if total != 100:
            raise ValueError(f"Grounding percentages must sum to 100, got {total}")
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "structural": self.structural,
            "heuristics": self.heuristics,
            "generic": self.generic,
        }
    
    def to_display_string(self) -> str:
        """Format as human-readable string."""
        return f"Grounding: {self.structural}% structural, {self.heuristics}% heuristics, {self.generic}% generic"


def compute_grounding_score(
    structure: Optional[dict] = None,
    evaluation: Optional[dict] = None,
    primary_failure: Optional[dict] = None,
    final_verdict: Optional[dict] = None,
) -> GroundingScore:
    """
    Compute grounding breakdown from evaluation artifacts.
    
    Args:
        structure: Structural snapshot dict (from generate_structure_snapshot)
        evaluation: Core evaluation response dict
        primary_failure: Primary failure diagnosis dict
        final_verdict: Final verdict dict
    
    Returns:
        GroundingScore with percentages summing to 100
    
    Algorithm:
        1. Start with base allocations
        2. Award structural points for each snapshot-derived feature used
        3. Award heuristic points for leg-type specific content
        4. Remainder goes to generic
    """
    # Base points (will be normalized to 100 at the end)
    structural_points = 0
    heuristics_points = 0
    generic_points = 10  # Minimum baseline for boilerplate
    
    # === STRUCTURAL SCORING ===
    # Points awarded when structural features drive the analysis
    
    if structure:
        leg_count = structure.get("leg_count", 0)
        correlation_flags = structure.get("correlation_flags", [])
        volatility_sources = structure.get("volatility_sources", [])
        props = structure.get("props", 0)
        totals = structure.get("totals", 0)
        
        # Leg count drives structural analysis
        if leg_count > 0:
            structural_points += 15
        if leg_count >= 3:
            structural_points += 10  # Multi-leg parlays are heavily structural
        if leg_count >= 5:
            structural_points += 5   # Large parlays even more so
        
        # Correlation detection is purely structural
        if correlation_flags:
            structural_points += 20  # Major structural contribution
            structural_points += len(correlation_flags) * 5  # More correlations = more structural
        
        # Volatility analysis from structure
        if volatility_sources:
            structural_points += 10
    
    # Evaluation metrics contribute to structural
    if evaluation:
        # Handle both dict and object types
        if isinstance(evaluation, dict):
            metrics = evaluation.get("metrics", {})
            correlations = evaluation.get("correlations", [])
        else:
            # Object with attributes
            metrics = getattr(evaluation, "metrics", None)
            correlations = getattr(evaluation, "correlations", [])
        
        # Correlation penalty calculation is structural
        if metrics:
            if isinstance(metrics, dict):
                correlation_penalty = metrics.get("correlation_penalty", 0)
                correlation_multiplier = metrics.get("correlation_multiplier", 1)
            else:
                correlation_penalty = getattr(metrics, "correlation_penalty", 0)
                correlation_multiplier = getattr(metrics, "correlation_multiplier", 1)
            
            if correlation_penalty > 0:
                structural_points += 15
            
            # Correlation multiplier application is structural
            if correlation_multiplier > 1:
                structural_points += 10
        
        # Number of detected correlations
        if correlations:
            structural_points += len(correlations) * 3
    
    # === HEURISTICS SCORING ===
    # Points awarded when leg-type templates drive the output
    
    if structure:
        leg_types = structure.get("leg_types", [])
        props = structure.get("props", 0)
        totals = structure.get("totals", 0)
        
        # Each leg type triggers type-specific heuristics
        unique_types = set(leg_types)
        heuristics_points += len(unique_types) * 8
        
        # Player props have specific heuristics
        if props > 0:
            heuristics_points += 15
            heuristics_points += min(props, 3) * 5  # Diminishing returns
        
        # Totals have specific heuristics
        if totals > 0:
            heuristics_points += 10
            heuristics_points += min(totals, 2) * 5
        
        # Spread-specific heuristics
        if "spread" in leg_types:
            heuristics_points += 8
        
        # Moneyline-specific heuristics
        if "ml" in leg_types or "moneyline" in leg_types:
            heuristics_points += 5
    
    # Primary failure analysis uses heuristics
    if primary_failure:
        pf_type = primary_failure.get("type", "")
        
        # Specific failure types indicate heuristic application
        if pf_type in ("correlation_risk", "same_game_parlay", "player_dependency"):
            heuristics_points += 12
        elif pf_type in ("leg_count", "complexity"):
            structural_points += 8  # These are more structural
        else:
            heuristics_points += 5  # Generic heuristic
    
    # === GENERIC SCORING ===
    # Points for fallback/boilerplate content
    
    # If no structure data, heavily generic
    if not structure:
        generic_points += 40
    
    # If no correlations found, some generic language used
    if structure and not structure.get("correlation_flags"):
        generic_points += 10
    
    # Verdict tone affects generic content
    if final_verdict:
        tone = final_verdict.get("tone", "")
        if tone == "positive":
            generic_points += 5  # Positive verdicts tend to be more generic
        elif tone == "cautious":
            structural_points += 5  # Cautious verdicts are more grounded
    
    # === NORMALIZE TO 100 ===
    total_points = structural_points + heuristics_points + generic_points
    
    if total_points == 0:
        # Edge case: no data at all
        return GroundingScore(structural=10, heuristics=20, generic=70)
    
    # Calculate percentages
    structural_pct = round(structural_points * 100 / total_points)
    heuristics_pct = round(heuristics_points * 100 / total_points)
    
    # Ensure they sum to 100 (rounding adjustment goes to generic)
    generic_pct = 100 - structural_pct - heuristics_pct
    
    # Clamp to valid range
    if generic_pct < 0:
        # Over-allocated to structural/heuristics, reduce largest
        if structural_pct > heuristics_pct:
            structural_pct += generic_pct
        else:
            heuristics_pct += generic_pct
        generic_pct = 0
    
    # Final validation
    return GroundingScore(
        structural=max(0, min(100, structural_pct)),
        heuristics=max(0, min(100, heuristics_pct)),
        generic=max(0, min(100, generic_pct)),
    )
