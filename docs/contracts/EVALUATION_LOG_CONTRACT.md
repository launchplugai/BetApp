# EVALUATION_LOG_CONTRACT.md
# Evaluation Log Contract

**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-08

---

## 1. Purpose

This contract defines the canonical evaluation log record for DNA Matrix / BetApp.

Evaluation logs are the foundation for:

- calibration
- protocol tuning
- recommendation analysis
- personalization learning
- auditability

---

## 2. Core Rules

- every completed evaluation SHOULD produce a log record
- evaluation logs MUST capture the exact model/config versions used
- evaluation logs MUST be immutable after settlement except for append-only enrichment fields
- evaluation logs MUST preserve enough detail to reconstruct why the system behaved as it did

---

## 3. Canonical Record

```json
{
  "evaluationId": "eval_123",
  "betId": "bet_456",
  "userId": "user_789",
  "timestamp": "2026-03-08T13:20:00-05:00",
  "sport": "NBA",
  "marketType": "parlay",
  "betType": "mixed",
  "legs": 4,
  "stake": 10000,
  "oddsSnapshot": {
    "books": []
  },
  "bestBook": "draftkings",
  "edgeScore": 3.2,
  "confidenceScore": 74,
  "fragilityScore": 58,
  "stabilityScore": 69,
  "dnaMode": "CORE_PLUS_PROTOCOLS",
  "triggeredProtocols": [
    "fatigue_b2b_v1",
    "pace_mismatch_v1"
  ],
  "recommendationType": "consider_simplifying",
  "recommendationDetails": {},
  "userAction": "paper_placed",
  "finalResult": "loss",
  "legsWon": 3,
  "legsLost": 1,
  "settlementTimestamp": "2026-03-08T23:15:00-05:00",
  "dnaModelVersion": "dna_v1.2.0",
  "protocolLibraryVersion": "pl_v1.0.0",
  "calibrationVersion": "cal_v1.0.1",
  "recommendationVersion": "rec_v1.0.0"
}
```

---

## 4. Required Fields

Required fields:

- `evaluationId`
- `timestamp`
- `sport`
- `marketType`
- `legs`
- `confidenceScore`
- `fragilityScore`
- `stabilityScore`
- `dnaMode`
- `triggeredProtocols`
- `recommendationType`
- `userAction`
- `dnaModelVersion`
- `protocolLibraryVersion`
- `calibrationVersion`
- `recommendationVersion`

### 4.1 Required When Available

These SHOULD be populated whenever the system knows them:

- `betId`
- `userId`
- `stake`
- `oddsSnapshot`
- `bestBook`
- `edgeScore`
- `recommendationDetails`
- `finalResult`
- `legsWon`
- `legsLost`
- `settlementTimestamp`

---

## 5. Enumerations

### 5.1 `dnaMode`

Initial allowed values:

- `CORE_ONLY`
- `CORE_PLUS_PROTOCOLS`
- `CORE_PLUS_PROTOCOLS_PLUS_CALIBRATION`

### 5.2 `userAction`

Initial allowed values:

- `no_action`
- `view_only`
- `paper_placed`
- `placed`
- `modified_after_suggestion`
- `dismissed`

### 5.3 `finalResult`

Initial allowed values:

- `win`
- `loss`
- `push`
- `void`
- `unknown`

---

## 6. Append-Only Enrichment Fields

These may be added or populated after the initial evaluation record exists:

- `finalResult`
- `legsWon`
- `legsLost`
- `settlementTimestamp`
- closing line data
- post-evaluation injury/news changes
- odds drift after evaluation
- alert interaction history

These enrichments MUST be timestamped if stored outside the base row.

---

## 7. Query Requirements

Evaluation logs MUST be queryable by:

- date range
- user
- sport
- market type
- triggered protocol
- recommendation type
- version set
- confidence bucket
- result outcome

---

## 8. Guardrails

- evaluation logs MUST NOT be rewritten to hide historical behavior
- version references MUST reflect what was live at evaluation time
- learning systems MUST treat evaluation logs as factual records, not mutable narrative

---

## 9. Invariants

```
INVARIANT: Evaluation logs MUST capture the exact version set used at evaluation time.
INVARIANT: Evaluation logs MUST remain audit-friendly after settlement.
INVARIANT: Append-only enrichment MUST NOT destroy the original record.
INVARIANT: Triggered protocols MUST be stored as actually emitted, not reconstructed later.
```
