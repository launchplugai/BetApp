# sherlock/mutation.py
"""
Sherlock Mode v1 - Mutation System

Mutations allow the investigation to adapt based on audit failures.
Mutations are OFF by default and must be explicitly enabled.

Constraints:
- MUST NOT auto-apply mutations.
- MUST log all proposed mutations.
- MUST NOT mutate application state or persistence.
- Mutations are proposals only; engine decides whether to apply.
"""
from __future__ import annotations

from typing import List, Optional
from dataclasses import dataclass

from sherlock.models import (
    MutationEvent,
    LogicAuditResult,
    LockedClaim,
    EvidenceMap,
    ArgumentGraph,
)


# =============================================================================
# Mutation Proposal Functions
# =============================================================================


def propose_mutation_for_clarity(
    version: int,
    failures: List[str],
    locked_claim: LockedClaim,
) -> Optional[MutationEvent]:
    """
    Propose a mutation to improve clarity.

    Returns MutationEvent or None if no mutation needed.
    """
    clarity_failures = [f for f in failures if "clarity" in f.lower() or "claim" in f.lower()]

    if not clarity_failures:
        return None

    return MutationEvent(
        version=version,
        trigger=f"Clarity failures: {clarity_failures[0]}",
        change="Refine claim to be more specific and testable",
        risk="May narrow scope too much",
        expected_benefit="Improved clarity score by 0.1-0.2",
        observed_outcome=None,
    )


def propose_mutation_for_evidence(
    version: int,
    failures: List[str],
    evidence_map: EvidenceMap,
) -> Optional[MutationEvent]:
    """
    Propose a mutation to improve evidence integrity.

    Returns MutationEvent or None if no mutation needed.
    """
    evidence_failures = [f for f in failures if "evidence" in f.lower() or "citation" in f.lower()]

    if not evidence_failures:
        return None

    if not evidence_map.has_evidence():
        return MutationEvent(
            version=version,
            trigger="No evidence collected",
            change="Expand evidence search parameters",
            risk="May introduce lower-tier evidence",
            expected_benefit="Evidence integrity score improvement",
            observed_outcome=None,
        )

    return MutationEvent(
        version=version,
        trigger=f"Evidence issue: {evidence_failures[0]}",
        change="Seek higher-tier evidence sources",
        risk="May not find additional evidence",
        expected_benefit="Improved evidence reliability score",
        observed_outcome=None,
    )


def propose_mutation_for_reasoning(
    version: int,
    failures: List[str],
    argument_graph: ArgumentGraph,
) -> Optional[MutationEvent]:
    """
    Propose a mutation to improve reasoning validity.

    Returns MutationEvent or None if no mutation needed.
    """
    reasoning_failures = [f for f in failures if "argument" in f.lower() or "reasoning" in f.lower()]

    if not reasoning_failures:
        return None

    pro_count = argument_graph.pro_count()
    con_count = argument_graph.con_count()

    if pro_count == 0 or con_count == 0:
        missing = "pro" if pro_count == 0 else "con"
        return MutationEvent(
            version=version,
            trigger=f"Missing {missing} arguments",
            change=f"Generate steelman {missing} arguments",
            risk="Generated arguments may be weak",
            expected_benefit="Balanced argument graph",
            observed_outcome=None,
        )

    return MutationEvent(
        version=version,
        trigger=f"Reasoning issue: {reasoning_failures[0]}",
        change="Strengthen logical connections between arguments",
        risk="May overcomplicate reasoning",
        expected_benefit="Improved reasoning validity score",
        observed_outcome=None,
    )


def propose_mutation_for_counterarguments(
    version: int,
    failures: List[str],
    argument_graph: ArgumentGraph,
) -> Optional[MutationEvent]:
    """
    Propose a mutation to improve counterargument handling.

    Returns MutationEvent or None if no mutation needed.
    """
    counter_failures = [f for f in failures if "counter" in f.lower()]

    if not counter_failures:
        return None

    return MutationEvent(
        version=version,
        trigger=f"Counterargument issue: {counter_failures[0]}",
        change="Add explicit attack relationships to address counterarguments",
        risk="May weaken main position",
        expected_benefit="Improved counterargument handling score",
        observed_outcome=None,
    )


# =============================================================================
# Main Mutation Proposal Function
# =============================================================================


def propose_mutations(
    version: int,
    audit_result: LogicAuditResult,
    locked_claim: LockedClaim,
    evidence_map: EvidenceMap,
    argument_graph: ArgumentGraph,
    mutations_enabled: bool = False,
) -> List[MutationEvent]:
    """
    Propose mutations based on audit failures.

    MUST NOT auto-apply mutations.
    MUST return empty list if mutations_enabled is False.

    Args:
        version: Current iteration version
        audit_result: The logic audit result
        locked_claim: Current locked claim
        evidence_map: Current evidence map
        argument_graph: Current argument graph
        mutations_enabled: Whether mutations are enabled (default False)

    Returns:
        List of proposed MutationEvents (empty if disabled or no failures)
    """
    # Mutations are OFF by default
    if not mutations_enabled:
        return []

    # No mutations needed if audit passed
    if audit_result.passed:
        return []

    mutations: List[MutationEvent] = []

    # Propose mutations for each failure category
    clarity_mutation = propose_mutation_for_clarity(
        version, audit_result.failures, locked_claim
    )
    if clarity_mutation:
        mutations.append(clarity_mutation)

    evidence_mutation = propose_mutation_for_evidence(
        version, audit_result.failures, evidence_map
    )
    if evidence_mutation:
        mutations.append(evidence_mutation)

    reasoning_mutation = propose_mutation_for_reasoning(
        version, audit_result.failures, argument_graph
    )
    if reasoning_mutation:
        mutations.append(reasoning_mutation)

    counter_mutation = propose_mutation_for_counterarguments(
        version, audit_result.failures, argument_graph
    )
    if counter_mutation:
        mutations.append(counter_mutation)

    return mutations


def apply_mutation_outcome(
    mutation: MutationEvent,
    outcome: str,
) -> MutationEvent:
    """
    Create a new MutationEvent with observed outcome.

    Returns a new MutationEvent (immutable pattern).
    """
    return MutationEvent(
        version=mutation.version,
        trigger=mutation.trigger,
        change=mutation.change,
        risk=mutation.risk,
        expected_benefit=mutation.expected_benefit,
        observed_outcome=outcome,
    )
