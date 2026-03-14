# PROMOTION_AUDIT_CONTRACT.md
# Promotion Audit Contract

**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-08

---

## 1. Purpose

This contract defines the canonical record for promoting approved learning proposals into active versioned production config.

Promotion records exist to answer:

- what changed?
- when did it change?
- who approved it?
- what can we roll back to?

---

## 2. Core Rules

- every promoted proposal MUST create a promotion audit record
- every promotion MUST reference an explicit rollback target when practical
- promotions MUST be append-only historical events
- rollback events MUST also be recorded explicitly

---

## 3. Canonical Promotion Record

```json
{
  "promotionId": "prom_101",
  "proposalId": "prop_001",
  "promotedAt": "2026-03-10T09:30:00-05:00",
  "approvedBy": "admin_user_1",
  "oldVersion": "pl_v1.0.0",
  "newVersion": "pl_v1.0.1",
  "rollbackVersion": "pl_v1.0.0",
  "notes": "Approved after holdout validation and QA review."
}
```

---

## 4. Required Fields

- `promotionId`
- `proposalId`
- `promotedAt`
- `approvedBy`
- `oldVersion`
- `newVersion`

### 4.1 Strongly Recommended

- `rollbackVersion`
- `notes`
- rollout mode
- environment or cohort scope

---

## 5. Rollback Record

Rollback events SHOULD be represented either:

- as explicit promotion audit records with rollback metadata
- or as a separate rollback table linked to the original promotion

Minimum rollback shape:

```json
{
  "rollbackId": "rb_001",
  "sourcePromotionId": "prom_101",
  "rolledBackAt": "2026-03-12T11:10:00-05:00",
  "rolledBackBy": "admin_user_2",
  "fromVersion": "pl_v1.0.1",
  "toVersion": "pl_v1.0.0",
  "reason": "Post-promotion calibration drift detected."
}
```

---

## 6. Query Requirements

Promotion audit records MUST support queries by:

- proposal ID
- version pair
- approver
- date range
- entity type
- scope
- rollback status

---

## 7. Guardrails

- promotions MUST NOT occur without an approved proposal
- promotion records MUST NOT be overwritten in place
- rollback targets MUST be explicit or intentionally null with reason
- promotion audit history MUST remain intact after rollback

---

## 8. Invariants

```
INVARIANT: Every production promotion MUST create an audit record.
INVARIANT: Promotions MUST reference the proposal they came from.
INVARIANT: Audit records MUST remain queryable after rollback.
INVARIANT: Rollback history MUST be explicit, not inferred.
```
