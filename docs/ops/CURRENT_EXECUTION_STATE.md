# Current Execution State

**Status:** ACTIVE  
**Last Updated:** 2026-03-16

## 0. Memory Heartbeat

- Active stream: `frontend-dev`
- Canonical blocker: `Next/package toolchain instability still blocks trustworthy local Next verification`
- Canonical next move: `Add shared request/status tracing and route-visible live/mock mode controls to the Next dev console`
- Freshness cadence: `Re-verify after each meaningful slice or within 24 hours while active`
- Cross-check with: `CONTEXT.md`, `docs/ops/ACTIVE_WAKEUP_TARGET.md`, `docs/ops/FRONTEND_DEV_BOOTSTRAP.md`, `docs/ops/FRONTEND_DEV_BUILD_TRACKER.md`, `docs/ops/FRONTEND_DEV_CONTEXT_LOG.md`, `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`

## 1. Current Objective

Produce a usable developer-facing frontend for the split BetApp flow without reopening backend boundaries, while packaging the chat-side operating system modularly enough to support future continuity layers.

The active objective is now:

```text
Frozen backend contracts
  ↓
Frontend normalization adapter
  ↓
EvaluationEnvelope
  ↓
Developer console / screen shells
  ↓
Later user-facing UI/UX polish
```

## 2. Most Recent Completed Slice

Completed the first usable dev-dashboard shell for the Next scaffold and wired route-level mock behavior into the main screen set.

Completed in:

- `frontend/src/lib/contracts/evaluation-envelope.ts`
- `frontend/src/lib/adapters/evaluation-envelope.ts`
- `frontend/src/lib/mocks/evaluation-envelope.ts`
- `frontend/src/components/evaluation-envelope-view.tsx`
- `frontend/src/components/dev-console-shell.tsx`
- `frontend/src/components/dev-page-header.tsx`
- `frontend/src/features/console/components/dev-console-home.tsx`
- `frontend/src/features/evaluate/components/evaluate-workbench.tsx`
- `frontend/src/features/ocr/components/ocr-review-shell.tsx`
- `frontend/src/features/builder/components/builder-handoff-shell.tsx`
- `frontend/src/features/history/components/history-shell.tsx`
- `frontend/src/lib/dev-session.ts`
- `frontend/src/lib/use-dev-mode.ts`
- `docs/ui/EVALUATION_ENVELOPE_BLUEPRINT.md`

## 3. Current Architecture State

Current runtime truth:

- FastAPI remains the backend and the separation stays additive
- `POST /app/evaluate` is still the primary Evaluate contract
- `POST /api/ocr/review` is still the OCR trust-gate contract
- persisted bet detail now safely exposes additive replay context even without evaluation-log enrichment
- the fallback frontend remains the actually previewable runtime
- the Next scaffold now has a real frontend normalization seam through `EvaluationEnvelope`
- Evaluate and OCR render through `EvaluationEnvelope`
- Builder and History can now derive `EvaluationEnvelope` views from saved handoff or replay data
- the new Next root page is a dev-console home instead of a blind redirect
- developer session state now has a shared storage layer for API base, auth token, and dev mode
- the Next routes now share a common console shell and page-header system
- Evaluate, OCR, Builder, and History all have first-pass route-level `mock` mode behavior

## 4. Latest Validation

Backend validation:

```bash
cd /Users/benaiahross/development/projects/betapp/app-src && \
uv run --project . pytest app/tests/test_bets_api.py -q
```

Result:

```text
13 passed
```

Frontend validation:

- Fallback server still serves on `http://localhost:3010`
- Updated fallback console HTML/CSS routes were verified by `curl`
- Full `next build` is still not available in this environment because package-install/runtime setup remains unhealthy

## 5. Known Debt

- final Next runtime is still blocked by package-manager/toolchain instability in this environment
- the fallback frontend is still the only reliable preview runtime
- route-level live/mock behavior exists, but the dashboard still needs clearer request/status tracing
- the active wake-up surfaces must be kept fresh before proving new-chat carry-over
- no full TypeScript/build verification was possible for the new Next work in this environment

## 6. Exact Next Step

Make the Next scaffold more operationally legible as a developer console.

Singular next move:

- add shared request/status tracing and route-visible mode controls so the dashboard explains what it is doing in `live` and `mock` modes

Parallel chat-side systems move:

- keep the active handoff and wake-up target fresh enough that a fresh chat can point at the real current work

## 7. Bootstrap Docs For Next Chat

Read in this order:

1. `docs/ops/BOOTSTRAP_PROTOCOL.md`
2. `docs/index/DOC_INDEX.md`
3. `docs/ops/CURRENT_EXECUTION_STATE.md`
4. `docs/ops/FRONTEND_BACKEND_CONTRACT_FREEZE_PHASE1.md`
5. `docs/ops/FRONTEND_BACKEND_DEPLOY_STATUS.md`
6. `docs/ops/FRONTEND_BACKEND_VISUAL_STATUS_MAP.md`
7. `docs/ui/EVALUATION_ENVELOPE_BLUEPRINT.md`
8. `docs/ui/SCREEN_COMPONENT_SPEC.md`
9. `docs/ui/FRONTEND_IMPLEMENTATION_SPEC.md`
10. `docs/ops/WHOLE_SYSTEM_PLAN.md`
11. `docs/ops/WORKING_MEMORY_MODULE.md`
12. `docs/ops/WORKING_MEMORY_HANDOFF_CONTRACT.md`
13. `docs/ops/NEW_CHAT_CARRYOVER_PROTOCOL.md`
14. `docs/ops/ACTIVE_WORKING_MEMORY_HANDOFF.yaml`
15. `docs/ops/ACTIVE_WAKEUP_TARGET.md`
16. `docs/ops/NEW_CHAT_WAKEUP_PROMPT_TEMPLATE.md`
17. `git -C /Users/benaiahross/development/projects/betapp/app-src status --short`
