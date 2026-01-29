# DNA_PRIMITIVES_CONTRACT.md
# DNA Matrix Primitives Contract

**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-01-29

---

## 1. Overview

This contract defines the 7 Frozen Primitives that form the DNA Matrix storage layer. These primitives are the canonical representation of all state changes in the system.

### 1.1 The 7 Frozen Primitives

| Primitive | Purpose | Mutability |
|-----------|---------|------------|
| `weight` | Numeric importance/confidence scores | Immutable after creation |
| `constraint` | Conditions that bound decisions | Immutable after creation |
| `conflict` | Detected contradictions | NEVER deleted, append-only |
| `baseline` | Known starting states | Immutable snapshot |
| `drift` | Changes from baseline | Append-only log |
| `tradeoff` | Explicit cost/benefit records | Required for decisions |
| `lineage` | Provenance chain | Append-only, never modified |

### 1.2 Invariants (FROZEN)

```
INVARIANT: Conflicts are NEVER deleted.
INVARIANT: Lineage is append-only.
INVARIANT: Baselines are immutable snapshots.
INVARIANT: Every decision MUST have a tradeoff record.
INVARIANT: All primitives MUST have version and created_at.
```

---

## 2. Primitive Schemas

### 2.1 Weight

Represents numeric importance, confidence, or scoring values.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Weight",
  "type": "object",
  "required": ["id", "version", "created_at", "target_type", "target_id", "value", "source"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier"
    },
    "version": {
      "type": "integer",
      "minimum": 1,
      "description": "Schema version"
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 creation timestamp"
    },
    "target_type": {
      "type": "string",
      "enum": ["claim", "evidence", "argument", "verdict"],
      "description": "Type of entity being weighted"
    },
    "target_id": {
      "type": "string",
      "description": "ID of the weighted entity"
    },
    "value": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Weight value (0.0-1.0)"
    },
    "source": {
      "type": "string",
      "enum": ["sherlock", "user", "system"],
      "description": "Origin of the weight"
    },
    "metadata": {
      "type": "object",
      "default": {},
      "description": "Additional context"
    }
  },
  "additionalProperties": false
}
```

### 2.2 Constraint

Represents conditions or rules that bound decisions.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Constraint",
  "type": "object",
  "required": ["id", "version", "created_at", "constraint_type", "expression", "scope"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "version": {
      "type": "integer",
      "minimum": 1
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "constraint_type": {
      "type": "string",
      "enum": ["assumption", "requirement", "boundary", "invariant"],
      "description": "Type of constraint"
    },
    "expression": {
      "type": "string",
      "minLength": 1,
      "description": "Human-readable constraint statement"
    },
    "scope": {
      "type": "string",
      "description": "What this constraint applies to"
    },
    "source_claim_id": {
      "type": ["string", "null"],
      "default": null,
      "description": "ID of claim that generated this constraint"
    },
    "is_violated": {
      "type": "boolean",
      "default": false,
      "description": "Whether constraint is currently violated"
    },
    "violation_details": {
      "type": ["string", "null"],
      "default": null,
      "description": "Details if violated"
    }
  },
  "additionalProperties": false
}
```

### 2.3 Conflict

Represents detected contradictions. NEVER deleted.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Conflict",
  "type": "object",
  "required": ["id", "version", "created_at", "conflict_type", "parties", "description", "status"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "version": {
      "type": "integer",
      "minimum": 1
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "conflict_type": {
      "type": "string",
      "enum": ["logical", "evidential", "temporal", "scope"],
      "description": "Category of conflict"
    },
    "parties": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["entity_type", "entity_id"],
        "properties": {
          "entity_type": {"type": "string"},
          "entity_id": {"type": "string"}
        }
      },
      "minItems": 2,
      "description": "Entities in conflict"
    },
    "description": {
      "type": "string",
      "minLength": 1,
      "description": "Human-readable conflict description"
    },
    "status": {
      "type": "string",
      "enum": ["open", "acknowledged", "resolved_by_tradeoff"],
      "description": "Conflict status"
    },
    "resolution_tradeoff_id": {
      "type": ["string", "null"],
      "default": null,
      "description": "ID of tradeoff that resolved this (if any)"
    },
    "detected_by": {
      "type": "string",
      "enum": ["sherlock", "user", "system"],
      "default": "sherlock"
    }
  },
  "additionalProperties": false
}
```

**INVARIANT:** Conflicts are NEVER deleted. Status may change, but record persists.

### 2.4 Baseline

Represents a known starting state (immutable snapshot).

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Baseline",
  "type": "object",
  "required": ["id", "version", "created_at", "entity_type", "entity_id", "snapshot"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "version": {
      "type": "integer",
      "minimum": 1
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "entity_type": {
      "type": "string",
      "description": "Type of entity snapshotted"
    },
    "entity_id": {
      "type": "string",
      "description": "ID of entity snapshotted"
    },
    "snapshot": {
      "type": "object",
      "description": "Complete state at baseline time"
    },
    "snapshot_hash": {
      "type": "string",
      "description": "SHA-256 hash of snapshot for integrity"
    },
    "reason": {
      "type": "string",
      "description": "Why this baseline was created"
    }
  },
  "additionalProperties": false
}
```

**INVARIANT:** Baselines are immutable. To update, create a new baseline.

### 2.5 Drift

Represents changes from a baseline (append-only log).

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Drift",
  "type": "object",
  "required": ["id", "version", "created_at", "baseline_id", "drift_type", "delta"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "version": {
      "type": "integer",
      "minimum": 1
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "baseline_id": {
      "type": "string",
      "format": "uuid",
      "description": "ID of baseline this drifts from"
    },
    "drift_type": {
      "type": "string",
      "enum": ["addition", "removal", "modification", "reweight"],
      "description": "Type of drift"
    },
    "delta": {
      "type": "object",
      "description": "The actual change (diff)"
    },
    "magnitude": {
      "type": "number",
      "minimum": 0.0,
      "description": "Quantified drift magnitude"
    },
    "cause": {
      "type": "string",
      "description": "What caused this drift"
    },
    "sherlock_report_id": {
      "type": ["string", "null"],
      "default": null,
      "description": "ID of Sherlock report that caused drift (if any)"
    }
  },
  "additionalProperties": false
}
```

**INVARIANT:** Drift records are append-only. Never modify or delete.

### 2.6 Tradeoff

Represents explicit cost/benefit records for decisions.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Tradeoff",
  "type": "object",
  "required": ["id", "version", "created_at", "decision", "benefits", "costs", "accepted_by"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "version": {
      "type": "integer",
      "minimum": 1
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "decision": {
      "type": "string",
      "minLength": 1,
      "description": "The decision being made"
    },
    "benefits": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1,
      "description": "List of benefits"
    },
    "costs": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1,
      "description": "List of costs/downsides"
    },
    "alternatives_considered": {
      "type": "array",
      "items": {"type": "string"},
      "default": [],
      "description": "Other options that were rejected"
    },
    "accepted_by": {
      "type": "string",
      "enum": ["user", "system", "sherlock"],
      "description": "Who accepted this tradeoff"
    },
    "resolves_conflict_id": {
      "type": ["string", "null"],
      "default": null,
      "description": "ID of conflict this tradeoff resolves"
    },
    "sherlock_report_id": {
      "type": ["string", "null"],
      "default": null,
      "description": "ID of Sherlock report backing this decision"
    }
  },
  "additionalProperties": false
}
```

**INVARIANT:** Every significant decision MUST have a tradeoff record.

### 2.7 Lineage

Represents provenance chain (append-only).

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Lineage",
  "type": "object",
  "required": ["id", "version", "created_at", "entity_type", "entity_id", "parent_id", "operation"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "version": {
      "type": "integer",
      "minimum": 1
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "entity_type": {
      "type": "string",
      "description": "Type of entity in lineage"
    },
    "entity_id": {
      "type": "string",
      "description": "ID of entity"
    },
    "parent_id": {
      "type": ["string", "null"],
      "description": "ID of parent lineage record (null for roots)"
    },
    "operation": {
      "type": "string",
      "enum": ["create", "derive", "transform", "merge", "split"],
      "description": "What operation produced this entity"
    },
    "source_ids": {
      "type": "array",
      "items": {"type": "string"},
      "default": [],
      "description": "IDs of source entities"
    },
    "actor": {
      "type": "string",
      "enum": ["user", "sherlock", "system"],
      "description": "Who performed the operation"
    },
    "sherlock_report_id": {
      "type": ["string", "null"],
      "default": null,
      "description": "ID of Sherlock report if Sherlock was actor"
    }
  },
  "additionalProperties": false
}
```

**INVARIANT:** Lineage is append-only. Never modify or delete lineage records.

---

## 3. Common Fields

All primitives MUST have these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | uuid | YES | Unique identifier |
| `version` | integer | YES | Schema version (≥1) |
| `created_at` | datetime | YES | ISO 8601 timestamp |

---

## 4. Versioning Rules

### 4.1 Schema Versioning

- Each primitive type has independent version numbering
- MAJOR version changes require migration
- MINOR version changes are backward-compatible
- Current versions: all primitives are v1

### 4.2 Instance Versioning

- `version` field tracks schema version used
- Old instances remain valid when schema evolves
- Migration scripts MUST exist for version bumps

---

## 5. Validation Rules

### 5.1 Required Validations

Before persisting any primitive:

1. `id` MUST be valid UUID
2. `version` MUST be ≥ 1
3. `created_at` MUST be valid ISO 8601
4. All required fields MUST be present
5. Enum fields MUST contain valid values
6. References (foreign keys) MUST exist

### 5.2 Integrity Checks

- Weight values MUST be 0.0-1.0
- Conflict parties MUST have ≥ 2 entities
- Baseline snapshot_hash MUST match snapshot
- Drift baseline_id MUST reference existing baseline
- Lineage parent_id MUST reference existing lineage (or be null)

---

## 6. Access Patterns

### 6.1 Read Operations (Allowed)

- Query by id
- Query by entity_type + entity_id
- Query by created_at range
- Query by status (for conflicts)
- Traverse lineage chain

### 6.2 Write Operations (Restricted)

| Primitive | Create | Update | Delete |
|-----------|--------|--------|--------|
| weight | YES | NO | NO |
| constraint | YES | is_violated only | NO |
| conflict | YES | status only | NEVER |
| baseline | YES | NO | NO |
| drift | YES | NO | NO |
| tradeoff | YES | NO | NO |
| lineage | YES | NO | NO |

---

## 7. Compliance Checklist

Before implementing DNA primitives:

- [ ] All 7 primitives have id, version, created_at
- [ ] Conflicts are never deleted
- [ ] Lineage is append-only
- [ ] Baselines are immutable
- [ ] Tradeoffs exist for all decisions
- [ ] Foreign key references are validated
- [ ] Schema version is tracked

---

## References

- `docs/contracts/SYSTEM_CONTRACT_SDS.md` - How Sherlock feeds DNA
- `docs/mappings/MAP_SHERLOCK_TO_DNA.md` - Sherlock → DNA translation
