# SYSTEM_CONTRACT_SDS.md
# Sherlock–DNA Sync (SDS) Contract

**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-01-29

---

## 1. Purpose

This contract defines how Sherlock investigation outputs flow into the DNA Matrix system. It establishes the synchronization protocol between the "truth-finding" layer (Sherlock) and the "change-representation" layer (DNA Matrix).

### 1.1 Goals

- Define unambiguous dataflow between Sherlock and DNA Matrix
- Prevent silent mutations to application state
- Ensure audit gates control downstream effects
- Maintain separation of concerns: Sherlock decides truth, DNA represents change

### 1.2 Non-Goals

- This contract does NOT define Sherlock's internal investigation logic
- This contract does NOT define UI rendering or presentation
- This contract does NOT define external API exposure
- This contract does NOT authorize network calls from Sherlock

---

## 2. Dataflow Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌────────────┐     ┌─────┐
│   Airlock   │ ──▶ │   Pipeline   │ ──▶ │   Sherlock    │ ──▶ │ DNA Matrix │ ──▶ │ UI  │
│  (Input)    │     │ (Transform)  │     │ (Investigate) │     │  (Store)   │     │     │
└─────────────┘     └──────────────┘     └───────────────┘     └────────────┘     └─────┘
                                                │
                                                ▼
                                         [Audit Gate]
                                                │
                                    ┌───────────┴───────────┐
                                    │                       │
                              PASS (≥0.85)            FAIL (<0.85)
                                    │                       │
                                    ▼                       ▼
                             DNA Accepts            DNA Rejects
                             (persist)              (no persist)
```

### 2.1 Stage Definitions

| Stage | Owner | Input | Output | Constraints |
|-------|-------|-------|--------|-------------|
| Airlock | App | Raw user input | NormalizedInput | MUST sanitize, MUST validate schema |
| Pipeline | App | NormalizedInput | PipelineResponse | MAY call Sherlock, MUST NOT mutate state |
| Sherlock | Library | ClaimInput | FinalReport | MUST NOT call network, MUST be deterministic |
| DNA Matrix | App | FinalReport | DNA Primitives | MUST respect audit gate, MUST log all changes |
| UI | App | DNA Primitives | HTML | MUST be read-only render |

### 2.2 Sherlock Invocation (Optional)

Sherlock is invoked by Pipeline when:
- User requests investigation/verification
- Claim requires truth assessment
- Conflict detection is needed

Sherlock is NOT invoked for:
- Simple CRUD operations
- Read-only queries
- Cached responses

---

## 3. Input/Output Contracts

### 3.1 Sherlock Input (ClaimInput)

```json
{
  "claim_text": "string (required, min 1 char)",
  "iterations": "integer (default 3, range 1-10)",
  "validation_threshold": "float (default 0.85, range 0.0-1.0)",
  "scope": "object (optional, investigation constraints)",
  "evidence_policy": "object (optional, evidence gathering rules)",
  "tone": "string (optional)",
  "time_bounds": "object (optional, temporal constraints)",
  "prior_assumptions": "array of strings (optional)"
}
```

### 3.2 Sherlock Output (FinalReport)

```json
{
  "iterations": "integer (completed count)",
  "final_verdict": {
    "version": "integer",
    "verdict": "enum: true|likely_true|unclear|likely_false|false|non_falsifiable",
    "confidence": "float (0.0-1.0)",
    "score_breakdown": "object (component scores)",
    "rationale_bullets": "array of strings"
  },
  "publishable_report": {
    "claim": "string",
    "verdict": "string",
    "confidence": "float",
    "iterations": "integer",
    "rationale": "array of strings"
  },
  "algorithm_evolution_report": {
    "iterations": "integer",
    "audit_scores": "array of floats",
    "final_passed": "boolean",
    "mutations_proposed": "integer"
  },
  "logic_audit_appendix": "array of LogicAuditResult",
  "mutation_log": "array of MutationEvent (empty if mutations disabled)"
}
```

### 3.3 DNA Matrix Input (from Sherlock)

DNA Matrix MUST receive:
- `FinalReport.final_verdict` - for baseline/projection decisions
- `FinalReport.logic_audit_appendix[-1]` - for gate check
- `FinalReport.publishable_report` - for UI rendering

DNA Matrix MUST NOT receive:
- Internal iteration artifacts (except via audit appendix)
- Mutation proposals (logged but not acted upon)

---

## 4. Invariants (MUST be enforced)

### 4.1 Sherlock Decides Truth

```
INVARIANT: Sherlock is the ONLY source of truth assessment.
           DNA Matrix MUST NOT override Sherlock verdicts.
           DNA Matrix MUST NOT invent verdicts without Sherlock.
```

### 4.2 DNA Represents Change

```
INVARIANT: DNA Matrix is the ONLY persistence layer.
           Sherlock MUST NOT write to any data store.
           Sherlock MUST NOT modify application state.
```

### 4.3 Audit Gate is Final

```
INVARIANT: If audit.passed == false, DNA MUST NOT persist changes.
           No bypass mechanism SHALL exist.
           Failed audits MUST be logged with full context.
```

### 4.4 No Silent Mutation

```
INVARIANT: Every DNA state change MUST be traceable to:
           1. A Sherlock FinalReport, OR
           2. An explicit user action (logged)

           Silent mutations are FORBIDDEN.
           Background jobs MUST NOT modify DNA state without audit.
```

---

## 5. Explicit Rules

### 5.1 When DNA Accepts Changes

DNA Matrix SHALL persist changes when ALL conditions are met:

1. `FinalReport.logic_audit_appendix[-1].passed == true`
2. `FinalReport.logic_audit_appendix[-1].weighted_score >= threshold`
3. `FinalReport.final_verdict.verdict != "non_falsifiable"`
4. No schema validation errors in the report

### 5.2 When DNA Rejects Changes

DNA Matrix SHALL reject and log when ANY condition is met:

1. Audit failed (`passed == false`)
2. Weighted score below threshold
3. Verdict is `non_falsifiable`
4. Schema validation failed
5. Required fields missing

### 5.3 Rejection Handling

When changes are rejected:
- Log the rejection with full FinalReport
- Return rejection reason to Pipeline
- UI displays "investigation incomplete" message
- NO state mutation occurs

---

## 6. Versioning

### 6.1 Contract Version

This contract follows semantic versioning:
- MAJOR: Breaking changes to dataflow or invariants
- MINOR: New optional fields, backward-compatible
- PATCH: Clarifications, typo fixes

### 6.2 Report Version

Each FinalReport is self-versioned via `iterations` count.
Version mismatches between components MUST be logged.

---

## 7. Error Handling

### 7.1 Sherlock Errors

| Error | DNA Response | Persistence |
|-------|--------------|-------------|
| Timeout | Reject | NO |
| Non-falsifiable claim | Reject | NO |
| Evidence ceiling | Accept if audit passed | CONDITIONAL |
| Internal error | Reject | NO |

### 7.2 DNA Errors

| Error | Response | Recovery |
|-------|----------|----------|
| Schema mismatch | Log + reject | Notify upstream |
| Storage failure | Retry 3x | Fail with logged state |
| Conflict detected | Create Conflict primitive | Persist conflict |

---

## 8. Compliance Checklist

Before any SDS-touching code is merged:

- [ ] Sherlock remains network-free
- [ ] Sherlock remains deterministic
- [ ] Audit gate cannot be bypassed
- [ ] All state changes are logged
- [ ] No silent mutations introduced
- [ ] Contract version updated if changed

---

## References

- `docs/contracts/SCH_SDK_CONTRACT.md` - Sherlock library contract
- `docs/contracts/DNA_PRIMITIVES_CONTRACT.md` - DNA primitive schemas
- `docs/mappings/MAP_SHERLOCK_TO_DNA.md` - Translation layer
