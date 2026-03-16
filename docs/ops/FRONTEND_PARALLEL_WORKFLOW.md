# Frontend / Backend Parallel Workflow

**Status:** DRAFT

This note operationalizes the canonical phase-one contract freeze for day-to-day implementation.

## Working boundary

- Frontend scaffold lives in `app-src/frontend/`
- Frontend consumes only frozen contracts in `app-src/frontend/src/lib/contracts/`
- Backend remains FastAPI and continues to evolve behind additive response changes or explicitly versioned changes

## Phase 1 frozen calls

- `POST /app/evaluate`
- `POST /api/ocr/review`

## Change rules

- Do add fields to backend responses when useful
- Do not rename or remove frozen frontend fields without updating the canonical contract docs
- Do normalize frontend state at the edge in the typed API client layer
- Do keep Builder, bets, and history work additive until their contracts are frozen into the same pattern

## Current frontend entry points

- `frontend/src/app/evaluate/page.tsx`
- `frontend/src/app/evaluate/review/page.tsx`

## Current fallback runtime entry points

- `frontend/static/index.html`
- `frontend/static/review.html`
- `frontend/static/builder.html`
- `frontend/static/history.html`
- `frontend/dev-server.mjs`

## Next additions after this scaffold

- Builder handoff client and state normalization
- bet create client
- history list/detail clients
