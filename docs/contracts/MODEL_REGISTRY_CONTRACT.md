# MODEL_REGISTRY_CONTRACT.md
# Model Registry Contract

**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-08

---

## 1. Purpose

This contract defines the canonical registry for all versioned logic that can affect evaluation, recommendations, personalization, alerts, and governed learning.

The model registry exists to answer:

- what logic was live when an evaluation happened?
- what changed later?
- what rollback target exists?

---

## 2. Scope

The model registry tracks versioned production-affecting artifacts including:

- DNA scoring models
- protocol library versions
- calibration versions
- recommendation versions
- personalization model versions
- alert ranking versions

---

## 3. Core Rules

- every production-affecting model or config MUST have a registry entry
- every evaluation log MUST reference the exact active versions used
- every promoted version MUST record a rollback target
- the registry MUST support staging and production status separately

---

## 4. Registry Record Contract

Minimum registry record shape:

```json
{
  "registryId": "reg_001",
  "entityType": "protocol_library",
  "entityName": "Protocol Library",
  "version": "pl_v1.0.0",
  "status": "production",
  "scope": ["global"],
  "createdAt": "2026-03-08T16:00:00-05:00",
  "promotedAt": "2026-03-10T09:30:00-05:00",
  "rollbackVersion": null,
  "sourceProposalId": null,
  "metadata": {
    "notes": "Initial launch version"
  }
}
```

### 4.1 Required Fields

- `registryId`
- `entityType`
- `entityName`
- `version`
- `status`
- `scope`
- `createdAt`

### 4.2 Optional Fields

- `promotedAt`
- `rollbackVersion`
- `sourceProposalId`
- `metadata`

---

## 5. Allowed Entity Types

Allowed initial `entityType` values:

- `dna_model`
- `protocol_library`
- `calibration`
- `recommendation_model`
- `personalization_model`
- `alert_ranking`

New entity types require contract review.

---

## 6. Status Values

Allowed `status` values:

- `draft`
- `staging`
- `production`
- `deprecated`
- `rolled_back`

### 6.1 Rules

- only one `production` version per `entityType` + scope combination SHOULD be active at once
- `deprecated` versions remain queryable
- `rolled_back` versions remain historically visible

---

## 7. Scope Rules

The registry MUST support scope values such as:

- `global`
- sport-specific scopes like `NBA`, `NFL`
- market-specific scopes
- cohort scopes for staged rollouts

The scope used by an evaluation MUST be reconstructible after the fact.

---

## 8. Promotion Linkage

If a registry version was created through governed learning, it SHOULD reference:

- `sourceProposalId`
- promotion record ID in metadata or relational linkage

This linkage is required for high-risk logic classes:

- calibration
- protocol library
- recommendation severity logic
- personalization behavior affecting ranked output

---

## 9. Query Requirements

The registry MUST support queries by:

- `entityType`
- `version`
- `status`
- scope
- date ranges
- proposal linkage

It MUST be possible to determine the full active version set for any evaluation timestamp.

---

## 10. Guardrails

- registry entries MUST be append-safe and audit-friendly
- production versions MUST NOT be overwritten in place
- registry MUST NOT allow silent version swaps
- rollback targets MUST be explicit for promoted versions where applicable

---

## 11. Invariants

```
INVARIANT: Every production-affecting model/config MUST have a registry entry.
INVARIANT: Every evaluation log MUST be able to reference exact active versions.
INVARIANT: Production versions MUST NOT be silently overwritten.
INVARIANT: Registry history MUST remain queryable after rollback or deprecation.
```
