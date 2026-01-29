# MAP_SHERLOCK_TO_DNA.md
# Sherlock → DNA Matrix Translation Layer

**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-01-29

---

## 1. Purpose

This document defines the exact translation rules for converting Sherlock investigation artifacts into DNA Matrix primitives. This is the "USB-C adapter" between truth-finding (Sherlock) and change-representation (DNA).

### 1.1 Translation Principle

```
Sherlock produces: Investigation artifacts (claims, evidence, verdicts)
DNA stores: State primitives (weights, constraints, conflicts, etc.)

This document maps: Sherlock artifact → DNA primitive(s)
```

---

## 2. Mapping Table

### 2.1 Primary Mappings

| Sherlock Artifact | DNA Primitive(s) | Mapping Rule |
|-------------------|------------------|--------------|
| `LockedClaim` | `Constraint` (multiple) | Each assumption → one Constraint |
| `LockedClaim.testable_claim` | `Baseline.snapshot.claim` | Claim text stored in baseline |
| `EvidenceMap.items` | `Lineage` + `Weight` | Each evidence → lineage record + weight |
| `ArgumentGraph.nodes` | `Conflict` (conditional) | Pro/con pairs → potential conflicts |
| `VerdictDraft` | `Baseline` or `Drift` | Depends on audit pass/fail |
| `LogicAuditResult` | Gate (no primitive) | Controls persistence, not stored |
| `MutationEvent` | Not persisted | Logged in Sherlock report only |

### 2.2 Detailed Mappings

#### 2.2.1 LockedClaim → Constraints

```
FOR EACH assumption IN LockedClaim.assumptions:
    CREATE Constraint:
        constraint_type = "assumption"
        expression = assumption
        scope = LockedClaim.testable_claim
        source_claim_id = {investigation_id}
```

**Rule:** Assumptions become explicit Constraints to track what was assumed.

#### 2.2.2 EvidenceMap → Lineage + Weight

```
FOR EACH item IN EvidenceMap.items:
    CREATE Lineage:
        entity_type = "evidence"
        entity_id = {generated_uuid}
        operation = "create"
        actor = "sherlock"
        sherlock_report_id = {report_id}

    CREATE Weight:
        target_type = "evidence"
        target_id = {same entity_id}
        value = item.reliability
        source = "sherlock"
        metadata = {
            "tier": item.tier,
            "source_type": item.source_type,
            "citation": item.citation
        }
```

**Rule:** Evidence creates lineage (provenance) and weight (reliability score).

#### 2.2.3 ArgumentGraph → Conflict Detection

```
FOR EACH pro_node IN ArgumentGraph.nodes WHERE side == "pro":
    FOR EACH con_node IN ArgumentGraph.nodes WHERE side == "con":
        IF con_node.attacks CONTAINS pro_node.id:
            CREATE Conflict:
                conflict_type = "logical"
                parties = [
                    {entity_type: "argument", entity_id: pro_node.id},
                    {entity_type: "argument", entity_id: con_node.id}
                ]
                description = "Pro argument attacked by con: {pro_node.claim} vs {con_node.claim}"
                status = "open"
                detected_by = "sherlock"
```

**Rule:** Attack relationships in argument graph become explicit Conflicts.

#### 2.2.4 VerdictDraft → Baseline/Drift Decision

```
IF audit.passed == true:
    # Verdict becomes authoritative baseline
    CREATE Baseline:
        entity_type = "verdict"
        entity_id = {verdict_id}
        snapshot = VerdictDraft.model_dump()
        reason = "Sherlock investigation passed audit"

ELSE:
    # No baseline created - verdict is not authoritative
    # Optionally create Drift to log the attempt:
    CREATE Drift:
        baseline_id = {prior_baseline_id or null}
        drift_type = "modification"
        delta = {"attempted_verdict": VerdictDraft.model_dump()}
        magnitude = 0.0  # No actual change
        cause = "Sherlock audit failed - verdict not persisted"
        sherlock_report_id = {report_id}
```

**Rule:** Only audited verdicts become baselines. Failed verdicts are logged as drift attempts.

---

## 3. Acceptance Rules

### 3.1 When DNA Accepts Changes

DNA SHALL persist Sherlock results when ALL conditions are met:

| Condition | Check |
|-----------|-------|
| Audit passed | `FinalReport.logic_audit_appendix[-1].passed == true` |
| Score threshold | `weighted_score >= threshold` (default 0.85) |
| Falsifiable claim | `VerdictDraft.verdict != "non_falsifiable"` |
| Schema valid | All required fields present |

### 3.2 When DNA Rejects Changes

DNA SHALL reject and log when ANY condition is met:

| Condition | Response |
|-----------|----------|
| Audit failed | Log rejection, return "audit_failed" |
| Below threshold | Log rejection, return "threshold_not_met" |
| Non-falsifiable | Log rejection, return "non_falsifiable_claim" |
| Schema invalid | Log rejection, return "schema_validation_error" |

### 3.3 Rejection Behavior

```python
def handle_rejection(report: FinalReport, reason: str) -> None:
    # 1. Log the rejection
    log.warning(f"DNA rejected Sherlock report: {reason}")
    log.debug(f"Report: {report.to_json()}")

    # 2. Create drift record (optional, for audit trail)
    create_drift(
        drift_type="modification",
        delta={"rejected_report": report.model_dump()},
        magnitude=0.0,
        cause=f"Rejection: {reason}"
    )

    # 3. NO state mutation
    # 4. Return rejection to caller
```

---

## 4. Conflict Persistence Rules

### 4.1 Conflicts Are Never Deleted

```
INVARIANT: Once a Conflict is created, it MUST NOT be deleted.
           Status may change from "open" to "resolved_by_tradeoff"
           but the record persists forever.
```

### 4.2 Conflict Resolution

```
To resolve a Conflict:
    1. CREATE Tradeoff:
        decision = "Resolution for conflict {conflict_id}"
        benefits = [...]
        costs = [...]
        resolves_conflict_id = {conflict_id}

    2. UPDATE Conflict:
        status = "resolved_by_tradeoff"
        resolution_tradeoff_id = {tradeoff_id}
```

### 4.3 Conflict from Sherlock

When Sherlock detects logical conflicts in ArgumentGraph:

1. Check if conflict already exists (same parties)
2. If not exists: CREATE new Conflict
3. If exists: Leave as-is (do not duplicate)

---

## 5. Tradeoff Requirements

### 5.1 When Tradeoffs Are Required

| Scenario | Tradeoff Required? |
|----------|-------------------|
| Verdict changes from prior baseline | YES |
| Conflict resolution | YES |
| New baseline created | YES |
| Evidence contradicts prior evidence | YES |
| Routine investigation with no changes | NO |

### 5.2 Tradeoff Creation from Sherlock

```python
def create_tradeoff_from_verdict(
    verdict: VerdictDraft,
    prior_baseline: Optional[Baseline]
) -> Tradeoff:
    return Tradeoff(
        decision=f"Accept verdict: {verdict.verdict.value}",
        benefits=verdict.rationale_bullets,
        costs=["May invalidate prior assumptions"],
        alternatives_considered=["Reject investigation", "Request more iterations"],
        accepted_by="sherlock",
        sherlock_report_id=report_id
    )
```

---

## 6. Lineage Chain

### 6.1 Lineage for Sherlock Investigations

Every Sherlock investigation creates a lineage chain:

```
[User Request]
      │
      ▼
[ClaimInput] ─────────────────┐
      │                       │
      ▼                       │
[LockedClaim] ───────────────┐│
      │                      ││
      ▼                      ││
[EvidenceMap] ──────────────┐││
      │                     │││
      ▼                     │││
[ArgumentGraph] ───────────┐│││
      │                    ││││
      ▼                    ││││
[VerdictDraft] ───────────┐│││││
      │                   ││││││
      ▼                   ▼▼▼▼▼▼
[FinalReport] ◄───────────────┘
      │
      ▼
[DNA Primitives] (if audit passed)
```

### 6.2 Lineage Record Structure

```json
{
  "entity_type": "sherlock_investigation",
  "entity_id": "{report_id}",
  "parent_id": null,
  "operation": "create",
  "source_ids": ["{claim_input_hash}"],
  "actor": "sherlock",
  "sherlock_report_id": "{report_id}"
}
```

---

## 7. Weight Propagation

### 7.1 From Sherlock to DNA

| Sherlock Source | DNA Weight.value | DNA Weight.target_type |
|-----------------|------------------|------------------------|
| `EvidenceItem.reliability` | 0.0-1.0 | "evidence" |
| `VerdictDraft.confidence` | 0.0-1.0 | "verdict" |
| `LogicAuditResult.weighted_score` | 0.0-1.0 | "audit" |
| `ArgumentNode` (pro/con balance) | computed | "argument" |

### 7.2 Weight Computation

```python
def compute_argument_weight(graph: ArgumentGraph) -> float:
    """Weight based on pro/con balance."""
    pro = graph.pro_count()
    con = graph.con_count()
    total = pro + con
    if total == 0:
        return 0.5
    return pro / total  # 0.0 = all con, 1.0 = all pro
```

---

## 8. Complete Translation Example

### 8.1 Input: Sherlock FinalReport

```json
{
  "iterations": 2,
  "final_verdict": {
    "version": 2,
    "verdict": "likely_true",
    "confidence": 0.78,
    "score_breakdown": {"evidence": 0.7, "argument_balance": 0.8, "falsifiability": 1.0},
    "rationale_bullets": ["Evidence supports claim", "Counterarguments addressed"]
  },
  "logic_audit_appendix": [
    {"version": 1, "passed": false, "weighted_score": 0.72},
    {"version": 2, "passed": true, "weighted_score": 0.88}
  ]
}
```

### 8.2 Output: DNA Primitives Created

```
1. Baseline (verdict snapshot)
   - entity_type: "verdict"
   - snapshot: {verdict object}
   - reason: "Sherlock investigation passed audit"

2. Weight (verdict confidence)
   - target_type: "verdict"
   - value: 0.78
   - source: "sherlock"

3. Tradeoff (decision record)
   - decision: "Accept verdict: likely_true"
   - benefits: ["Evidence supports claim", "Counterarguments addressed"]
   - accepted_by: "sherlock"

4. Lineage (provenance)
   - entity_type: "sherlock_investigation"
   - operation: "create"
   - actor: "sherlock"
```

---

## 9. Compliance Checklist

Before implementing Sherlock → DNA translation:

- [ ] Audit gate is checked before any persistence
- [ ] Conflicts are created, never deleted
- [ ] Tradeoffs exist for all decisions
- [ ] Lineage chain is complete
- [ ] Weights are in 0.0-1.0 range
- [ ] Rejected reports are logged as drift
- [ ] All primitives have id, version, created_at

---

## References

- `docs/contracts/SCH_SDK_CONTRACT.md` - Sherlock schemas
- `docs/contracts/DNA_PRIMITIVES_CONTRACT.md` - DNA schemas
- `docs/contracts/SYSTEM_CONTRACT_SDS.md` - System dataflow
