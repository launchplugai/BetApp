# Frontend Dev Build Tracker

Status: ACTIVE
Last updated: 2026-03-16

## Memory Heartbeat

- Active stream: `frontend-dev`
- Canonical blocker: `No major blocker; Next typecheck and build now pass locally`
- Canonical next move: `Visually verify the new route-controls and request-trace surfaces in the Next app, then choose the next dev-console refinement slice`
- Freshness cadence: `Re-verify after each meaningful slice or within 24 hours while active`
- Cross-check with: `CONTEXT.md`, `docs/ops/CURRENT_EXECUTION_STATE.md`, `docs/ops/ACTIVE_WAKEUP_TARGET.md`, `docs/ops/FRONTEND_DEV_BOOTSTRAP.md`, `docs/ops/FRONTEND_DEV_CONTEXT_LOG.md`

## Goal

Reach a usable developer-facing frontend that lets a visual learner inspect:

- current runtime state
- contract boundaries
- normalized frontend envelopes
- the main Evaluate -> OCR -> Builder -> History flow

## Working Definition Of Usable

- one clear developer home
- one shared runtime config surface
- route shells feel like one tool, not four disconnected experiments
- live backend mode works against frozen contracts
- mock mode works against `EvaluationEnvelope` fixtures
- major payloads are visible without digging through backend internals

## Current Completed

- fallback runtime serves the split flow
- Next scaffold exists for Evaluate, OCR, Builder, History
- `EvaluationEnvelope` contract exists
- adapters exist for Evaluate, OCR, persisted History detail, and legacy replay detail
- mock `EvaluationEnvelope` fixtures exist
- root Next page is now a dev home instead of a redirect
- shared dev-session storage exists for API base, auth token, and dev mode
- Evaluate, OCR, Builder, and History can render envelope views
- shared console shell and route-level page headers now make the Next scaffold feel like one developer dashboard instead of disconnected screens
- route-level mock behavior now exists for Evaluate, OCR, Builder, and History so the dashboard can be used visually even when live backend interaction is not the current task
- shared route-controls and request-trace surfaces now exist across Evaluate, OCR Review, Builder, and History
- the shell now shows active route state alongside mode, API base, and path
- local Next verification now works through `tsc --noEmit` and `next build`

## Current Blockers

- direct visual verification of the Next screens is still pending
- fallback runtime is still the easiest preview path during day-to-day work

## Active Build Order

1. Shared console frame and route navigation
2. Live/mock mode wiring across route shells
3. Better developer event/status traces
4. Preview/build verification once the toolchain is healthy
5. User-facing UI/UX layer on top

## Validation Commands

Backend:

```bash
cd /Users/benaiahross/development/projects/betapp/app-src
uv run --project . pytest app/tests/test_bets_api.py -q
```

Fallback preview:

```bash
cd /Users/benaiahross/development/projects/betapp/app-src/frontend
PORT=3010 node dev-server.mjs
```

## Next Milestone

Visually verify the new route-controls and request-trace console surfaces in the Next app.
