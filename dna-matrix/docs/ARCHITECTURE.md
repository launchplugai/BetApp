# DNA Matrix: Architecture Specification v3

> A decision engine disguised as a data system.
> Built on 7 primitives. No exceptions.

---

## Constitutional Foundation

This architecture obeys the frozen genome (v0.1):

```
1. weight      Relative importance
2. constraint  Boundary on valid states
3. conflict    Competing forces
4. baseline    Reference state for comparison
5. drift       Deviation from baseline (computed)
6. tradeoff    Exchange of one value for another
7. lineage     Provenance and causal history
```

Coherence, identity, score, and signal are **computed**, never stored.

---

## Core Mental Model Shift

### Old Model (Spreadsheet)

```
Gene = value at row × column (Organism × Column)
```

### New Model (Constitutional)

```
Claim = assertion with state + 7 primitive dimensions + lineage over time
```

The matrix view still exists—as a **projection**, never as truth.

---

## Structural Invariants

These are non-negotiable:

1. **Claims are the units of meaning**
2. **Mutations are the only way claims change**
3. **Lineage is append-only**
4. **Constraints attach to claims and validate mutations**
5. **Conflicts are relations between claims**
6. **Drift and coherence are computed from stored causes**
7. **Matrix is a projection, never the source of truth**

---

# Part I: Core Data Objects

## 1.1 Organism

The anchor. The "thing" being modeled. Has no primitives—just identity.

```json
{
  "id": "org_7b3f8a2c",
  "type": "organism",
  "organismType": "brand|person|agent|product|org|custom",
  "name": "Apple",
  "tags": ["portfolio:consumer-tech", "sector:hardware"],
  "createdAt": "2025-01-15T10:00:00Z",
  "updatedAt": "2025-01-20T14:30:00Z"
}
```

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | UUID v7 prefixed with `org_` |
| type | string | ✓ | Always `"organism"` |
| organismType | enum | ✓ | Category for clustering |
| name | string | ✓ | Human-readable identifier |
| tags | string[] | | Arbitrary labels |
| createdAt | datetime | ✓ | ISO 8601 |
| updatedAt | datetime | ✓ | ISO 8601 |

---

## 1.2 Lens

Replaces "Column." A semantic key with optional resolver and policy.

```json
{
  "id": "lns_voice_tone",
  "type": "lens",
  "cluster": "brand",
  "key": "voice.tone",
  "name": "Brand Voice Tone",
  "description": "The emotional register of brand communication",
  "valueType": "enum",
  "schema": {
    "allowed": ["luxury", "bold", "minimal", "playful", "authoritative"]
  },
  "resolver": null,
  "defaultWeight": 0.7,
  "createdAt": "2025-01-01T00:00:00Z"
}
```

### Computed Lenses

Lenses can have resolvers that compute values from other claims:

```json
{
  "id": "lns_brand_strength",
  "type": "lens",
  "cluster": "brand",
  "key": "strength.index",
  "name": "Brand Strength Index",
  "valueType": "number",
  "resolver": {
    "type": "function",
    "inputs": ["brand.awareness", "brand.nps", "market.share"],
    "formula": "(awareness * 0.3) + ((nps + 100) / 200 * 0.4) + (share * 0.3)"
  },
  "cacheTTL": 3600
}
```

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | UUID v7 prefixed with `lns_` |
| type | string | ✓ | Always `"lens"` |
| cluster | string | ✓ | Grouping namespace |
| key | string | ✓ | Dot-notation path |
| name | string | ✓ | Human-readable |
| valueType | enum | ✓ | string, number, bool, enum, json |
| schema | object | | Validation rules |
| resolver | object | | Computation definition |
| defaultWeight | number | | 0.0-1.0 |
| cacheTTL | number | | Seconds |

---

## 1.3 Claim

The atomic unit of meaning. Replaces "Gene."

A claim is: "something asserted about an organism through a lens."

```json
{
  "id": "clm_8x9f2k4m",
  "type": "claim",
  "organismId": "org_7b3f8a2c",
  "lensId": "lns_voice_tone",
  "lens": {
    "cluster": "brand",
    "key": "voice.tone"
  },
  "value": {
    "kind": "enum",
    "data": "luxury"
  },
  "weight": 0.83,
  "constraints": [
    {
      "id": "cst_enum_check",
      "rule": "enum",
      "params": { "allowed": ["luxury", "bold", "minimal", "playful", "authoritative"] },
      "severity": "hard"
    }
  ],
  "baseline": {
    "mode": "snapshot",
    "ref": "clm_older123",
    "value": { "kind": "enum", "data": "premium" },
    "capturedAt": "2024-06-01T00:00:00Z"
  },
  "lastMutationId": "mut_abc123",
  "version": 3,
  "createdAt": "2024-06-01T00:00:00Z",
  "updatedAt": "2025-01-20T14:30:00Z"
}
```

### Primitive Mapping

| Primitive | Where It Lives |
|-----------|----------------|
| **weight** | `claim.weight` (scalar 0.0-1.0) |
| **constraint** | `claim.constraints[]` (array of rules) |
| **baseline** | `claim.baseline` (reference frame) |
| **lineage** | `claim.lastMutationId` → mutation chain |
| **drift** | Computed: `distance(value, baseline.value)` |
| **conflict** | Separate object (relation between claims) |
| **tradeoff** | Captured on mutation |

### Constraint Structure

```json
{
  "id": "cst_range_check",
  "rule": "range",
  "params": { "min": 0, "max": 100 },
  "severity": "hard|soft",
  "message": "Value must be between 0 and 100"
}
```

Constraint rules:
- `enum` — value must be in allowed set
- `range` — numeric bounds
- `pattern` — regex match
- `dependency` — requires another claim to exist
- `exclusion` — incompatible with another claim
- `custom` — function reference

### Baseline Modes

| Mode | Meaning |
|------|---------|
| `snapshot` | Captured state at a point in time |
| `declared` | What was promised/intended |
| `ideal` | Theoretical optimum |
| `historical` | First recorded value |
| `selected` | Manually chosen reference |

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | UUID v7 prefixed with `clm_` |
| type | string | ✓ | Always `"claim"` |
| organismId | string | ✓ | Reference to organism |
| lensId | string | ✓ | Reference to lens |
| lens | object | ✓ | Denormalized cluster + key |
| value | object | ✓ | Kind + data |
| weight | number | ✓ | 0.0-1.0 |
| constraints | array | | Validation rules |
| baseline | object | | Reference frame |
| lastMutationId | string | | Lineage pointer |
| version | number | ✓ | Increment on change |

---

## 1.4 Mutation

The only way claims change. Append-only.

```json
{
  "id": "mut_def456",
  "type": "mutation",
  "organismId": "org_7b3f8a2c",
  "actor": {
    "type": "human",
    "id": "usr_alice",
    "label": "Alice Chen"
  },
  "intent": "repositioning",
  "changes": [
    {
      "claimId": "clm_8x9f2k4m",
      "op": "set",
      "before": { "kind": "enum", "data": "premium" },
      "after": { "kind": "enum", "data": "luxury" }
    },
    {
      "claimId": "clm_9y0g3l5n",
      "op": "reweight",
      "before": 0.5,
      "after": 0.8
    }
  ],
  "tradeoffs": [
    {
      "gaveUp": { "lens": "brand.accessibility", "delta": -0.2 },
      "gained": { "lens": "brand.exclusivity", "delta": +0.3 },
      "weight": 0.7,
      "notes": "Accepted reduced mass-market appeal for premium positioning"
    }
  ],
  "constraintResults": [
    { "constraintId": "cst_enum_check", "passed": true }
  ],
  "expectedConflicts": [],
  "status": "committed",
  "prevMutationId": "mut_abc123",
  "createdAt": "2025-01-20T14:30:00Z",
  "committedAt": "2025-01-20T14:30:05Z"
}
```

### Primitive Mapping

| Primitive | How It's Captured |
|-----------|-------------------|
| **tradeoff** | `mutation.tradeoffs[]` — recorded at decision time |
| **lineage** | `mutation.prevMutationId` — append-only chain |
| **constraint** | `mutation.constraintResults[]` — validated at commit |
| **weight** | Can be changed via `reweight` op |

### Operations

| Op | Description |
|----|-------------|
| `set` | Replace value |
| `merge` | Deep merge (for json values) |
| `delete` | Remove claim |
| `reweight` | Change weight only |
| `rebaseline` | Update baseline reference |
| `constrain` | Add/modify constraints |

### Status Flow

```
proposed → validated → committed
    ↓          ↓
rejected   rejected
              ↓
         rolledBack
```

### Actor Types

| Type | Description |
|------|-------------|
| `human` | User action |
| `agent` | AI system |
| `system` | Automated process |
| `import` | Bulk data load |

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | UUID v7 prefixed with `mut_` |
| type | string | ✓ | Always `"mutation"` |
| organismId | string | ✓ | Target organism |
| actor | object | ✓ | Who initiated |
| intent | string | | Why this change |
| changes | array | ✓ | List of operations |
| tradeoffs | array | | Explicit cost/benefit |
| constraintResults | array | | Validation results |
| expectedConflicts | array | | Known conflicts |
| status | enum | ✓ | Lifecycle state |
| prevMutationId | string | | Lineage chain |
| createdAt | datetime | ✓ | When proposed |
| committedAt | datetime | | When applied |

---

## 1.5 Conflict

A relation between claims, not an attribute.

```json
{
  "id": "cnf_ghi789",
  "type": "conflict",
  "organismId": "org_7b3f8a2c",
  "left": {
    "claimId": "clm_8x9f2k4m",
    "lens": "brand.voice.tone",
    "value": "luxury"
  },
  "right": {
    "claimId": "clm_price_pos",
    "lens": "price.strategy",
    "value": "discount-heavy"
  },
  "reason": "incompatible-signals",
  "rule": {
    "type": "exclusion",
    "params": { "luxury": ["discount-heavy", "budget"] }
  },
  "severity": 0.74,
  "status": "open",
  "resolution": null,
  "createdAt": "2025-01-20T14:30:05Z",
  "updatedAt": "2025-01-20T14:30:05Z"
}
```

### Resolution

```json
{
  "resolution": {
    "strategy": "prefer-weight",
    "winnerClaimId": "clm_8x9f2k4m",
    "loserClaimId": "clm_price_pos",
    "mutationId": "mut_resolve_123",
    "notes": "Brand positioning takes precedence over pricing strategy",
    "resolvedAt": "2025-01-21T10:00:00Z",
    "resolvedBy": "usr_alice"
  }
}
```

### Resolution Strategies

| Strategy | Logic |
|----------|-------|
| `prefer-weight` | Higher weight wins |
| `prefer-source` | Certain actor types win |
| `prefer-newest` | Most recent wins |
| `prefer-oldest` | Original wins |
| `manual` | Human decision |
| `suppress` | Acknowledge but ignore |

### Status

| Status | Meaning |
|--------|---------|
| `open` | Unresolved, active |
| `resolved` | Winner chosen |
| `suppressed` | Ignored intentionally |
| `superseded` | Obsolete (claims changed) |

### Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string | ✓ | UUID v7 prefixed with `cnf_` |
| type | string | ✓ | Always `"conflict"` |
| organismId | string | ✓ | Context |
| left | object | ✓ | First competing claim |
| right | object | ✓ | Second competing claim |
| reason | string | ✓ | Why they conflict |
| rule | object | | What rule detected this |
| severity | number | ✓ | 0.0-1.0 |
| status | enum | ✓ | Lifecycle state |
| resolution | object | | How it was resolved |

---

## 1.6 Projection

The matrix view. Computed, cached, never authoritative.

```json
{
  "id": "prj_jkl012",
  "type": "projection",
  "organismId": "org_7b3f8a2c",
  "projectionType": "matrix",
  "version": 12,
  "asOf": "2025-01-20T14:30:05Z",
  "generatedAt": "2025-01-20T14:30:10Z",
  "data": {
    "brand.voice.tone": {
      "value": "luxury",
      "weight": 0.83,
      "drift": 0.15,
      "hasConflict": true
    },
    "price.strategy": {
      "value": "discount-heavy",
      "weight": 0.6,
      "drift": 0.0,
      "hasConflict": true
    }
  },
  "computed": {
    "brand.strength.index": 0.847,
    "coherence": 0.62,
    "openConflicts": 1,
    "totalDrift": 0.15
  }
}
```

### Projection Types

| Type | Purpose |
|------|---------|
| `matrix` | Current state grid |
| `timeline` | Change history |
| `diff` | Comparison between states |
| `summary` | Aggregated metrics |

### What Gets Computed Here

| Metric | Formula |
|--------|---------|
| `drift` | `distance(current, baseline)` |
| `coherence` | `1 - (weighted_conflicts + constraint_violations)` |
| `openConflicts` | `count(conflicts where status = open)` |
| `totalDrift` | `sum(drift * weight) / sum(weight)` |

---

# Part II: Primitive Residence Summary

| Primitive | Stored Where | Stored How |
|-----------|--------------|------------|
| **weight** | Claim | `claim.weight` scalar |
| **constraint** | Claim | `claim.constraints[]` array |
| **baseline** | Claim | `claim.baseline` object |
| **conflict** | Conflict | Separate first-class object |
| **tradeoff** | Mutation | `mutation.tradeoffs[]` array |
| **lineage** | Mutation | `mutation.prevMutationId` chain |
| **drift** | Projection | Computed at query time |

---

# Part III: Operations

## 3.1 The Only Write Path

```
                    ┌──────────────┐
                    │   Mutation   │
                    │   Proposal   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │   Validate   │
                    │  Constraints │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌────▼────┐ ┌─────▼─────┐
        │  Reject   │ │ Detect  │ │  Commit   │
        │           │ │Conflicts│ │           │
        └───────────┘ └────┬────┘ └─────┬─────┘
                           │            │
                    ┌──────▼───────┐    │
                    │   Create     │    │
                    │  Conflict    │    │
                    │   Objects    │    │
                    └──────────────┘    │
                                        │
                    ┌───────────────────▼─────┐
                    │   Update Claims         │
                    │   Append to Log         │
                    │   Invalidate Projections│
                    └─────────────────────────┘
```

## 3.2 Mutation Operations

| Operation | What Changes |
|-----------|--------------|
| `set` | `claim.value`, `claim.version++`, `claim.lastMutationId` |
| `reweight` | `claim.weight`, `claim.version++`, `claim.lastMutationId` |
| `rebaseline` | `claim.baseline`, `claim.version++`, `claim.lastMutationId` |
| `constrain` | `claim.constraints[]`, `claim.version++`, `claim.lastMutationId` |
| `delete` | Soft delete claim, `claim.lastMutationId` |

## 3.3 Conflict Operations

| Operation | Effect |
|-----------|--------|
| `resolve` | Sets winner, creates resolution mutation |
| `suppress` | Marks as intentionally ignored |
| `escalate` | Increases severity, triggers alert |

---

# Part IV: Query System

## 4.1 Query DSL

```json
{
  "from": "claims",
  "where": {
    "organism.id": "org_7b3f8a2c",
    "lens.cluster": "brand",
    "weight": { ">": 0.5 },
    "drift": { ">": 0.1 }
  },
  "select": ["lens.key", "value", "weight", "drift", "baseline"],
  "orderBy": [{ "field": "weight", "direction": "desc" }],
  "limit": 50,
  "explain": true
}
```

## 4.2 Computed Fields Available in Queries

| Field | Computation |
|-------|-------------|
| `drift` | `distance(value, baseline.value)` |
| `age` | `now - createdAt` |
| `staleness` | `now - updatedAt` |
| `mutationCount` | Count of mutations in lineage |
| `hasConflict` | Boolean from conflict lookup |

## 4.3 Query Response

```json
{
  "results": [...],
  "meta": {
    "total": 127,
    "returned": 50,
    "queryTimeMs": 23
  },
  "explanation": {
    "plan": "index_scan(organism) → filter(weight) → compute(drift) → sort",
    "indexesUsed": ["idx_organism_id", "idx_weight"],
    "claimsScanned": 340,
    "computationsPerformed": ["drift"]
  }
}
```

---

# Part V: API Endpoints

## 5.1 Resource Endpoints (Plumbing)

```
/api/v1/organisms
  POST   /                    Create organism
  GET    /{id}                Get organism
  GET    /{id}/claims         Get all claims
  GET    /{id}/conflicts      Get conflicts
  GET    /{id}/mutations      Get mutation history

/api/v1/claims
  GET    /{id}                Get claim with lineage
  GET    /{id}/history        Get version history

/api/v1/mutations
  POST   /                    Propose mutation
  GET    /{id}                Get mutation details
  POST   /{id}/commit         Commit proposed mutation
  POST   /{id}/reject         Reject proposed mutation
  POST   /{id}/rollback       Rollback committed mutation

/api/v1/conflicts
  GET    /                    List open conflicts
  POST   /{id}/resolve        Resolve with strategy
  POST   /{id}/suppress       Suppress intentionally

/api/v1/lenses
  GET    /                    List lenses
  GET    /{id}                Get lens definition
```

## 5.2 Task Endpoints (Value)

```
/api/v1/evaluate
  POST   /                    Score organism against criteria

/api/v1/simulate
  POST   /                    Test mutations without commit

/api/v1/diff
  POST   /                    Compare states

/api/v1/explain
  POST   /                    Show reasoning for claim

/api/v1/recommend
  POST   /                    Suggest actions

/api/v1/project
  POST   /                    Generate projection
  GET    /{id}                Get cached projection
```

---

# Part VI: SDK Design

## 6.1 Fluent Interface

```python
from dna_matrix import Matrix

matrix = Matrix(url="http://localhost:8080", api_key="...")

# Fluent mutation
result = (
    matrix.organism("apple")
    .claim("brand.voice.tone")
    .set("luxury", weight=0.83)
    .with_tradeoff(
        gave_up=("brand.accessibility", -0.2),
        gained=("brand.exclusivity", +0.3)
    )
    .with_intent("rebrand-2025")
    .commit()
)

# Query
claims = (
    matrix.query()
    .from_organism("apple")
    .where(cluster="brand", weight__gt=0.5)
    .with_drift()
    .execute()
)

# Explain
why = matrix.organism("apple").explain("brand.strength.index")
print(f"Inputs: {why.lineage}")
print(f"Formula: {why.resolver.formula}")
```

## 6.2 Conflict Handling

```python
conflicts = matrix.organism("apple").conflicts.open()

for conflict in conflicts:
    print(f"{conflict.left.lens} vs {conflict.right.lens}")
    print(f"Severity: {conflict.severity}")
    
    # Resolve
    conflict.resolve(strategy="prefer-weight", notes="Brand takes precedence")
```

## 6.3 Time Travel

```python
# Get state at a point in time
past_state = matrix.organism("apple").as_of("2024-06-01").project()

# Diff against current
diff = matrix.organism("apple").diff(since="2024-06-01")

for change in diff.changes:
    print(f"{change.lens}: {change.before} → {change.after}")
```

---

# Part VII: Storage Architecture

## 7.1 Layers

```
┌─────────────────────────────────────────────────────────┐
│                    MUTATION LOG                          │
│              Append-only, immutable                      │
│     ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐            │
│     │ M1  │→│ M2  │→│ M3  │→│ M4  │→│ M5  │→ ...       │
│     └─────┘ └─────┘ └─────┘ └─────┘ └─────┘            │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │  Claim   │   │ Conflict │   │Projection│
   │  Store   │   │  Store   │   │  Cache   │
   └──────────┘   └──────────┘   └──────────┘
```

## 7.2 Operations

| Operation | Description |
|-----------|-------------|
| `append_mutation` | Add to log, update stores |
| `rebuild_state` | Replay log to reconstruct |
| `query_claims` | Read from claim store |
| `project` | Generate from current state |

---

# Part VIII: Terminology Migration

| Old Term | New Term | Why |
|----------|----------|-----|
| Gene | Claim | "Gene" implied fixed structure; "Claim" implies assertion with evidence |
| Column | Lens | "Column" implied spreadsheet; "Lens" implies perspective |
| Matrix | Projection | "Matrix" implied source of truth; "Projection" implies computed view |
| Static vocabulary | Cluster package | Vocabulary is optional, not core |

---

# Part IX: File Structure

```
dna-matrix/
├── core/
│   ├── claim.py         # Claim dataclass + validation
│   ├── lens.py          # Lens definitions + resolvers
│   ├── mutation.py      # Mutation engine
│   ├── conflict.py      # Conflict detection + resolution
│   ├── projection.py    # View generation
│   └── primitives.py    # The 7 primitives as types
├── storage/
│   ├── log.py           # Mutation log interface
│   ├── claims.py        # Claim store
│   ├── conflicts.py     # Conflict store
│   └── projections.py   # Projection cache
├── api/
│   ├── routes/
│   │   ├── organisms.py
│   │   ├── claims.py
│   │   ├── mutations.py
│   │   ├── conflicts.py
│   │   └── tasks.py     # evaluate, simulate, diff, explain, recommend
│   └── main.py
├── sdk/
│   └── python/
│       ├── matrix.py    # Main client
│       ├── organism.py  # Organism operations
│       ├── query.py     # Query builder
│       └── conflict.py  # Conflict handling
└── clusters/
    ├── brand/           # Optional: brand lens package
    ├── market/          # Optional: market lens package
    └── risk/            # Optional: risk lens package
```

---

# Part X: Success Criteria

| Metric | Target |
|--------|--------|
| All 7 primitives addressable | ✓ |
| Mutations append-only | ✓ |
| Lineage queryable | ✓ |
| Conflicts first-class | ✓ |
| Coherence computed, never stored | ✓ |
| Matrix is projection only | ✓ |
| Time-travel possible | ✓ |

---

## Next Pass

**Primitive → Interactions**

How do the 7 primitives affect each other?

- Weight influences conflict severity
- Constraint violations affect coherence
- Drift triggers conflict detection
- Tradeoffs modify weight distribution
- Lineage determines rollback scope
