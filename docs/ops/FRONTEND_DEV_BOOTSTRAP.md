# Frontend Dev Bootstrap

Status: ACTIVE
Last updated: 2026-03-16

## Memory Heartbeat

- Active stream: `frontend-dev`
- Canonical blocker: `No major blocker; Next typecheck and build now pass locally`
- Canonical next move: `Visually verify the new route-controls and request-trace surfaces in the Next app, then choose the next dev-console refinement slice`
- Freshness cadence: `Re-verify after each meaningful slice or within 24 hours while active`
- Cross-check with: `CONTEXT.md`, `docs/ops/CURRENT_EXECUTION_STATE.md`, `docs/ops/ACTIVE_WAKEUP_TARGET.md`, `docs/ops/FRONTEND_DEV_BUILD_TRACKER.md`, `docs/ops/FRONTEND_DEV_CONTEXT_LOG.md`

## Purpose

This is the fastest bootstrap path for any chat, agent, or VPS worker that needs to resume the frontend-dev stream without depending on thread memory.

If the local Codex skill `anti-amnesia-heartbeat` is available, use it for this stream.

## Prime Directive

Build a usable developer-facing frontend first.

Do not optimize for final user polish yet.
Do not reopen frozen backend contracts unless a documented conflict requires it.

## Read Order

1. `docs/index/DOC_INDEX.md`
2. `docs/ops/CURRENT_EXECUTION_STATE.md`
3. `docs/ops/FRONTEND_BACKEND_CONTRACT_FREEZE_PHASE1.md`
4. `docs/ops/FRONTEND_BACKEND_DEPLOY_STATUS.md`
5. `docs/ops/FRONTEND_BACKEND_VISUAL_STATUS_MAP.md`
6. `docs/ui/EVALUATION_ENVELOPE_BLUEPRINT.md`
7. `docs/ui/SCREEN_COMPONENT_SPEC.md`
8. `docs/ui/FRONTEND_IMPLEMENTATION_SPEC.md`
9. `git -C /Users/benaiahross/development/projects/betapp/app-src status --short`

## Current Runtime Truth

- FastAPI is the backend and stays the backend.
- The fallback frontend is the only reliably previewable runtime right now.
- The Next scaffold is the active frontend-dev target.
- `EvaluationEnvelope` is now the frontend rendering seam.
- Evaluate, OCR, Builder, and History should move toward one shared developer-console shell.

## Immediate Objective

Turn the Next scaffold into a usable dev console with:

- one shared frame
- one shared environment state
- live and mock workflows
- envelope-driven screen rendering

## Exact Next Move

Visually verify the new route-controls and request-trace surfaces in the Next app, then choose the next dev-console refinement slice.
