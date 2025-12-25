# DNA Matrix: Constraint Language v0.1

> Where the system stops being a clever model and becomes a governable machine.

---

## Goals

Constraint Language must be:

| Goal | Why |
|------|-----|
| **Composable** | Rules build bigger rules |
| **Typed** | Rules know what they apply to |
| **Explainable** | Every pass/fail returns "why" with evidence |
| **Portable** | Constraints live in config, not code |
| **Stable** | Versioned, migration-friendly |

---

## Core Concepts

### Constraint

A rule attached to a target (claim, lens, organism, cluster) that evaluates truthiness under a given state and optional context.

### Outcome

Every evaluation returns:

```json
{
  "passed": false,
  "severity": "hard|soft",
  "code": "EXCLUSION_VIOLATION",
  "message": "Human-readable explanation",
  "evidence": { "...": "machine-readable proof" },
  "repairHints": [ "..." ],
  "conflictSpec": { "..." }
}
```

### Constitutional Alignment

| Result | Behavior |
|--------|----------|
| Hard fail | Blocks commit |
| Soft fail | Allows commit, requires tradeoff, coherence penalty |

---

## Data Model

### Constraint Object

```json
{
  "id": "cst_01J8K9M2N3P4Q5R6",
  "version": "1.0",
  "name": "Luxury excludes discount-heavy",
  "description": "Premium positioning cannot coexist with aggressive discounting",
  "severity": "hard",
  "scope": "claim",
  "target": {
    "organismId": "org_...",
    "lens": "brand.positioning"
  },
  "when": {
    "op": "exists",
    "path": "$.value"
  },
  "rule": {
    "op": "exclusion",
    "args": [
      { "lens": "brand.positioning", "equals": "luxury" },
      { "lens": "brand.discounting.strategy", "equals": "discount-heavy" }
    ]
  },
  "onFail": {
    "requireTradeoff": true,
    "emitEvents": ["constraint.failed"],
    "createConflict": {
      "type": "exclusion-constraint",
      "leftLens": "brand.positioning",
      "rightLens": "brand.discounting.strategy",
      "reason": "luxury cannot coexist with discount-heavy"
    }
  },
  "meta": {
    "tags": ["brand", "identity"],
    "owner": "policy-team",
    "createdAt": "2025-12-25T00:00:00Z"
  }
}
```

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | UUID v7 prefixed with `cst_` |
| version | string | ✓ | Semantic version |
| name | string | ✓ | Human-readable name |
| description | string | | Longer explanation |
| severity | enum | ✓ | `hard` or `soft` |
| scope | enum | ✓ | `claim`, `lens`, `organism`, `cluster` |
| target | object | ✓ | What this constraint applies to |
| when | object | | Guard condition (skip if not met) |
| rule | object | ✓ | The actual logic |
| onFail | object | | Actions on failure |
| meta | object | | Tags, owner, timestamps |

---

## Operand Types

Operands reference values for comparison.

| Type | Syntax | Example |
|------|--------|---------|
| Claim value | `{ "path": "$.value.data" }` | Current value |
| Claim weight | `{ "path": "$.weight" }` | Weight scalar |
| Baseline | `{ "path": "$.baseline.value.data" }` | Baseline value |
| Drift | `{ "fn": "drift", "of": { "lens": "..." } }` | Computed drift |
| Other claim | `{ "lens": "x.y.z" }` | Cross-reference |
| Context | `{ "ctx": "market.region" }` | Runtime context |
| Literal | `{ "lit": 0.7 }` | Constant value |

---

## Operators

### Boolean Composition

| Op | Description | Example |
|----|-------------|---------|
| `and` | All args must pass | `{ "op": "and", "args": [...] }` |
| `or` | Any arg must pass | `{ "op": "or", "args": [...] }` |
| `not` | Invert result | `{ "op": "not", "args": [...] }` |
| `xor` | Exactly one passes | `{ "op": "xor", "args": [...] }` |

### Comparisons

| Op | Description | Args |
|----|-------------|------|
| `eq` | Equal | `[left, right]` |
| `neq` | Not equal | `[left, right]` |
| `gt` | Greater than | `[left, right]` |
| `gte` | Greater or equal | `[left, right]` |
| `lt` | Less than | `[left, right]` |
| `lte` | Less or equal | `[left, right]` |
| `in` | In set | `[value, set]` |
| `not_in` | Not in set | `[value, set]` |

### Range / Envelope

| Op | Description | Args |
|----|-------------|------|
| `between` | Inclusive range | `[value, min, max]` |
| `within_tolerance` | Baseline ± tolerance | `[lens, tolerance]` |
| `max_delta` | Change limit | `[lens, max_change]` |

### Set / Cardinality

| Op | Description | Args |
|----|-------------|------|
| `exists` | Value present | `[path]` |
| `missing` | Value absent | `[path]` |
| `count_gte` | Array size ≥ | `[path, min]` |
| `count_lte` | Array size ≤ | `[path, max]` |

### Domain-Universal

| Op | Description | Args |
|----|-------------|------|
| `exclusion` | A excludes B | `[claim_a, claim_b]` |
| `requires` | If A then B | `[condition, requirement]` |
| `implies` | A ⇒ B (soft) | `[antecedent, consequent]` |
| `compatible_with` | Compatibility table | `[value, table]` |
| `schema` | JSON Schema validation | `[value, schema]` |

### Drift-Related

| Op | Description | Args |
|----|-------------|------|
| `drift_lte` | Drift ≤ threshold | `[lens, threshold]` |
| `weighted_drift_lte` | Drift × weight ≤ threshold | `[lens, threshold]` |

---

## Evaluation Pipeline

On mutation commit:

```
┌─────────────────────────────────────────────────────────┐
│              1. GATHER IMPACTED CLAIMS                   │
│         Direct changes + referenced by rules             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              2. COLLECT CONSTRAINTS                      │
│    Target claim → lens → cluster → organism → global     │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              3. EVALUATE GUARDS (when)                   │
│              Skip if guard not satisfied                 │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              4. EVALUATE RULES                           │
│              Collect all results                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              5. APPLY COMMIT RULES                       │
│    Hard fail → REJECT                                    │
│    Soft fail → REQUIRE TRADEOFF → COMMIT with penalty   │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              6. EMIT EVENTS + CREATE CONFLICTS           │
│              7. INVALIDATE PROJECTIONS                   │
└─────────────────────────────────────────────────────────┘
```

---

## Explainability Payload

Every constraint result returns structured evidence.

```json
{
  "constraintId": "cst_01J8K9M2N3P4Q5R6",
  "passed": false,
  "severity": "hard",
  "code": "EXCLUSION_VIOLATION",
  "message": "brand.positioning=luxury excludes brand.discounting.strategy=discount-heavy",
  "evidence": {
    "left": { "lens": "brand.positioning", "value": "luxury" },
    "right": { "lens": "brand.discounting.strategy", "value": "discount-heavy" }
  },
  "repairHints": [
    { "action": "set", "lens": "brand.discounting.strategy", "suggest": "minimal" },
    { "action": "set", "lens": "brand.positioning", "suggest": "premium" }
  ]
}
```

This powers:
- `/evaluate` endpoint
- `/explain` endpoint
- Mutation rejection messages
- UI tooltips

---

## Composition Rules

### Constraint Sets

Constraints can be grouped and inherited:

| Level | Applies To |
|-------|------------|
| Global | All organisms |
| Cluster | All claims in cluster |
| Lens | That lens across organisms |
| Organism | Specific organism |
| Claim | Specific claim |

### Precedence (Simple, Predictable)

1. Claim-specific (highest)
2. Organism-specific
3. Lens
4. Cluster
5. Global (lowest)

### Conflict Between Constraints

When two constraints conflict:
- Both still evaluate
- Resolution via policy (`hard` beats `soft`)
- Lineage records what was overridden (no silent magic)

---

## Examples

### A) Brand: Exclusion + Requires

Luxury cannot be discount-heavy (hard). If luxury, minimum packaging quality (soft).

```yaml
- id: cst_luxury_exclusion
  severity: hard
  rule:
    op: exclusion
    args:
      - { lens: brand.positioning, equals: luxury }
      - { lens: brand.discounting.strategy, equals: discount-heavy }
  onFail:
    createConflict:
      type: exclusion-constraint
      reason: "luxury cannot coexist with discount-heavy"

- id: cst_luxury_packaging
  severity: soft
  rule:
    op: requires
    args:
      - { lens: brand.positioning, equals: luxury }
      - { lens: brand.packaging.qualityScore, gte: 0.8 }
  onFail:
    requireTradeoff: true
```

### B) Organization: Drift Threshold by Baseline Mode

Declared values must not drift past 0.3 weighted drift (hard).

```yaml
- id: cst_declared_drift
  severity: hard
  when:
    op: eq
    args:
      - { path: "$.baseline.mode" }
      - { lit: "declared" }
  rule:
    op: weighted_drift_lte
    args:
      - { lens: org.values.customer_obsession }
      - { lit: 0.3 }
```

### C) AI Agent: Permission Boundary

Tool usage must be within tier permissions (hard).

```yaml
- id: cst_tool_permission
  severity: hard
  rule:
    op: in
    args:
      - { ctx: requestedTool }
      - { ctx: allowedTools }
```

### D) Product: Feature Dependency

If feature A is enabled, feature B must exist (hard).

```yaml
- id: cst_feature_dependency
  severity: hard
  rule:
    op: requires
    args:
      - { lens: product.features.A, equals: true }
      - { lens: product.features.B, equals: true }
```

### E) Person: Spending Tolerance

Spending variance within tolerance of baseline (soft).

```yaml
- id: cst_spending_tolerance
  severity: soft
  rule:
    op: within_tolerance
    args:
      - { lens: person.finance.monthlySpend }
      - { lit: 0.15 }
  onFail:
    requireTradeoff: true
```

---

## Constraint → Conflict Bridge

Two modes for constraint failures to create conflicts:

### 1. Direct Conflict Creation (Exclusion Rules)

```json
{
  "rule": { "op": "exclusion", "args": [...] },
  "onFail": {
    "createConflict": {
      "type": "exclusion-constraint",
      "leftLens": "...",
      "rightLens": "...",
      "reason": "..."
    }
  }
}
```

### 2. Drift-Driven Self-Conflict

```json
{
  "rule": { "op": "weighted_drift_lte", "args": [...] },
  "onFail": {
    "createConflict": {
      "type": "baseline-violation",
      "lens": "...",
      "reason": "drift exceeds threshold"
    }
  }
}
```

Everything else can remain "constraint failure only" without creating conflicts, unless policy says otherwise.

---

## File Structure

```
dna-matrix/
├── docs/
│   └── CONSTRAINT_LANGUAGE.md     # This spec
├── policies/
│   ├── constraints/
│   │   ├── global.yaml            # Global defaults
│   │   ├── brand.yaml             # Brand cluster rules
│   │   ├── market.yaml            # Market cluster rules
│   │   └── risk.yaml              # Risk cluster rules
│   └── interactions.yaml          # Coefficients + thresholds
└── core/
    └── constraints/
        ├── __init__.py
        ├── parser.py              # YAML/JSON → AST
        ├── evaluator.py           # AST execution
        ├── types.py               # Operand/value types
        ├── results.py             # Explain payload
        ├── registry.py            # Op registry, versioned
        └── tests/
            ├── test_parser.py
            ├── test_evaluator.py
            └── test_operators.py
```

---

## Operator Registry

Operators are versioned. Semantics don't change without version bump.

```python
OPERATOR_REGISTRY = {
    "v1": {
        "and": AndOperator,
        "or": OrOperator,
        "not": NotOperator,
        "eq": EqOperator,
        "neq": NeqOperator,
        "gt": GtOperator,
        "gte": GteOperator,
        "lt": LtOperator,
        "lte": LteOperator,
        "in": InOperator,
        "not_in": NotInOperator,
        "between": BetweenOperator,
        "within_tolerance": WithinToleranceOperator,
        "max_delta": MaxDeltaOperator,
        "exists": ExistsOperator,
        "missing": MissingOperator,
        "count_gte": CountGteOperator,
        "count_lte": CountLteOperator,
        "exclusion": ExclusionOperator,
        "requires": RequiresOperator,
        "implies": ImpliesOperator,
        "compatible_with": CompatibleWithOperator,
        "schema": SchemaOperator,
        "drift_lte": DriftLteOperator,
        "weighted_drift_lte": WeightedDriftLteOperator,
    }
}
```

---

## Migration Path

When constraint semantics change:

1. Bump version in constraint definition
2. Old version continues to work
3. Migration script updates constraints
4. Deprecation warning for old versions
5. Eventually remove old version

No silent semantic changes. Constitutional.

---

## Next Pass

**Conflict Detection**

- When conflicts fire
- Conflict types
- Severity computation
- Auto-resolution policies
