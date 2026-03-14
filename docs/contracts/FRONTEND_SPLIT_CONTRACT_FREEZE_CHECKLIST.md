# Frontend Split Contract Freeze Checklist

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

This checklist defines the first frontend-facing contracts that must be frozen before the dedicated frontend app is scaffolded.

It is the execution bridge between:

- `docs/ops/FRONTEND_BACKEND_SEPARATION_PLAN.md`
- `docs/ui/FRONTEND_IMPLEMENTATION_SPEC.md`

## 1. Purpose

Before separating the frontend, the backend must expose stable, frontend-safe contracts for the first migration slice.

That first slice is:

```text
Evaluate
→ OCR review
→ Builder handoff
→ bet placement with evaluation linkage
→ history replay support
```

This checklist marks each surface as:

- `FROZEN` - safe for new frontend use
- `NEEDS_NORMALIZATION` - usable but inconsistent
- `NEEDS_EXTRACTION` - route exists but is not yet in the right API shape

## 2. Contract Table

| Surface | Route / Source | Status | Notes |
|---------|----------------|--------|-------|
| Text Evaluate | `POST /app/evaluate` | `NEEDS_NORMALIZATION` | Stable enough to build against, but payload still mixes backend legacy detail with frontend needs |
| Image Evaluate | `POST /app/evaluate/image` | `NEEDS_NORMALIZATION` | Used by live UI, but should not be the long-term OCR review contract for the new frontend |
| OCR Review | `POST /api/ocr/review` | `FROZEN` | Dedicated frontend-facing OCR trust-gate contract already exists |
| Evaluation Result Payload | `app.schemas.frontend_contracts.WebEvaluateResponseSchema` + `/app/evaluate` | `NEEDS_NORMALIZATION` | Top-level `evaluationId` is present, but payload remains additive and broader than necessary |
| Builder Handoff Payload | frontend state derived from evaluate response | `NEEDS_NORMALIZATION` | No dedicated backend contract doc yet; currently assembled in frontend JS from multiple fields |
| Bet Create | `POST /api/bets/` | `FROZEN` for first slice | Supports `evaluation_id` and returns it |
| Bet History List | `GET /api/bets/history` | `FROZEN` for first slice | Authenticated list with `evaluation_id` available |
| History Replay Detail | `GET /history/{item_id}` | `NEEDS_EXTRACTION` | Useful for replay/edit, but not yet aligned as the dedicated frontend contract |

## 3. Surface Details

## 3.1 Text Evaluate

### Current route

`POST /app/evaluate`

### Current source

- `app/routers/web.py`
- `app/schemas/frontend_contracts.py`

### Current strengths

- accepts text input
- accepts optional canonical legs
- exposes top-level `evaluationId`
- test-backed in `app/tests/test_frontend_contracts.py`

### Current issues

- response is converted from a broader backend result
- includes many additive fields not yet explicitly tiered into a clean frontend contract
- still carries both legacy backend structure and frontend compatibility shaping

### Freeze decision

Freeze for first frontend slice with these rules:

- top-level `evaluationId` is required
- `input`, `evaluation`, `interpretation`, `explain`, `signalInfo`, `primaryFailure`, `deltaPreview`, `nextAction`, `triggeredProtocols`, and `dnaScoring` are the supported additive fields
- additional fields may remain additive but should not be required by the new frontend

### Status

`NEEDS_NORMALIZATION`

## 3.2 Image Evaluate

### Current route

`POST /app/evaluate/image`

### Current use

- current live app UI posts here directly
- returns an evaluated result and may include `image_parse`

### Problem

This route skips the ideal trust-gate shape for the new frontend.

The dedicated frontend should not rely on immediate score-first OCR flow as its primary contract.

### Freeze decision

Do not treat this as the primary OCR contract for the new frontend.

Keep it as:

- legacy-compatible
- additive backend route

Use `POST /api/ocr/review` as the canonical OCR review path instead.

### Status

`NEEDS_NORMALIZATION`

## 3.3 OCR Review

### Current route

`POST /api/ocr/review`

### Current source

- `app/routers/ocr.py`
- `app/services/ocr_review.py`
- `app/schemas/frontend_contracts.py`

### Current response shape

- `requestId`
- `source`
- `fileName`
- `rawText`
- `detectedLegs`
- `confidence`
- `requiresReview`

### Current strengths

- explicitly stops before evaluation
- designed for frontend trust gate ownership
- test-backed in `app/tests/test_frontend_contracts.py`
- already produces parsed leg objects with clarity state

### Freeze decision

Freeze as the canonical OCR trust-gate contract for the new frontend.

### Status

`FROZEN`

## 3.4 Evaluation Result Payload

### Current shape source

- `WebEvaluateResponseSchema` in `app/schemas/frontend_contracts.py`
- actual route shaping in `app/routers/web.py`

### Required frozen fields for first frontend slice

- `evaluationId`
- `input`
- `evaluation`
- `interpretation`
- `explain`
- `signalInfo`
- `primaryFailure`
- `deltaPreview`
- `nextAction`
- `triggeredProtocols`
- `dnaScoring`

### Current issue

The route also adds broader or historical fields that should remain additive, not mandatory.

### Freeze decision

Freeze the minimal supported field set above as required-for-frontend.

### Status

`NEEDS_NORMALIZATION`

## 3.5 Builder Handoff

### Current reality

There is no dedicated backend handoff route.

The current frontend builds Builder context from evaluation response fields and history replay data.

### Current frontend fields in use

- `evaluationId`
- `primaryFailure`
- `fastestFix`
- `deltaPreview`
- `input.bet_text`
- `signalInfo`
- `tier`

### Problem

This contract is real in practice, but implicit.

### Freeze decision

Freeze a builder handoff payload shape at the documentation level before new frontend work starts.

### Required shape

```json
{
  "evaluationId": "eval_123",
  "inputText": "original or current slip text",
  "primaryFailure": {},
  "fastestFix": {},
  "deltaPreview": {},
  "signalInfo": {},
  "tier": "good"
}
```

### Status

`NEEDS_NORMALIZATION`

## 3.6 Bet Create

### Current route

`POST /api/bets/`

### Current source

- `app/routers/bets.py`

### Current strengths

- accepts `evaluation_id`
- returns `evaluation_id`
- test-backed in `app/tests/test_bets_api.py`

### Freeze decision

Freeze this as usable for the first split slice.

### Required fields for first frontend slice

Request:

- `input_text`
- `legs`
- `wager`
- optional `total_odds`
- optional `potential_payout`
- optional `evaluation_id`
- optional `verdict`
- optional `confidence`

Response:

- `success`
- `bet_id`
- `message`
- `evaluation_id`
- optional warnings / snapshot fields

### Status

`FROZEN`

## 3.7 Bet History List

### Current route

`GET /api/bets/history`

### Current strengths

- auth-gated
- paginated
- returns `evaluation_id` on items when present
- test-backed

### Freeze decision

Freeze for first frontend use.

### Required item fields

- `id`
- `evaluation_id`
- `input_text`
- `legs`
- `wager`
- `total_odds`
- `potential_payout`
- `status`
- `actual_payout`
- `verdict`
- `confidence`
- `created_at`
- `settled_at`

### Status

`FROZEN`

## 3.8 History Replay Detail

### Current route

`GET /history/{item_id}`

### Current source

- `app/routers/history.py`

### Current strengths

- returns raw evaluation data for replay/edit

### Current issue

- currently separate from `/api/bets/history`
- not yet framed as the dedicated replay contract for the new frontend
- uses the in-memory history store and not the authenticated bet-history domain

### Freeze decision

Do not treat this as final for the dedicated frontend yet.

It needs either:

- extraction into a clearer frontend replay contract

or

- explicit confirmation that replay for the new frontend will come from this endpoint family

### Status

`NEEDS_EXTRACTION`

## 4. Required Normalizations Before Frontend Scaffold

These should be resolved or explicitly documented before the new frontend depends on them.

### 4.1 Evaluation Identifier Naming

Current state:

- `evaluationId` appears in frontend-facing evaluate responses
- `evaluation_id` appears in bet APIs and backend persistence
- current frontend JS normalizes between both

Rule:

- frontend-facing evaluate and handoff contracts should use `evaluationId`
- persistence and write-side bet/history contracts may continue using `evaluation_id`
- mapping must be explicit and documented

### 4.2 OCR Contract Split

Current state:

- `/app/evaluate/image` is live
- `/api/ocr/review` is the better dedicated frontend shape

Rule:

- new frontend uses `/api/ocr/review` for OCR trust gate
- image evaluation route remains legacy-compatible until later consolidation

### 4.3 History Split

Current state:

- `/api/bets/history` is auth-backed bet history
- `/history` and `/history/{item_id}` come from history store replay

Rule:

- decide explicitly whether the new frontend replay surface will use:
  - bet-history APIs only,
  - history-store APIs only,
  - or a dedicated replay endpoint

This decision must be made before History migration.

## 5. Definition Of Done For Contract Freeze Phase

The first phase is done when:

- this checklist is accepted as the working contract map
- required fields for Evaluate, OCR review, Bet Create, and History List are stable
- Builder handoff payload is documented and treated as intentional
- `evaluationId` versus `evaluation_id` rules are explicit
- History replay source is decided before frontend History work begins

