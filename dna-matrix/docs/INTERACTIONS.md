# DNA Matrix: Primitive Interactions

> Primitives are not fields. They're forces.

---

## The Interaction Graph

Each primitive influences others, depends on others, and triggers behavior.

```
           ┌─────────────────────────────────────────────┐
           │                                             │
           │              LINEAGE                        │
           │         (causal spine)                      │
           │              │                              │
           │              │ explains everything          │
           │              ▼                              │
           │  ┌───────────────────────┐                  │
           │  │                       │                  │
           │  │   weight ◄──────► conflict               │
           │  │     │                 ▲                  │
           │  │     │                 │                  │
           │  │     ▼                 │                  │
           │  │  tradeoff ◄───► constraint               │
           │  │                       │                  │
           │  │                       │                  │
           │  │   baseline ──────► drift ────────────┘   │
           │  │                                          │
           │  └──────────────────────────────────────────┘
           │                                             │
           └─────────────────────────────────────────────┘
```

---

## 1. weight ↔ conflict

Weight is what makes conflict real. Two claims can disagree, but if both are low-weight, it's a harmless argument.

### Rules

| Rule | Description |
|------|-------------|
| Severity scaling | Conflict severity increases with combined weight of opposing claims |
| Resolution default | `prefer-weight` uses weight as winner selection |
| Attention routing | High-weight conflicts surface first in queries |

### Trigger

When a mutation changes weight (`reweight`) on either side of an existing conflict:
- Re-score the conflict
- Severity can spike without changing values

### Formula

```
conflict.severity = base_severity * (left.weight + right.weight) / 2
```

---

## 2. constraint ↔ tradeoff

Constraints create the need for tradeoffs. If nothing is bounded, tradeoff is cosplay.

### Rules

| Rule | Description |
|------|-------------|
| Tradeoff mandatory | Mutations approaching or violating constraints must record tradeoffs |
| Attribution required | Tradeoff entries reference impacted lenses/claims |
| Justification scaling | Higher-weight claims require stronger justification |

### Trigger

| Constraint Result | Behavior |
|-------------------|----------|
| Hard constraint fails | Mutation cannot commit |
| Soft constraint fails | Mutation can commit, tradeoff mandatory, coherence penalty |

### Validation Flow

```
mutation.changes
    │
    ▼
validate_constraints()
    │
    ├── hard fail → REJECT
    │
    └── soft fail → REQUIRE tradeoff → COMMIT with penalty
```

---

## 3. baseline ↔ drift

Baseline is the reference frame. Drift is meaningless without it.

### Rules

| Rule | Description |
|------|-------------|
| Drift computation | Always `distance(current, baseline)` at query time |
| Mode affects semantics | Declared/ideal baselines trigger stricter drift thresholds |
| Never stored | Drift is computed, never persisted |

### Trigger

`rebaseline` operation:
- Invalidates all cached projections for that organism
- Changes drift everywhere without changing values
- Does not create new mutations for affected claims

### Baseline Modes and Drift Interpretation

| Mode | Drift Meaning |
|------|---------------|
| `snapshot` | Change since captured point |
| `declared` | Deviation from promise |
| `ideal` | Distance from optimum |
| `historical` | Evolution from origin |
| `selected` | Deviation from chosen reference |

---

## 4. drift ↔ conflict

Drift is a conflict generator. Not just claim vs claim, but claim vs its own promised identity.

### Rules

| Rule | Description |
|------|-------------|
| Self-conflict | Drift past threshold creates baseline-violation conflict |
| Escalation | High drift increases severity on related conflicts |
| Weighted matters | Small drift on high-weight claim > large drift on low-weight |

### Trigger

```python
if weighted_drift(claim) > threshold:
    if claim.baseline.mode in ["declared", "ideal"]:
        create_conflict(
            type="baseline-violation",
            left=claim.current,
            right=claim.baseline,
            severity=weighted_drift(claim)
        )
```

### Weighted Drift

```
weighted_drift(claim) = drift(claim) * claim.weight
```

---

## 5. lineage ↔ everything

Lineage is the causal spine. It doesn't influence like weight does—it determines what can be:

- Explained
- Rolled back
- Trusted
- Blamed

### Rules

| Rule | Description |
|------|-------------|
| Explanation requirement | Every state evaluation answers "what changed and why" |
| Identity through history | Identical states with different lineage are NOT identical |
| Rollback scope | Lineage determines what gets undone |

### Trigger

Any query with `explain=true`:
- Returns lineage excerpts
- Shows mutation IDs responsible for current state
- Traces causal path to computed values

### Lineage Walk

```
current_state
    │
    └── lastMutationId: mut_005
            │
            └── prevMutationId: mut_004
                    │
                    └── prevMutationId: mut_003
                            │
                            └── ... (origin)
```

---

## 6. tradeoff ↔ weight

Tradeoff isn't just notes. It's the record of why weights changed, or why constraints were grazed.

### Rules

| Rule | Description |
|------|-------------|
| Weight redistribution | Tradeoffs can propose weight changes across related claims |
| Temporary incoherence | Tradeoffs justify short-term conflicts (e.g., during repositioning) |
| Justification bar | High-weight claim changes require stronger tradeoff notes |

### Trigger

If a tradeoff references a claim with `weight > 0.7`:
- Require explicit intent
- Require notes field
- Flag for review if notes are empty

### Tradeoff Structure

```json
{
  "gaveUp": { "lens": "brand.accessibility", "delta": -0.2 },
  "gained": { "lens": "brand.exclusivity", "delta": +0.3 },
  "weight": 0.7,
  "justification": "required-for-premium-repositioning",
  "temporary": true,
  "expiresAt": "2025-06-01T00:00:00Z"
}
```

---

## 7. constraint ↔ conflict

Constraints define what's allowed. Conflicts arise when valid states still oppose each other.

### Rules

| Rule | Description |
|------|-------------|
| Exclusion constraints | Directly create conflicts when triggered |
| Constraint as referee | Some resolution strategies use constraints to pick winner |
| Cascade detection | Constraint on claim A can trigger conflict check on dependent claim B |

### Trigger

Exclusion constraint fires:
```python
# Constraint on "luxury" excludes "discount-heavy"
if claim_a.value == "luxury" and claim_b.value == "discount-heavy":
    if constraint.rule == "exclusion":
        create_conflict(
            left=claim_a,
            right=claim_b,
            reason="exclusion-constraint",
            rule=constraint
        )
```

---

# Computed Metrics

Interactions become measurable through these formulas.

## Drift (per-claim)

```
drift(claim) = distance(claim.value, claim.baseline.value)
```

Distance by value type:

| Type | Distance Function |
|------|-------------------|
| number | `abs(current - baseline) / scale` |
| enum | `0` if match, `1` if different (or embedding distance) |
| bool | `0` if match, `1` if different |
| json | Per-key diff score, averaged |

## Total Drift (organism)

```
totalDrift = Σ(drift_i × weight_i) / Σ(weight_i)
```

## Conflict Burden

```
conflictBurden = Σ(severity_c × combinedWeight_c)

where combinedWeight = (left.weight + right.weight) / 2
```

## Constraint Burden

```
constraintBurden = Σ(penalty × claim.weight)

where penalty = ∞ if hard_fail, else soft_penalty (0.1-0.5)
```

## Coherence (the verdict)

```
coherence = clamp(1 - (α×conflictBurden + β×constraintBurden + γ×totalDrift), 0, 1)
```

Default coefficients:
- α = 0.4 (conflict weight)
- β = 0.3 (constraint weight)
- γ = 0.3 (drift weight)

Coherence is **derived from causes**, never stored.

---

# Policy Configuration

Interactions should be tunable without code changes.

## policies/interactions.yaml

```yaml
drift:
  thresholds:
    warning: 0.2
    critical: 0.5
  by_baseline_mode:
    declared: 0.3  # stricter for promises
    ideal: 0.4
    snapshot: 0.6  # more lenient for historical

conflict:
  severity_curve: "linear"  # or "exponential"
  weight_influence: 0.5
  auto_resolve_below: 0.2

coherence:
  coefficients:
    conflict: 0.4
    constraint: 0.3
    drift: 0.3
  
constraint:
  soft_penalty: 0.2
  require_tradeoff_on_soft_fail: true

tradeoff:
  require_notes_above_weight: 0.7
  allow_temporary: true
  max_temporary_duration_days: 90
```

---

# Event Stream

Mutations emit events. Interactions subscribe.

## Events

| Event | Emitted When |
|-------|--------------|
| `claim.value.changed` | Value set or merged |
| `claim.weight.changed` | Reweight operation |
| `claim.baseline.changed` | Rebaseline operation |
| `claim.constraint.changed` | Constraint added/modified |
| `conflict.created` | New conflict detected |
| `conflict.resolved` | Conflict resolution committed |

## Subscribers

| Subscriber | Listens To | Action |
|------------|------------|--------|
| ConflictScorer | `claim.weight.changed` | Re-score related conflicts |
| DriftChecker | `claim.value.changed`, `claim.baseline.changed` | Check drift thresholds |
| ProjectionInvalidator | All claim events | Invalidate cached projections |
| ExplanationBuilder | All events | Build audit trail |

---

# Integration Pattern

```
┌─────────────────────────────────────────────────────────┐
│                    MUTATION COMMITTED                    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    EVENT EMITTED                         │
│     claim.value.changed, claim.weight.changed, etc.     │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Conflict │   │  Drift   │   │Projection│
   │ Rescorer │   │ Checker  │   │Invalidate│
   └────┬─────┘   └────┬─────┘   └────┬─────┘
        │              │              │
        ▼              ▼              ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ Update   │   │ Create   │   │  Clear   │
   │ Severity │   │ Warning  │   │  Cache   │
   └──────────┘   └──────────┘   └──────────┘
```

---

# What This Enables

The interaction layer makes the system explain itself. Every evaluation returns:

- Top contributing conflicts
- Biggest drift contributors
- Constraint failures
- Mutation IDs responsible

**That's the product, not the CRUD.**

## Immediate Applications

| App | What It Does | Endpoint Used |
|-----|--------------|---------------|
| Ops Drift Dashboard | Values vs behavior for teams | `/diff`, `/explain` |
| Agent Governance Console | Keep AI workflows on rails | `/evaluate`, `/conflicts` |
| Product Frankenstein Detector | Flag roadmap incoherence | `/evaluate`, `/recommend` |
| Policy Compliance Monitor | Track deviation from policy | `/diff`, `/conflicts` |

---

## Next Pass

**Constraint Language**

How do you encode rules without hardcoding?

- Rule syntax
- Validation semantics
- Composition
- Conflict detection rules
