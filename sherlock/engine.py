# sherlock/engine.py
"""
Sherlock Mode v1 - Investigation Engine

Implements the 6-step canonical investigation loop:
1. Claim Lock - Lock the claim for investigation
2. Evidence Map - Gather and map evidence
3. Argument Graph - Build pro/con argument graph
4. Scoring/Verdict - Score and draft verdict
5. Logic Audit Gate - Validate investigation quality
6. Handoff - Prepare final output

Constraints:
- MUST NOT mutate application state or persistence.
- MUST NOT call external network/web.
- MUST be deterministic: same input => same output.
- Mutations are OFF by default.
"""
from __future__ import annotations

import hashlib
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sherlock.models import (
    ClaimInput,
    LockedClaim,
    EvidenceItem,
    EvidenceMap,
    EvidenceTier,
    ArgumentNode,
    ArgumentGraph,
    ArgumentSide,
    VerdictDraft,
    VerdictLevel,
    LogicAuditResult,
    MutationEvent,
    IterationArtifacts,
    FinalReport,
)
from sherlock.audit import run_logic_audit, DEFAULT_THRESHOLD
from sherlock.mutation import propose_mutations


# =============================================================================
# Stop Condition Evaluators
# =============================================================================


def _is_non_falsifiable(locked_claim: LockedClaim) -> bool:
    """
    Check if claim is non-falsifiable (no falsifiability conditions).

    Non-falsifiable claims trigger early stop.
    """
    return not locked_claim.is_falsifiable()


def _is_evidence_ceiling_reached(evidence_map: EvidenceMap, iteration: int) -> bool:
    """
    Check if evidence ceiling is reached.

    Evidence ceiling is reached when:
    - No new evidence can be gathered (skeleton: no evidence after iteration 1)
    - Evidence reliability is maxed out
    """
    # Skeleton implementation: ceiling after iteration 2 if no evidence
    if iteration >= 2 and not evidence_map.has_evidence():
        return True
    return False


# =============================================================================
# Sherlock Engine
# =============================================================================


class SherlockEngine:
    """
    Main Sherlock investigation engine.

    Implements the 6-step canonical loop with iteration support.
    Produces structured artifacts at each step.

    Constraints:
    - MUST NOT call external network.
    - MUST NOT mutate application state.
    - Mutations are OFF by default.
    """

    def __init__(self, mutations_enabled: bool = False):
        """
        Initialize the Sherlock engine.

        Args:
            mutations_enabled: Whether to enable mutation proposals (default False)
        """
        self.mutations_enabled = mutations_enabled

    def run(self, input: ClaimInput) -> FinalReport:
        """
        Run a full Sherlock investigation.

        MUST:
        - Run up to input.iterations iterations
        - Stop early if: audit passes, claim is non-falsifiable, or evidence ceiling
        - Produce FinalReport with all artifacts

        Args:
            input: The claim input to investigate

        Returns:
            FinalReport containing all investigation results
        """
        iterations_completed = 0
        all_artifacts: List[IterationArtifacts] = []
        all_mutations: List[MutationEvent] = []
        all_audits: List[LogicAuditResult] = []

        prior_artifacts: Optional[IterationArtifacts] = None
        final_verdict: Optional[VerdictDraft] = None

        for i in range(1, input.iterations + 1):
            # Run iteration
            artifacts = self.run_iteration(i, prior_artifacts, input)
            all_artifacts.append(artifacts)
            all_audits.append(artifacts.audit)
            all_mutations.extend(artifacts.mutations)
            iterations_completed = i
            final_verdict = artifacts.verdict

            # Check stop conditions
            if artifacts.audit.passed:
                # Audit passed - investigation complete
                break

            if _is_non_falsifiable(artifacts.locked_claim):
                # Non-falsifiable claim - stop and mark verdict
                final_verdict = VerdictDraft(
                    version=i,
                    verdict=VerdictLevel.NON_FALSIFIABLE,
                    confidence=1.0,
                    score_breakdown={"non_falsifiable": 1.0},
                    rationale_bullets=["Claim lacks falsifiability conditions"],
                )
                break

            if _is_evidence_ceiling_reached(artifacts.evidence_map, i):
                # Evidence ceiling - use current verdict
                break

            # Prepare for next iteration
            prior_artifacts = artifacts

        # Determine final verdict based on audit trend
        if final_verdict is None:
            final_verdict = self._compute_fallback_verdict(all_audits, iterations_completed)

        # Build final report
        return self._build_final_report(
            iterations_completed=iterations_completed,
            final_verdict=final_verdict,
            all_artifacts=all_artifacts,
            all_audits=all_audits,
            all_mutations=all_mutations,
            input=input,
        )

    def run_iteration(
        self,
        n: int,
        prior: Optional[IterationArtifacts],
        input: ClaimInput,
    ) -> IterationArtifacts:
        """
        Run a single investigation iteration.

        MUST:
        - Execute all 6 steps in order
        - Produce IterationArtifacts with matching version numbers

        Args:
            n: Iteration number (1-indexed)
            prior: Artifacts from previous iteration (None for first)
            input: Original claim input

        Returns:
            IterationArtifacts for this iteration
        """
        # Step 1: Claim Lock
        locked_claim = self.step_claim_lock(n, input, prior)

        # Step 2: Evidence Map
        evidence_map = self.step_evidence_map(n, locked_claim, input, prior)

        # Step 3: Argument Graph
        argument_graph = self.step_argument_graph(n, locked_claim, evidence_map, prior)

        # Step 4: Scoring/Verdict
        verdict = self.step_scoring_verdict(n, locked_claim, evidence_map, argument_graph)

        # Step 5: Logic Audit Gate
        audit = self.step_logic_audit_gate(
            n, locked_claim, evidence_map, argument_graph, verdict, input.validation_threshold
        )

        # Step 6: Handoff (mutation proposals)
        mutations = self.step_handoff(n, audit, locked_claim, evidence_map, argument_graph)

        return IterationArtifacts(
            version=n,
            locked_claim=locked_claim,
            evidence_map=evidence_map,
            argument_graph=argument_graph,
            verdict=verdict,
            audit=audit,
            mutations=mutations,
        )

    # =========================================================================
    # Step 1: Claim Lock
    # =========================================================================

    def step_claim_lock(
        self,
        version: int,
        input: ClaimInput,
        prior: Optional[IterationArtifacts],
    ) -> LockedClaim:
        """
        Lock the claim for investigation.

        MUST:
        - Produce a testable, unambiguous claim
        - Decompose into subclaims if complex
        - Identify assumptions
        - Define falsifiability conditions

        Returns:
            LockedClaim artifact
        """
        claim_text = input.claim_text.strip()

        # Generate deterministic subclaims based on claim structure
        subclaims = self._decompose_claim(claim_text)

        # Extract assumptions from prior_assumptions or derive from claim
        assumptions = list(input.prior_assumptions) if input.prior_assumptions else []
        if not assumptions:
            assumptions = self._derive_assumptions(claim_text)

        # Generate falsifiability conditions
        falsifiability = self._generate_falsifiability(claim_text)

        return LockedClaim(
            version=version,
            testable_claim=claim_text,
            subclaims=subclaims,
            assumptions=assumptions,
            falsifiability=falsifiability,
        )

    def _decompose_claim(self, claim_text: str) -> List[str]:
        """Decompose claim into subclaims (deterministic heuristic)."""
        # Simple decomposition: split on conjunctions
        subclaims = []

        # Check for "and" conjunctions
        if " and " in claim_text.lower():
            parts = claim_text.lower().split(" and ")
            subclaims.extend([p.strip().capitalize() for p in parts if len(p.strip()) > 5])

        # If claim is long, create a subclaim about scope
        if len(claim_text) > 100:
            subclaims.append("Claim scope is well-defined")

        return subclaims

    def _derive_assumptions(self, claim_text: str) -> List[str]:
        """Derive implicit assumptions from claim (deterministic)."""
        assumptions = []

        # Common assumption patterns
        if any(word in claim_text.lower() for word in ["will", "should", "must"]):
            assumptions.append("Future predictions assume current conditions persist")

        if any(word in claim_text.lower() for word in ["all", "every", "always"]):
            assumptions.append("Universal quantifier assumes no exceptions")

        if any(word in claim_text.lower() for word in ["best", "worst", "most"]):
            assumptions.append("Superlative assumes complete comparison set")

        if not assumptions:
            assumptions.append("Claim is taken at face value")

        return assumptions

    def _generate_falsifiability(self, claim_text: str) -> List[str]:
        """Generate falsifiability conditions (deterministic)."""
        conditions = []

        # Generate based on claim content
        claim_lower = claim_text.lower()

        # Check for negatable patterns
        if any(word in claim_lower for word in ["is", "are", "will", "can"]):
            conditions.append(f"Finding counter-evidence that contradicts: {claim_text[:50]}...")

        if any(word in claim_lower for word in ["always", "never", "all", "none"]):
            conditions.append("Single counter-example would falsify")

        if any(word in claim_lower for word in ["better", "worse", "more", "less"]):
            conditions.append("Measurable comparison shows opposite result")

        # If no patterns found, claim may be non-falsifiable
        # (empty list triggers non-falsifiable stop condition)

        return conditions

    # =========================================================================
    # Step 2: Evidence Map
    # =========================================================================

    def step_evidence_map(
        self,
        version: int,
        locked_claim: LockedClaim,
        input: ClaimInput,
        prior: Optional[IterationArtifacts],
    ) -> EvidenceMap:
        """
        Gather and map evidence.

        SKELETON BEHAVIOR:
        - Evidence is bounded and non-networked
        - Creates EvidenceMap from input.evidence_policy placeholders
        - Empty by default (no external sources)

        Returns:
            EvidenceMap artifact
        """
        items: List[EvidenceItem] = []

        # If evidence_policy provides mock evidence, use it
        mock_evidence = input.evidence_policy.get("mock_evidence", [])
        for i, mock in enumerate(mock_evidence):
            items.append(EvidenceItem(
                tier=EvidenceTier(mock.get("tier", "tier_2")),
                source_type=mock.get("source_type", "mock"),
                citation=mock.get("citation", f"Mock source {i+1}"),
                summary=mock.get("summary", "Mock evidence summary"),
                reliability=float(mock.get("reliability", 0.7)),
            ))

        # Generate deterministic placeholder evidence based on claim
        if not items and input.evidence_policy.get("generate_placeholder", False):
            items = self._generate_placeholder_evidence(version, locked_claim)

        return EvidenceMap(version=version, items=items)

    def _generate_placeholder_evidence(
        self,
        version: int,
        locked_claim: LockedClaim,
    ) -> List[EvidenceItem]:
        """Generate deterministic placeholder evidence."""
        # Use claim hash for deterministic generation
        claim_hash = hashlib.md5(locked_claim.testable_claim.encode()).hexdigest()
        reliability = 0.5 + (int(claim_hash[:2], 16) / 512)  # 0.5-1.0 range

        return [
            EvidenceItem(
                tier=EvidenceTier.TIER_2,
                source_type="placeholder",
                citation=f"Placeholder evidence for claim hash {claim_hash[:8]}",
                summary="This is placeholder evidence for skeleton testing",
                reliability=round(reliability, 2),
            )
        ]

    # =========================================================================
    # Step 3: Argument Graph
    # =========================================================================

    def step_argument_graph(
        self,
        version: int,
        locked_claim: LockedClaim,
        evidence_map: EvidenceMap,
        prior: Optional[IterationArtifacts],
    ) -> ArgumentGraph:
        """
        Build pro/con argument graph.

        SKELETON BEHAVIOR:
        - Steelman pro/con based on claim text heuristics
        - Simple templates OK

        Returns:
            ArgumentGraph artifact
        """
        nodes: List[ArgumentNode] = []

        # Generate pro argument
        pro_node = ArgumentNode(
            id=f"pro_{version}_1",
            side=ArgumentSide.PRO,
            claim=f"The claim '{locked_claim.testable_claim[:50]}...' is supported by available evidence",
            supports=[],
            attacks=[],
        )
        nodes.append(pro_node)

        # Generate con argument (steelman)
        con_node = ArgumentNode(
            id=f"con_{version}_1",
            side=ArgumentSide.CON,
            claim=f"The claim may be limited by assumptions: {', '.join(locked_claim.assumptions[:2]) if locked_claim.assumptions else 'unstated assumptions'}",
            supports=[],
            attacks=[pro_node.id],  # Con attacks pro
        )
        nodes.append(con_node)

        # Add evidence-based arguments if evidence exists
        if evidence_map.has_evidence():
            evidence_pro = ArgumentNode(
                id=f"pro_{version}_2",
                side=ArgumentSide.PRO,
                claim=f"Evidence supports claim with {evidence_map.total_reliability():.0%} average reliability",
                supports=[pro_node.id],
                attacks=[],
            )
            nodes.append(evidence_pro)

        # Add subclaim arguments
        for i, subclaim in enumerate(locked_claim.subclaims[:2]):
            subclaim_node = ArgumentNode(
                id=f"pro_{version}_sub_{i}",
                side=ArgumentSide.PRO,
                claim=f"Subclaim: {subclaim}",
                supports=[pro_node.id],
                attacks=[],
            )
            nodes.append(subclaim_node)

        return ArgumentGraph(version=version, nodes=nodes)

    # =========================================================================
    # Step 4: Scoring / Verdict
    # =========================================================================

    def step_scoring_verdict(
        self,
        version: int,
        locked_claim: LockedClaim,
        evidence_map: EvidenceMap,
        argument_graph: ArgumentGraph,
    ) -> VerdictDraft:
        """
        Score and draft verdict.

        MUST be deterministic based on artifacts.

        Returns:
            VerdictDraft artifact
        """
        score_breakdown: Dict[str, float] = {}

        # Score components
        evidence_score = evidence_map.total_reliability() if evidence_map.has_evidence() else 0.3
        score_breakdown["evidence"] = evidence_score

        # Argument balance score
        pro_count = argument_graph.pro_count()
        con_count = argument_graph.con_count()
        total_args = pro_count + con_count
        balance_score = pro_count / total_args if total_args > 0 else 0.5
        score_breakdown["argument_balance"] = balance_score

        # Falsifiability score
        falsifiability_score = 1.0 if locked_claim.is_falsifiable() else 0.0
        score_breakdown["falsifiability"] = falsifiability_score

        # Compute overall score
        overall_score = (
            evidence_score * 0.4 +
            balance_score * 0.3 +
            falsifiability_score * 0.3
        )
        score_breakdown["overall"] = round(overall_score, 4)

        # Determine verdict based on score
        verdict, confidence = self._score_to_verdict(overall_score)

        # Build rationale
        rationale = self._build_rationale(
            evidence_map, argument_graph, locked_claim, overall_score
        )

        return VerdictDraft(
            version=version,
            verdict=verdict,
            confidence=confidence,
            score_breakdown=score_breakdown,
            rationale_bullets=rationale,
        )

    def _score_to_verdict(self, score: float) -> tuple[VerdictLevel, float]:
        """Convert score to verdict and confidence (deterministic)."""
        if score >= 0.85:
            return VerdictLevel.TRUE, min(score, 0.95)
        elif score >= 0.7:
            return VerdictLevel.LIKELY_TRUE, score
        elif score >= 0.5:
            return VerdictLevel.UNCLEAR, 0.5 + (score - 0.5)
        elif score >= 0.3:
            return VerdictLevel.LIKELY_FALSE, 1.0 - score
        else:
            return VerdictLevel.FALSE, min(1.0 - score, 0.95)

    def _build_rationale(
        self,
        evidence_map: EvidenceMap,
        argument_graph: ArgumentGraph,
        locked_claim: LockedClaim,
        score: float,
    ) -> List[str]:
        """Build rationale bullets (deterministic)."""
        rationale = []

        # Evidence rationale
        if evidence_map.has_evidence():
            rationale.append(
                f"Evidence reliability: {evidence_map.total_reliability():.0%} "
                f"({len(evidence_map.items)} items)"
            )
        else:
            rationale.append("No evidence was gathered for this claim")

        # Argument rationale
        pro = argument_graph.pro_count()
        con = argument_graph.con_count()
        rationale.append(f"Argument balance: {pro} pro, {con} con")

        # Falsifiability rationale
        if locked_claim.is_falsifiable():
            rationale.append(
                f"Claim is falsifiable with {len(locked_claim.falsifiability)} condition(s)"
            )
        else:
            rationale.append("Claim lacks falsifiability conditions")

        # Score summary
        rationale.append(f"Overall score: {score:.2f}")

        return rationale

    # =========================================================================
    # Step 5: Logic Audit Gate
    # =========================================================================

    def step_logic_audit_gate(
        self,
        version: int,
        locked_claim: LockedClaim,
        evidence_map: EvidenceMap,
        argument_graph: ArgumentGraph,
        verdict: VerdictDraft,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> LogicAuditResult:
        """
        Run logic audit gate.

        Delegates to sherlock.audit.run_logic_audit.

        Returns:
            LogicAuditResult artifact
        """
        return run_logic_audit(
            version=version,
            locked_claim=locked_claim,
            evidence_map=evidence_map,
            argument_graph=argument_graph,
            verdict=verdict,
            threshold=threshold,
        )

    # =========================================================================
    # Step 6: Handoff
    # =========================================================================

    def step_handoff(
        self,
        version: int,
        audit: LogicAuditResult,
        locked_claim: LockedClaim,
        evidence_map: EvidenceMap,
        argument_graph: ArgumentGraph,
    ) -> List[MutationEvent]:
        """
        Prepare handoff and mutation proposals.

        MUST NOT auto-apply mutations.
        Returns empty list if mutations disabled.

        Returns:
            List of proposed MutationEvents
        """
        return propose_mutations(
            version=version,
            audit_result=audit,
            locked_claim=locked_claim,
            evidence_map=evidence_map,
            argument_graph=argument_graph,
            mutations_enabled=self.mutations_enabled,
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _compute_fallback_verdict(
        self,
        all_audits: List[LogicAuditResult],
        iterations: int,
    ) -> VerdictDraft:
        """
        Compute fallback verdict when no audit passed.

        Rule: If audit score trend is improving, use "Unclear".
        If trend is declining or flat, use "Likely false".
        """
        if not all_audits:
            return VerdictDraft(
                version=iterations,
                verdict=VerdictLevel.UNCLEAR,
                confidence=0.5,
                score_breakdown={"fallback": 1.0},
                rationale_bullets=["No audits completed"],
            )

        # Check score trend
        scores = [a.weighted_score for a in all_audits]
        if len(scores) >= 2:
            trend = scores[-1] - scores[0]
            improving = trend > 0.05
        else:
            improving = False

        if improving:
            verdict = VerdictLevel.UNCLEAR
            rationale = ["Audit scores improving but threshold not met"]
        else:
            verdict = VerdictLevel.LIKELY_FALSE
            rationale = ["Audit scores flat or declining, threshold not met"]

        return VerdictDraft(
            version=iterations,
            verdict=verdict,
            confidence=max(scores) if scores else 0.5,
            score_breakdown={"trend": scores[-1] if scores else 0.0},
            rationale_bullets=rationale,
        )

    def _build_final_report(
        self,
        iterations_completed: int,
        final_verdict: VerdictDraft,
        all_artifacts: List[IterationArtifacts],
        all_audits: List[LogicAuditResult],
        all_mutations: List[MutationEvent],
        input: ClaimInput,
    ) -> FinalReport:
        """Build the final report from all artifacts."""
        # Build publishable report
        publishable = {
            "claim": input.claim_text,
            "verdict": final_verdict.verdict.value,
            "confidence": final_verdict.confidence,
            "iterations": iterations_completed,
            "rationale": final_verdict.rationale_bullets,
        }

        # Build algorithm evolution report
        evolution = {
            "iterations": iterations_completed,
            "audit_scores": [a.weighted_score for a in all_audits],
            "final_passed": all_audits[-1].passed if all_audits else False,
            "mutations_proposed": len(all_mutations),
        }

        return FinalReport(
            iterations=iterations_completed,
            final_verdict=final_verdict,
            publishable_report=publishable,
            algorithm_evolution_report=evolution,
            logic_audit_appendix=all_audits,
            mutation_log=all_mutations,
        )
