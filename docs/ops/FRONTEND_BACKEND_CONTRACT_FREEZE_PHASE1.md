# Frontend/Backend Contract Freeze Audit: Phase 1

**Status:** CANONICAL  
**Last Updated:** 2026-03-14

## Scope

This document covers the first separation phase requested in:

- `docs/ops/FRONTEND_BACKEND_SEPARATION_PLAN.md`
- `docs/architecture/USER_FLOW_MAP.md`
- `docs/ui/SCREEN_COMPONENT_SPEC.md`
- `docs/ui/LIVE_UX_GAP_REPORT.md`
- `docs/ui/FRONTEND_IMPLEMENTATION_SPEC.md`
- `docs/index/DOC_INDEX.md`

The goal is not a rewrite. The goal is to freeze the frontend-facing contracts for the first migration slice before scaffolding a new frontend.

## 1. Governing Constraints

The source docs impose these constraints:

- Keep FastAPI as the backend runtime.
- Do not redesign from scratch.
- Do not rewrite the backend.
- Split incrementally.
- Freeze frontend-facing contracts before scaffolding a new frontend.
- Treat the current Evaluate frontend as split/duplicated until proven otherwise.
- Prefer additive changes and docs-backed decisions.
- Migrate in this order: contracts first, then dedicated frontend scaffold, then Evaluate first.
- Keep scoring, OCR parsing, protocol logic, persistence, and auth on the backend.
- Put page flow, OCR trust gate UX, result hierarchy, Builder handoff UX, and History replay UX in the frontend.

## 2. Current Frontend Reality

The current codebase matches the duplication called out in `docs/ui/FRONTEND_IMPLEMENTATION_SPEC.md`.

### Evaluate is split across multiple surfaces

- `app/templates/app/index.html` contains a chat-style/paste-style Evaluate surface, OCR upload UI, OCR review gate markup, inline re-evaluation, and builder-oriented controls.
- `app/web_assets/static/js/app.js` owns OCR parsing, OCR review gating, canonical leg generation, `/app/evaluate` calls, session history, and refine-in-builder behavior.
- `app/web_assets/templates/app.html` contains a different tabbed Discover/Evaluate/Advanced/History shell that still references `/static/app.js`.
- `app/routers/web.py` does not currently serve `app/templates/app/index.html`; `/app` serves screen templates like dashboard, browse, builder, history, and auth.

### Practical conclusion

- The current Evaluate frontend is duplicated.
- The contract freeze should target backend APIs and normalized state, not the existing template ownership.
- The new frontend should start with Evaluate and treat the existing template/JS paths as legacy fallback.

## 3. Backend Route Audit

## 3.1 Evaluate text input

### Current route

- `POST /app/evaluate` in `app/routers/web.py`

### Request shape

```json
{
  "input": "bet text",
  "tier": "good|better|best",
  "legs": [
    {
      "entity": "LeBron James",
      "market": "player_prop",
      "value": "27.5",
      "raw": "LeBron James over 27.5 pts"
    }
  ]
}
```

### Backend behavior

- Passes through `airlock_ingest()`.
- Supports optional canonical legs from Builder.
- Calls canonical `run_evaluation()`.
- Converts the pipeline result from snake_case to camelCase for the current JS frontend.

### Assessment

- This is the strongest candidate for the first frontend slice.
- It is already the richest evaluation contract in the app.
- It needs explicit response schemas and cleanup, but not a backend rewrite.

## 3.2 Evaluate image/OCR input

### Current route

- `POST /leading-light/evaluate/image` in `app/routers/leading_light.py`

### Request shape

- `multipart/form-data`
- fields: `image`, `plan`, `session_id`

### Backend behavior

- Validates file type, size, and rate limit.
- Runs vision OCR.
- Extracts plain text.
- Immediately parses and evaluates the extracted text.
- Returns OCR text plus evaluation payload.

### Assessment

- This route does not match the target UX trust gate.
- It collapses OCR extraction, OCR review, and evaluation into one backend call.
- It over-centers raw extracted text and has no structured parsed-leg review payload.
- Keep the OCR/parsing backend logic, but freeze a new frontend-facing OCR review contract before treating this as the new frontend API.

## 3.3 OCR review payload

### Current route

- `POST /api/ocr/review`

### Current state

- A backend OCR review contract now exists and returns parsed legs without evaluating.
- The existing frontend JS still contains legacy OCR parsing logic in `app/web_assets/static/js/app.js`.
- The backend route should now be treated as the source of truth for the new dedicated frontend.

### Current frontend-derived state

```json
{
  "source": "image",
  "fileName": "slip.png",
  "rawText": "Jalen Brunson 8+ assists\nKnicks ML",
  "detectedLegs": [
    {
      "leg_id": "leg_123",
      "entity": "Jalen Brunson",
      "market": "player_prop",
      "value": "over 8 assists",
      "raw": "Jalen Brunson 8+ assists",
      "source": "ocr",
      "clarity": "clear|review|ambiguous"
    }
  ],
  "confidence": 0.0,
  "requiresReview": true
}
```

### Assessment

- This is now the correct frontend-facing OCR trust-gate contract base.
- The old browser-side parsing logic should be treated as legacy fallback until the dedicated frontend takes over.

## 3.4 Evaluation result payload

### Current routes

- `POST /app/evaluate`
- `POST /leading-light/evaluate`
- `POST /leading-light/evaluate/text`

### Best current candidate

- `POST /app/evaluate`

### Why

- It includes the full pipeline response needed by Evaluate, Builder handoff, and future History replay.
- It already includes `signalInfo`, `primaryFailure`, `deltaPreview`, `evaluatedParlay`, `nextAction`, `triggeredProtocols`, `dnaScoring`, `proofSummary`, `structure`, and other downstream state.

### Assessment

- Use `/app/evaluate` as the contract-freeze base.
- Do not use the simpler Leading Light result payload as the frontend contract for the Evaluate-first migration.

## 3.5 Builder handoff payload

### Current state

- No backend handoff route exists.
- Handoff is currently implicit via frontend state and session storage.
- The docs already define the desired normalized shape:

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

### Assessment

- Freeze this as a frontend domain contract first.
- It does not require a new backend route for phase 1.
- It does require stable fields in the evaluation result payload.

## 3.6 Bet create payload

### Current route

- `POST /api/bets/` in `app/routers/bets.py`

### Request shape

```json
{
  "input_text": "bet text",
  "legs": [
    {
      "entity": "Lakers",
      "market": "spread",
      "value": "-5.5",
      "odds": -110,
      "selection": "Lakers -5.5"
    }
  ],
  "wager": 10000,
  "total_odds": 250,
  "potential_payout": 35000,
  "evaluation_id": "eval_123",
  "verdict": "GOOD",
  "confidence": 72
}
```

### Assessment

- This route is already usable for the Builder/place-bet seam.
- It already supports `evaluation_id`.
- It needs cleanup around field semantics and how verdict/confidence are sourced from evaluation results.

## 3.7 History list/detail payload

### Current routes

- `GET /api/bets/history`
- `GET /api/bets/{bet_id}`
- `GET /history`
- `GET /history/{item_id}`

### Split reality

- `/api/bets/history` and `/api/bets/{bet_id}` are authenticated, persisted bet history routes used by the current History screen.
- `/history` and `/history/{item_id}` are unauthenticated in-memory evaluation history routes for raw evaluation replay/testing.

### Assessment

- History is split across two backends with different purposes.
- The authenticated bet history routes should be the base for the migrated History surface.
- The in-memory evaluation history routes should be treated as legacy/dev support until a real replay contract is frozen.

## 4. Contract-Freeze Checklist

## 4.1 Evaluate text input

- Freeze request field names and casing.
- Freeze whether canonical legs are optional or required for Builder-originated evaluation.
- Freeze accepted tier values and aliases.
- Freeze error envelope for empty input, invalid tier, oversized input, and rate limit.
- Freeze whether response remains camelCase for frontend compatibility or whether a versioned API will switch to snake_case plus generated TS types.

## 4.2 Evaluate image/OCR input

- Split OCR extraction/review from evaluation.
- Freeze multipart request fields for image upload.
- Freeze OCR extraction response envelope.
- Freeze whether image upload returns `rawText`, `detectedLegs`, `confidence`, and `requiresReview`.
- Freeze the rule that evaluation does not start until the slip is confirmed.

## 4.3 OCR review payload

- Freeze `source`, `fileName`, `rawText`, `detectedLegs`, `confidence`, and `requiresReview`.
- Freeze detected-leg item fields: `id` or `legId`, `entity`, `market`, `value`, `raw`, `source`, `clarity`.
- Freeze review-state semantics for high-confidence, mixed-confidence, and poor-confidence OCR.
- Freeze whether raw OCR text is secondary/debug-only.

## 4.4 Evaluation result payload

- Freeze the frontend-minimum fields:
  - `evaluationId`
  - `input`
  - `signalInfo`
  - `primaryFailure`
  - `deltaPreview`
  - `triggeredProtocols`
  - `dnaScoring`
  - `evaluatedParlay`
  - `nextAction`
- Freeze whether the evaluation identifier is top-level, nested, or both.
- Freeze the result hierarchy fields needed by Evaluate-first UX.
- Freeze explicit error envelopes.

## 4.5 Builder handoff payload

- Freeze the normalized frontend state shape.
- Freeze `evaluationId`, `inputText`, `primaryFailure`, `fastestFix`, `deltaPreview`, `signalInfo`, and `tier`.
- Freeze which evaluation fields are authoritative sources for those handoff values.
- Freeze whether History replay uses the same builder handoff shape.

## 4.6 Bet create payload

- Freeze request fields and required auth behavior.
- Freeze `evaluation_id` semantics as the link between evaluation and placed bet.
- Freeze the leg input shape used by Builder.
- Freeze success and failure envelopes.
- Freeze whether `verdict` and `confidence` are optional derived fields or required persisted receipt fields.

## 4.7 History list/detail payload

- Freeze which history contract is canonical for the new frontend.
- Freeze list fields for card rendering, filters, and pagination.
- Freeze detail fields needed for replay and refine.
- Freeze whether history detail includes original evaluation receipt, builder deltas, and triggered protocols.
- Freeze whether replay/edit uses persisted bet detail alone or requires a dedicated evaluation receipt endpoint.

## 5. Current Routes: Ready vs Cleanup Needed

| Contract | Current route(s) | Status | Notes |
|---|---|---|---|
| Evaluate text input | `POST /app/evaluate` | Partial fit, best base | Rich payload, Airlock-backed, but undocumented response model and camelCase proxy behavior |
| Evaluate image/OCR input | `POST /leading-light/evaluate/image` | Needs cleanup | Evaluates too early, raw-text-first, no explicit parsed-slip review contract |
| OCR review payload | `POST /api/ocr/review` | Partial fit, new base | Explicit parsed-slip review contract now exists; legacy JS parsing still needs retirement |
| Evaluation result payload | `POST /app/evaluate` | Partial fit, best base | Strongest payload for Evaluate-first migration; needs explicit contract freeze |
| Builder handoff payload | none | Missing as API, present as implicit state | Freeze as normalized frontend contract first |
| Bet create payload | `POST /api/bets/` | Mostly fit | Supports `evaluation_id`, auth, persistence; needs field cleanup |
| History list payload | `GET /api/bets/history` | Partial fit | Used by live History screen; missing learning/replay emphasis |
| History detail payload | `GET /api/bets/{bet_id}` | Partial fit | Exists, but no current replay/refine contract built on it |
| Legacy eval history | `GET /history`, `GET /history/{item_id}` | Legacy/support only | In-memory and unauthenticated; not the canonical migrated history base |

## 6. Missing Fields And Inconsistencies

## 6.1 Evaluation ID is not frontend-stable enough

- `/app/evaluate` currently exposes the canonical evaluation identifier as `evaluation.parlayId`.
- Builder code already has fallback logic for `evaluation_id`, `evaluationId`, or `_builderContext.evaluationId`.
- That indicates the contract is not frozen.
- Phase 1 should freeze a single frontend-stable field: `evaluationId`.

## 6.2 OCR trust gate is frontend-only and not backed by an API contract

- The UX docs require parsed-leg confirmation before evaluation.
- The current backend OCR route evaluates immediately.
- The current review experience depends on client-side OCR text parsing inside legacy JS.

## 6.3 Evaluation contracts are split across incompatible APIs

- `/leading-light/evaluate` is block-based and not the active product loop contract.
- `/leading-light/evaluate/text` and `/leading-light/evaluate/image` return a simpler wrapper.
- `/app/evaluate` returns the richer contract the product actually needs.
- Phase 1 should standardize on one frontend evaluation contract, not three.

## 6.4 `/app/evaluate` is rich but not explicit

- No response model is declared.
- OpenAPI for the real Evaluate payload is effectively incomplete.
- The route transforms keys to camelCase after pipeline execution, which is convenient but currently implicit.

## 6.5 History is split between persisted bets and ephemeral evaluation history

- The live History screen reads `/api/bets/history`.
- Replay-oriented `/history/{item_id}` uses a different in-memory store and different semantics.
- The migrated frontend needs one canonical history contract, with replay added intentionally.

## 6.6 Builder submission fields do not line up cleanly with evaluation outputs

- Builder submits `verdict` and `confidence`.
- `/app/evaluate` does not expose those in a simple top-level stable shape for Builder consumption.
- Builder currently derives outcome signals by probing multiple possible fields.

## 6.7 Dashboard and Builder remain more mature than Evaluate in the served `/app` router

- `/app` currently serves dashboard/browse/builder/history/auth screens.
- The legacy Evaluate surface is not the screen currently mounted by `web.py`.
- This reinforces the docs’ warning that Evaluate ownership is unresolved.

## 7. Recommended Frontend Scaffold Shape

## Recommendation

Start with:

```text
app-src/frontend/
```

not:

```text
apps/web/
```

for the first separation pass.

## Why

- `docs/ops/FRONTEND_BACKEND_SEPARATION_PLAN.md` explicitly recommends `app-src/frontend/` as the least disruptive transitional shape.
- The current backend already lives under `app-src/`.
- The user asked for incremental separation and no major code moves yet.
- This keeps the first scaffold additive while preserving the path to a later `apps/api` + `apps/web` repo shape.

## Recommended stack

- Next.js
- TypeScript
- App Router
- TanStack Query
- Zod

## Initial scaffold boundaries

- `app-src/frontend/app/evaluate/page.tsx`
- `app-src/frontend/app/evaluate/review/page.tsx` or a nested modal/state route for OCR review
- `app-src/frontend/src/lib/api/`
- `app-src/frontend/src/lib/contracts/`
- `app-src/frontend/src/features/evaluate/`
- `app-src/frontend/src/features/ocr/`
- `app-src/frontend/src/features/builder-handoff/`

## Initial API client targets

- `POST /app/evaluate`
- new or refactored OCR review endpoint derived from `/leading-light/evaluate/image`
- `POST /api/bets/`
- `GET /api/bets/history`
- `GET /api/bets/{bet_id}`

## 8. Evaluate-First Implementation Start

For the first implementation slice, the backend target should be:

- keep `POST /app/evaluate` as the evaluation engine entry point
- do not move scoring, protocol logic, or Airlock out of FastAPI
- add contract documentation and schema cleanup around `/app/evaluate`
- define a dedicated OCR extraction/review contract before wiring the new frontend upload path

For the new frontend target, the first slice should implement:

- Evaluate text input
- OCR upload shell
- OCR review state model
- evaluation result normalization
- guided-fix to Builder handoff state

## 9. Phase 1 Done Criteria Check

- contract-freeze checklist exists: yes
- backend endpoints for the first frontend slice are identified: yes
- missing fields and inconsistencies are listed: yes
- frontend scaffold recommendation is concrete: yes
- no major code moves yet unless they directly support contract freeze: yes
