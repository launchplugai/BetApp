# DNA Matrix: API Schemas v0.1

> Where the constitution meets button-mashing humans.

---

## Conventions

### Base URL

```
/api/v1
```

### Authentication

Support both (middleware decides):

| Method | Header |
|--------|--------|
| JWT | `Authorization: Bearer <token>` |
| API Key | `X-API-Key: <key>` |

### ID Format

All IDs are **UUID v7** with prefixes:

| Prefix | Entity |
|--------|--------|
| `org_` | Organism |
| `clm_` | Claim |
| `mut_` | Mutation |
| `cst_` | Constraint |
| `cfl_` | Conflict |
| `prj_` | Projection |
| `lns_` | Lens |

### Response Envelope

**Success**:

```json
{
  "ok": true,
  "data": { },
  "meta": {
    "requestId": "req_...",
    "timestamp": "2025-12-25T12:00:00Z"
  }
}
```

**Error**:

```json
{
  "ok": false,
  "error": {
    "code": "CONSTRAINT_HARD_FAIL",
    "message": "Mutation rejected due to hard constraint failure.",
    "details": {
      "constraintResults": [ ],
      "mutationId": "mut_..."
    }
  },
  "meta": {
    "requestId": "req_...",
    "timestamp": "2025-12-25T12:00:00Z"
  }
}
```

### Pagination

```json
{
  "ok": true,
  "data": [ ],
  "meta": {
    "cursor": "next_cursor",
    "limit": 50,
    "total": 1234
  }
}
```

---

## Core Types

### Value (ClaimValue)

```json
{
  "kind": "string|number|bool|enum|json",
  "data": "..."
}
```

### LensRef

```json
{
  "cluster": "brand|org|agent|product|person|custom",
  "key": "dot.path.key"
}
```

### Actor

```json
{
  "type": "human|agent|system",
  "id": "usr_...|agt_...|sys_...",
  "label": "Display Name"
}
```

### TradeoffEntry

```json
{
  "gaveUp": { "lens": "brand.accessibility", "delta": -0.2 },
  "gained": { "lens": "brand.exclusivity", "delta": 0.3 },
  "weight": 0.7,
  "cost": "reduced short-term revenue potential",
  "justification": "brand integrity takes precedence"
}
```

### ConstraintResult

```json
{
  "constraintId": "cst_...",
  "passed": false,
  "severity": "hard|soft",
  "code": "EXCLUSION_VIOLATION",
  "message": "brand.positioning=luxury excludes brand.discounting.strategy=discount-heavy",
  "evidence": {
    "left": { "lens": "brand.positioning", "value": "luxury" },
    "right": { "lens": "brand.discounting.strategy", "value": "discount-heavy" }
  },
  "repairHints": [
    { "action": "set", "lens": "brand.discounting.strategy", "suggest": "minimal" }
  ]
}
```

---

# Organisms

## Model

```json
{
  "id": "org_7b3f8a2c",
  "organismType": "brand|person|agent|product|org|custom",
  "name": "Apple",
  "tags": ["portfolio:consumer-tech", "sector:hardware"],
  "createdAt": "2025-12-25T00:00:00Z",
  "updatedAt": "2025-12-25T00:00:00Z"
}
```

## Endpoints

### Create Organism

**POST** `/organisms`

```json
{
  "organismType": "brand",
  "name": "Apple",
  "tags": ["portfolio:consumer-tech"]
}
```

**Response**: `Organism`

---

### List Organisms

**GET** `/organisms`

| Param | Type | Description |
|-------|------|-------------|
| type | string | Filter by organismType |
| tag | string | Filter by tag |
| limit | int | Max results (default 50) |
| cursor | string | Pagination cursor |

**Response**: `Organism[]`

---

### Get Organism

**GET** `/organisms/{organismId}`

**Response**: `Organism`

---

### Get Organism Claims

**GET** `/organisms/{organismId}/claims`

| Param | Type | Description |
|-------|------|-------------|
| cluster | string | Filter by cluster |
| limit | int | Max results |
| cursor | string | Pagination cursor |

**Response**: `Claim[]`

---

### Get Organism Conflicts

**GET** `/organisms/{organismId}/conflicts`

| Param | Type | Description |
|-------|------|-------------|
| status | string | active, resolved, suppressed |
| severity | string | low, medium, high, existential |

**Response**: `Conflict[]`

---

### Get Organism Mutations

**GET** `/organisms/{organismId}/mutations`

| Param | Type | Description |
|-------|------|-------------|
| status | string | Filter by status |
| since | datetime | After this time |
| limit | int | Max results |

**Response**: `Mutation[]`

---

# Claims

## Model

```json
{
  "id": "clm_8x9f2k4m",
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
  "constraints": ["cst_enum_check", "cst_luxury_exclusion"],
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

## Endpoints

### List Claims

**GET** `/claims`

| Param | Type | Description |
|-------|------|-------------|
| organismId | string | Required filter |
| cluster | string | Filter by cluster |
| lens | string | Filter by lens key |
| limit | int | Max results |
| cursor | string | Pagination cursor |

**Response**: `Claim[]`

---

### Get Claim

**GET** `/claims/{claimId}`

| Param | Type | Description |
|-------|------|-------------|
| expand | string | `constraints` to include full objects |

**Response**: `Claim`

---

### Get Claim History

**GET** `/claims/{claimId}/history`

| Param | Type | Description |
|-------|------|-------------|
| limit | int | Max versions |

**Response**:

```json
{
  "claimId": "clm_...",
  "versions": [
    {
      "version": 3,
      "value": { "kind": "enum", "data": "luxury" },
      "weight": 0.83,
      "mutationId": "mut_...",
      "changedAt": "2025-01-20T14:30:00Z"
    },
    {
      "version": 2,
      "value": { "kind": "enum", "data": "premium" },
      "weight": 0.7,
      "mutationId": "mut_...",
      "changedAt": "2024-06-01T00:00:00Z"
    }
  ]
}
```

---

### Direct Claim Write

**⚠️ NOT ALLOWED**

There is no direct "set claim value" endpoint. All writes go through **mutations**. This keeps lineage sacred.

---

# Mutations

## Model

```json
{
  "id": "mut_def456",
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
    }
  ],
  "tradeoffs": [],
  "constraintResults": [],
  "conflictsCreated": [],
  "status": "proposed",
  "prevMutationId": "mut_abc123",
  "createdAt": "2025-01-20T14:30:00Z",
  "committedAt": null
}
```

### Change Object

```json
{
  "claimId": "clm_...",
  "op": "set|merge|delete|reweight|rebaseline|constrain",
  "before": { },
  "after": { }
}
```

### Status Values

| Status | Meaning |
|--------|---------|
| `proposed` | Created, not validated |
| `validated` | Constraints checked |
| `committed` | Applied to claims |
| `rejected` | Failed validation |
| `rolledBack` | Undone after commit |

## Endpoints

### Propose Mutation

**POST** `/mutations`

```json
{
  "organismId": "org_...",
  "actor": {
    "type": "human",
    "id": "usr_alice",
    "label": "Alice Chen"
  },
  "intent": "repositioning",
  "changes": [
    {
      "claimId": "clm_...",
      "op": "set",
      "after": { "kind": "enum", "data": "luxury" }
    },
    {
      "claimId": "clm_...",
      "op": "reweight",
      "after": 0.9
    }
  ]
}
```

**Response**: `Mutation` with `status=proposed`

---

### Validate Mutation

**POST** `/mutations/{mutationId}/validate`

```json
{
  "dryRun": true,
  "requireExplain": true
}
```

**Response**:

```json
{
  "mutationId": "mut_...",
  "valid": false,
  "hardFails": 1,
  "softFails": 2,
  "constraintResults": [ ],
  "conflictsWouldCreate": [ ],
  "tradeoffRequired": true,
  "explain": {
    "topIssues": [ ]
  }
}
```

---

### Commit Mutation

**POST** `/mutations/{mutationId}/commit`

```json
{
  "tradeoffs": [
    {
      "gaveUp": { "lens": "brand.accessibility", "delta": -0.2 },
      "gained": { "lens": "brand.exclusivity", "delta": 0.3 },
      "justification": "Brand integrity takes precedence"
    }
  ],
  "comment": "Proceed with repositioning"
}
```

**Response**: `Mutation` with `status=committed`

**Error** (hard constraint fail):

```json
{
  "ok": false,
  "error": {
    "code": "CONSTRAINT_HARD_FAIL",
    "message": "Mutation rejected due to hard constraint failure.",
    "details": {
      "constraintResults": [ ],
      "hardFails": 1
    }
  }
}
```

---

### Reject Mutation

**POST** `/mutations/{mutationId}/reject`

```json
{
  "reason": "Does not align with Q1 strategy",
  "rejectedBy": "usr_bob"
}
```

**Response**: `Mutation` with `status=rejected`

---

### Rollback Mutation

**POST** `/mutations/{mutationId}/rollback`

```json
{
  "reason": "Bad outcome in market response",
  "actor": {
    "type": "human",
    "id": "usr_alice",
    "label": "Alice Chen"
  }
}
```

**Response**: `Mutation` with `status=rolledBack`

---

### Get Mutation

**GET** `/mutations/{mutationId}`

**Response**: `Mutation`

---

# Constraints

## Model

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

## Endpoints

### List Constraints

**GET** `/constraints`

| Param | Type | Description |
|-------|------|-------------|
| scope | string | claim, lens, organism, cluster, global |
| cluster | string | Filter by cluster |
| severity | string | hard, soft |
| limit | int | Max results |

**Response**: `Constraint[]`

---

### Get Constraint

**GET** `/constraints/{constraintId}`

**Response**: `Constraint`

---

### Create Constraint

**POST** `/constraints`

```json
{
  "version": "1.0",
  "name": "...",
  "severity": "hard",
  "scope": "claim",
  "target": { },
  "rule": { },
  "onFail": { }
}
```

**Response**: `Constraint`

---

### Update Constraint

**PUT** `/constraints/{constraintId}`

Version bump required.

```json
{
  "version": "1.1",
  "name": "...",
  "rule": { }
}
```

**Response**: `Constraint`

---

### Delete Constraint

**DELETE** `/constraints/{constraintId}`

Soft delete. Constraint remains in history for lineage.

---

# Conflicts

## Model

```json
{
  "id": "cfl_ghi789",
  "type": "exclusion-constraint",
  "status": "active",
  "severity": "high",
  "organismId": "org_7b3f8a2c",
  "claims": [
    {
      "claimId": "clm_8x9f2k4m",
      "lens": "brand.positioning",
      "value": "luxury",
      "weight": 0.83
    },
    {
      "claimId": "clm_price_pos",
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
  "lineage": {
    "parentMutation": "mut_ghi789",
    "supersedes": []
  },
  "resolution": null,
  "createdAt": "2025-12-25T00:00:00Z",
  "updatedAt": "2025-12-25T00:00:00Z"
}
```

## Endpoints

### List Conflicts

**GET** `/conflicts`

| Param | Type | Description |
|-------|------|-------------|
| status | string | active, resolved, suppressed |
| severity | string | low, medium, high, existential |
| type | string | exclusion-constraint, baseline-violation, derived |
| organismId | string | Filter by organism |
| since | datetime | Created after |
| limit | int | Max results |

**Response**: `Conflict[]`

---

### Get Conflict

**GET** `/conflicts/{conflictId}`

**Response**: `Conflict`

---

### Resolve Conflict

**POST** `/conflicts/{conflictId}/resolve`

```json
{
  "resolvedBy": "usr_alice",
  "strategy": "prefer-weight",
  "chosenClaimId": "clm_8x9f2k4m",
  "sacrificed": [
    {
      "claimId": "clm_price_pos",
      "action": "changed",
      "newValue": { "kind": "enum", "data": "minimal" }
    }
  ],
  "tradeoff": {
    "gaveUp": { "lens": "brand.discounting.strategy", "delta": "discount-heavy → minimal" },
    "gained": { "lens": "brand.positioning", "preserved": "luxury" },
    "justification": "Brand integrity takes precedence"
  }
}
```

**Response**: `Conflict` with populated `resolution` + `mutationId`

---

### Suppress Conflict

**POST** `/conflicts/{conflictId}/suppress`

```json
{
  "reason": "Temporary exception for holiday campaign",
  "expiresAt": "2026-01-10T00:00:00Z",
  "approvedBy": "usr_policy_owner"
}
```

**Response**: `Conflict` with `status=suppressed`

---

### Get Conflict Stats

**GET** `/conflicts/stats`

| Param | Type | Description |
|-------|------|-------------|
| organismId | string | Filter by organism |

**Response**:

```json
{
  "total": 47,
  "byStatus": {
    "active": 12,
    "resolved": 30,
    "suppressed": 5
  },
  "bySeverity": {
    "low": 8,
    "medium": 25,
    "high": 12,
    "existential": 2
  },
  "byType": {
    "exclusion-constraint": 30,
    "baseline-violation": 15,
    "derived": 2
  }
}
```

---

# Query / Evaluate

## Evaluate Organism

**POST** `/query/evaluate`

```json
{
  "organismId": "org_...",
  "include": {
    "coherence": true,
    "drift": true,
    "conflicts": true,
    "constraintResults": true,
    "explain": true
  },
  "policyProfile": "default"
}
```

**Response**:

```json
{
  "organismId": "org_...",
  "coherence": 0.71,
  "drift": {
    "total": 0.22,
    "topContributors": [
      { "lens": "brand.voice.tone", "drift": 0.4, "weight": 0.83, "weighted": 0.33 }
    ]
  },
  "conflicts": {
    "active": 2,
    "highSeverity": 1,
    "items": [ ]
  },
  "constraintResults": {
    "passed": 45,
    "softFailed": 3,
    "hardFailed": 0,
    "items": [ ]
  },
  "explain": {
    "coherenceDrivers": [
      { "type": "conflict", "id": "cfl_...", "impact": -0.18 },
      { "type": "drift", "lens": "brand.voice.tone", "impact": -0.11 }
    ],
    "recentMutations": ["mut_1", "mut_2", "mut_3"]
  }
}
```

---

## Simulate Mutation

**POST** `/query/simulate`

```json
{
  "organismId": "org_...",
  "changes": [
    { "lens": "brand.voice.tone", "op": "set", "value": { "kind": "enum", "data": "aggressive" } }
  ],
  "include": {
    "coherenceDelta": true,
    "conflictsCreated": true,
    "constraintResults": true
  }
}
```

**Response**:

```json
{
  "valid": true,
  "coherence": {
    "before": 0.71,
    "after": 0.58,
    "delta": -0.13
  },
  "conflictsWouldCreate": [ ],
  "constraintResults": [ ],
  "tradeoffRequired": true,
  "warnings": [
    "Coherence would drop below 0.6 threshold"
  ]
}
```

---

## Diff

**POST** `/query/diff`

```json
{
  "left": { "organismId": "org_a" },
  "right": { "organismId": "org_b" },
  "include": {
    "claims": true,
    "weights": true,
    "drift": true
  }
}
```

Or compare to baseline:

```json
{
  "left": { "organismId": "org_a", "asOf": "2024-06-01T00:00:00Z" },
  "right": { "organismId": "org_a" }
}
```

**Response**:

```json
{
  "summary": {
    "changedClaims": 32,
    "addedClaims": 5,
    "removedClaims": 2,
    "weightShifts": 9,
    "coherenceDelta": -0.12
  },
  "changes": [
    {
      "lens": "brand.voice.tone",
      "left": { "value": "luxury", "weight": 0.83 },
      "right": { "value": "minimal", "weight": 0.55 },
      "delta": { "valueChanged": true, "weightDelta": -0.28 }
    }
  ]
}
```

---

## Explain

**POST** `/query/explain`

```json
{
  "organismId": "org_...",
  "lens": "brand.strength.index"
}
```

**Response**:

```json
{
  "lens": "brand.strength.index",
  "value": 0.847,
  "computed": true,
  "resolver": {
    "type": "function",
    "formula": "(awareness * 0.3) + ((nps + 100) / 200 * 0.4) + (share * 0.3)"
  },
  "inputs": [
    { "lens": "brand.awareness", "value": 0.85, "claimId": "clm_...", "mutationId": "mut_001" },
    { "lens": "brand.nps", "value": 72, "claimId": "clm_...", "mutationId": "mut_002" },
    { "lens": "market.share", "value": 0.23, "claimId": "clm_...", "mutationId": "mut_003" }
  ],
  "lineage": {
    "lastModified": "2025-01-15T10:00:00Z",
    "mutationChain": ["mut_003", "mut_002", "mut_001"]
  }
}
```

---

## Recommend

**POST** `/query/recommend`

```json
{
  "organismId": "org_...",
  "goal": "increase_coherence",
  "constraints": {
    "maxChanges": 3,
    "preserveLenses": ["brand.positioning"]
  }
}
```

**Response**:

```json
{
  "recommendations": [
    {
      "action": "resolve_conflict",
      "conflictId": "cfl_...",
      "strategy": "prefer-weight",
      "impact": { "coherence": "+0.12" },
      "confidence": 0.85
    },
    {
      "action": "reweight",
      "claimId": "clm_...",
      "lens": "brand.discounting.strategy",
      "from": 0.6,
      "to": 0.3,
      "impact": { "coherence": "+0.05" },
      "confidence": 0.72
    }
  ],
  "projectedCoherence": 0.88
}
```

---

# Projections

## Generate Projection

**POST** `/projections`

```json
{
  "organismId": "org_...",
  "projectionType": "matrix|timeline|summary",
  "asOf": "2025-01-20T00:00:00Z"
}
```

**Response**: `Projection`

---

## Get Projection

**GET** `/projections/{projectionId}`

**Response**: `Projection`

---

# Lenses

## List Lenses

**GET** `/lenses`

| Param | Type | Description |
|-------|------|-------------|
| cluster | string | Filter by cluster |

**Response**: `Lens[]`

---

## Get Lens

**GET** `/lenses/{lensId}`

**Response**: `Lens`

---

# Health

## Health Check

**GET** `/health`

```json
{ "status": "ok" }
```

---

## Readiness

**GET** `/ready`

```json
{
  "status": "ready",
  "checks": {
    "storage": "ok",
    "migrations": "ok",
    "policyRegistry": "ok"
  }
}
```

---

## Metrics

**GET** `/metrics`

Prometheus format or JSON.

---

# Error Codes

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| `CONSTRAINT_HARD_FAIL` | 422 | Hard constraint blocked commit |
| `CONSTRAINT_SOFT_FAIL` | 422 | Soft constraint requires tradeoff |
| `CONFLICT_UNRESOLVED` | 422 | Must resolve conflict first |
| `TRADEOFF_REQUIRED` | 422 | Tradeoff missing for soft fail |
| `MUTATION_NOT_FOUND` | 404 | Mutation ID invalid |
| `CLAIM_NOT_FOUND` | 404 | Claim ID invalid |
| `ORGANISM_NOT_FOUND` | 404 | Organism ID invalid |
| `INVALID_OP` | 400 | Unknown operation |
| `LINEAGE_VIOLATION` | 409 | Would break lineage integrity |
| `VERSION_CONFLICT` | 409 | Concurrent modification |

---

# OpenAPI Tags

| Tag | Endpoints |
|-----|-----------|
| organisms | /organisms/* |
| claims | /claims/* |
| mutations | /mutations/* |
| constraints | /constraints/* |
| conflicts | /conflicts/* |
| query | /query/* |
| projections | /projections/* |
| lenses | /lenses/* |
| health | /health, /ready, /metrics |

---

## Next Pass

**SDK Finalization**

- Typed models matching these schemas
- Pagination helpers
- Mutation builder (fluent interface)
- Evaluate/diff convenience methods
- Retry/backoff
- Rich error mapping (codes → exceptions)
