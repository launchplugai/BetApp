# Frontend Dev Context Log

Status: ACTIVE
Last updated: 2026-03-16

## Memory Heartbeat

- Active stream: `frontend-dev`
- Canonical blocker: `Next/package toolchain instability still blocks trustworthy local Next verification`
- Canonical next move: `Add shared request/status tracing and route-visible live/mock mode controls to the Next dev console`
- Freshness cadence: `Re-verify after each meaningful slice or within 24 hours while active`
- Cross-check with: `CONTEXT.md`, `docs/ops/CURRENT_EXECUTION_STATE.md`, `docs/ops/ACTIVE_WAKEUP_TARGET.md`, `docs/ops/FRONTEND_DEV_BOOTSTRAP.md`, `docs/ops/FRONTEND_DEV_BUILD_TRACKER.md`

## Why This Exists

This is the compact continuity log for the frontend-dev stream.

Use it when:

- chat context gets compressed
- a new agent or VPS worker takes over
- a restart happens mid-slice

## Current Canon

- backend contract freeze: `docs/ops/FRONTEND_BACKEND_CONTRACT_FREEZE_PHASE1.md`
- deploy readiness/status: `docs/ops/FRONTEND_BACKEND_DEPLOY_STATUS.md`
- visual separation map: `docs/ops/FRONTEND_BACKEND_VISUAL_STATUS_MAP.md`
- normalized frontend seam: `docs/ui/EVALUATION_ENVELOPE_BLUEPRINT.md`

## Current Working Model

- fallback frontend is the reliable preview tool
- Next scaffold is the active implementation target
- `EvaluationEnvelope` is the rendering boundary
- frontend should not read backend guts directly
- mock and live work should coexist in the same dev dashboard

## Recently Landed

- safer persisted history replay on backend
- review findings fixed for bet-detail regression and stale History state
- fallback UI reframed as a console
- `EvaluationEnvelope` contract, adapters, mocks, and viewer added
- Next Evaluate/OCR/Builder/History now render through or alongside envelope views
- root dev-console home added
- shared console shell and page-header system added across the Next routes
- route-level mock mode now drives first-pass behavior across Evaluate, OCR, Builder, and History

## Known Risks

- no trustworthy local Next build yet
- fallback runtime may still be needed for preview until the toolchain is healthy
- Builder remains state-driven more than API-driven

## Recovery Rule

If this chat dies:

1. read `docs/ops/FRONTEND_DEV_BOOTSTRAP.md`
2. check `git status`
3. continue from the exact next move recorded there

## Continuity Tooling

- local skill: `anti-amnesia-heartbeat`
- purpose: keep build work and repo memory synchronized every cycle instead of relying on chat recall
