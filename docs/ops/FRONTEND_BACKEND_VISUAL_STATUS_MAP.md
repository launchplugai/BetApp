# Frontend / Backend Visual Status Map

**Status:** DRAFT

This map is a quick reality check for whether the current work still serves the separation goal.

## Goal

```text
frontend can build product UX in parallel
backend can evolve scoring / OCR / governance in parallel
without reopening contracts every sprint
```

## Current Shape

```text
app-src/
  app/                    FastAPI backend
  frontend/               dedicated frontend module
    src/                  intended Next.js app
    static/               working fallback runtime
    dev-server.mjs        fallback frontend server
```

## Boundary Map

```text
Frontend surfaces
  fallback runtime
    /                     Evaluate
    /review               OCR review
    /builder              Builder handoff
    /history              History / replay

  Next scaffold
    /evaluate
    /evaluate/review
    /builder
    /history

                consumes
                    |
                    v
Backend contracts
  POST /app/evaluate
  POST /api/ocr/review
  GET  /api/bets/history
  GET  /api/bets/{bet_id}
  GET  /app/history              legacy/dev replay support
  GET  /app/history/{item_id}    legacy/dev replay support
```

## Flow Map

### 1. Evaluate

```text
frontend
  -> POST /app/evaluate
      -> Airlock
      -> evaluation pipeline
      -> shaped frontend response
           evaluationId
           signalInfo
           primaryFailure
           deltaPreview
           builderHandoff
```

### 2. OCR Review

```text
frontend
  -> POST /api/ocr/review
      -> OCR extraction
      -> parsed legs
      -> review payload
           rawText
           detectedLegs
           confidence
           requiresReview
```

### 3. Builder Handoff

```text
frontend evaluate result
  -> normalize handoff state
      evaluationId
      inputText
      primaryFailure
      fastestFix
      deltaPreview
      signalInfo
      tier
  -> frontend /builder
  -> optional re-evaluate through POST /app/evaluate
```

### 4. History

```text
canonical persisted base
  frontend
    -> GET /api/bets/history
    -> GET /api/bets/{bet_id}
         -> additive replay payload

legacy support path
  frontend
    -> GET /app/history
    -> GET /app/history/{item_id}
```

## Status By Area

### Evaluate

```text
contract freeze: strong
backend route: strong
frontend path: strong
overall: serving the goal
```

Why:

- one main frontend contract now exists
- backend remains authoritative for evaluation logic
- frontend can build result hierarchy and handoff UX without touching scoring internals

### OCR Review

```text
contract freeze: strong
backend route: strong
frontend path: good
overall: serving the goal
```

Why:

- OCR review is now split from evaluation
- trust gate belongs to frontend
- extraction/parsing remains backend-owned

### Builder

```text
contract freeze: medium
backend route: not a dedicated API
frontend path: good
overall: partially serving the goal
```

Why:

- Builder handoff shape is stable enough for frontend work
- no dedicated backend handoff API exists yet
- this is acceptable for phase one, but still a transitional seam

### History

```text
contract freeze: medium
backend route: improved but still split
frontend path: medium
overall: partially serving the goal
```

Why:

- persisted bet detail now includes additive replay context
- persisted history is the intended canonical base
- legacy `/app/history` still exists as replay support
- history is no longer the main blocker, but it is not fully unified yet

### Frontend Platform

```text
contract freeze: n/a
code migration: good
runtime migration: weak
overall: not fully serving the goal yet
```

Why:

- the dedicated frontend module exists
- Next app code now covers Evaluate, OCR, Builder, and History
- the working runtime is still the fallback server because package install is failing in this environment

## Canonical vs Transitional

### Canonical enough for active work

- `POST /app/evaluate`
- `POST /api/ocr/review`
- `GET /api/bets/history`
- `GET /api/bets/{bet_id}` with additive replay payload
- `frontend/src/lib/contracts/*`

### Transitional

- `frontend/static/*`
- `frontend/dev-server.mjs`
- Builder handoff via browser storage
- `GET /app/history`
- `GET /app/history/{item_id}`

## Answer To The Goal Check

```text
Is the overall goal being served?

Yes for contract separation.
Mostly yes for product flow separation.
Not fully yet for final frontend platform separation.
```

## What Must Be True Before We Call This Fully Landed

```text
1. frontend runs from the dedicated app runtime, not only fallback static pages
2. persisted history fully replaces legacy replay routes for the main loop
3. builder handoff is either formally frozen as a shared contract or backed by a dedicated API
```

## Recommended Next Decision

```text
deploy current state to validate the split itself
then fix the frontend runtime/toolchain in a healthier environment
```
