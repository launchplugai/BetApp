# DNA Matrix: Conflict Detection v0.1

> Where the system admits that reality contains mutually exclusive truths.

---

## What a Conflict Is

A **conflict** exists when two or more claims cannot simultaneously satisfy the system's constraints given the same baseline and lineage.

| Statement | Meaning |
|-----------|---------|
| Conflicts are not errors | They're valid states |
| Conflicts are not failures | They're detected tensions |
| Conflicts are not optional | They must be surfaced |
| Conflicts are first-class state | They persist, have lineage |

If the system can't represent conflict, it cannot explain choice, tradeoff, or evolution.

---

## Conflict vs Constraint

| Concept | Role |
|---------|------|
| Constraint | Declares what is allowed |
| Conflict | Declares what cannot both be true |
| Tradeoff | Declares what was sacrificed |
| Resolution | Declares what won (temporarily) |

Constraints **detect**.
Conflicts **persist**.
Tradeoffs **explain**.
Lineage **remembers**.

---

## When Conflicts Fire

Exactly **three legal entry points**. No others.

### 1. Explicit Constraint Failure (Direct)

Triggered by constraints that declare incompatibility.

**Canonical trigger**: `exclusion` operator.

```json
{
  "rule": { "op": "exclusion", "args": [...] },
  "onFail": {
    "createConflict": {
      "type": "exclusion-constraint",
      "leftLens": "brand.positioning",
      "rightLens": "brand.discounting.strategy",
      "reason": "luxury cannot coexist with discount-heavy"
    }
  }
}
```

**Interpretation**: These two claims cannot coexist. Not "one is wrong." Incompatible.

---

### 2. Drift Threshold Violation (Self-Conflict)

Triggered when drift exceeds allowed envelope relative to baseline.

```json
{
  "rule": { "op": "weighted_drift_lte", "args": [...] },
  "onFail": {
    "createConflict": {
      "type": "baseline-violation",
      "lens": "org.values.customer_obsession",
      "reason": "drift exceeds 0.3 threshold"
    }
  }
}
```

**Interpretation**: Current state contradicts the system's own past commitments.

This is a **self-conflict**. Most systems silently overwrite baselines. This one doesn't.

---

### 3. Competing Constraint Outcomes (Derived)

Occurs when:
- Two constraints both pass individually
- But their combined implications are mutually exclusive

**Example**:
- Constraint A requires `speed > 0.8`
- Constraint B requires `safety > 0.9`
- Physical constraint: `speed + safety ≤ 1.2`

Neither constraint is wrong. The combination is impossible.

This creates a **derived conflict**.

---

## Conflict Types

| Type | Description | Source |
|------|-------------|--------|
| `exclusion-constraint` | Two claims declared incompatible | `exclusion` operator |
| `baseline-violation` | Claim drifted beyond threshold | `weighted_drift_lte` |
| `derived` | Combined constraints impossible | Inference engine |

---

## Conflict Object

```json
{
  "id": "cfl_01J8K9M2N3P4Q5R6",
  "type": "exclusion-constraint",
  "status": "active",
  "severity": "high",
  "organismId": "org_7b3f8a2c",
  "claims": [
    {
      "claimId": "clm_abc123",
      "lens": "brand.positioning",
      "value": "luxury",
      "weight": 0.83
    },
    {
      "claimId": "clm_def456",
      "lens": "brand.discounting.strategy",
      "value": "discount-heavy",
      "weight": 0.6
    }
  ],
  "origin": {
    "constraintIds": ["cst_luxury_exclusion"],
    "trigger": "constraint-failure",
    "mutationId": "mut_ghi789"
  },
  "baseline": {
    "mode": "declared",
    "snapshotId": "base_jkl012"
  },
  "tradeoffRequired": true,
  "createdAt": "2025-12-25T00:00:00Z",
  "updatedAt": "2025-12-25T00:00:00Z",
  "lineage": {
    "parentMutation": "mut_ghi789",
    "supersedes": []
  },
  "resolution": null
}
```

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | UUID v7 prefixed with `cfl_` |
| type | enum | ✓ | `exclusion-constraint`, `baseline-violation`, `derived` |
| status | enum | ✓ | `active`, `resolved`, `suppressed` |
| severity | enum | ✓ | `low`, `medium`, `high`, `existential` |
| organismId | string | ✓ | Context organism |
| claims | array | ✓ | Involved claims with values |
| origin | object | ✓ | What triggered this conflict |
| baseline | object | | Reference frame if relevant |
| tradeoffRequired | boolean | ✓ | Must resolution include tradeoff? |
| lineage | object | ✓ | Mutation chain |
| resolution | object | | How it was resolved (null if active) |

---

## Severity Model

Severity is **computed**, not declared.

### Formula

```
severity = f(
  weight_of_claims,
  constraint_severity,
  drift_magnitude,
  baseline_mode,
  repetition_count
)
```

### Suggested Implementation

```python
def compute_severity(conflict: Conflict) -> str:
    combined_weight = sum(c.weight for c in conflict.claims) / len(conflict.claims)
    
    # Base score from weights
    score = combined_weight
    
    # Boost for hard constraints
    if conflict.origin.constraint_severity == "hard":
        score *= 1.5
    
    # Boost for declared/ideal baselines
    if conflict.baseline and conflict.baseline.mode in ["declared", "ideal"]:
        score *= 1.3
    
    # Boost for repeated conflicts
    score *= (1 + 0.1 * conflict.repetition_count)
    
    # Map to bands
    if score >= 1.5:
        return "existential"
    elif score >= 1.0:
        return "high"
    elif score >= 0.5:
        return "medium"
    else:
        return "low"
```

### Severity Bands

| Severity | Meaning | Action |
|----------|---------|--------|
| `low` | Cosmetic inconsistency | Monitor |
| `medium` | Strategic tension | Review |
| `high` | Identity damage | Resolve soon |
| `existential` | System no longer describes reality | Immediate action |

**Existential** conflicts signal that the baseline itself is obsolete. That's evolution pressure, not failure.

---

## Conflict Lifecycle

```
┌──────────────┐
│   CREATED    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   ACTIVE     │◄───────────────┐
└──────┬───────┘                │
       │                        │
       ├────────┐               │
       │        │               │
       ▼        ▼               │
┌──────────┐ ┌──────────┐       │
│ RESOLVED │ │SUPPRESSED│───────┘
└──────────┘ └──────────┘   (expires)
```

### Status Transitions

| From | To | Requires |
|------|----|----------|
| created | active | Automatic |
| active | resolved | Tradeoff + lineage record |
| active | suppressed | Policy + expiration |
| suppressed | active | Expiration or re-evaluation |
| resolved | active | New mutation creates same conflict |

### Rules

**Resolved** requires:
- Explicit tradeoff
- Updated baseline or constraint
- Lineage record

**Suppressed**:
- Allowed only by policy
- Never deletes conflict
- Must expire or be re-evaluated

No silent dismissal. Ever.

---

## Resolution Object

Resolution means: "We chose, and here's what we gave up."

```json
{
  "resolution": {
    "resolvedAt": "2025-12-26T12:00:00Z",
    "resolvedBy": "usr_alice",
    "strategy": "prefer-weight",
    "chosenClaim": {
      "claimId": "clm_abc123",
      "lens": "brand.positioning",
      "value": "luxury"
    },
    "sacrificed": [
      {
        "claimId": "clm_def456",
        "lens": "brand.discounting.strategy",
        "value": "discount-heavy",
        "action": "changed",
        "newValue": "minimal"
      }
    ],
    "tradeoff": {
      "gaveUp": { "lens": "brand.discounting.strategy", "delta": "discount-heavy → minimal" },
      "gained": { "lens": "brand.positioning", "preserved": "luxury" },
      "cost": "reduced short-term revenue potential",
      "justification": "brand integrity takes precedence"
    },
    "mutationId": "mut_resolve_123",
    "newBaseline": null
  }
}
```

### Resolution Effects

Resolution may:
- Adjust weights
- Change constraints
- Update baseline
- Spawn new constraints
- Modify sacrificed claims

But it **must** leave a scar in lineage.

---

## Auto-Resolution

Auto-resolution is allowed **only** when:

1. One side has strictly lower weight
2. Constraint severity mismatch exists (hard beats soft)
3. Policy explicitly allows it

### Policy Configuration

```yaml
# policies/conflict_resolution.yaml

autoResolution:
  enabled: true
  rules:
    - condition: weight_difference_gt
      threshold: 0.3
      action: suppress_lower
      requireTradeoff: true
    
    - condition: hard_vs_soft
      action: enforce_hard
      requireTradeoff: true
    
    - condition: baseline_mode_declared
      action: prefer_baseline
      requireTradeoff: true

  prohibited:
    - severity: existential
    - severity: high
    - type: derived
```

### Auto-Resolution Still Emits

Even auto-resolution creates:
- Tradeoff record
- Lineage entry
- Conflict resolution record

No invisible magic. Ever.

---

## Detection Pipeline

```
┌─────────────────────────────────────────────────────────┐
│              MUTATION COMMITTED                          │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│         CONSTRAINT EVALUATION (from Constraint Lang)     │
│         Collect all constraint results                   │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Exclusion│   │  Drift   │   │ Derived  │
   │ Detector │   │ Detector │   │ Detector │
   └────┬─────┘   └────┬─────┘   └────┬─────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              CONFLICT CREATION                           │
│    - Compute severity                                    │
│    - Check for duplicates/supersedes                     │
│    - Link to triggering mutation                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              AUTO-RESOLUTION CHECK                       │
│    - Policy allows?                                      │
│    - Conditions met?                                     │
│    - Create resolution + tradeoff if yes                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              EMIT EVENTS                                 │
│    - conflict.created                                    │
│    - conflict.resolved (if auto)                         │
│    - conflict.severity.changed                           │
└─────────────────────────────────────────────────────────┘
```

---

## Interaction With Projections

| Projections May | Projections May Not |
|-----------------|---------------------|
| Hide conflicts | Delete conflicts |
| Score conflicts | Resolve conflicts |
| Filter conflicts | Change conflict state |
| Aggregate conflicts | Alter lineage |

> Conflicts live below projections and outlast them.

This preserves explainability when views change.

---

## Events

| Event | Emitted When |
|-------|--------------|
| `conflict.created` | New conflict detected |
| `conflict.resolved` | Resolution committed |
| `conflict.suppressed` | Policy suppression |
| `conflict.reactivated` | Suppression expired |
| `conflict.severity.changed` | Severity recalculated |
| `conflict.superseded` | Replaced by new conflict |

---

## API Endpoints

```
/api/v1/conflicts
  GET    /                    List conflicts (filterable)
  GET    /{id}                Get conflict details
  POST   /{id}/resolve        Resolve with strategy + tradeoff
  POST   /{id}/suppress       Suppress with policy + expiration
  GET    /organism/{id}       Get conflicts for organism
  GET    /stats               Conflict statistics

Query parameters:
  ?status=active|resolved|suppressed
  ?severity=low|medium|high|existential
  ?type=exclusion-constraint|baseline-violation|derived
  ?organism_id=org_...
  ?since=2025-01-01T00:00:00Z
```

---

## File Structure

```
dna-matrix/
├── docs/
│   └── CONFLICT_DETECTION.md    # This spec
├── policies/
│   └── conflict_resolution.yaml # Auto-resolution rules
└── core/
    └── conflicts/
        ├── __init__.py
        ├── models.py            # Conflict, Resolution dataclasses
        ├── detector.py          # Detection pipeline
        ├── severity.py          # Severity computation
        ├── resolver.py          # Resolution logic
        ├── policies.py          # Policy evaluation
        └── tests/
            ├── test_detector.py
            ├── test_severity.py
            └── test_resolver.py
```

---

## Test Cases (Required)

| Test | Proves |
|------|--------|
| Exclusion constraint → conflict | Direct detection works |
| Drift threshold → self-conflict | Baseline violation works |
| Combined constraints → derived conflict | Inference works |
| Resolution writes lineage | Accountability preserved |
| Auto-resolution creates tradeoff | No invisible magic |
| Suppression expires | Temporal policies work |
| Severity recalculates on weight change | Interactions work |

---

## Why This Matters

**Without explicit conflict detection:**
- Brands turn incoherent quietly
- Organizations rot without alarms
- Agents drift into contradiction
- Products become Frankensteins
- People repeat the same mistakes forever

**With it:**
- Decisions become legible
- Tradeoffs become explicit
- Evolution becomes traceable

That's the point.

---

## Next Pass

**API Schemas**

Surface conflicts cleanly. Full request/response definitions for all endpoints.
