"""
NBA Context Hook for DNA Pipeline

Clean, defensive integration of NBA heuristics into bet evaluation.
Never allowed to break the pipeline.
"""
import logging
from typing import Dict, List, Optional

log = logging.getLogger("pipeline.nba")


def apply_nba_context(bet_input: str, teams: List[str], result: Dict) -> Dict:
    """
    Inject NBA heuristics into final DNA evaluation.
    
    Runs AFTER core confidence is computed.
    Never allowed to break the pipeline.
    
    Args:
        bet_input: Raw bet input text
        teams: List of team abbreviations detected
        result: Current DNA evaluation result (will be modified)
        
    Returns:
        Modified result with NBA context injected
    """
    try:
        from app.nba.protocol_integration import enhance_nba_bet
        
        nba_context = enhance_nba_bet(bet_input, teams)
        adjustment = nba_context["confidence_adjustments"]["total_adjustment"]
        
        # Apply adjustment with bounds
        result["confidence"] = max(
            0, min(100, result["confidence"] + adjustment)
        )
        
        result["nba_heuristics"] = {
            "confidence_adjustment": adjustment,
            "risk_flags": nba_context.get("risk_flags", []),
            "context_summary": nba_context.get("context_summary", ""),
            "data_quality": nba_context.get("data_quality", "Unknown"),
        }
        
        log.info(
            "NBA_CONTEXT_APPLIED",
            extra={
                "bet_input": bet_input[:50],
                "teams": teams,
                "adjustment": adjustment,
                "new_confidence": result["confidence"],
            }
        )
        
    except Exception as e:
        log.error(
            "NBA_CONTEXT_FAILED",
            extra={
                "bet_input": bet_input[:50],
                "teams": teams,
                "error": str(e),
            }
        )
        
        # Explicit fallback - never break pipeline
        result["nba_heuristics"] = {
            "confidence_adjustment": 0,
            "risk_flags": ["⚠️ NBA context unavailable"],
            "context_summary": "NBA heuristics failed; base confidence used",
            "data_quality": "Unavailable",
        }
    
    return result
