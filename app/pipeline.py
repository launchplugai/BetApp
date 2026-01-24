# app/pipeline.py
"""
Pipeline Facade - Single entry point for all evaluation requests.

This is the ONLY place where core evaluation is called.
All routes MUST go through this facade:

    Airlock (validation) → Pipeline (evaluation) → Route (HTTP response)

The pipeline:
1. Parses text input into BetBlocks
2. Calls the canonical evaluate_parlay()
3. Fetches external context (Sprint 3: NBA availability)
4. Wraps response with plain-English explanations
5. Applies tier-based filtering

Routes should NOT:
- Import core.evaluation directly
- Reimplement parsing/summary logic
- Call evaluate_parlay() themselves
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from app.airlock import NormalizedInput, Tier

# Core evaluation - the ONLY direct import of core.evaluation in app/
from core.evaluation import EvaluationResponse, evaluate_parlay
from core.models.leading_light import (
    BetBlock,
    BetType,
    ContextModifier,
    ContextModifiers,
)

# Context ingestion (Sprint 3)
from context.service import get_context
from context.apply import apply_context, ContextImpact

# Alerts (Sprint 4)
from alerts.service import check_for_alerts

_logger = logging.getLogger(__name__)


# =============================================================================
# Pipeline Response
# =============================================================================


@dataclass(frozen=True)
class PipelineResponse:
    """
    Unified response from the evaluation pipeline.

    Contains:
    - Raw evaluation response from core engine
    - Plain-English interpretation
    - Tier-filtered explain content
    - Context data (Sprint 3)
    - Metadata for logging
    """
    # Core evaluation result
    evaluation: EvaluationResponse

    # Plain-English interpretation (always included)
    interpretation: dict

    # Explain content (tier-filtered)
    explain: dict

    # Context impact (Sprint 3 - additive only, does not modify engine)
    context: Optional[dict] = None

    # Primary failure diagnosis + delta preview (Ticket 4)
    primary_failure: Optional[dict] = None
    delta_preview: Optional[dict] = None

    # Metadata
    leg_count: int = 0
    tier: str = "good"


# =============================================================================
# Text Parsing (moved from leading_light.py)
# =============================================================================


def _parse_bet_text(bet_text: str) -> list[BetBlock]:
    """
    Parse bet_text into BetBlock objects.

    Minimal parser that creates simple bet blocks from text.
    Does NOT implement scoring logic - just format conversion.
    """
    # Count legs based on delimiters
    leg_count = 1
    for delimiter in ['+', ',', 'and ', ' parlay']:
        if delimiter in bet_text.lower():
            leg_count = bet_text.lower().count(delimiter) + 1
            break

    # Cap at reasonable limit
    leg_count = min(leg_count, 5)

    # Detect bet types from text
    text_lower = bet_text.lower()
    is_prop = any(word in text_lower for word in ['yards', 'points', 'rebounds', 'assists', 'touchdowns', 'td'])
    is_total = any(word in text_lower for word in ['over', 'under', 'o/', 'u/'])
    is_spread = any(word in text_lower for word in ['-', '+']) and not is_total

    # Determine bet type
    if is_prop:
        bet_type = BetType.PLAYER_PROP
        base_fragility = 0.20  # Props are inherently more fragile
    elif is_total:
        bet_type = BetType.TOTAL
        base_fragility = 0.12
    elif is_spread:
        bet_type = BetType.SPREAD
        base_fragility = 0.10
    else:
        bet_type = BetType.ML
        base_fragility = 0.08

    # Create bet blocks (one per leg)
    blocks = []
    default_mod = ContextModifier(applied=False, delta=0.0, reason=None)
    modifiers = ContextModifiers(
        weather=default_mod,
        injury=default_mod,
        trade=default_mod,
        role=default_mod,
    )

    for i in range(leg_count):
        block = BetBlock(
            block_id=uuid4(),
            sport="generic",
            game_id=f"game_{i+1}",
            bet_type=bet_type,
            selection=f"Leg {i+1}",
            base_fragility=base_fragility,
            context_modifiers=modifiers,
            correlation_tags=(),
            effective_fragility=base_fragility,
            player_id=None,
            team_id=None,
        )
        blocks.append(block)

    return blocks


# =============================================================================
# Summary Generation (moved from leading_light.py)
# =============================================================================


def _generate_summary(response: EvaluationResponse, leg_count: int) -> list[str]:
    """Generate plain-English summary bullets from evaluation response."""
    summary = [
        f"Detected {leg_count} leg(s) in this bet",
        f"Risk level: {response.inductor.level.value.upper()}",
        f"Final fragility: {response.metrics.final_fragility:.2f}",
    ]

    if response.metrics.correlation_penalty > 0:
        summary.append(f"Correlation penalty applied: +{response.metrics.correlation_penalty:.2f}")

    if len(response.correlations) > 0:
        summary.append(f"Found {len(response.correlations)} correlation(s) between legs")

    return summary


def _generate_alerts(response: EvaluationResponse) -> list[str]:
    """Generate alerts from evaluation response."""
    alerts = []

    # Check for DNA violations
    if response.dna.violations:
        for violation in response.dna.violations:
            alerts.append(violation)

    # Check for high correlation
    if response.metrics.correlation_multiplier >= 1.5:
        alerts.append("High correlation detected between selections")

    # Check for critical risk
    if response.inductor.level.value == "critical":
        alerts.append("Critical risk level - structure exceeds safe thresholds")

    return alerts


def _interpret_fragility(final_fragility: float) -> dict:
    """
    Generate user-friendly interpretation of fragility score.

    Maps 0-100 scale to buckets with plain-English meaning and actionable advice.
    Does NOT modify engine metrics - interpretation layer only.
    """
    # Clamp for display (engine can produce values outside 0-100)
    display_value = max(0.0, min(100.0, final_fragility))

    # Determine bucket
    if final_fragility <= 15:
        bucket = "low"
        meaning = "Few dependencies; most paths lead to success."
        what_to_do = "Structure is solid; proceed with confidence."
    elif final_fragility <= 35:
        bucket = "medium"
        meaning = "Moderate complexity; several things must align."
        what_to_do = "Review each leg independently before committing."
    elif final_fragility <= 60:
        bucket = "high"
        meaning = "Many things must go right; one miss breaks the ticket."
        what_to_do = "Reduce legs or remove correlated/prop legs to lower failure points."
    else:  # > 60
        bucket = "critical"
        meaning = "Extreme fragility; compounding failure paths."
        what_to_do = "Simplify significantly or avoid this structure entirely."

    return {
        "scale": "0-100",
        "value": final_fragility,
        "display_value": display_value,
        "bucket": bucket,
        "meaning": meaning,
        "what_to_do": what_to_do,
    }


# =============================================================================
# Tier Filtering (moved from leading_light.py)
# =============================================================================


def _apply_tier_filtering(tier: Tier, explain: dict, evaluation=None, blocks=None, primary_failure=None) -> dict:
    """
    Apply tier-based filtering to explain content.

    Tier rules:
    - GOOD: Structured output (signal, grade, contributors, warnings, tips, removals)
    - BETTER: summary only
    - BEST: summary + alerts + recommended_next_step
    """
    if tier == Tier.GOOD:
        return _build_good_tier_output(evaluation, blocks, primary_failure) if evaluation else {}
    elif tier == Tier.BETTER:
        return {"summary": explain.get("summary", [])}
    else:  # BEST
        return explain


def _build_good_tier_output(evaluation, blocks, primary_failure=None) -> dict:
    """
    Build structured GOOD tier output from evaluation response.

    Derives signal, grade, contributors, warnings, tips, and removal
    suggestions from existing evaluation metrics. Does NOT modify engine math.
    """
    metrics = evaluation.metrics
    final_fragility = metrics.final_fragility

    # Map fragility to signal: low→blue, medium→green, high→yellow, critical→red
    if final_fragility <= 15:
        signal = "blue"
    elif final_fragility <= 35:
        signal = "green"
    elif final_fragility <= 60:
        signal = "yellow"
    else:
        signal = "red"

    # Grade: A=blue, B=green, C=yellow, D=red
    grade_map = {"blue": "A", "green": "B", "yellow": "C", "red": "D"}
    grade = grade_map[signal]

    # Contributors: factors that materially affect risk
    contributors = []

    if metrics.correlation_penalty > 0:
        impact = "high" if metrics.correlation_penalty > 5 else ("medium" if metrics.correlation_penalty > 2 else "low")
        contributors.append({"type": "correlation", "impact": impact})

    if metrics.leg_penalty > 0:
        impact = "high" if metrics.leg_penalty > 20 else ("medium" if metrics.leg_penalty > 10 else "low")
        contributors.append({"type": "leg_count", "impact": impact})

    if len(evaluation.correlations) > 0:
        impact = "high" if len(evaluation.correlations) > 2 else ("medium" if len(evaluation.correlations) > 1 else "low")
        contributors.append({"type": "dependency", "impact": impact})

    # Check for prop-type volatility from blocks
    if blocks:
        prop_count = sum(1 for b in blocks if b.base_fragility >= 0.20)
        if prop_count > 0:
            impact = "high" if prop_count > 2 else ("medium" if prop_count > 1 else "low")
            contributors.append({"type": "volatility", "impact": impact})

    # Warnings: specific risk statements referencing primary failure
    warnings = []
    pf_type = primary_failure.get("type") if primary_failure else None
    pf_action = primary_failure.get("fastestFix", {}).get("action") if primary_failure else None

    if pf_type == "correlation" and metrics.correlation_multiplier >= 1.5:
        warnings.append(f"Correlation penalty: +{metrics.correlation_penalty:.1f}pt from shared outcomes")
    elif pf_type == "correlation" and metrics.correlation_penalty > 0:
        warnings.append(f"Correlated selections add +{metrics.correlation_penalty:.1f}pt penalty")
    if pf_type == "leg_count" and metrics.leg_penalty > 10:
        warnings.append(f"Leg penalty: +{metrics.leg_penalty:.1f}pt from {len(blocks or [])} selections")
    if pf_type == "volatility":
        prop_count = sum(1 for b in (blocks or []) if b.base_fragility >= 0.20)
        warnings.append(f"{prop_count} prop-type bet{'s' if prop_count != 1 else ''} with elevated base fragility")
    if pf_type == "dependency" and len(evaluation.correlations) > 1:
        warnings.append(f"{len(evaluation.correlations)} outcome pairs share dependent variables")
    # Secondary warnings (only if they reference a real factor)
    if metrics.correlation_multiplier >= 1.5 and pf_type != "correlation":
        warnings.append(f"Correlation multiplier at {metrics.correlation_multiplier:.1f}x")
    if metrics.leg_penalty > 20 and pf_type != "leg_count":
        warnings.append(f"{len(blocks or [])} legs add +{metrics.leg_penalty:.1f}pt structural penalty")

    # Tips: actionable, referencing primary failure fix path
    tips = []
    if pf_action == "remove_leg" and metrics.leg_penalty > 10:
        tips.append(f"Remove 1 leg to reduce penalty by ~{metrics.leg_penalty * 0.3:.0f}pt")
    if pf_action == "split_parlay":
        tips.append("Split correlated legs into separate tickets")
    if pf_action in ("reduce_props", "swap_leg"):
        tips.append("Replace prop bets with totals or spreads")
    if pf_action == "reduce_same_game":
        tips.append("Move same-game legs to separate tickets")
    # Secondary tips (only if specific)
    if len(blocks or []) >= 4 and pf_action != "remove_leg":
        tips.append(f"Reduce from {len(blocks)} to {max(2, len(blocks) - 2)} legs")
    if metrics.correlation_penalty > 0 and pf_action != "split_parlay":
        tips.append("Separate correlated selections into distinct tickets")

    # Removal suggestions: blocks involved in most correlations
    removal_suggestions = []
    if evaluation.correlations:
        block_corr_count = {}
        for corr in evaluation.correlations:
            block_corr_count[str(corr.block_a)] = block_corr_count.get(str(corr.block_a), 0) + 1
            block_corr_count[str(corr.block_b)] = block_corr_count.get(str(corr.block_b), 0) + 1
        # Sort by frequency, suggest top offenders
        sorted_blocks = sorted(block_corr_count.items(), key=lambda x: x[1], reverse=True)
        for block_id, count in sorted_blocks[:2]:
            if count > 0:
                removal_suggestions.append(block_id)

    return {
        "overallSignal": signal,
        "grade": grade,
        "fragilityScore": final_fragility,
        "contributors": contributors,
        "warnings": warnings,
        "tips": tips,
        "removalSuggestions": removal_suggestions,
    }


def _fragility_to_signal(fragility: float) -> str:
    """Map fragility score to signal color."""
    if fragility <= 15:
        return "blue"
    elif fragility <= 35:
        return "green"
    elif fragility <= 60:
        return "yellow"
    else:
        return "red"


def _signal_to_grade(signal: str) -> str:
    """Map signal to grade letter."""
    return {"blue": "A", "green": "B", "yellow": "C", "red": "D"}[signal]


def _build_primary_failure(evaluation, blocks) -> dict:
    """
    Identify the single biggest cause of fragility.

    Returns exactly one primaryFailure object with:
    - type, severity, description, affectedLegIds, fastestFix
    """
    metrics = evaluation.metrics
    correlations = evaluation.correlations
    leg_count = len(blocks) if blocks else 0

    # Score each failure type by its contribution to final fragility
    scores = {
        "correlation": metrics.correlation_penalty * (metrics.correlation_multiplier or 1.0),
        "leg_count": metrics.leg_penalty,
        "volatility": sum(1 for b in (blocks or []) if b.base_fragility >= 0.20) * 5.0,
        "dependency": len(correlations) * 3.0,
    }

    # Primary = highest scoring factor
    primary_type = max(scores, key=lambda k: scores[k])

    # If all scores are 0, default to leg_count for single legs
    if all(v == 0 for v in scores.values()):
        primary_type = "leg_count"

    # Severity from the primary factor's magnitude
    primary_score = scores[primary_type]
    if primary_score >= 15:
        severity = "high"
    elif primary_score >= 5:
        severity = "medium"
    else:
        severity = "low"

    # Build specific description (no banned phrases)
    affected_leg_ids = []
    candidate_leg_ids = []

    if primary_type == "correlation":
        if correlations:
            top_corr = max(correlations, key=lambda c: c.penalty)
            affected_leg_ids = [str(top_corr.block_a), str(top_corr.block_b)]
            candidate_leg_ids = [str(top_corr.block_b)]
            corr_type = top_corr.type
            description = f"{corr_type.replace('_', ' ').title()} correlation between 2 legs adds +{top_corr.penalty:.1f}pt penalty"
        else:
            description = f"Correlation penalty of +{metrics.correlation_penalty:.1f}pt detected across selections"

    elif primary_type == "leg_count":
        description = f"{leg_count} leg{'s' if leg_count != 1 else ''} produce{'s' if leg_count == 1 else ''} +{metrics.leg_penalty:.1f}pt structural penalty"
        if blocks and leg_count > 2:
            # Suggest removing the last-added leg
            candidate_leg_ids = [str(blocks[-1].block_id)]

    elif primary_type == "volatility":
        prop_blocks = [b for b in (blocks or []) if b.base_fragility >= 0.20]
        prop_count = len(prop_blocks)
        description = f"{prop_count} high-variance selection{'s' if prop_count != 1 else ''} with base fragility >= 20pt"
        affected_leg_ids = [str(b.block_id) for b in prop_blocks[:3]]
        candidate_leg_ids = [str(prop_blocks[0].block_id)] if prop_blocks else []

    else:  # dependency
        dep_count = len(correlations)
        description = f"{dep_count} dependent outcome pair{'s' if dep_count != 1 else ''} share variables"
        if correlations:
            # Find the block appearing most in correlations
            block_freq = {}
            for c in correlations:
                block_freq[str(c.block_a)] = block_freq.get(str(c.block_a), 0) + 1
                block_freq[str(c.block_b)] = block_freq.get(str(c.block_b), 0) + 1
            top_block = max(block_freq, key=lambda k: block_freq[k])
            affected_leg_ids = [top_block]
            candidate_leg_ids = [top_block]

    # Determine fastestFix action
    if primary_type == "correlation":
        action = "split_parlay" if len(correlations) > 1 else "remove_leg"
    elif primary_type == "leg_count":
        action = "remove_leg"
    elif primary_type == "volatility":
        action = "reduce_props" if len([b for b in (blocks or []) if b.base_fragility >= 0.20]) > 1 else "swap_leg"
    else:
        action = "split_parlay"

    # Build fix description
    fix_descriptions = {
        "remove_leg": f"Remove the most correlated leg to reduce penalty by ~{primary_score * 0.5:.0f}pt",
        "split_parlay": "Split into 2 uncorrelated tickets to eliminate dependency penalty",
        "swap_leg": "Replace the high-variance selection with a spread or total",
        "reduce_props": "Replace prop selections with game-level bets (spread/total)",
        "reduce_same_game": "Move same-game legs to separate tickets",
    }

    return {
        "type": primary_type,
        "severity": severity,
        "description": description,
        "affectedLegIds": affected_leg_ids,
        "fastestFix": {
            "action": action,
            "description": fix_descriptions.get(action, "Simplify parlay structure"),
            "candidateLegIds": candidate_leg_ids,
        },
    }


def _build_delta_preview(evaluation, blocks, primary_failure) -> dict:
    """
    Compute a deterministic 'what if you apply fastestFix' preview.

    Uses existing evaluate_parlay() — no new math.
    If candidate leg exists and action is remove_leg, re-evaluates without it.
    Otherwise returns null after/change.
    """
    fastest_fix = primary_failure.get("fastestFix", {})
    candidate_ids = fastest_fix.get("candidateLegIds", [])
    action = fastest_fix.get("action", "")

    # Before state (current)
    before_fragility = evaluation.metrics.final_fragility
    before_signal = _fragility_to_signal(before_fragility)
    before_state = {
        "signal": before_signal,
        "grade": _signal_to_grade(before_signal),
        "fragilityScore": before_fragility,
    }

    # Can only simulate remove_leg with a known candidate and >1 blocks
    if action == "remove_leg" and candidate_ids and blocks and len(blocks) > 1:
        remove_id = candidate_ids[0]
        remaining_blocks = [b for b in blocks if str(b.block_id) != remove_id]

        if remaining_blocks:
            after_eval = evaluate_parlay(
                blocks=remaining_blocks,
                dna_profile=None,
                bankroll=None,
                candidates=None,
                max_suggestions=0,
            )
            after_fragility = after_eval.metrics.final_fragility
            after_signal = _fragility_to_signal(after_fragility)
            after_state = {
                "signal": after_signal,
                "grade": _signal_to_grade(after_signal),
                "fragilityScore": after_fragility,
            }

            # Determine direction of change
            signal_order = {"blue": 0, "green": 1, "yellow": 2, "red": 3}
            before_idx = signal_order[before_signal]
            after_idx = signal_order[after_signal]
            if after_idx < before_idx:
                signal_change = "up"
            elif after_idx > before_idx:
                signal_change = "down"
            else:
                signal_change = "same"

            if after_fragility < before_fragility:
                fragility_change = "down"
            elif after_fragility > before_fragility:
                fragility_change = "up"
            else:
                fragility_change = "same"

            return {
                "before": before_state,
                "after": after_state,
                "change": {"signal": signal_change, "fragility": fragility_change},
            }

    # No simulation possible
    return {
        "before": before_state,
        "after": None,
        "change": None,
    }
# Main Pipeline Function
# =============================================================================


def _extract_entities_from_text(text: str) -> tuple[list[str], list[str]]:
    """
    Extract player names and team names from bet text.

    Sprint 3 scope: Simple extraction for NBA.
    Returns (player_names, team_names).
    """
    text_lower = text.lower()

    # NBA team abbreviations/names to look for
    nba_teams = {
        "lakers": "LAL", "lal": "LAL", "los angeles lakers": "LAL",
        "celtics": "BOS", "bos": "BOS", "boston": "BOS",
        "nuggets": "DEN", "den": "DEN", "denver": "DEN",
        "bucks": "MIL", "mil": "MIL", "milwaukee": "MIL",
        "warriors": "GSW", "gsw": "GSW", "golden state": "GSW",
        "suns": "PHX", "phx": "PHX", "phoenix": "PHX",
        "76ers": "PHI", "phi": "PHI", "sixers": "PHI", "philadelphia": "PHI",
        "mavericks": "DAL", "dal": "DAL", "dallas": "DAL", "mavs": "DAL",
        "heat": "MIA", "mia": "MIA", "miami": "MIA",
        "nets": "BKN", "bkn": "BKN", "brooklyn": "BKN",
        "knicks": "NYK", "nyk": "NYK", "new york": "NYK",
        "bulls": "CHI", "chi": "CHI", "chicago": "CHI",
        "clippers": "LAC", "lac": "LAC",
        "thunder": "OKC", "okc": "OKC", "oklahoma": "OKC",
        "timberwolves": "MIN", "min": "MIN", "minnesota": "MIN", "wolves": "MIN",
        "kings": "SAC", "sac": "SAC", "sacramento": "SAC",
        "pelicans": "NOP", "nop": "NOP", "new orleans": "NOP",
        "grizzlies": "MEM", "mem": "MEM", "memphis": "MEM",
        "cavaliers": "CLE", "cle": "CLE", "cleveland": "CLE", "cavs": "CLE",
        "hawks": "ATL", "atl": "ATL", "atlanta": "ATL",
        "raptors": "TOR", "tor": "TOR", "toronto": "TOR",
        "pacers": "IND", "ind": "IND", "indiana": "IND",
        "hornets": "CHA", "cha": "CHA", "charlotte": "CHA",
        "wizards": "WAS", "was": "WAS", "washington": "WAS",
        "magic": "ORL", "orl": "ORL", "orlando": "ORL",
        "pistons": "DET", "det": "DET", "detroit": "DET",
        "jazz": "UTA", "uta": "UTA", "utah": "UTA",
        "rockets": "HOU", "hou": "HOU", "houston": "HOU",
        "spurs": "SAS", "sas": "SAS", "san antonio": "SAS",
        "trail blazers": "POR", "por": "POR", "portland": "POR", "blazers": "POR",
    }

    # Common NBA player names to look for (from sample data)
    known_players = [
        "lebron james", "lebron", "anthony davis", "ad",
        "jaylen brown", "jayson tatum", "tatum",
        "nikola jokic", "jokic", "jamal murray",
        "giannis", "giannis antetokounmpo", "damian lillard", "lillard", "dame",
        "stephen curry", "curry", "steph", "klay thompson",
        "kevin durant", "durant", "kd", "devin booker", "booker",
        "joel embiid", "embiid", "tyrese maxey", "maxey",
        "luka doncic", "luka", "doncic", "kyrie irving", "kyrie",
    ]

    found_teams = []
    for team_key, team_abbr in nba_teams.items():
        if team_key in text_lower:
            if team_abbr not in found_teams:
                found_teams.append(team_abbr)

    found_players = []
    for player in known_players:
        if player in text_lower:
            # Map to full name for context lookup
            player_map = {
                "lebron": "LeBron James", "ad": "Anthony Davis",
                "tatum": "Jayson Tatum", "jokic": "Nikola Jokic",
                "giannis": "Giannis Antetokounmpo", "lillard": "Damian Lillard",
                "dame": "Damian Lillard", "curry": "Stephen Curry",
                "steph": "Stephen Curry", "durant": "Kevin Durant",
                "kd": "Kevin Durant", "booker": "Devin Booker",
                "embiid": "Joel Embiid", "maxey": "Tyrese Maxey",
                "luka": "Luka Doncic", "doncic": "Luka Doncic",
                "kyrie": "Kyrie Irving",
            }
            full_name = player_map.get(player, player.title())
            if full_name not in found_players:
                found_players.append(full_name)

    return found_players, found_teams


def _fetch_context_for_bet(text: str, correlation_id: Optional[str] = None) -> Optional[dict]:
    """
    Fetch context data relevant to the bet.

    Sprint 3 scope: NBA availability only.
    Sprint 4: Also triggers alert generation for availability changes.

    Returns context dict or None if not applicable.
    """
    try:
        # Extract entities from bet text
        player_names, team_names = _extract_entities_from_text(text)

        # Check if this looks like an NBA bet
        text_lower = text.lower()
        is_nba = (
            "nba" in text_lower
            or len(player_names) > 0
            or len(team_names) > 0
            or any(word in text_lower for word in ["basketball", "points", "rebounds", "assists"])
        )

        if not is_nba:
            return None

        # Fetch NBA context
        snapshot = get_context("NBA")

        # Sprint 4: Check for alerts (stores any new alerts)
        new_alerts = check_for_alerts(
            snapshot=snapshot,
            player_names=player_names if player_names else None,
            team_names=team_names if team_names else None,
            correlation_id=correlation_id,
        )
        if new_alerts:
            _logger.info(f"Generated {len(new_alerts)} alert(s) for bet evaluation")

        # Apply context to get impact
        impact = apply_context(
            snapshot=snapshot,
            player_names=player_names if player_names else None,
            team_names=team_names if team_names else None,
        )

        # Convert to dict for response
        return {
            "sport": snapshot.sport,
            "source": snapshot.source,
            "as_of": snapshot.as_of.isoformat(),
            "impact": {
                "adjustment": impact.total_adjustment,
                "summary": impact.summary,
                "modifiers": [
                    {
                        "adjustment": m.adjustment,
                        "reason": m.reason,
                        "affected_players": list(m.affected_players),
                    }
                    for m in impact.modifiers
                ],
            },
            "missing_data": list(impact.missing_data),
            "player_count": snapshot.player_count,
            "entities_found": {
                "players": player_names,
                "teams": team_names,
            },
            "alerts_generated": len(new_alerts),
        }

    except Exception as e:
        _logger.warning(f"Failed to fetch context: {e}")
        return None


def run_evaluation(normalized: NormalizedInput) -> PipelineResponse:
    """
    Run the canonical evaluation pipeline.

    This is the ONLY entry point for evaluation. All routes call this.

    Args:
        normalized: Validated input from Airlock

    Returns:
        PipelineResponse with evaluation, interpretation, context, and explain

    Flow:
        1. Parse text → BetBlocks
        2. Call evaluate_parlay() (the canonical core function)
        3. Fetch external context (Sprint 3)
        4. Generate plain-English interpretation
        5. Apply tier filtering to explain
        6. Return unified response
    """
    # Step 1: Parse text into BetBlocks
    blocks = _parse_bet_text(normalized.input_text)
    leg_count = len(blocks)

    # Step 2: Call canonical evaluation engine
    evaluation = evaluate_parlay(
        blocks=blocks,
        dna_profile=None,
        bankroll=None,
        candidates=None,
        max_suggestions=0,
    )

    # Step 3: Fetch external context (Sprint 3 - additive only)
    # Sprint 4: Pass parlay_id as correlation_id for alert tracking
    context_data = _fetch_context_for_bet(
        normalized.input_text,
        correlation_id=str(evaluation.parlay_id),
    )

    # Step 4: Generate plain-English interpretation
    interpretation = {
        "fragility": _interpret_fragility(evaluation.metrics.final_fragility),
    }

    # Step 5: Build full explain wrapper
    explain_full = {
        "summary": _generate_summary(evaluation, leg_count),
        "alerts": _generate_alerts(evaluation),
        "recommended_next_step": evaluation.recommendation.reason,
    }

    # Step 6: Build primary failure + delta preview (Ticket 4)
    primary_failure = _build_primary_failure(evaluation, blocks)
    delta_preview = _build_delta_preview(evaluation, blocks, primary_failure)

    # Step 7: Apply tier filtering (uses primary_failure for specific warnings/tips)
    explain_filtered = _apply_tier_filtering(normalized.tier, explain_full, evaluation, blocks, primary_failure)

    return PipelineResponse(
        evaluation=evaluation,
        interpretation=interpretation,
        explain=explain_filtered,
        context=context_data,
        primary_failure=primary_failure,
        delta_preview=delta_preview,
        leg_count=leg_count,
        tier=normalized.tier.value,
    )
