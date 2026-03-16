# EvaluationEnvelope Blueprint

Status: DRAFT
Last updated: 2026-03-16

## Purpose

`EvaluationEnvelope` is the normalized frontend contract layer for the next UI build phase.

The UI should render from this envelope instead of reading backend route payloads directly.

## Flow Model

Main river:

`Input -> Analyze -> Score -> Explain -> Suggest -> Output`

Tributaries:

- protocols
- alerts
- heuristics
- Sherlock
- DNA
- async updates

## Rule

1. Backend signals are gathered from existing contracts.
2. A frontend normalization adapter maps them into one envelope.
3. UI screens render from the envelope only.
4. Notifications and live updates arrive as controlled deltas, not raw backend leakage.

## 5-Zone UI Structure

- Input Builder
- Evaluation Summary
- Why Panel
- Protocol Panel
- Action Rail

## Current Repo Mapping

Envelope types:

- `frontend/src/lib/contracts/evaluation-envelope.ts`

Normalization adapters:

- `frontend/src/lib/adapters/evaluation-envelope.ts`

Mock payloads:

- `frontend/src/lib/mocks/evaluation-envelope.ts`

Initial UI usage:

- `frontend/src/features/evaluate/components/evaluate-workbench.tsx`
- `frontend/src/features/ocr/components/ocr-review-shell.tsx`

## Current Adapter Coverage

- `POST /app/evaluate` -> `createEnvelopeFromEvaluate(...)`
- `POST /api/ocr/review` -> `createEnvelopeFromOcrReview(...)`
- `GET /api/bets/{bet_id}` -> `createEnvelopeFromPersistedBetDetail(...)`
- `GET /app/history/{item_id}` -> `createEnvelopeFromEvaluationHistoryDetail(...)`

## Recommended Build Path

1. Build UI from mocked `EvaluationEnvelope` payloads first.
2. Validate the 5-zone screen system without backend coupling.
3. Connect backend routes only through normalization adapters.
4. Keep raw route payload views only in console/debug surfaces.

## Notes

- This is additive and does not replace the existing frozen backend contracts.
- The envelope is a frontend rendering boundary, not a backend rewrite.
- The fallback console remains useful for contract debugging while the final UI grows on top.
