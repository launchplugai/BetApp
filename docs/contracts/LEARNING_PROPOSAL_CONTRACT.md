# LEARNING_PROPOSAL_CONTRACT.md
# Learning Proposal Contract

**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-08

---

## 1. Purpose

This contract defines the canonical proposal record produced by governed learning systems.

Learning proposals are the unit of change for:

- calibration updates
- protocol tuning
- recommendation ranking adjustments
- personalization behavior tuning
- alert ranking adjustments

They are proposals only, never direct production mutations.

---

## 2. Core Rules

- every production-affecting learning change MUST begin as a proposal
- proposals MUST contain evidence, scope, and bounds
- proposals MUST support explicit review and rejection
- proposals MUST NOT mutate production state directly

---

## 3. Canonical Record

```json
{
  "proposalId": "prop_001",
  "proposalType": "protocol_tuning",
  "createdAt": "2026-03-08T15:00:00-05:00",
  "status": "pending_review",
  "target": {
    "entityType": "protocol",
    "entityId": "fatigue_b2b_v1",
    "field": "stabilityPenalty"
  },
  "currentValue": -8,
  "proposedValue": -10,
  "reason": "Observed underestimation of performance degradation in qualifying games.",
  "evidence": {
    "sampleSize": 4231,
    "holdoutImprovement": 0.04,
    "calibrationImpact": "neutral"
  },
  "allowedRange": [-12, -4],
  "modelScope": ["NBA"],
  "review": {
    "required": true,
    "reviewedBy": null,
    "reviewedAt": null,
    "decision": null
  }
}
```

---

## 4. Required Fields

- `proposalId`
- `proposalType`
- `createdAt`
- `status`
- `target`
- `currentValue`
- `proposedValue`
- `reason`
- `evidence`
- `allowedRange`
- `modelScope`
- `review`

---

## 5. Allowed Proposal Types

Initial allowed values:

- `calibration_update`
- `protocol_tuning`
- `recommendation_ranking`
- `personalization_tuning`
- `alert_ranking_tuning`
- `strategy_discovery_research`

New production-affecting proposal types require contract review.

---

## 6. Status Values

Allowed `status` values:

- `draft`
- `pending_review`
- `approved`
- `rejected`
- `promoted`
- `rolled_back`

---

## 7. Target Object

The `target` object MUST include:

- `entityType`
- `entityId`
- `field`

Examples:

- protocol field
- calibration bucket map
- recommendation rank parameter
- personalization setting

The target MUST be specific enough for reviewers to understand the blast radius.

---

## 8. Evidence Requirements

The `evidence` object SHOULD include:

- `sampleSize`
- `holdoutImprovement`
- `calibrationImpact`
- confidence or significance indicators when relevant

Additional evidence fields MAY include:

- segment scope
- regression check summary
- overconfidence delta
- explanation integrity notes

---

## 9. Bounds And Safety

Every proposal MUST define:

- `allowedRange`
- effective scope
- current value
- proposed value

Where relevant, systems SHOULD also store:

- minimum step size
- maximum allowed delta
- rollback target hint

---

## 10. Review Object

Minimum `review` object shape:

```json
{
  "required": true,
  "reviewedBy": null,
  "reviewedAt": null,
  "decision": null
}
```

Optional extended review fields MAY include:

- reviewer notes
- requested changes
- narrowed scope
- rollout mode

---

## 11. Guardrails

- proposals MUST NOT apply themselves to production
- proposals MUST remain queryable after rejection
- proposals MUST preserve current and proposed values explicitly
- proposals for forbidden self-modification domains MUST be blocked at creation

Forbidden proposal domains include:

- legal language
- odds parsing logic
- settlement logic
- core scoring equation structure
- compliance gating

---

## 12. Invariants

```
INVARIANT: Production-affecting learning changes MUST begin as proposals.
INVARIANT: Proposals MUST contain explicit target, current value, proposed value, and evidence.
INVARIANT: Proposals MUST NOT mutate production state directly.
INVARIANT: Rejected proposals MUST remain queryable for audit.
```
