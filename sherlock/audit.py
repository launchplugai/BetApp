# sherlock/audit.py
"""
Sherlock Mode v1 - Logic Audit Framework

Implements the Logic Audit Gate that validates investigation quality.
This is the quality control step that determines if an iteration passes.

Categories and Weights (LOCKED):
- clarity: 0.10 - Is the claim and reasoning clear?
- evidence_integrity: 0.30 - Is evidence properly sourced and reliable?
- reasoning_validity: 0.25 - Is the reasoning logically valid?
- counterargument_handling: 0.20 - Are counterarguments addressed?
- scope_control: 0.10 - Is the investigation within scope?
- conclusion_discipline: 0.05 - Is the conclusion properly bounded?

Constraints:
- Scoring MUST be deterministic (same input => same scores).
- MUST fail if required artifacts are missing or claim not locked.
- Default pass threshold is 0.85.
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from sherlock.models import (
    LockedClaim,
    EvidenceMap,
    ArgumentGraph,
    VerdictDraft,
    LogicAuditResult,
    ArgumentSide,
)


# =============================================================================
# Category Weights (LOCKED - DO NOT MODIFY)
# =============================================================================

AUDIT_WEIGHTS: Dict[str, float] = {
    "clarity": 0.10,
    "evidence_integrity": 0.30,
    "reasoning_validity": 0.25,
    "counterargument_handling": 0.20,
    "scope_control": 0.10,
    "conclusion_discipline": 0.05,
}

DEFAULT_THRESHOLD = 0.85


# =============================================================================
# Scoring Functions
# =============================================================================


def score_clarity(
    locked_claim: LockedClaim,
    verdict: VerdictDraft,
) -> Tuple[float, List[str]]:
    """
    Score clarity of claim and reasoning.

    MUST return score 0.0-1.0 and list of failures.
    Deterministic: based on artifact structure only.
    """
    failures = []
    score = 1.0

    # Check claim is not empty
    if not locked_claim.testable_claim.strip():
        failures.append("Testable claim is empty")
        score -= 0.5

    # Check claim has reasonable length (not too short)
    if len(locked_claim.testable_claim) < 10:
        failures.append("Claim is too short to be meaningful")
        score -= 0.2

    # Check subclaims exist for complex claims
    if len(locked_claim.testable_claim) > 100 and not locked_claim.subclaims:
        failures.append("Complex claim lacks subclaim decomposition")
        score -= 0.2

    # Check verdict has rationale
    if not verdict.rationale_bullets:
        failures.append("Verdict lacks rationale bullets")
        score -= 0.3

    return max(0.0, score), failures


def score_evidence_integrity(
    evidence_map: EvidenceMap,
    locked_claim: LockedClaim,
) -> Tuple[float, List[str]]:
    """
    Score evidence quality and integrity.

    MUST return score 0.0-1.0 and list of failures.
    Deterministic: based on evidence reliability and coverage.
    """
    failures = []

    # No evidence = partial score (investigation may be valid with no evidence)
    if not evidence_map.has_evidence():
        return 0.5, ["No evidence collected"]

    # Calculate average reliability
    avg_reliability = evidence_map.total_reliability()

    # Penalize if all evidence is low tier
    tier_3_count = sum(1 for e in evidence_map.items if e.tier.value == "tier_3")
    if tier_3_count == len(evidence_map.items):
        failures.append("All evidence is tier 3 (low reliability)")
        avg_reliability *= 0.7

    # Check for citation completeness
    missing_citations = sum(1 for e in evidence_map.items if not e.citation.strip())
    if missing_citations > 0:
        failures.append(f"{missing_citations} evidence item(s) lack citations")
        avg_reliability *= 0.9

    return min(1.0, avg_reliability), failures


def score_reasoning_validity(
    argument_graph: ArgumentGraph,
    verdict: VerdictDraft,
) -> Tuple[float, List[str]]:
    """
    Score logical validity of reasoning.

    MUST return score 0.0-1.0 and list of failures.
    Deterministic: based on argument structure.
    """
    failures = []
    score = 1.0

    # Must have at least one argument
    if not argument_graph.nodes:
        failures.append("No arguments in graph")
        return 0.3, failures

    # Check for both pro and con arguments (steelmanning)
    pro_count = argument_graph.pro_count()
    con_count = argument_graph.con_count()

    if pro_count == 0:
        failures.append("No pro arguments present")
        score -= 0.3

    if con_count == 0:
        failures.append("No con arguments present")
        score -= 0.3

    # Check verdict confidence aligns with argument balance
    if pro_count > 0 and con_count > 0:
        balance = pro_count / (pro_count + con_count)
        # If highly confident verdict but balanced arguments, suspicious
        if verdict.confidence > 0.9 and 0.3 < balance < 0.7:
            failures.append("High confidence despite balanced arguments")
            score -= 0.2

    return max(0.0, score), failures


def score_counterargument_handling(
    argument_graph: ArgumentGraph,
) -> Tuple[float, List[str]]:
    """
    Score how well counterarguments are addressed.

    MUST return score 0.0-1.0 and list of failures.
    Deterministic: based on attack relationships in graph.
    """
    failures = []

    if not argument_graph.nodes:
        return 0.5, ["No arguments to evaluate"]

    # Count nodes with attacks (addressing counterarguments)
    nodes_with_attacks = sum(1 for n in argument_graph.nodes if n.attacks)
    total_nodes = len(argument_graph.nodes)

    # At least some nodes should address counterarguments
    attack_ratio = nodes_with_attacks / total_nodes if total_nodes > 0 else 0

    if attack_ratio == 0:
        failures.append("No counterarguments addressed")
        return 0.4, failures

    if attack_ratio < 0.3:
        failures.append("Few counterarguments addressed")

    # Score based on attack engagement
    score = 0.5 + (attack_ratio * 0.5)

    return min(1.0, score), failures


def score_scope_control(
    locked_claim: LockedClaim,
    evidence_map: EvidenceMap,
) -> Tuple[float, List[str]]:
    """
    Score whether investigation stayed within scope.

    MUST return score 0.0-1.0 and list of failures.
    Deterministic: based on assumptions and evidence alignment.
    """
    failures = []
    score = 1.0

    # Check assumptions are explicit
    if not locked_claim.assumptions:
        failures.append("No explicit assumptions stated")
        score -= 0.2

    # Check falsifiability is defined
    if not locked_claim.is_falsifiable():
        failures.append("Claim lacks falsifiability conditions")
        score -= 0.3

    # Evidence should exist if claim is falsifiable
    if locked_claim.is_falsifiable() and not evidence_map.has_evidence():
        failures.append("Falsifiable claim but no evidence gathered")
        score -= 0.2

    return max(0.0, score), failures


def score_conclusion_discipline(
    verdict: VerdictDraft,
    evidence_map: EvidenceMap,
) -> Tuple[float, List[str]]:
    """
    Score whether conclusion is properly bounded.

    MUST return score 0.0-1.0 and list of failures.
    Deterministic: based on confidence vs evidence.
    """
    failures = []
    score = 1.0

    # High confidence requires evidence
    if verdict.confidence > 0.8 and not evidence_map.has_evidence():
        failures.append("High confidence verdict without evidence")
        score -= 0.4

    # Extreme verdicts require high confidence
    extreme_verdicts = {"true", "false"}
    if verdict.verdict.value in extreme_verdicts and verdict.confidence < 0.7:
        failures.append("Extreme verdict with low confidence")
        score -= 0.3

    # Check score breakdown exists
    if not verdict.score_breakdown:
        failures.append("Verdict lacks score breakdown")
        score -= 0.2

    return max(0.0, score), failures


# =============================================================================
# Main Audit Function
# =============================================================================


def run_logic_audit(
    version: int,
    locked_claim: LockedClaim,
    evidence_map: EvidenceMap,
    argument_graph: ArgumentGraph,
    verdict: VerdictDraft,
    threshold: float = DEFAULT_THRESHOLD,
) -> LogicAuditResult:
    """
    Run the full logic audit on an iteration's artifacts.

    MUST:
    - Score all categories using deterministic scoring functions
    - Compute weighted score
    - Determine pass/fail based on threshold
    - Collect all failures

    Args:
        version: Iteration version number
        locked_claim: The locked claim artifact
        evidence_map: The evidence map artifact
        argument_graph: The argument graph artifact
        verdict: The verdict draft artifact
        threshold: Pass threshold (default 0.85)

    Returns:
        LogicAuditResult with pass/fail, scores, and failures
    """
    all_failures: List[str] = []
    category_scores: Dict[str, float] = {}

    # Validate artifacts exist and have correct version
    if locked_claim.version != version:
        all_failures.append(f"LockedClaim version mismatch: {locked_claim.version} != {version}")
    if evidence_map.version != version:
        all_failures.append(f"EvidenceMap version mismatch: {evidence_map.version} != {version}")
    if argument_graph.version != version:
        all_failures.append(f"ArgumentGraph version mismatch: {argument_graph.version} != {version}")
    if verdict.version != version:
        all_failures.append(f"VerdictDraft version mismatch: {verdict.version} != {version}")

    # Score each category
    clarity_score, clarity_failures = score_clarity(locked_claim, verdict)
    category_scores["clarity"] = clarity_score
    all_failures.extend(clarity_failures)

    evidence_score, evidence_failures = score_evidence_integrity(evidence_map, locked_claim)
    category_scores["evidence_integrity"] = evidence_score
    all_failures.extend(evidence_failures)

    reasoning_score, reasoning_failures = score_reasoning_validity(argument_graph, verdict)
    category_scores["reasoning_validity"] = reasoning_score
    all_failures.extend(reasoning_failures)

    counter_score, counter_failures = score_counterargument_handling(argument_graph)
    category_scores["counterargument_handling"] = counter_score
    all_failures.extend(counter_failures)

    scope_score, scope_failures = score_scope_control(locked_claim, evidence_map)
    category_scores["scope_control"] = scope_score
    all_failures.extend(scope_failures)

    conclusion_score, conclusion_failures = score_conclusion_discipline(verdict, evidence_map)
    category_scores["conclusion_discipline"] = conclusion_score
    all_failures.extend(conclusion_failures)

    # Compute weighted score
    weighted_score = sum(
        category_scores[cat] * weight
        for cat, weight in AUDIT_WEIGHTS.items()
    )

    # Determine pass/fail
    passed = weighted_score >= threshold and len(all_failures) == 0

    # If score meets threshold but has failures, still fail
    if weighted_score >= threshold and all_failures:
        passed = False

    return LogicAuditResult(
        version=version,
        passed=passed,
        threshold=threshold,
        category_scores=category_scores,
        weighted_score=round(weighted_score, 4),
        failures=all_failures,
    )


def get_audit_weights() -> Dict[str, float]:
    """Return the audit category weights (read-only copy)."""
    return AUDIT_WEIGHTS.copy()
